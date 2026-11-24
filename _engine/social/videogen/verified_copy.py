"""Store-verified copy that overrides registry.py lines (stdlib only, no package imports).

registry.py is paired byte for byte with the iOS App Guide mirror
(_engine/social/videogen/registry.py, geo/owned_app_feeds.SOURCE_FILES), so it
stays identical to the guide until a back-to-back release updates both.  Until
then the store-verified copy for apps whose registry lines carried unverified
claims is applied on top of APPS: videogen/__init__.py applies it for every
consumer that imports ``videogen.registry``; loaders that read registry.py by
path (agent/app_directory_receipts.py) call apply() themselves.

mochi (App Store 6785004775): the App Store listing does not state "no ads",
"no account" or "no subscription"; it does state a Home Screen widget and Apple
Watch (2026-11-24 lookup).  Remove an entry once the guide mirror carries the
same values in registry.py.
"""

OVERRIDES = {
    "mochi": {
        "sub": "Cute, cozy checklists with a satisfying tap to complete",
        "tag": "Free to start · Apple Watch",
        "cta_bullets": ["Free to start", "Home Screen widget", "Apple Watch"],
    },
}


def apply(apps):
    """Update the registry APPS dict in place; returns it."""
    for key, fields in OVERRIDES.items():
        app = apps.get(key)
        if app is not None:
            app.update({name: (list(value) if isinstance(value, list) else value)
                        for name, value in fields.items()})
    return apps
