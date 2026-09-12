"""Shared mutation boundary for held WebSub, rssCloud and IndexNow releases."""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid

POLICY = Path(__file__).with_name("notification_policy.json")


def read_policy(path: Path = POLICY) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if (
        policy.get("schema") != "lumi.notification-release-policy/v1"
        or type(policy.get("notification_release_hold")) is not bool
        or set(policy.get("providers", [])) != {"websub", "rsscloud", "indexnow"}
    ):
        raise ValueError("Invalid notification release policy")
    return policy


def held_result(protocol: str, *, receipt_file: Path | None = None,
                source_sha: str | None = None, policy_path: Path = POLICY) -> dict | None:
    policy = read_policy(policy_path)
    if not policy["notification_release_hold"]:
        return None
    if protocol not in {"websub", "rsscloud", "indexnow", "owned-feeds"}:
        raise ValueError("Unknown held provider")
    result = {
        "schema": "lumi.notification-release-hold/v1",
        "notification_release_hold": True, "protocol": protocol,
        "source_sha": source_sha or os.environ.get("GITHUB_SHA"),
        "provider_intents": 0, "provider_requests": 0, "accepted_ack": 0,
        "subscriber_delivery_verified": False, "indexing_verified": False,
        "reason": policy["reason"],
    }
    if receipt_file is not None:
        path = Path(receipt_file)
        if path.is_symlink():
            raise ValueError("Hold receipt must not be a symlink")
        path.parent.mkdir(parents=True, exist_ok=True)
        staged = path.with_name(f".{path.name}.writing-{uuid.uuid4().hex}")
        fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(result, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, path)
        finally:
            staged.unlink(missing_ok=True)
    return result
