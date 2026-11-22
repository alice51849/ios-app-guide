"""Store-copy guard for an App whose store text is being resubmitted.

Pages are built from data/<app>_full.json, which mirrors the live App Store
text. While a resubmission is pending, the guard file holds a filtered copy
of the description, keywords and subtitle for each locale, together with the
recorded old value of each field (the description by SHA-256). Each field
is replaced only while its data value still equals that old value, so each
one retires on its own once its store text is updated and synced into data/. A missing or unreadable guard file changes nothing.
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD_PATH = os.path.join(HERE, "data", "store_copy_guard.json")


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


def guard_signature(path=None):
    path = GUARD_PATH if path is None else path
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (path, stat.st_mtime_ns, stat.st_size)


def guarded_locales(key, values, path=None):
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
    for locale, row in rows.items():
        current = values.get(locale)
        if not isinstance(current, dict) or not isinstance(row, dict):
            continue
        updated = dict(current)
        if "description" in row and _sha256(
            current.get("description", "")
        ) == row.get("old_sha256"):
            updated["description"] = row["description"]
        for field in ("keywords", "subtitle"):
            if field in row and current.get(field) == row.get(f"old_{field}"):
                updated[field] = row[field]
        if updated != current:
            result[locale] = updated
    return result
