#!/usr/bin/env python3
"""Copy/check the reviewed identity contract; never fetch or publish anything."""
from __future__ import annotations

import argparse
from pathlib import Path

from current_source import load_source


HERE = Path(__file__).resolve().parent
FILES = ("current_source.py", "live_app_manifest.json", "official_locales.py")


def synchronize(target: Path, *, layout: str, check: bool = False) -> dict:
    source = load_source()
    relative = {"guide": Path("_engine/geo"), "social": Path("."), "owned": Path("geo")}
    destination = target / relative[layout]
    expected = {name: (HERE / name).read_bytes() for name in FILES}
    mismatches = [
        name for name, content in expected.items()
        if not (destination / name).is_file()
        or (destination / name).read_bytes() != content
    ]
    if check and mismatches:
        raise ValueError(f"Current-source mirror drift at {destination}: {mismatches}")
    if not check:
        destination.mkdir(parents=True, exist_ok=True)
        for name in mismatches:
            (destination / name).write_bytes(expected[name])
    load_source(destination / "live_app_manifest.json")
    return {
        "source_sha256": source["source_sha256"],
        "apps": source["app_count"], "locales": source["locale_count"],
        "pairs": source["pair_count"], "changed_files": len(mismatches),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=("guide", "social", "owned"), required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = synchronize(args.target, layout=args.layout, check=args.check)
    print(
        f"Current source: {result['apps']} apps x {result['locales']} locales "
        f"= {result['pairs']}; sha256={result['source_sha256']}; "
        f"changed={result['changed_files']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
