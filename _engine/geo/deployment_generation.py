#!/usr/bin/env python3
"""Source-bound deployment generations; preparation is local, readback is GET-only.

The additive ``generation`` field does not change the legacy deployment/route
schemas. A legacy document remains readable, but is never generation-verified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


VERSION = 1
GENERATION_SCHEMA_VERSION = 2
DEPLOYMENT_PATH = ".well-known/deployment.json"
MANIFEST_PATH = "data/high-intent-decision-routes/expected-output-manifest.json"
CATALOG_PATH = "data/verified-ios-app-finder-catalog.json"
MAX_BYTES = 16 * 1024 * 1024
SOURCE_FIELDS = {
    "source_sha", "source_tree", "generator_digest", "dependency_lock_digest",
}
DIGEST_FIELDS = {
    "generator_digest", "dependency_lock_digest", "mirror_digest",
    "mirror_inputs_digest", "build_config_digest", "manifest_digest",
    "manifest_file_digest", "catalog_digest", "outputs_digest",
    "dependency_environment_digest",
}
LEGACY_GENERATION_FIELDS = SOURCE_FIELDS | DIGEST_FIELDS | {
    "schema_version", "scope", "pages_source_sha", "pages_source_tree",
    "run_id", "run_attempt", "generation_id",
}
GENERATION_ID_FIELDS = {
    "generation_id", "execution_generation_id", "measurement_generation_id",
}
GENERATION_FIELDS = LEGACY_GENERATION_FIELDS | GENERATION_ID_FIELDS
MEASUREMENT_FIELDS = SOURCE_FIELDS | {
    "dependency_environment_digest", "mirror_digest", "manifest_digest",
    "catalog_digest", "outputs_digest",
}


class GenerationError(ValueError):
    """Evidence cannot prove one immutable generation."""


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise GenerationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise GenerationError(f"non-finite JSON constant: {value}")


def parse_json(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_strict_object,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError) as error:
        raise GenerationError(f"invalid generation JSON: {error}") from error
    if not isinstance(value, dict):
        raise GenerationError("generation JSON must be an object")
    return value


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True,
        text=True, timeout=60,
    )
    if result.returncode:
        raise GenerationError(f"git {args[0]} failed in {root}")
    return result.stdout.strip()


def _repository(root: Path) -> tuple[str, str]:
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise GenerationError("source must be a separate repository root")
    return (
        _git(root, "rev-parse", "HEAD"),
        _git(root, "rev-parse", "HEAD^{tree}"),
    )


def _paths(root: Path, *specs: str) -> list[str]:
    return sorted(filter(None, _git(root, "ls-files", "-z", "--", *specs).split("\0")))


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str):
        raise GenerationError("manifest path must be a string")
    path = PurePosixPath(relative)
    if (
        not isinstance(relative, str) or not relative or path.is_absolute()
        or ".." in path.parts or "\\" in relative or path.as_posix() != relative
    ):
        raise GenerationError(f"unsafe manifest path: {relative!r}")
    result = root / relative
    if any((root / Path(*path.parts[:index])).is_symlink()
           for index in range(1, len(path.parts) + 1)):
        raise GenerationError(f"symlink in generation input: {relative}")
    if not result.is_file() or not result.resolve().is_relative_to(root.resolve()):
        raise GenerationError(f"missing generation input: {relative}")
    return result


def _files(root: Path, paths: list[str]) -> list[dict[str, str]]:
    return [
        {"path": relative, "sha256": hashlib.sha256(
            _safe_file(root, relative).read_bytes()
        ).hexdigest()}
        for relative in sorted(paths)
    ]


def source_identity(root: Path, *, mode: str = "prepare") -> dict[str, str]:
    """Preparation is pristine; consumers ignore unrelated working runtime state."""
    if mode not in {"prepare", "consumer"}:
        raise GenerationError("source identity mode must be prepare or consumer")
    root = root.resolve()
    revision, tree = _repository(root)
    # geo/pages is a separate output repository, not GrowthEngine source.
    status_args = (
        "status", "--porcelain=v1", "--untracked-files=all",
        "--ignore-submodules=all", "--",
        "." if mode == "prepare" else "geo", ":(exclude)geo/pages",
    )
    if _git(root, *status_args):
        raise GenerationError("GrowthEngine source is dirty; previous evidence is invalid")
    paths = _paths(root, "geo", ":(exclude)geo/pages")
    generators = [p for p in paths if p.endswith(".py")]
    locks = [p for p in paths if (
        Path(p).name.startswith("requirements") and p.endswith(".txt")
    ) or Path(p).name in {"uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json"}]
    if not generators or not locks:
        raise GenerationError("generator source or dependency lock is missing")
    result = {
        "source_sha": revision,
        "source_tree": tree,
        "generator_digest": digest(_files(root, generators)),
        "dependency_lock_digest": digest(_files(root, locks)),
    }
    if _repository(root) != (revision, tree) or _git(root, *status_args):
        raise GenerationError("GrowthEngine source changed while hashing")
    return result


def _runtime_input(relative: str) -> bool:
    # These are Guide-owned outputs/caches, not canonical source mirrors.
    # Their exact bytes are still bound by mirror_inputs_digest.
    path = PurePosixPath(relative)
    return (
        path.parts[0] in {"i18n_trans", "_demand", "reports"}
        or relative in {"sitemap_lastmod_state.json", "standard_site_sync_state.json"}
    )


def dependency_environment_digest() -> str:
    distributions = sorted(
        (distribution.metadata.get("Name", ""), distribution.version,
         hashlib.sha256((distribution.read_text("RECORD") or "").encode()).hexdigest(),
         hashlib.sha256((distribution.read_text("direct_url.json") or "").encode()).hexdigest())
        for distribution in importlib.metadata.distributions()
    )
    return digest({"python": sys.version, "distributions": distributions})


def build_identity(
    source_root: Path, site_root: Path, *, run_id: str, run_attempt: str,
    settings: dict[str, str],
) -> dict[str, Any]:
    if source_root.resolve() == site_root.resolve():
        raise GenerationError("GrowthEngine and Guide must be separate checkouts")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", run_id):
        raise GenerationError("run_id must explicitly identify this build")
    if not re.fullmatch(r"[1-9][0-9]*", run_attempt):
        raise GenerationError("run_attempt must be a positive integer")
    source = source_identity(source_root, mode="prepare")
    revision, tree = _repository(site_root)
    status_args = ("status", "--porcelain=v1", "--untracked-files=all",
                   "--", ".github", "_engine")
    if _git(site_root, *status_args):
        raise GenerationError("Guide build inputs are not the committed source")
    mirror_paths = _paths(site_root, "_engine/geo")
    if "_engine/geo/deployment_generation.py" not in mirror_paths:
        raise GenerationError("generation verifier is absent from the committed mirror")
    static = []
    runtime = []
    for entry in _files(site_root, mirror_paths):
        relative = entry["path"].removeprefix("_engine/geo/")
        if _runtime_input(relative):
            runtime.append(entry)
            continue
        canonical = _safe_file(source_root, f"geo/{relative}")
        if hashlib.sha256(canonical.read_bytes()).hexdigest() != entry["sha256"]:
            raise GenerationError(f"GrowthEngine → Guide mirror drift: {relative}")
        static.append(entry)
    config_paths = _paths(site_root, ".github", "_engine")
    result = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "scope": "high_intent_route_closure",
        **source,
        "pages_source_sha": revision,
        "pages_source_tree": tree,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "dependency_environment_digest": dependency_environment_digest(),
        "mirror_digest": digest(static),
        "mirror_inputs_digest": digest(runtime),
        "build_config_digest": digest({
            "files": _files(site_root, config_paths),
            "settings": settings,
        }),
    }
    if _repository(site_root) != (revision, tree) or _git(site_root, *status_args):
        raise GenerationError("Guide source changed while hashing")
    return result


def manifest_outputs(document: dict[str, Any]) -> list[dict[str, str]]:
    manifest_digest = document.get("manifest_digest")
    if manifest_digest != digest({
        key: value for key, value in document.items() if key != "manifest_digest"
    }):
        raise GenerationError("route manifest digest differs")
    outputs = document.get("expected_outputs")
    if not isinstance(outputs, list) or not outputs:
        raise GenerationError("route manifest has no expected outputs")
    result = []
    paths: set[str] = set()
    for row in outputs:
        if not isinstance(row, dict):
            raise GenerationError("invalid output manifest row")
        path, sha = row.get("relative_path"), row.get("generated_sha256")
        if (
            not isinstance(path, str) or not path or path in paths
            or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
            or "\\" in path or PurePosixPath(path).as_posix() != path
            or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
        ):
            raise GenerationError("unsafe or duplicate output manifest entry")
        paths.add(path)
        result.append({"path": path, "sha256": sha})
    return sorted(result, key=lambda row: row["path"])


def output_identity(site_root: Path) -> dict[str, str]:
    body = _safe_file(site_root, MANIFEST_PATH).read_bytes()
    manifest = parse_json(body)
    outputs = manifest_outputs(manifest)
    if _files(site_root, [row["path"] for row in outputs]) != outputs:
        raise GenerationError("generated output bytes differ from the manifest")
    return {
        "manifest_digest": manifest["manifest_digest"],
        "manifest_file_digest": hashlib.sha256(body).hexdigest(),
        "catalog_digest": hashlib.sha256(
            _safe_file(site_root, CATALOG_PATH).read_bytes()
        ).hexdigest(),
        "outputs_digest": digest(outputs),
    }


def seal_generation(identity: dict[str, Any], outputs: dict[str, str]) -> dict[str, Any]:
    generation = {
        key: value for key, value in {**identity, **outputs}.items()
        if key not in GENERATION_ID_FIELDS
    }
    generation["schema_version"] = GENERATION_SCHEMA_VERSION
    generation["measurement_generation_id"] = _measurement_digest(generation)
    execution_id = digest(generation)
    generation["execution_generation_id"] = execution_id
    generation["generation_id"] = execution_id
    validate_generation(generation)
    return generation


def validate_generation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationError("missing or unsupported deployment generation")
    version = value.get("schema_version")
    expected_fields = LEGACY_GENERATION_FIELDS if version == 1 else GENERATION_FIELDS
    if type(version) is not int or version not in {1, GENERATION_SCHEMA_VERSION} or set(value) != expected_fields:
        raise GenerationError("missing or unsupported deployment generation")
    identity_fields = {"generation_id"} if version == 1 else GENERATION_ID_FIELDS
    if (
        value["scope"] != "high_intent_route_closure"
        or any(not isinstance(value[key], str) or
               not re.fullmatch(r"[0-9a-f]{64}", value[key])
               for key in DIGEST_FIELDS | identity_fields)
        or any(not isinstance(value[key], str) or
               not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value[key])
               for key in {"source_sha", "source_tree", "pages_source_sha", "pages_source_tree"})
        or not isinstance(value["run_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value["run_id"])
        or not isinstance(value["run_attempt"], str)
        or not re.fullmatch(r"[1-9][0-9]*", value["run_attempt"])
    ):
        raise GenerationError("deployment generation is invalid")
    excluded = {"generation_id"}
    if version == GENERATION_SCHEMA_VERSION:
        excluded.add("execution_generation_id")
        if (
            value["measurement_generation_id"] != _measurement_digest(value)
            or value["generation_id"] != value["execution_generation_id"]
        ):
            raise GenerationError("deployment generation identities differ")
    if value["generation_id"] != digest({
        key: item for key, item in value.items() if key not in excluded
    }):
        raise GenerationError("deployment generation is invalid")
    return value


def _measurement_digest(value: dict[str, Any]) -> str:
    return digest({
        "measurement_contract_version": 1,
        "scope": value["scope"],
        "inputs": {key: value[key] for key in sorted(MEASUREMENT_FIELDS)},
    })


def lineage_ids(value: dict[str, Any]) -> dict[str, str]:
    validate_generation(value)
    return {
        "generation_id": value["generation_id"],
        "execution_generation_id": value.get("execution_generation_id", value["generation_id"]),
        "measurement_generation_id": value.get("measurement_generation_id", _measurement_digest(value)),
    }


def validate_binding(document: dict[str, Any]) -> dict[str, Any]:
    generation = validate_generation(document.get("generation"))
    if (
        document.get("source_commit") != generation["pages_source_sha"]
        or document.get("engine_source_revision") != generation["source_sha"]
        or document.get("route_manifest_digest") != generation["manifest_digest"]
    ):
        raise GenerationError("deployment aliases differ from its generation")
    return generation


def validate_current_source(
    generation: dict[str, Any], source_root: Path,
) -> dict[str, str]:
    validate_generation(generation)
    current = source_identity(source_root, mode="consumer")
    if any(current[key] != generation[key] for key in SOURCE_FIELDS):
        raise GenerationError("source changed; previous generation evidence is invalid")
    return current


def same_generation(*documents: dict[str, Any]) -> dict[str, Any]:
    if not documents:
        raise GenerationError("no generation evidence")
    expected = validate_binding(documents[0])
    if any(validate_binding(row) != expected for row in documents[1:]):
        raise GenerationError("cross-generation evidence is forbidden")
    return expected


def validate_receipt(
    receipt: dict[str, Any], deployment: dict[str, Any], *,
    source_root: Path | None = None,
) -> dict[str, Any]:
    generation = same_generation(receipt, deployment)
    if (
        receipt.get("schema_version") != VERSION
        or receipt.get("status") != "verified"
        or receipt.get("observation_method") != "https_get_exact_bytes"
        or receipt.get("receipt_digest") != digest({
            key: value for key, value in receipt.items() if key != "receipt_digest"
        })
        or not isinstance(receipt.get("observations"), list)
        or not receipt["observations"]
    ):
        raise GenerationError("invalid live readback receipt")
    for observation in receipt["observations"]:
        if (
            not isinstance(observation, dict)
            or observation.get("generation_id") != generation["generation_id"]
            or not isinstance(observation.get("checks"), list)
            or not observation["checks"]
            or observation.get("checks_digest") != digest(observation["checks"])
            or any(not isinstance(row, dict) or row.get("http_status") != 200
                   or row.get("method") != "GET" for row in observation["checks"])
        ):
            raise GenerationError("live observations mix generations or lack exact GETs")
    if source_root is not None:
        validate_current_source(generation, source_root)
    return generation


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pending")
    try:
        with staged.open("x", encoding="utf-8") as handle:
            os.chmod(staged, 0o600)
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def prepare(
    *, source_root: Path, site_root: Path, inventory: Path,
    source_commit: str, engine_source_revision: str, run_id: str, run_attempt: str,
) -> dict[str, Any]:
    settings = {
        "GEO_SITE": os.environ.get("GEO_SITE", ""),
        "APP_STORE_PROVIDER_TOKEN": os.environ.get("APP_STORE_PROVIDER_TOKEN", ""),
    }
    before = build_identity(source_root, site_root, run_id=run_id,
                            run_attempt=run_attempt, settings=settings)
    if (before["source_sha"] != engine_source_revision
            or before["pages_source_sha"] != source_commit):
        raise GenerationError("declared source SHA is not the checked-out source")
    import high_intent_decision_routes as routes

    routes.prepare_pages_deployment(
        site_root, inventory_path=inventory, source_path=routes.SOURCE_PATH,
        provider_token=settings["APP_STORE_PROVIDER_TOKEN"],
        source_commit=source_commit, current_source_root=source_root / "geo",
        engine_source_revision=engine_source_revision,
    )
    outputs = output_identity(site_root)
    after = build_identity(source_root, site_root, run_id=run_id,
                           run_attempt=run_attempt, settings=settings)
    if after != before:
        raise GenerationError("build inputs changed during generation")
    deployment = parse_json(_safe_file(site_root, DEPLOYMENT_PATH).read_bytes())
    deployment["generation"] = seal_generation(before, outputs)
    validate_binding(deployment)
    atomic_json(site_root / DEPLOYMENT_PATH, deployment)
    # The public artifact must remain readable by the Pages web server.
    (site_root / DEPLOYMENT_PATH).chmod(0o644)
    return deployment


def get_bytes(url: str, *, timeout: int, maximum: int) -> tuple[bytes, str, int]:
    request = Request(url, method="GET", headers={
        "Cache-Control": "no-cache", "User-Agent": "Lumi-Deployment-Generation/1",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(maximum + 1)
            result = body, response.geturl(), int(response.status)
    except (OSError, ValueError, HTTPException) as error:
        raise GenerationError(f"live GET failed: {url}") from error
    if len(body) > maximum:
        raise GenerationError("live GET exceeded byte limit")
    return result


def live_readback(
    deployment: dict[str, Any], *, sites: list[str], now: datetime,
    timeout: int = 20, fetch: Callable[..., tuple[bytes, str, int]] = get_bytes,
    source_root: Path | None = None,
) -> dict[str, Any]:
    generation = validate_binding(deployment)
    sites = [site.rstrip("/") for site in sites]
    if now.tzinfo is None or not sites or len(sites) != len(set(sites)):
        raise GenerationError("readback requires a timezone and distinct endpoints")
    if source_root is not None:
        validate_current_source(generation, source_root)
    observed_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    nonce = digest([generation["generation_id"], observed_at])
    observations = []

    def read(site: str, relative: str, phase: str) -> bytes:
        expected = f"{site.rstrip('/')}/{relative}"
        parsed = urlsplit(expected)
        if (parsed.scheme != "https" or not parsed.netloc or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise GenerationError("readback endpoints must be credential-free HTTPS URLs")
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path,
                         urlencode({"generation": nonce, "phase": phase}), ""))
        body, final_url, status = fetch(url, timeout=timeout, maximum=MAX_BYTES)
        final = urlsplit(final_url)
        if status != 200 or (
            final.scheme, final.netloc, final.path
        ) != (parsed.scheme, parsed.netloc, parsed.path):
            raise GenerationError(f"live GET status or endpoint drift: {relative}")
        return body

    for site in sites:
        before = read(site, DEPLOYMENT_PATH, "before")
        if parse_json(before) != deployment:
            raise GenerationError("live deployment is not the expected generation")
        manifest_body = read(site, MANIFEST_PATH, "manifest")
        if hashlib.sha256(manifest_body).hexdigest() != generation["manifest_file_digest"]:
            raise GenerationError("live manifest bytes belong to another generation")
        manifest = parse_json(manifest_body)
        outputs = manifest_outputs(manifest)
        for field in ("route_count", "app_count", "candidate_app_locale_pairs",
                      "abstained_pairs", "fallback_records", "source_contract_digest"):
            if (field in deployment or field in manifest) and deployment.get(field) != manifest.get(field):
                raise GenerationError(f"deployment/manifest contract drift: {field}")
        if (manifest["manifest_digest"] != generation["manifest_digest"]
                or digest(outputs) != generation["outputs_digest"]):
            raise GenerationError("live output manifest differs from the generation")
        checks = []
        for row in [*outputs, {"path": CATALOG_PATH, "sha256": generation["catalog_digest"]}]:
            body = read(site, row["path"], "output")
            actual = hashlib.sha256(body).hexdigest()
            if actual != row["sha256"]:
                raise GenerationError(f"live output digest drift: {row['path']}")
            checks.append({**row, "http_status": 200, "method": "GET"})
        observations.append({
            "site": site.rstrip("/"), "generation_id": generation["generation_id"],
            "observed_at": observed_at, "checks": checks,
            "checks_digest": digest(checks),
        })
        if read(site, DEPLOYMENT_PATH, "after") != before:
            raise GenerationError("deployment rolled over during live readback")
        if read(site, MANIFEST_PATH, "after") != manifest_body:
            raise GenerationError("manifest rolled over during live readback")
    # Bracket *all* origins, not just each origin separately.
    for site in sites:
        if parse_json(read(site, DEPLOYMENT_PATH, "final")) != deployment:
            raise GenerationError("deployment rolled over between origins")
        if hashlib.sha256(read(site, MANIFEST_PATH, "final")).hexdigest() != generation["manifest_file_digest"]:
            raise GenerationError("manifest rolled over between origins")
        if hashlib.sha256(read(site, CATALOG_PATH, "final")).hexdigest() != generation["catalog_digest"]:
            raise GenerationError("catalog rolled over during live readback")
    if source_root is not None:
        validate_current_source(generation, source_root)
    receipt = {
        "schema_version": VERSION, "status": "verified",
        "generated_at": observed_at, "generation": generation,
        "source_commit": deployment["source_commit"],
        "engine_source_revision": deployment["engine_source_revision"],
        "route_manifest_digest": deployment["route_manifest_digest"],
        "deployment_id": deployment["deployment_id"],
        "observation_method": "https_get_exact_bytes",
        "observations": observations,
    }
    receipt["receipt_digest"] = digest(receipt)
    validate_receipt(receipt, deployment)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("prepare")
    build.add_argument("--prepare-pages-deployment", action="store_true", required=True)
    build.add_argument("--current-source-root", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--inventory", type=Path, required=True)
    build.add_argument("--source-commit", required=True)
    build.add_argument("--engine-source-revision", required=True)
    build.add_argument("--run-id", required=True)
    build.add_argument("--run-attempt", required=True)
    live = sub.add_parser("verify-live")
    live.add_argument("--deployment", type=Path, required=True)
    live.add_argument("--receipt", type=Path, required=True)
    live.add_argument("--site", action="append", required=True)
    live.add_argument("--source-root", type=Path)
    live.add_argument("--attempts", type=int, default=1, choices=range(1, 31))
    live.add_argument("--retry-delay", type=int, default=10, choices=range(0, 61))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                source_root=args.current_source_root.resolve().parent,
                site_root=args.output_dir.resolve(), inventory=args.inventory,
                source_commit=args.source_commit,
                engine_source_revision=args.engine_source_revision,
                run_id=args.run_id, run_attempt=args.run_attempt,
            )
            print(f"Sealed generation: {result['generation']['generation_id']}")
            return 0
        deployment = parse_json(args.deployment.read_bytes())
        for attempt in range(args.attempts):
            try:
                result = live_readback(
                    deployment, sites=args.site, now=datetime.now(timezone.utc),
                    source_root=args.source_root,
                )
                atomic_json(args.receipt, result)
                print(f"Verified generation: {result['generation']['generation_id']}")
                return 0
            except (OSError, ValueError) as error:
                if attempt + 1 == args.attempts:
                    raise error
                time.sleep(args.retry_delay)
    except (OSError, GenerationError) as error:
        if args.command == "verify-live":
            atomic_json(args.receipt, {"schema_version": VERSION, "status": "blocked",
                                      "reason": str(error)})
        parser.exit(1, f"Deployment generation blocked: {error}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
