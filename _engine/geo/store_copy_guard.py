"""Store-copy guard for an App whose store text is being resubmitted.

Pages are built from data/<app>_full.json, which mirrors the live App Store
text. While a resubmission is pending, the guard file holds a filtered copy
of the description, keywords and subtitle for each locale, together with the
recorded old value of each field (the description by SHA-256). Each field
is replaced only while its data value still equals that old value, so each
one retires on its own once its store text is updated and synced into data/. A missing or unreadable guard file changes nothing.

promotionalText works like keywords/subtitle (exact old value). A locale row with
"while_duo_claim_paused": true applies only while aso/duo/claim_lines.json top-level
status starts with 暫停 (paused iPhone Duo claim, 11-21 coordinator item 53).
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD_PATH = os.path.join(HERE, "data", "store_copy_guard.json")
CLAIM_LINES_PATH = os.path.join(HERE, os.pardir, "aso", "duo", "claim_lines.json")


def _sha256(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def load_guard(path=None):
    path = GUARD_PATH if path is None else path
    try:
        with open(path, encoding="utf-8") as f:
            document = json.load(f)
    except (OSError, ValueError):
        return {}
    apps = document.get("apps") if isinstance(document, dict) else None
    return apps if isinstance(apps, dict) else {}


def duo_claim_paused(path=None):
    """True while claim_lines.json top-level status starts with 暫停; unreadable = not paused."""
    path = CLAIM_LINES_PATH if path is None else path
    try:
        with open(path, encoding="utf-8") as f:
            document = json.load(f)
    except (OSError, ValueError):
        return False
    status = document.get("status") if isinstance(document, dict) else None
    return str(status or "").strip().startswith("暫停")


def _stat(path):
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (path, stat.st_mtime_ns, stat.st_size)


def guard_signature(path=None):
    path = GUARD_PATH if path is None else path
    stat = _stat(path)
    if stat is None:
        return None
    return (*stat, _stat(CLAIM_LINES_PATH))


def guarded_locales(key, values, path=None, claim_lines_path=None):
    """Return values with each guarded field applied while it is still old.

    Description, keywords and subtitle are checked separately: each one is
    replaced only while its current value still equals the recorded old value
    (the description by SHA-256), so each field retires on its own once the
    store copy for that field is updated.
    """
    rows = load_guard(path).get(key)
    if not isinstance(rows, dict):
        return values
    result = dict(values)
    paused = None
    for locale, row in rows.items():
        current = values.get(locale)
        if not isinstance(current, dict) or not isinstance(row, dict):
            continue
        if row.get("while_duo_claim_paused"):
            if paused is None:
                paused = duo_claim_paused(claim_lines_path)
            if not paused:
                continue
        updated = dict(current)
        if "description" in row and _sha256(
            current.get("description", "")
        ) == row.get("old_sha256"):
            updated["description"] = row["description"]
        for field in ("keywords", "subtitle", "promotionalText"):
            if field in row and current.get(field) == row.get(f"old_{field}"):
                updated[field] = row[field]
        if updated != current:
            result[locale] = updated
    return result
