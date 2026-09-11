"""Reviewed external identities; never write these overrides back to ASC."""

from __future__ import annotations

INDIC_LOCALES = (
    "bn-BD", "gu-IN", "hi", "kn-IN", "ml-IN",
    "mr-IN", "or-IN", "pa-IN", "ta-IN", "te-IN",
)
TRIP_PLANET_NAME = "Trip Planet: Kids Quest"
TRIP_PLANET_ID = "6787193643"
TRIP_PLANET_ALIASES = (
    "Lumi Trip Planet: World Travel",
    "Lumi Trip Planet: यात्रा",
    "Lumi Trip Planet",
)

# External headlines have no ASC 30-character limit. Keep complete source
# words here instead of trying to repair every legitimate Indic final virama.
SOURCE_HEADLINES = {
    "lumimission": {
        "bn-BD": {"subtitle": "দৈনন্দিন রুটিন ও পুরস্কার চার্ট"},
        "or-IN": {"name": "Lumi Mission Planet: ଦୈନିକ ଅଭ୍ୟାସ"},
    },
    "gmoney": {
        "or-IN": {"subtitle": "ଯାତ୍ରା ମୁଦ୍ରା ଓ ଖର୍ଚ୍ଚ ନିୟନ୍ତ୍ରଣ"},
    },
}


def external_brand(key: str, locale: str, text: str) -> str:
    """Replace identity tokens only, preserving the surrounding native copy."""
    if key == "tripplanet" and locale in INDIC_LOCALES:
        for alias in TRIP_PLANET_ALIASES:
            text = text.replace(alias, TRIP_PLANET_NAME)
    return text


def external_identity(key: str, locale: str, attributes: dict) -> dict:
    values = dict(attributes)
    for field in ("name", "subtitle", "description", "promotionalText"):
        value = values.get(field)
        if isinstance(value, str):
            values[field] = external_brand(key, locale, value)
    values.update(SOURCE_HEADLINES.get(key, {}).get(locale, {}))
    if key == "tripplanet" and locale in INDIC_LOCALES:
        values["name"] = TRIP_PLANET_NAME
    return values


def registry_name(key: str, app_id: str, name: str) -> str:
    if key == "tripplanet":
        if app_id != TRIP_PLANET_ID:
            raise ValueError("Trip Planet App Store identity mismatch")
        return TRIP_PLANET_NAME
    return name
