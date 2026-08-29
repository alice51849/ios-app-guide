#!/usr/bin/env python3
"""Fail-closed unpacked-tree and tar gate for the exact Pages artifact."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import errno
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile
from typing import BinaryIO
import zipfile


DEFAULT_EXCLUDES = frozenset({".git", ".github"})
PLATFORM_UNPACKED_BYTES = 900_000_000
MIN_HEADROOM_BYTES = 30_000_000
MAX_UNPACKED_BYTES = PLATFORM_UNPACKED_BYTES - MIN_HEADROOM_BYTES
MAX_DEFLATE_UPLOAD_BYTES = 900_000_000
MAX_TAR_BYTES = 10_000_000_000
CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class TreeEntry:
    path: str
    kind: str
    size: int
    mode: int
    mtime_ns: int
    device: int
    inode: int
    links: int


def _root(path: Path) -> Path:
    try:
        root_lstat = path.lstat()
    except OSError as error:
        raise ValueError(f"Pages source is unavailable: {path}") from error
    if stat.S_ISLNK(root_lstat.st_mode):
        raise ValueError(f"Pages source root is a symlink: {path}")
    root = path.resolve()
    if not root.is_dir():
        raise ValueError(f"Pages source is not a directory: {root}")
    return root


def _excludes(values: list[str]) -> frozenset[str]:
    result = set(DEFAULT_EXCLUDES)
    for value in values:
        if (
            not value
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
        ):
            raise ValueError(f"Invalid excluded path component: {value!r}")
        result.add(value)
    return frozenset(result)


def _has_sparse_hole(path: Path, metadata: os.stat_result) -> bool:
    if metadata.st_size == 0:
        return False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        if hasattr(os, "SEEK_HOLE"):
            try:
                return os.lseek(descriptor, 0, os.SEEK_HOLE) < metadata.st_size
            except OSError as error:
                if error.errno not in {errno.EINVAL, errno.ENOTSUP}:
                    raise
        return metadata.st_blocks * 512 < metadata.st_size
    finally:
        os.close(descriptor)


def scan_tree(
    source_root: Path,
    *,
    excluded_components: frozenset[str] = DEFAULT_EXCLUDES,
) -> tuple[Path, dict[str, TreeEntry]]:
    root = _root(source_root)
    entries: dict[str, TreeEntry] = {}
    inodes: dict[tuple[int, int], str] = {}
    pending: list[tuple[Path, PurePosixPath]] = [(root, PurePosixPath())]
    while pending:
        directory, relative_directory = pending.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise ValueError(f"Cannot scan Pages directory: {directory}") from error
        for child in children:
            relative = relative_directory / child.name
            if any(part in excluded_components for part in relative.parts):
                continue
            path = relative.as_posix()
            if (
                path in entries
                or path.startswith("/")
                or "\\" in path
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise ValueError(f"Unsafe or duplicate Pages path: {path!r}")
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError as error:
                raise ValueError(f"Cannot stat Pages path: {path}") from error
            mode = metadata.st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"Pages source contains symlink: {path}")
            if stat.S_ISDIR(mode):
                kind = "directory"
                pending.append((Path(child.path), relative))
            elif stat.S_ISREG(mode):
                kind = "file"
                if metadata.st_nlink != 1:
                    raise ValueError(
                        f"Pages source contains hard-linked file: {path}"
                    )
                if _has_sparse_hole(Path(child.path), metadata):
                    raise ValueError(
                        f"Pages source contains sparse file: {path}"
                    )
                inode_key = (metadata.st_dev, metadata.st_ino)
                previous = inodes.get(inode_key)
                if previous is not None:
                    raise ValueError(
                        f"Pages source aliases one inode: {previous}, {path}"
                    )
                inodes[inode_key] = path
            else:
                raise ValueError(f"Pages source contains special file: {path}")
            entries[path] = TreeEntry(
                path=path,
                kind=kind,
                size=metadata.st_size if kind == "file" else 0,
                mode=stat.S_IMODE(mode),
                mtime_ns=metadata.st_mtime_ns,
                device=metadata.st_dev,
                inode=metadata.st_ino,
                links=metadata.st_nlink,
            )
    return root, entries


def _artifact_path(source_root: Path, artifact: Path) -> Path:
    if artifact.is_symlink():
        raise ValueError(f"Pages artifact is a symlink: {artifact}")
    resolved = artifact.parent.resolve() / artifact.name
    try:
        resolved.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise ValueError("Pages artifact must be outside the Pages source tree")
    return resolved


def _matches(entry: TreeEntry, metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_size == entry.size
        and metadata.st_mtime_ns == entry.mtime_ns
        and metadata.st_dev == entry.device
        and metadata.st_ino == entry.inode
        and metadata.st_nlink == 1
    )


def _open_source(root: Path, entry: TreeEntry) -> BinaryIO:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(root / entry.path, flags)
    except OSError as error:
        raise ValueError(f"Cannot open Pages file safely: {entry.path}") from error
    metadata = os.fstat(descriptor)
    if not _matches(entry, metadata):
        os.close(descriptor)
        raise ValueError(f"Pages file changed during artifact review: {entry.path}")
    return os.fdopen(descriptor, "rb")


def build_review_tar(
    source_root: Path,
    artifact: Path,
    *,
    excluded_components: frozenset[str] = DEFAULT_EXCLUDES,
) -> dict[str, int]:
    root, entries = scan_tree(
        source_root,
        excluded_components=excluded_components,
    )
    target = _artifact_path(root, artifact)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".pending",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            with tarfile.open(
                fileobj=handle,
                mode="w",
                format=tarfile.GNU_FORMAT,
            ) as archive:
                root_info = tarfile.TarInfo(".")
                root_info.type = tarfile.DIRTYPE
                root_info.mode = stat.S_IMODE(root.stat().st_mode)
                root_info.mtime = int(root.stat().st_mtime)
                archive.addfile(root_info)
                for path, entry in sorted(entries.items()):
                    info = tarfile.TarInfo(f"./{path}")
                    info.mode = entry.mode
                    info.mtime = entry.mtime_ns // 1_000_000_000
                    if entry.kind == "directory":
                        info.type = tarfile.DIRTYPE
                        archive.addfile(info)
                        continue
                    info.type = tarfile.REGTYPE
                    info.size = entry.size
                    with _open_source(root, entry) as source:
                        archive.addfile(info, source)
                        if not _matches(entry, os.stat(root / path, follow_symlinks=False)):
                            raise ValueError(
                                f"Pages file changed while archiving: {path}"
                            )
            handle.flush()
            os.fchmod(handle.fileno(), 0o644)
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "files": sum(entry.kind == "file" for entry in entries.values()),
        "directories": sum(
            entry.kind == "directory" for entry in entries.values()
        ),
        "unpacked_bytes": sum(entry.size for entry in entries.values()),
        "tar_bytes": target.stat().st_size,
    }


def _member_path(name: str) -> str:
    if name in {".", "./"}:
        return "."
    raw_name = name[:-1] if name.endswith("/") else name
    if (
        not raw_name.startswith("./")
        or "\\" in raw_name
        or "\x00" in raw_name
    ):
        raise ValueError(f"Unsafe Pages artifact path: {name!r}")
    relative = PurePosixPath(raw_name[2:])
    if (
        not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or any(0xD800 <= ord(character) <= 0xDFFF for character in name)
    ):
        raise ValueError(f"Unsafe Pages artifact path: {name!r}")
    canonical = relative.as_posix()
    if raw_name != f"./{canonical}":
        raise ValueError(f"Non-canonical Pages artifact path: {name!r}")
    return canonical


def _digest_stream(stream: BinaryIO) -> tuple[int, str]:
    import hashlib

    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(CHUNK_BYTES):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def _measure_upload_zip(artifact: Path) -> int:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            dir=artifact.parent,
            prefix=f".{artifact.name}.",
            suffix=".upload-measure.zip",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            archive.write(artifact, arcname="artifact.tar")
        return temporary.stat().st_size
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_artifact(
    source_root: Path,
    artifact: Path,
    *,
    excluded_components: frozenset[str] = DEFAULT_EXCLUDES,
    max_unpacked_bytes: int = MAX_UNPACKED_BYTES,
    max_deflate_upload_bytes: int = MAX_DEFLATE_UPLOAD_BYTES,
) -> dict[str, int]:
    if max_unpacked_bytes <= 0:
        raise ValueError("Pages unpacked byte limit must be positive")
    if max_unpacked_bytes > MAX_UNPACKED_BYTES:
        raise ValueError(
            f"Pages unpacked byte limit cannot exceed {MAX_UNPACKED_BYTES}"
        )
    if max_deflate_upload_bytes <= 0:
        raise ValueError("Pages deflate upload byte limit must be positive")
    root, entries = scan_tree(
        source_root,
        excluded_components=excluded_components,
    )
    unpacked_bytes = sum(entry.size for entry in entries.values())
    if unpacked_bytes > max_unpacked_bytes:
        raise ValueError(
            "Pages staging unpacked bytes exceed "
            f"{max_unpacked_bytes} bytes: {unpacked_bytes}"
        )
    target = _artifact_path(root, artifact)
    try:
        target_metadata = target.lstat()
    except OSError as error:
        raise ValueError(f"Pages artifact is unavailable: {target}") from error
    if (
        not stat.S_ISREG(target_metadata.st_mode)
        or target_metadata.st_nlink != 1
    ):
        raise ValueError("Pages artifact must be one regular, unlinked file")
    if target_metadata.st_size > MAX_TAR_BYTES:
        raise ValueError(
            f"Pages tar exceeds {MAX_TAR_BYTES} bytes: "
            f"{target_metadata.st_size}"
        )

    expected_paths = {".", *entries}
    seen: set[str] = set()
    last_end = 0
    try:
        with tarfile.open(target, mode="r:") as archive:
            for member in archive:
                if member.name.endswith("/") and not member.isdir():
                    raise ValueError(
                        f"Non-directory artifact member has slash: {member.name}"
                    )
                path = _member_path(member.name)
                if path in seen:
                    raise ValueError(f"Duplicate Pages artifact path: {path}")
                seen.add(path)
                last_end = max(
                    last_end,
                    member.offset_data
                    + ((member.size + 511) // 512) * 512,
                )
                if member.issym() or member.islnk():
                    raise ValueError(
                        f"Pages artifact contains link member: {path}"
                    )
                if member.issparse():
                    raise ValueError(
                        f"Pages artifact contains sparse member: {path}"
                    )
                if path == ".":
                    if not member.isdir():
                        raise ValueError("Pages artifact root is not a directory")
                    continue
                entry = entries.get(path)
                if entry is None:
                    raise ValueError(
                        f"Unexpected Pages artifact member: {path}"
                    )
                if entry.kind == "directory":
                    if not member.isdir():
                        raise ValueError(
                            f"Pages artifact type mismatch: {path}"
                        )
                    continue
                if not member.isfile() or member.size != entry.size:
                    raise ValueError(f"Pages artifact file mismatch: {path}")
                archived = archive.extractfile(member)
                if archived is None:
                    raise ValueError(f"Cannot read Pages artifact file: {path}")
                with _open_source(root, entry) as source:
                    source_size, source_digest = _digest_stream(source)
                    archived_size, archived_digest = _digest_stream(archived)
                if (
                    source_size != entry.size
                    or archived_size != entry.size
                    or source_digest != archived_digest
                    or not _matches(
                        entry,
                        os.stat(root / path, follow_symlinks=False),
                    )
                ):
                    raise ValueError(
                        f"Pages artifact content mismatch: {path}"
                    )
    except (tarfile.TarError, OSError, EOFError, UnicodeError) as error:
        raise ValueError(f"Cannot parse Pages artifact: {target}") from error
    if seen != expected_paths:
        missing = sorted(expected_paths - seen)
        raise ValueError(
            "Pages artifact is incomplete: " + ", ".join(missing[:8])
        )
    with target.open("rb") as handle:
        handle.seek(last_end)
        trailer = handle.read()
    if (
        len(trailer) < 1024
        or len(trailer) % 512
        or any(trailer)
    ):
        raise ValueError("Pages artifact has a corrupt or non-zero trailer")

    deflate_upload_bytes = _measure_upload_zip(target)
    if deflate_upload_bytes > max_deflate_upload_bytes:
        raise ValueError(
            "Pages deflate upload artifact exceeds "
            f"{max_deflate_upload_bytes} bytes: {deflate_upload_bytes}"
        )
    headroom_bytes = PLATFORM_UNPACKED_BYTES - unpacked_bytes
    if headroom_bytes < MIN_HEADROOM_BYTES:
        raise ValueError(
            f"Pages staging headroom is below {MIN_HEADROOM_BYTES}: "
            f"{headroom_bytes}"
        )
    return {
        "files": sum(entry.kind == "file" for entry in entries.values()),
        "directories": sum(
            entry.kind == "directory" for entry in entries.values()
        ),
        "unpacked_bytes": unpacked_bytes,
        "tar_bytes": target_metadata.st_size,
        "deflate_upload_bytes": deflate_upload_bytes,
        "headroom_bytes": headroom_bytes,
        "max_deflate_upload_bytes": max_deflate_upload_bytes,
        "max_unpacked_bytes": max_unpacked_bytes,
        "minimum_headroom_bytes": MIN_HEADROOM_BYTES,
        "platform_unpacked_bytes": PLATFORM_UNPACKED_BYTES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("tree", "artifact", "build-review"),
    )
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument(
        "--exclude-component",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--max-unpacked-bytes",
        type=int,
        default=MAX_UNPACKED_BYTES,
    )
    parser.add_argument(
        "--max-deflate-upload-bytes",
        type=int,
        default=MAX_DEFLATE_UPLOAD_BYTES,
    )
    args = parser.parse_args()
    excluded = _excludes(args.exclude_component)
    if args.mode == "tree":
        if args.max_unpacked_bytes > MAX_UNPACKED_BYTES:
            raise ValueError(
                "Pages unpacked byte limit cannot exceed "
                f"{MAX_UNPACKED_BYTES}"
            )
        _root_path, entries = scan_tree(
            args.site_root,
            excluded_components=excluded,
        )
        result = {
            "files": sum(
                entry.kind == "file" for entry in entries.values()
            ),
            "directories": sum(
                entry.kind == "directory" for entry in entries.values()
            ),
            "unpacked_bytes": sum(entry.size for entry in entries.values()),
        }
        if result["unpacked_bytes"] > args.max_unpacked_bytes:
            raise ValueError(
                "Pages staging unpacked bytes exceed "
                f"{args.max_unpacked_bytes} bytes: {result['unpacked_bytes']}"
            )
        result["max_unpacked_bytes"] = args.max_unpacked_bytes
        result["headroom_bytes"] = (
            PLATFORM_UNPACKED_BYTES - result["unpacked_bytes"]
        )
        if result["headroom_bytes"] < MIN_HEADROOM_BYTES:
            raise ValueError(
                "Pages staging headroom is below "
                f"{MIN_HEADROOM_BYTES}: {result['headroom_bytes']}"
            )
        result["minimum_headroom_bytes"] = MIN_HEADROOM_BYTES
        result["platform_unpacked_bytes"] = PLATFORM_UNPACKED_BYTES
    else:
        if args.artifact is None:
            parser.error("--artifact is required for artifact modes")
        if args.mode == "build-review":
            build_review_tar(
                args.site_root,
                args.artifact,
                excluded_components=excluded,
            )
        result = verify_artifact(
            args.site_root,
            args.artifact,
            excluded_components=excluded,
            max_unpacked_bytes=args.max_unpacked_bytes,
            max_deflate_upload_bytes=args.max_deflate_upload_bytes,
        )
    print("PAGES_ARTIFACT " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
