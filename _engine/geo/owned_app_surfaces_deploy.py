#!/usr/bin/env python3
"""Overlay only the reviewed discovery manifest on the currently deployed artifact."""
from __future__ import annotations

import argparse
import copy
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import tarfile

from owned_app_surfaces import OUTPUT, SCHEMA, SurfaceError, digest, discover, load_json, write_json
from site_config import PUBLIC_SITE


def current_baseline(deployments, statuses, *, repository, expected_run, current_run):
    prefix = f"https://github.com/{repository}/actions/runs/"
    for deployment in deployments:
        history = statuses(deployment["id"])
        if not history:
            raise SurfaceError("Newer deployment has no definitive status")
        status = history[0]
        log = (status.get("log_url") or "").rstrip("/") + "/"
        if log.startswith(f"{prefix}{current_run}/"):
            continue
        # A failure can occur after deploy-pages succeeded (e.g. in a notifier).
        # Never search past it and overwrite the live site with an older success.
        if status.get("state") != "success":
            raise SurfaceError("Newer deployment may already be live; baseline is ambiguous")
        if not log.startswith(f"{prefix}{expected_run}/"):
            raise SurfaceError("The current deployed baseline changed")
        return deployment["id"]
    raise SurfaceError("No definitive current deployment")


def tree_hashes(root):
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SurfaceError("Deployment artifact cannot contain symlinks")
        if path.is_file():
            with path.open("rb") as stream:
                hashes[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return hashes


def overlay(archive, manifest, output, *, roster=None, site=PUBLIC_SITE):
    archive, manifest, output = Path(archive), Path(manifest), Path(output)
    document = load_json(manifest)
    if (
        document.get("schema") != SCHEMA
        or document.get("coverage", {}).get("source_checks_passed") != 470
        or document.get("coverage", {}).get("native_reviewed_cells") != 470
        or document.get("coverage", {}).get("devto_eligible_cells") != 0
        or len(document.get("cells", [])) != 470
        or any(cell.get("owned_native") != "PASS_REVIEWED" for cell in document["cells"])
    ):
        raise SurfaceError("Only a complete, independently reviewed discovery may deploy")
    if output.exists():
        raise SurfaceError("Overlay output must be a new owner-specific directory")
    with tarfile.open(archive) as bundle:
        names = set()
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if (
                path.is_absolute() or ".." in path.parts or "\\" in member.name
                or not (member.isfile() or member.isdir())
                or (member.isfile() and path.as_posix() in names)
            ):
                raise SurfaceError("Unsafe or duplicate deployment archive member")
            names.add(path.as_posix())
        output.mkdir(parents=True)
        bundle.extractall(output, filter="data")
    before = tree_hashes(output)
    if not {"index.html", "robots.txt"} <= set(before):
        raise SurfaceError("Baseline is not a complete Pages artifact")
    for relative, expected in document["source_sha256"].items():
        if before.get(relative) != expected:
            raise SurfaceError(f"Deployed source changed; rebase discovery first: {relative}")
    actual, _ = discover(output, roster=roster, site=site)
    expected = copy.deepcopy(document)
    expected["coverage"]["native_reviewed_cells"] = 0
    for cell in expected["cells"]:
        cell["owned_native"] = "NOT_REVIEWED"
    if actual != expected:
        raise SurfaceError("Deployed sitemap/task-page discovery differs from the reviewed source")
    destination = output / OUTPUT
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, destination)
    after = tree_hashes(output)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(name for name in before.keys() & after.keys() if before[name] != after[name])
    if removed or (set(added) | set(changed)) - {OUTPUT}:
        raise SurfaceError("Owned deployment attempted to change another owner's files")
    return {
        "schema": "lumi.owned-app-surfaces-overlay/v1",
        "baseline_tree_digest": digest(before), "result_tree_digest": digest(after),
        "unchanged_files": sum(after.get(name) == value for name, value in before.items()),
        "added_files": added, "updated_files": changed, "removed_files": removed,
        "only_allowed_public_path": OUTPUT,
        "all_other_bytes_preserved": True,
        "baseline_discovery_digest": digest(actual),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    result = overlay(args.archive, args.manifest, args.output)
    write_json(args.evidence, result)
    print(f"Preserved {result['unchanged_files']} files; changed only {OUTPUT}")


if __name__ == "__main__":
    main()
