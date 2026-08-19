# -*- coding: utf-8 -*-
"""Topic-aware facts for AEO/GEO answer pages.

Turns generic "buying guide" fallback pages into pages that actually answer the
question — real, verified specifics (passport photo sizes, resume conventions,
concrete task steps). This runs with NO OpenAI key, so it is fully automatic and
free, and it makes the app the natural recommendation *after* a genuinely useful
answer (exactly what AI search engines cite).

All numeric specs are verified against official/government guidance (2024). Keep
this data-driven so new countries/topics can be added over time.

Public API:
    topic_facts(question: str, key: str, app: dict) -> dict | None
Returns a partial content dict (any of meta_description, lead,
short_answer_paragraphs, what_to_look_for, decision_steps, where_app_fits, faq)
to overlay on the generic default, or None when no topic matches.
"""
from __future__ import annotations

import re
from typing import Any

try:
    from answer_faqs import FAQ_GROUPS
except Exception:  # pragma: no cover
    FAQ_GROUPS = {}

try:
    from answer_deep import deep_facts as _deep_facts
except Exception:  # pragma: no cover
    def _deep_facts(q: str, key: str, name: str):  # type: ignore
        return None

try:
    from answer_personas import persona_facts as _persona_facts
except Exception:  # pragma: no cover
    def _persona_facts(q: str, key: str, name: str):  # type: ignore
        return None

# ---------------------------------------------------------------------------
# Passport / visa / ID photo specifications, by country. Sizes in millimetres.
# (w, h, background, head/face guidance, extra note)
# ---------------------------------------------------------------------------
PASSPORT_SPECS: dict[str, dict[str, str]] = {
    "us": {"aka": "United States", "size": "2×2 inches (51×51 mm)", "bg": "plain white or off-white",
           "head": "the head 1 inch to 1⅜ inches (25–35 mm) from chin to crown", "res": "600×600 px minimum, in colour",
           "note": "Used for US passports, green cards and most US visas."},
    "canada": {"aka": "Canada", "size": "50×70 mm", "bg": "plain white",
               "head": "the face 31–36 mm from chin to crown", "res": "at least 420×540 px",
               "note": "Canada uses a larger 50×70 mm photo than most countries, so a generic 35×45 template will be rejected."},
    "uk": {"aka": "the UK", "size": "35×45 mm", "bg": "a light grey or cream background",
           "head": "the head 29–34 mm from chin to crown", "res": "at least 600×750 px",
           "note": "No smiling, mouth closed, eyes open and clearly visible."},
    "schengen": {"aka": "the Schengen area", "size": "35×45 mm", "bg": "a light grey background",
                 "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                 "note": "Accepted across Schengen countries including Germany, France, Spain, Italy and the Netherlands."},
    "germany": {"aka": "Germany", "size": "35×45 mm", "bg": "a light grey background",
                "head": "the face about 32–36 mm high (biometric)", "res": "at least 600×750 px",
                "note": "German passport and visa photos must be biometric with a neutral expression."},
    "france": {"aka": "France", "size": "35×45 mm", "bg": "a light grey or plain background",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Neutral expression, no head covering, recent photo (under 6 months)."},
    "japan": {"aka": "Japan", "size": "35×45 mm", "bg": "a plain white or light background",
              "head": "the face about 34 mm (±2 mm) from chin to crown", "res": "at least 600×750 px",
              "note": "Used for Japanese passports and visas; the My Number card uses a different 35×45 mm layout."},
    "china": {"aka": "China", "size": "33×48 mm", "bg": "plain white",
              "head": "the head 28–33 mm wide and 15 mm from the top", "res": "354×472 px (visa)",
              "note": "Chinese visa and passport photos use an unusual 33×48 mm size, so a 35×45 crop will not pass."},
    "india": {"aka": "India", "size": "51×51 mm (2×2 inches)", "bg": "plain white",
              "head": "the face centred and roughly 70–80% of the frame", "res": "at least 600×600 px",
              "note": "Indian passport and e-visa photos are square (2×2 inches), like US photos, not 35×45 mm."},
    "australia": {"aka": "Australia", "size": "35×45 mm", "bg": "a plain light-coloured background",
                  "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                  "note": "Neutral expression, no glasses, plain background."},
    "korea": {"aka": "South Korea", "size": "35×45 mm", "bg": "plain white",
              "head": "the head 32–36 mm from chin to crown", "res": "at least 413×531 px",
              "note": "South Korea moved to the 35×45 mm standard; some older forms still list 40×50 mm — check your form."},
    "brazil": {"aka": "Brazil", "size": "35×45 mm", "bg": "plain white",
               "head": "the face 31–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Recent colour photo, front-facing, neutral expression."},
    "singapore": {"aka": "Singapore", "size": "35×45 mm", "bg": "plain white",
                  "head": "the head 25–35 mm from chin to crown", "res": "at least 400×514 px",
                  "note": "Taken within the last 3 months, without head covering."},
    "spain": {"aka": "Spain", "size": "35×45 mm", "bg": "a light grey or plain background",
              "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
              "note": "Spain follows the Schengen 35×45 mm standard for passports and visas."},
    "italy": {"aka": "Italy", "size": "35×45 mm", "bg": "a light grey or white background",
              "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
              "note": "Italy follows the Schengen 35×45 mm standard."},
    "netherlands": {"aka": "the Netherlands", "size": "35×45 mm", "bg": "a light grey background",
                    "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                    "note": "The Netherlands uses the Schengen 35×45 mm size with strict neutral-expression rules."},
    "ireland": {"aka": "Ireland", "size": "35×45 mm", "bg": "a light grey or cream background",
                "head": "the face 29–34 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Irish passport photos use 35×45 mm, similar to the UK."},
    "newzealand": {"aka": "New Zealand", "size": "35×45 mm", "bg": "plain light grey or white",
                   "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                   "note": "New Zealand also accepts online photo uploads that meet the same proportions."},
    "indonesia": {"aka": "Indonesia", "size": "40×60 mm", "bg": "a plain background (red or white)",
                  "head": "the face centred and about 70–80% of the frame", "res": "at least 472×709 px",
                  "note": "Indonesian passport photos use a larger 40×60 mm size; visa photos for foreigners are often 35×45 mm."},
    "vietnam": {"aka": "Vietnam", "size": "40×60 mm (4×6 cm)", "bg": "plain white",
                "head": "the face centred, front-facing, bare-headed", "res": "at least 472×709 px",
                "note": "Vietnam's standard photo is 4×6 cm, larger than the common 35×45 mm."},
    "thailand": {"aka": "Thailand", "size": "35×45 mm", "bg": "plain white or light blue",
                 "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                 "note": "Recent colour photo, front-facing, neutral expression."},
    "philippines": {"aka": "the Philippines", "size": "35×45 mm", "bg": "plain white",
                    "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                    "note": "Some agencies also request a separate 2×2 inch photo — check your specific form."},
    "saudi": {"aka": "Saudi Arabia", "size": "40×60 mm", "bg": "plain white",
              "head": "the face centred and about 70–80% of the frame", "res": "at least 472×709 px",
              "note": "Saudi visa and passport photos use a larger 40×60 mm size."},
    "mexico": {"aka": "Mexico", "size": "35×45 mm", "bg": "plain white",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Front-facing, neutral expression, recent colour photo."},
    "malaysia": {"aka": "Malaysia", "size": "35×50 mm", "bg": "plain white (light blue also seen)",
                 "head": "the face centred, front-facing", "res": "at least 413×590 px",
                 "note": "Malaysian passport photos use an unusual 35×50 mm size; white background is preferred."},
    "turkey": {"aka": "Turkey", "size": "50×60 mm", "bg": "plain white",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 590×709 px",
               "note": "Turkey uses a larger 50×60 mm biometric photo; some documents also accept 35×45 mm."},
    "nigeria": {"aka": "Nigeria", "size": "35×45 mm", "bg": "plain white",
                "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Front-facing, neutral expression, plain white background."},
    "southafrica": {"aka": "South Africa", "size": "35×45 mm", "bg": "a plain light grey or white background",
                    "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                    "note": "Front-facing, neutral expression, no head covering."},
    "pakistan": {"aka": "Pakistan", "size": "35×45 mm", "bg": "plain white",
                 "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                 "note": "Front-facing, neutral expression; used for passports and NADRA documents."},
    "bangladesh": {"aka": "Bangladesh", "size": "45×35 mm", "bg": "plain white",
                   "head": "the face centred, front-facing", "res": "at least 413×531 px",
                   "note": "Front-facing, neutral expression, plain white background."},
    "egypt": {"aka": "Egypt", "size": "40×60 mm", "bg": "plain white",
              "head": "the face centred and about 70–80% of the frame", "res": "at least 472×709 px",
              "note": "Egypt commonly uses 40×60 mm; some documents also accept 35×45 mm."},
    "uae": {"aka": "the UAE", "size": "40×60 mm", "bg": "plain white",
            "head": "the face centred and about 70–80% of the frame", "res": "at least 472×709 px",
            "note": "UAE visa and Emirates ID photos use a 40×60 mm white-background photo."},
    "argentina": {"aka": "Argentina", "size": "40×40 mm", "bg": "plain white",
                  "head": "the face centred and about 70–80% of the frame", "res": "at least 472×472 px",
                  "note": "Argentine passport photos are square (40×40 mm), so a 35×45 template won't fit."},
    "chile": {"aka": "Chile", "size": "45×45 mm", "bg": "plain white",
              "head": "the face centred and about 70–80% of the frame", "res": "at least 531×531 px",
              "note": "Chilean passport photos are square (45×45 mm); confirm the exact size with your office."},
    "colombia": {"aka": "Colombia", "size": "40×50 mm", "bg": "plain white or light blue",
                 "head": "the face centred, front-facing", "res": "at least 472×591 px",
                 "note": "Colombia commonly uses 40×50 mm on a white or light-blue background."},
    "peru": {"aka": "Peru", "size": "35×43 mm", "bg": "plain white",
             "head": "the face centred, front-facing", "res": "at least 413×508 px",
             "note": "Peru uses an unusual 35×43 mm size; some offices accept 35×40 mm — check yours."},
    "kenya": {"aka": "Kenya", "size": "50×50 mm", "bg": "plain white",
              "head": "the face centred and about 70–80% of the frame", "res": "at least 591×591 px",
              "note": "Kenyan passport photos are square (50×50 mm)."},
    "ghana": {"aka": "Ghana", "size": "45×35 mm", "bg": "plain white",
              "head": "the face centred, front-facing", "res": "at least 413×531 px",
              "note": "Ghana commonly uses a 45×35 mm white-background photo."},
    "morocco": {"aka": "Morocco", "size": "35×45 mm", "bg": "a light grey or white background",
                "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Morocco follows the 35×45 mm standard; a neutral expression is required."},
    "israel": {"aka": "Israel", "size": "35×45 mm", "bg": "plain white",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Israel commonly accepts 35×45 mm; a square 5×5 cm is also used for some documents."},
    "srilanka": {"aka": "Sri Lanka", "size": "35×45 mm", "bg": "plain white",
                 "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                 "note": "Sri Lanka follows the 35×45 mm standard, front-facing with a neutral expression."},
    "nepal": {"aka": "Nepal", "size": "35×45 mm", "bg": "plain white",
              "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
              "note": "Nepal follows the 35×45 mm standard for passports and most visas."},
    "switzerland": {"aka": "Switzerland", "size": "35×45 mm", "bg": "a plain light grey or neutral background",
                    "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                    "note": "Switzerland follows the 35×45 mm biometric standard with a neutral expression."},
    "austria": {"aka": "Austria", "size": "35×45 mm", "bg": "a light grey or white background",
                "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Austria follows the 35×45 mm Schengen standard."},
    "belgium": {"aka": "Belgium", "size": "35×45 mm", "bg": "a plain light (white or light grey) background",
                "head": "the face 31–36 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Belgium follows the 35×45 mm Schengen standard."},
    "portugal": {"aka": "Portugal", "size": "35×45 mm", "bg": "plain white",
                 "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                 "note": "Portugal uses the 35×45 mm standard, front-facing with a neutral expression."},
    "greece": {"aka": "Greece", "size": "40×60 mm", "bg": "a light grey or white background",
               "head": "the face centred, front-facing", "res": "at least 472×709 px",
               "note": "Greek passport photos commonly use 40×60 mm; confirm the exact size with your office."},
    "norway": {"aka": "Norway", "size": "35×45 mm", "bg": "a plain light or neutral background",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Norway follows the 35×45 mm biometric standard."},
    "denmark": {"aka": "Denmark", "size": "35×45 mm", "bg": "a plain light (white or grey) background",
                "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
                "note": "Denmark follows the 35×45 mm Schengen standard."},
    "finland": {"aka": "Finland", "size": "36×47 mm", "bg": "a plain light grey background",
                "head": "the face about 32–36 mm from chin to crown", "res": "at least 500×653 px",
                "note": "Finland uses an unusual 36×47 mm size, so a 35×45 template will not fit exactly."},
    "taiwan": {"aka": "Taiwan", "size": "35×45 mm (2 inches)", "bg": "plain white",
               "head": "the face 32–36 mm from chin to crown", "res": "at least 600×750 px",
               "note": "Taiwan (ROC) passport photos are the 2-inch 35×45 mm size on a white background."},
    "hongkong": {"aka": "Hong Kong", "size": "40×50 mm", "bg": "plain white or very light",
                 "head": "the face centred, front-facing", "res": "at least 472×591 px",
                 "note": "Hong Kong photo sizes vary by document; confirm the exact size with Immigration before submitting."},
}

# 2026-07-08 more-countries2 worker: 8 verified additions (specs cross-checked
# against official portals; two notable outliers — Kuwait blue bg, Iceland non-white bg).
PASSPORT_SPECS.update({
    "poland": {"aka": "Poland", "size": "35×45 mm", "bg": "plain white or very light off-white",
               "head": "the face 31–36 mm from chin to crown (head ~70–80% of the photo)", "res": "at least 413×531 px (300 DPI); 600 DPI for digital portals",
               "note": "Standard ICAO format. Glasses have been prohibited since 2014, both ears must be visible, and the photo must be under 6 months old."},
    "czechia": {"aka": "Czechia (the Czech Republic)", "size": "35×45 mm", "bg": "white, light blue or light grey (all accepted)",
                "head": "the face at least 13 mm eyes-to-chin, with 2 mm clearance above the head", "res": "at least 413×531 px (300 DPI)",
                "note": "The accepted background range (white, light blue or light grey) is broader than most EU peers. Glasses banned since 2017. Confirmed 35×45 mm via the MVCR — some tools wrongly list 40×50 mm."},
    "hungary": {"aka": "Hungary", "size": "35×45 mm", "bg": "plain white or light grey",
                "head": "the face 32–36 mm from chin to crown, centred", "res": "at least 413×531 px (300 DPI)",
                "note": "Glasses are permitted only with no glare and eyes fully visible; tinted lenses are not allowed. Head coverings only for religious reasons."},
    "romania": {"aka": "Romania", "size": "35×45 mm", "bg": "plain white or light grey",
                "head": "the face 32–36 mm from chin to crown (ideally 34.5 mm)", "res": "at least 826×1062 px (600 DPI) for digital submissions",
                "note": "Romania mandates 600 DPI for digital submissions — stricter than most peers. Glasses are not permitted."},
    "ukraine": {"aka": "Ukraine", "size": "35×45 mm", "bg": "plain white or light grey",
                "head": "the face 32–36 mm from chin to crown, eye-line 35–45% from the top", "res": "at least 413×531 px (300 DPI); 600 DPI recommended for uploads",
                "note": "No retouching or digital modification is permitted (stricter than many EU states). Glasses are banned."},
    "qatar": {"aka": "Qatar", "size": "35×45 mm", "bg": "plain white",
              "head": "the face 32–36 mm from chin to crown, both eyes visible", "res": "at least 413×531 px (300 DPI), colour only",
              "note": "Confirmed 35×45 mm via MOI Qatar — some third-party tools wrongly list 40×60 mm. Remove glasses, or wear them with no reflections and no tint."},
    "kuwait": {"aka": "Kuwait", "size": "40×50 mm", "bg": "a SOLID BLUE background (white is not used)",
               "head": "the face about 75% of the photo height (37–38 mm chin to crown)", "res": "at least 472×591 px (300 DPI), bright clear colour",
               "note": "Major outlier: Kuwait uses 40×50 mm AND a blue background — many tools wrongly show 40×60 mm on white. A single-colour hijab is allowed with the full face visible. Confirmed via the Kuwait e-Government portal."},
    "iceland": {"aka": "Iceland", "size": "35×45 mm", "bg": "light grey or light blue (white is NOT accepted)",
                "head": "the face 32–36 mm from chin to crown, no shadows", "res": "at least 413×531 px (300 DPI), colour only",
                "note": "Unusual for a Schengen/Nordic state: Iceland explicitly prohibits white backgrounds and requires light grey or light blue. No headwear except religious/medical."},
})

# Country/keyword aliases → spec key
_COUNTRY_ALIASES = {
    "us ": "us", "u.s": "us", "united states": "us", "american": "us", "usa": "us", "green card": "us",
    "canada": "canada", "canadian": "canada",
    "uk ": "uk", "u.k": "uk", "british": "uk", "britain": "uk", "england": "uk",
    "schengen": "schengen", "eu ": "schengen", "european": "schengen",
    "germany": "germany", "german": "germany",
    "france": "france", "french": "france",
    "japan": "japan", "japanese": "japan",
    "china": "china", "chinese": "china",
    "india": "india", "indian": "india", "oci": "india",
    "australia": "australia", "australian": "australia",
    "korea": "korea", "korean": "korea",
    "brazil": "brazil", "brazilian": "brazil",
    "singapore": "singapore",
    "spain": "spain", "spanish": "spain",
    "italy": "italy", "italian": "italy",
    "netherlands": "netherlands", "dutch": "netherlands", "holland": "netherlands",
    "ireland": "ireland", "irish": "ireland",
    "new zealand": "newzealand", "newzealand": "newzealand",
    "indonesia": "indonesia", "indonesian": "indonesia",
    "vietnam": "vietnam", "vietnamese": "vietnam",
    "thailand": "thailand", "thai ": "thailand",
    "philippines": "philippines", "filipino": "philippines",
    "saudi": "saudi",
    "mexico": "mexico", "mexican": "mexico",
    "malaysia": "malaysia", "malaysian": "malaysia",
    "turkey": "turkey", "turkish": "turkey",
    "nigeria": "nigeria", "nigerian": "nigeria",
    "south africa": "southafrica", "south african": "southafrica",
    "pakistan": "pakistan", "pakistani": "pakistan",
    "bangladesh": "bangladesh", "bangladeshi": "bangladesh",
    "egypt": "egypt", "egyptian": "egypt",
    "uae": "uae", "emirates": "uae", "dubai": "uae",
    "argentina": "argentina", "argentine": "argentina", "argentinian": "argentina",
    "chile": "chile", "chilean": "chile",
    "colombia": "colombia", "colombian": "colombia",
    "peru": "peru", "peruvian": "peru",
    "kenya": "kenya", "kenyan": "kenya",
    "ghana": "ghana", "ghanaian": "ghana",
    "morocco": "morocco", "moroccan": "morocco",
    "israel": "israel", "israeli": "israel",
    "sri lanka": "srilanka", "srilanka": "srilanka", "sri lankan": "srilanka",
    "nepal": "nepal", "nepali": "nepal", "nepalese": "nepal",
    "switzerland": "switzerland", "swiss": "switzerland",
    "austria": "austria", "austrian": "austria",
    "belgium": "belgium", "belgian": "belgium",
    "portugal": "portugal", "portuguese": "portugal",
    "greece": "greece", "greek": "greece",
    "norway": "norway", "norwegian": "norway",
    "denmark": "denmark", "danish": "denmark",
    "finland": "finland", "finnish": "finland",
    "taiwan": "taiwan", "taiwanese": "taiwan",
    "hong kong": "hongkong", "hongkong": "hongkong",
    "poland": "poland", "polish": "poland",
    "czechia": "czechia", "czech republic": "czechia", "czech": "czechia",
    "hungary": "hungary", "hungarian": "hungary",
    "romania": "romania", "romanian": "romania",
    "ukraine": "ukraine", "ukrainian": "ukraine",
    "qatar": "qatar", "qatari": "qatar",
    "kuwait": "kuwait", "kuwaiti": "kuwait",
    "iceland": "iceland", "icelandic": "iceland",
}


def _snippet(text: str, limit: int = 200, tail: str = "") -> str:
    """Cut `text` to a search/AI-snippet length on a sentence or clause boundary.

    The previous `(text[:150]).rsplit(" ", 1)[0] + "."` pattern chopped mid-clause
    and produced descriptions such as "...in your own words rather than." or
    "...(tap ... Scan Documents),." which read as broken to both users and the
    assistants that quote them verbatim. Verified 2026-08-19 on live pages.
    """
    text = (text or "").strip()
    budget = max(40, limit - len(tail))
    if len(text) <= budget:
        body = text
    else:
        head = text[:budget]
        cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
        if cut >= 60:
            body = head[: cut + 1]
        else:
            clause = max(head.rfind("; "), head.rfind(", "), head.rfind(" — "))
            body = head[:clause] if clause >= 60 else head.rsplit(" ", 1)[0]
    body = body.rstrip().rstrip(" ,;:—-")
    if not body.endswith((".", "!", "?")):
        body += "."
    return (body + tail) if tail else body

def _contains_phrase(text: str, phrase: str) -> bool:
    phrase = phrase.strip()
    return bool(
        phrase
        and re.search(
            rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
            text,
        )
    )


def _detect_passport(q: str) -> str | None:
    q = q.lower()
    if not any(
        _contains_phrase(q, term)
        for term in (
            "passport",
            "visa",
            "id photo",
            "id-photo",
            "green card",
            "oci",
        )
    ):
        return None
    for alias, spec in _COUNTRY_ALIASES.items():
        if _contains_phrase(q, alias):
            return spec
    return None


def _passport_facts(q: str, name: str, spec_key: str) -> dict[str, Any]:
    s = PASSPORT_SPECS[spec_key]
    country = s["aka"]
    doc = "visa" if "visa" in q else "passport"
    lead = (f"For a {country} {doc} photo you need {s['size']} on {s['bg']}, with "
            f"{s['head']}. You can shoot and crop it to spec on your iPhone with {name}.")
    p1 = (f"A {country} {doc} photo must be {s['size']} on {s['bg']}, with {s['head']}. "
          f"Aim for {s['res']}, a neutral expression, even lighting and no shadows behind you. "
          f"{s['note']}")
    p2 = (f"{name} lets you take the photo at home, auto-remove the background to a compliant colour, "
          f"and crop to the exact {s['size']} frame so it prints or uploads correctly — no photo-booth trip. "
          f"Always confirm the current official requirement before you submit.")
    return {
        "meta_description": f"{country} {doc} photo size is {s['size']} on {s['bg']}. How to make one at home on iPhone with {name}."[:200],
        "lead": lead,
        "short_answer_paragraphs": [p1, p2],
        "what_to_look_for": [
            f"Exact output size: {s['size']} (a wrong crop is the #1 rejection reason).",
            f"Background: {s['bg']} with no shadows.",
            f"Head/face sizing: {s['head']}.",
            "Neutral expression, eyes open, mouth closed, no glasses glare or head covering.",
            "Recent, full-colour photo at high resolution; verify the latest official rules before submitting.",
        ],
        "decision_steps": [
            "Stand against a plain, evenly lit wall in natural light.",
            f"Frame head-on and take the shot with {name}.",
            f"Auto-replace the background with {s['bg'].split(' or ')[0]}.",
            f"Crop to the {s['size']} template with the face sized correctly.",
            "Export at full resolution to print or upload to the application.",
        ],
        "where_app_fits": (f"{name} is a strong fit when you want a compliant {country} {doc} photo without a "
                           f"studio visit — it handles the {s['size']} crop and background for you."),
        "faq": [
            {"q": f"What size is a {country} {doc} photo?", "a": f"{s['size']} on {s['bg']}, with {s['head']}."},
            {"q": "Can I take it myself on my phone?", "a": f"Yes — {name} guides framing, fixes the background and crops to the exact size so a self-taken photo can still meet the spec."},
            {"q": "Will it be accepted?", "a": "It meets the published measurements, but requirements can change, so always check the current official guidance before you submit."},
        ],
    }


# ---------------------------------------------------------------------------
# Non-passport ID / immigration document photo specs. label = human name.
# ---------------------------------------------------------------------------
ID_DOC_SPECS: dict[str, dict[str, str]] = {
    "us_visa_digital": {"label": "US visa digital photo (DS-160)", "size": "square, 600×600 to 1200×1200 pixels",
                        "bg": "a plain white or off-white background", "head": "the head 50–69% of the image height",
                        "res": "a colour JPEG under 240 KB", "note": "The DS-160 online application needs a square digital photo, not a printed 35×45 mm one."},
    "us_citizenship": {"label": "US citizenship (naturalization) photo", "size": "2×2 inches (51×51 mm)",
                       "bg": "a plain white or off-white background", "head": "the head 1 inch to 1⅜ inches (25–35 mm) from chin to crown",
                       "res": "a recent colour photo (taken within 6 months)", "note": "USCIS forms such as N-400 use the same 2×2 inch photo as a US passport."},
    "us_green_card": {"label": "US green card (permanent resident) photo", "size": "2×2 inches (51×51 mm)",
                      "bg": "a plain white or off-white background", "head": "the head 1 inch to 1⅜ inches (25–35 mm) from chin to crown",
                      "res": "a recent colour photo", "note": "Green card and most USCIS applications use the 2×2 inch format."},
    "canada_citizenship": {"label": "Canadian citizenship photo", "size": "50×70 mm",
                           "bg": "a plain white or light-coloured background", "head": "the face 31–36 mm from chin to crown",
                           "res": "at least 420×540 px", "note": "Canadian citizenship photos use the same 50×70 mm size as the passport, but the endorsement on the back differs."},
    "schengen_residence": {"label": "Schengen residence permit photo", "size": "35×45 mm",
                           "bg": "a plain light (white or off-white) background", "head": "the face 32–36 mm from chin to crown",
                           "res": "at least 600×750 px", "note": "EU residence-permit photos follow the 35×45 mm biometric standard."},
    "uk_visa": {"label": "UK visa / settlement photo", "size": "45×35 mm",
                "bg": "a light grey or plain cream background", "head": "the head 29–34 mm from chin to crown",
                "res": "at least 600×750 px", "note": "UK visa, settlement and BRP photos use 45×35 mm, the same as a UK passport photo."},
    "au_citizenship": {"label": "Australian citizenship photo", "size": "45×35 mm",
                       "bg": "a plain light-coloured background", "head": "the face 32–36 mm from chin to crown",
                       "res": "at least 600×750 px", "note": "Australian citizenship photos are 45×35 mm; two identical copies are usually required."},
    "india_oci": {"label": "India OCI photo", "size": "2×2 inches (51×51 mm)",
                  "bg": "a plain white background with no shadows", "head": "the face 70–80% of the frame",
                  "res": "350×350 px recommended (200–900 px)", "note": "OCI photos are square (2×2 inches), like a US photo, not 35×45 mm."},
    "india_pan": {"label": "India PAN card photo", "size": "35×25 mm",
                  "bg": "a plain white background", "head": "the face filling 70–80% of the frame",
                  "res": "at least 413×295 px", "note": "PAN card photos use a small 35×25 mm size, so a passport crop won't fit."},
}
_IDDOC_ALIASES = [
    (("ds-160", "ds160", "us visa digital", "digital visa photo", "online us visa"), "us_visa_digital"),
    (("citizenship", "naturalization", "naturalisation", "n-400", "uscis citizen"), "us_citizenship"),
    (("green card", "permanent resident card", "i-485"), "us_green_card"),
    (("canadian citizenship", "canada citizenship"), "canada_citizenship"),
    (("uk visa", "uk settlement", "settlement photo", "brp", "biometric residence"), "uk_visa"),
    (("oci photo", "oci card", "overseas citizen of india"), "india_oci"),
    (("pan card", "pan photo"), "india_pan"),
    (("residence permit", "residency permit", "resident permit"), "schengen_residence"),
]


def _detect_id_doc(q: str) -> str | None:
    # Country-specific citizenship must win over the generic "citizenship" -> US mapping.
    if ("canadian citizenship" in q) or ("canada" in q and "citizenship" in q):
        return "canada_citizenship"
    if ("australian citizenship" in q) or ("australia" in q and "citizenship" in q):
        return "au_citizenship"
    for words, spec in _IDDOC_ALIASES:
        if any(w in q for w in words):
            return spec
    return None


def _id_doc_facts(q: str, name: str, spec_key: str) -> dict[str, Any]:
    s = ID_DOC_SPECS[spec_key]
    label = s["label"]
    p1 = (f"A {label} must be {s['size']} on {s['bg']}, with {s['head']}. "
          f"Aim for {s['res']}, a neutral expression, even lighting and no shadows. {s['note']}")
    p2 = (f"{name} lets you take it at home, set a compliant background and crop to the exact spec, "
          f"so a self-taken photo still meets the requirement. Always confirm the current official rule before you submit.")
    return {
        "meta_description": f"A {label} is {s['size']} on {s['bg']}. Make one at home on iPhone with {name}."[:200],
        "lead": f"A {label} needs {s['size']} on {s['bg']} — {name} helps you make one on your iPhone.",
        "short_answer_paragraphs": [p1, p2],
        "what_to_look_for": [
            f"Exact spec: {s['size']} (the #1 rejection reason is the wrong size/crop).",
            f"Background: {s['bg']} with no shadows.",
            f"Head/face sizing: {s['head']}.",
            "Neutral expression, eyes open, no glasses glare or head covering.",
            "A recent, high-resolution colour photo; verify the latest official rule before submitting.",
        ],
        "decision_steps": [
            "Stand against a plain, evenly lit wall.",
            f"Take the shot head-on with {name}.",
            f"Set the background to {s['bg'].split(' or ')[0].replace('a ', '')}.",
            f"Crop/export to {s['size']}.",
            "Save at full quality to upload or print.",
        ],
        "where_app_fits": f"{name} is a strong fit when you need a compliant {label} without a studio visit.",
        "faq": [
            {"q": f"What are the specs for a {label}?", "a": f"{s['size']} on {s['bg']}, with {s['head']}."},
            {"q": "Can I take it myself on my phone?", "a": f"Yes — {name} handles the background and exact crop so a self-taken photo can meet the spec."},
            {"q": "Will it be accepted?", "a": "It meets the published specs, but rules change — always check the current official guidance before submitting."},
        ],
    }


# ---------------------------------------------------------------------------
# Passport-photo RULES / FAQ (high-volume informational demand). Verified 2024.
# Gated to Snapport; each returns the direct answer + Snapport as the at-home fix.
# ---------------------------------------------------------------------------
def _passport_rule_facts(q: str, name: str) -> dict[str, Any] | None:
    def rule(lead: str, detail: str, look: list[str], steps: list[str], faq: list[dict]) -> dict[str, Any]:
        return {
            "meta_description": _snippet(lead, 200),
            "lead": lead,
            "short_answer_paragraphs": [
                detail,
                f"{name} lets you take a compliant photo at home: it sets a plain background, crops to the exact size and helps you avoid the common rejection reasons. Always confirm your country's current official rules before you submit.",
            ],
            "what_to_look_for": look,
            "decision_steps": steps,
            "where_app_fits": f"{name} is a strong fit when you want to get the rules right and take the photo at home, not at a booth.",
            "faq": faq,
        }

    if "glasses" in q:
        return rule(
            "No — glasses are not allowed in passport photos in the US, UK and most countries (since 2016). Take them off before the shot.",
            "Glasses are no longer permitted in passport photos in the US, UK and most countries — even thin frames or clear lenses cause rejection because of glare and eye visibility. The only exception is a documented medical reason, usually needing a signed doctor's note. Remove glasses and make sure your eyes are open and clearly visible.",
            ["Remove glasses entirely before shooting.", "Eyes open and clearly visible, no glare.",
             "Neutral expression, mouth closed.", "Plain background with no shadows.", "Check your country's current official rule."],
            ["Take off your glasses.", "Face the camera with a neutral expression.",
             f"Take the photo with {name}.", "Check eyes are open and clearly visible.", "Crop to the required size and export."],
            [{"q": "Can I wear glasses in a passport photo?", "a": "No — glasses are not allowed in the US, UK and most countries. Remove them unless you have a documented medical exemption."},
             {"q": "What about medical reasons?", "a": "A medical exemption usually requires a signed doctor's note; check your country's official guidance."},
             {"q": "Can I take it at home?", "a": f"Yes — {name} helps you frame and crop a compliant photo at home."}])
    if "smile" in q or "expression" in q:
        return rule(
            "No — you should keep a neutral expression with your mouth closed. A big smile will usually get a passport photo rejected.",
            "Passport photos require a neutral, natural expression with your mouth closed and eyes open. A slight relaxed look is fine, but an open-mouthed smile, raised eyebrows or exaggerated expressions cause rejection because they interfere with facial recognition. Look straight at the camera and relax your face.",
            ["Neutral expression, mouth closed.", "Eyes open, looking at the camera.",
             "No exaggerated smile or raised eyebrows.", "Even lighting, no shadows.", "Plain background."],
            ["Relax your face and close your mouth.", "Look straight at the camera.",
             f"Take the photo with {name}.", "Check the expression is neutral.", "Crop and export to the right size."],
            [{"q": "Can I smile in a passport photo?", "a": "No — keep a neutral expression with your mouth closed. A slight natural look is fine, but not an open smile."},
             {"q": "Why is smiling not allowed?", "a": "Neutral expressions work better with facial-recognition systems used at borders."},
             {"q": "Can I take it at home?", "a": f"Yes — {name} lets you retake easily until the expression is right."}])
    if "background" in q or "background color" in q or "background colour" in q:
        return rule(
            "Passport photos need a plain, light background: white or off-white in the US, and light grey, cream or white in the UK and EU — with no shadows or objects.",
            "The background must be plain and light with no patterns, objects or shadows. The US requires plain white or off-white; the UK and EU accept light grey, cream or white; Canada wants white or light-coloured. Stand a little away from the wall so you don't cast a shadow behind you.",
            ["Plain, light background (white/off-white/light grey).", "No patterns, objects or other people.",
             "No shadows behind your head.", "Even, front-on lighting.", "Check your country's exact colour rule."],
            ["Find a plain, light-coloured wall.", "Stand slightly away from it to avoid shadows.",
             f"Take the photo with {name} (it can replace the background).", "Check for an even, plain backdrop.", "Crop and export."],
            [{"q": "What background color for a passport photo?", "a": "Plain white or off-white in the US; light grey, cream or white in the UK/EU; white or light for Canada."},
             {"q": "Can the app fix the background?", "a": f"Yes — {name} can replace the background with a compliant plain colour."},
             {"q": "Why do shadows matter?", "a": "Shadows behind the head are a common rejection reason; stand away from the wall."}])
    if "baby" in q or "infant" in q or "newborn" in q or "toddler" in q:
        return rule(
            "For a baby's passport photo, no one else can be in the shot and the background must be plain — but for infants the eyes don't have to be fully open.",
            "Baby and infant passport photos follow the same size and background rules, with some flexibility: for newborns and infants the eyes can be closed or partly open, and there should be no toys, hands or other people visible. Lay the baby on a plain white sheet and shoot from directly above, keeping the face evenly lit.",
            ["No other person, hands or toys visible.", "Plain white background (a sheet works).",
             "Eyes open if possible; closed is often OK for infants.", "Face centred and evenly lit.", "Correct size and head proportions."],
            ["Lay the baby on a plain white sheet.", "Shoot from directly above.",
             f"Capture with {name} and pick the best frame.", "Make sure no hands are in shot.", "Crop to the required size."],
            [{"q": "Do a baby's eyes need to be open?", "a": "For newborns and infants, closed or partly open eyes are usually accepted; older children should have eyes open."},
             {"q": "Can I hold the baby?", "a": "Your hands can't be visible — lay the baby on a plain sheet and shoot from above."},
             {"q": "Can I take it at home?", "a": f"Yes — {name} makes it easy to capture and crop a baby photo at home."}])
    if "head covering" in q or re.search(r"\bhats?\b", q) or "scarf" in q or "hijab" in q or "turban" in q:
        return rule(
            "Hats and head coverings aren't allowed in passport photos except for religious or medical reasons — and even then your full face must be visible with no shadows.",
            "You can't wear hats or head coverings for style. Religious or medical head coverings are allowed, but they must be a plain colour, cast no shadows on your face, and leave your full face visible from the bottom of the chin to the top of the forehead. Remove any casual hats before shooting.",
            ["No casual hats or head coverings.", "Religious/medical coverings must not shadow the face.",
             "Full face visible, chin to forehead.", "Plain, non-patterned covering if worn.", "Plain background, even lighting."],
            ["Remove any casual hat.", "If worn for religion/medicine, keep the face fully visible.",
             f"Take the photo with {name}.", "Check for shadows on the face.", "Crop and export to size."],
            [{"q": "Can I wear a hat in a passport photo?", "a": "No — only religious or medical head coverings are allowed, and your full face must stay visible."},
             {"q": "Can I wear a hijab or turban?", "a": "Yes, for religious reasons, as long as it doesn't cover the face or cast shadows."},
             {"q": "Can I take it at home?", "a": f"Yes — {name} helps you check the face is fully visible and evenly lit."}])
    if "cost" in q or "how much" in q or "price" in q or "cheap" in q:
        return rule(
            "A passport photo at a store typically costs about $15–$18 in the US, £8–£12 in the UK, or $15–$20 CAD in Canada — but taking it at home can be far cheaper.",
            "Pharmacies and photo shops charge roughly $15–$18 (US), £8–£12 (UK) or $15–$20 CAD (Canada) for two printed passport photos. Taking your own on your iPhone and either printing it yourself or uploading a digital photo is much cheaper, as long as it meets the size, background and expression rules.",
            ["Store prices: ~$15–$18 US / £8–£12 UK.", "DIY at home is far cheaper.",
             "You still must meet all official rules.", "Digital upload avoids printing costs.", "Retakes are free when you DIY."],
            ["Set up a plain, well-lit background.", f"Take the photo with {name}.",
             "Let it crop to the correct size.", "Print at home or upload digitally.", "Confirm it meets the official rules."],
            [{"q": "How much is a passport photo at a store?", "a": "Around $15–$18 in the US, £8–£12 in the UK, or $15–$20 CAD in Canada for two photos."},
             {"q": "Is it cheaper to take it myself?", "a": f"Yes — {name} lets you take and crop a compliant photo at home, with free retakes."},
             {"q": "Will a home photo be accepted?", "a": "Yes, if it meets the size, background and expression rules — always check the current official guidance."}])
    if "mistake" in q or "rejected" in q or "reject" in q or "rules" in q or "requirements" in q:
        return rule(
            "The most common passport photo mistakes are the wrong size/crop, shadows or a busy background, wearing glasses, smiling, and uneven lighting.",
            "Most rejections come from a handful of avoidable mistakes: the wrong size or head proportions, shadows or a non-plain background, wearing glasses, smiling or a non-neutral expression, hair covering the eyes, and poor or uneven lighting. Getting the crop and background right is where most home photos fail — and where an app helps most.",
            ["Correct size and head proportions.", "Plain background, no shadows.",
             "No glasses, neutral expression.", "Eyes visible, hair off the face.", "Even, front-on lighting."],
            ["Use even, front-on lighting.", "Stand away from a plain wall.",
             f"Take the photo with {name}.", "Let it crop to the exact size.", "Review against the official checklist."],
            [{"q": "What are common passport photo mistakes?", "a": "Wrong size/crop, shadows or busy background, glasses, smiling, hair over the eyes, and uneven lighting."},
             {"q": "What's the number-one rejection reason?", "a": "The wrong size or crop — which is exactly what an app fixes automatically."},
             {"q": "Can an app help me avoid these?", "a": f"Yes — {name} handles the size and background and lets you retake for free."}])
    return None


# ---------------------------------------------------------------------------
# Resume / CV conventions by country.
# ---------------------------------------------------------------------------
RESUME_FORMATS: dict[str, dict[str, str]] = {
    "germany": {"aka": "German", "doc": "Lebenslauf",
                "rule": "a professional photo top-right, a clean tabular reverse-chronological layout, and personal details; usually paired with a separate cover letter (Anschreiben)",
                "len": "1–2 pages", "photo": "Yes — a professional headshot is expected"},
    "japan": {"aka": "Japanese", "doc": "rirekisho (履歴書)",
              "rule": "a fixed government-style form, a 30×40 mm photo, date of birth, and a personal seal or signature; work history lists reasons for leaving",
              "len": "1–2 pages, fixed form", "photo": "Yes — a 30×40 mm formal photo"},
    "uk": {"aka": "UK", "doc": "CV",
           "rule": "no photo and no date of birth, a short personal statement, then skills and reverse-chronological experience",
           "len": "up to 2 pages", "photo": "No"},
    "europass": {"aka": "Europass", "doc": "Europass CV",
                 "rule": "the standard EU template with language and digital-skills self-assessment; widely accepted across the EU",
                 "len": "2+ pages", "photo": "Optional"},
    "france": {"aka": "French", "doc": "CV",
               "rule": "an optional photo, concise one-page layout, and a short centres d'intérêt (interests) section; personal details are common",
               "len": "1–2 pages", "photo": "Optional"},
    "us": {"aka": "US", "doc": "resume",
           "rule": "no photo and no personal details, one page for most roles, strong action verbs, and an ATS-friendly single-column layout",
           "len": "1 page (up to 2 when experienced)", "photo": "No — never include a photo"},
    "canada": {"aka": "Canadian", "doc": "resume",
               "rule": "no photo, no date of birth, a skills-forward reverse-chronological layout similar to the US style",
               "len": "1–2 pages", "photo": "No"},
    "australia": {"aka": "Australian", "doc": "resume",
                  "rule": "no photo, and — for government roles — explicit responses to the 'selection criteria'",
                  "len": "2–3 pages", "photo": "No"},
    "spain": {"aka": "Spanish", "doc": "CV",
              "rule": "commonly a professional photo, personal details (date of birth, nationality) and a chronological layout with a languages section",
              "len": "1–2 pages", "photo": "Commonly expected"},
    "italy": {"aka": "Italian", "doc": "CV",
              "rule": "often a photo and personal details, and frequently the Europass template in traditional sectors",
              "len": "1–2 pages", "photo": "Often expected"},
    "netherlands": {"aka": "Dutch", "doc": "CV",
                    "rule": "usually no photo (to avoid bias), a short profile, then a concise reverse-chronological layout",
                    "len": "1–2 pages", "photo": "Optional — often left off"},
    "china": {"aka": "Chinese", "doc": "resume (简历)",
              "rule": "a formal passport-sized photo and personal details (gender, date of birth) near the top, then education and experience",
              "len": "1–2 pages", "photo": "Yes — a formal photo is standard"},
    "korea": {"aka": "South Korean", "doc": "resume (이력서)",
              "rule": "a headshot at the top, personal details, and — for men — military-service status; standardized forms are common",
              "len": "1–2 pages", "photo": "Yes — a headshot is standard"},
    "brazil": {"aka": "Brazilian", "doc": "currículo",
               "rule": "no photo, personal data, and a reverse-chronological layout with a languages section",
               "len": "1–2 pages", "photo": "No — usually omitted"},
    "india": {"aka": "Indian", "doc": "resume",
              "rule": "usually no photo, a career objective/summary, then education and reverse-chronological experience",
              "len": "1–2 pages", "photo": "No — usually omitted"},
    "singapore": {"aka": "Singapore", "doc": "resume",
                  "rule": "an optional photo, a career summary and a clean reverse-chronological layout",
                  "len": "1–2 pages", "photo": "Optional"},
    "mexico": {"aka": "Mexican", "doc": "CV / currículum",
               "rule": "written in Spanish, reverse-chronological, with a header that traditionally lists name, date of birth and nationality; a passport-style photo top-right is common in traditional sectors but often dropped for multinationals",
               "len": "1–2 pages", "photo": "Optional — common traditionally, omitted for multinationals"},
    "sweden": {"aka": "Swedish", "doc": "CV",
               "rule": "a minimalist, strictly reverse-chronological CV in Swedish or English with just name, phone and email; date of birth, marital status and photo are deliberately omitted under strong anti-discrimination norms",
               "len": "1–2 pages", "photo": "No — omitted by convention"},
    "poland": {"aka": "Polish", "doc": "CV",
               "rule": "a reverse-chronological CV that must end with the mandatory GDPR data-processing consent clause; a professional photo and date of birth are optional and increasingly dropped",
               "len": "1–2 pages", "photo": "Optional — declining"},
    "turkey": {"aka": "Turkish", "doc": "CV / özgeçmiş",
               "rule": "written in Turkish with a passport-style photo and a header listing date of birth and marital status, plus — uniquely — a military-service status field for male candidates",
               "len": "1–2 pages", "photo": "Yes — a professional photo is expected"},
    "uae": {"aka": "UAE", "doc": "CV",
            "rule": "a detailed personal header that prominently states nationality and visa/residency status (needed for work permits), plus date of birth, marital status and a passport-style photo",
            "len": "2 pages", "photo": "Yes — a professional photo is standard"},
    "russia": {"aka": "Russian", "doc": "resume (резюме)",
               "rule": "written in Russian, reverse-chronological, with a header that includes date of birth, city and often a desired salary; a professional photo is recommended (hh.ru prompts for one)",
               "len": "1–2 pages", "photo": "Recommended — commonly included"},
    "indonesia": {"aka": "Indonesian", "doc": "CV / daftar riwayat hidup",
                  "rule": "a 'data diri' section with name, date of birth, gender and marital status (sometimes religion for government roles), topped by a formal passport-style photo",
                  "len": "1–2 pages", "photo": "Yes — a formal photo is standard"},
}

# 2026-07-08 more-countries2 worker: 7 verified additions. Photo norms cross-checked
# against official guidance (TAFEP/MOM Singapore, POPIA South Africa, recruiter norms).
RESUME_FORMATS.update({
    "saudi": {"aka": "Saudi", "doc": "CV (السيرة الذاتية)",
              "rule": "a passport-style photo (top corner) plus nationality, age, marital status and iqama/visa status for local GCC employers; English (British spelling) or Arabic — but omit the photo and personal data for multinational or ATS-screened applications",
              "len": "1–2 pages", "photo": "Yes for local employers — discouraged for MNC/ATS roles"},
    "thailand": {"aka": "Thai", "doc": "resume",
                 "rule": "a professional passport-style photo at the top, plus date of birth, gender and address; reverse-chronological with a factual, humble tone; Thai or English depending on the employer",
                 "len": "1–2 pages", "photo": "Yes — a professional headshot is the norm"},
    "vietnam": {"aka": "Vietnamese", "doc": "CV / Sơ yếu lý lịch",
                "rule": "a professional photo (top corner) plus date of birth, gender and marital status; reverse-chronological; Vietnamese for domestic firms, English for international/MNC roles",
                "len": "1–2 pages", "photo": "Yes — expected by nearly all local employers"},
    "philippines": {"aka": "Philippine", "doc": "resume",
                    "rule": "traditionally a small passport-style ID photo (upper corner) with personal details, though photos are increasingly omitted at multinationals to reduce bias; English; always check the job ad",
                    "len": "1–2 pages", "photo": "Optional — traditional but a shifting norm"},
    "southafrica": {"aka": "South African", "doc": "CV",
                    "rule": "no photo, ID number, race or marital status (POPIA and Employment Equity Act make these legally sensitive); British English; references 'available on request'",
                    "len": "2 pages (up to 3 for senior or academic roles)", "photo": "No — legally sensitive under POPIA"},
    "nigeria": {"aka": "Nigerian", "doc": "CV",
                "rule": "no photo for standard roles; full referee details listed at the end (not just 'on request'); a cover letter is usually expected; formal, concise and reverse-chronological",
                "len": "1–2 pages (up to 3 for 10+ years' experience)", "photo": "No — not standard for professional roles"},
    "egypt": {"aka": "Egyptian", "doc": "CV",
              "rule": "a passport-style photo plus date of birth, nationality and marital status for private-sector roles (NGOs/UN agencies may discourage it); mention a strong GPA or honours; English or Arabic",
              "len": "1–2 pages", "photo": "Yes for private sector — discouraged by NGOs/UN"},
})
_RESUME_ALIASES = {
    "lebenslauf": "germany", "german": "germany",
    "rirekisho": "japan", "japanese": "japan",
    "uk cv": "uk", "british": "uk",
    "europass": "europass",
    "french cv": "france", "france": "france",
    "us resume": "us", "american resume": "us",
    "canadian": "canada", "canada": "canada",
    "australian": "australia",
    "spanish": "spain", "spain cv": "spain",
    "italian": "italy", "italy cv": "italy",
    "dutch": "netherlands", "netherlands cv": "netherlands",
    "chinese": "china", "china resume": "china",
    "korean": "korea", "korea resume": "korea",
    "brazilian": "brazil", "brazil resume": "brazil",
    "indian": "india", "india resume": "india",
    "singapore": "singapore",
    "mexican": "mexico", "mexico cv": "mexico", "mexico resume": "mexico",
    "swedish": "sweden", "sweden cv": "sweden",
    "polish": "poland", "poland cv": "poland",
    "turkish": "turkey", "turkey cv": "turkey", "ozgecmis": "turkey",
    "uae cv": "uae", "dubai cv": "uae", "emirates cv": "uae",
    "russian": "russia", "russia cv": "russia", "rezume": "russia",
    "indonesian": "indonesia", "indonesia cv": "indonesia",
    "saudi cv": "saudi", "saudi arabia cv": "saudi", "saudi resume": "saudi", "saudi arabia resume": "saudi",
    "thai resume": "thailand", "thailand cv": "thailand", "thai cv": "thailand", "thailand resume": "thailand",
    "vietnamese": "vietnam", "vietnam cv": "vietnam", "vietnam resume": "vietnam",
    "philippine resume": "philippines", "philippines cv": "philippines", "philippines resume": "philippines", "filipino resume": "philippines",
    "south africa cv": "southafrica", "south african cv": "southafrica", "south africa resume": "southafrica",
    "nigerian cv": "nigeria", "nigeria cv": "nigeria", "nigeria resume": "nigeria",
    "egypt cv": "egypt", "egyptian cv": "egypt", "egypt resume": "egypt",
}


def _detect_resume(q: str) -> str | None:
    if not any(t in q for t in ("resume", "cv", "lebenslauf", "rirekisho", "europass")):
        return None
    for alias, spec in _RESUME_ALIASES.items():
        if alias in q:
            return spec
    return None


def _resume_facts(q: str, name: str, spec_key: str) -> dict[str, Any]:
    s = RESUME_FORMATS[spec_key]
    label = f"{s['aka']} {s['doc']}"
    p1 = (f"A {label} follows local hiring conventions: {s['rule']}. Typical length is {s['len']}. "
          f"Photo: {s['photo']}. Matching these expectations matters as much as the content.")
    p2 = (
        f"{name}'s current App Store listing describes an on-device 0–100 ATS estimate "
        "and free resume building and preview. A one-time purchase unlocks watermark-free "
        "PDF and editable DOCX export. Tailor the wording manually, follow the employer's "
        "file instructions, and treat the score as an editing estimate rather than a result prediction."
    )
    return {
        "meta_description": f"How to build a {label} on iPhone: format, length ({s['len']}) and photo rules, with {name}."[:200],
        "lead": f"A {label} has its own format rules — {name} helps you match them and export a clean PDF.",
        "short_answer_paragraphs": [p1, p2],
        "what_to_look_for": [
            f"Correct format for a {label}: {s['rule']}.",
            f"Length: {s['len']}.",
            f"Photo: {s['photo']}.",
            "Simple reading order, familiar headings, and no important text stored only in images.",
            "Watermark-free PDF and editable DOCX export require the one-time unlock.",
        ],
        "decision_steps": [
            f"Pick a {label}-appropriate template.",
            "Fill in reverse-chronological experience with measurable results.",
            f"Apply the local photo rule ({s['photo'].split(' —')[0].split(' -')[0]}).",
            "Add only relevant terms that truthfully describe your experience.",
            "Follow the employer's file instructions and inspect the exact export.",
        ],
        "where_app_fits": (
            f"{name} can help you build a {label} and run an on-device ATS preflight estimate. "
            "Employer systems vary, so the estimate cannot guarantee parsing, ranking, an interview, or an offer."
        ),
        "faq": [
            {"q": f"Does a {label} need a photo?", "a": s["photo"] + "."},
            {"q": f"How long should a {label} be?", "a": f"Usually {s['len']}."},
            {
                "q": "Will it pass ATS?",
                "a": (
                    "No app can guarantee that. Follow the employer's instructions, keep the "
                    "structure simple, and use the estimate only to prioritize manual edits."
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# Resume FAQ (high-volume informational demand). Verified 2024. Gated to CV Desk.
# ---------------------------------------------------------------------------
def _resume_faq_facts(q: str, name: str) -> dict[str, Any] | None:
    def faq(lead: str, detail: str, look: list[str], steps: list[str], qa: list[dict]) -> dict[str, Any]:
        return {
            "meta_description": _snippet(lead, 200),
            "lead": lead,
            "short_answer_paragraphs": [
                detail,
                (
                    f"{name}'s current App Store listing describes an on-device 0–100 ATS "
                    "estimate, free resume building and preview, and a one-time unlock for "
                    "watermark-free PDF and editable DOCX export. It requires no account, "
                    "upload or subscription. Always adapt the resume manually to the role, "
                    "country and employer instructions."
                ),
            ],
            "what_to_look_for": look,
            "decision_steps": steps,
            "where_app_fits": (
                f"{name} can provide an on-device resume preflight and editing workflow. "
                "Its ATS score is an estimate and cannot guarantee parsing, ranking, an "
                "interview or an offer."
            ),
            "faq": qa,
        }

    if "how many pages" in q or "resume length" in q or "one page or two" in q or "how long should a resume" in q or "how long should a cv" in q:
        return faq(
            "In the US, keep a resume to one page for under ~7 years of experience; two pages is fine — often preferred — for experienced professionals.",
            "One page is the US norm for early-career candidates; two pages is widely accepted, and often preferred, once you have around seven or more years of relevant experience. UK CVs run to about two pages, and academic CVs can be longer. The goal is relevance — cut anything that doesn't support the target role rather than padding to fill a page.",
            ["One page for early career (US).", "Two pages once experienced (~7+ years).",
             "UK CVs ~2 pages; academic CVs longer.", "Cut anything not relevant to the role.", "Prioritise recent, measurable achievements."],
            ["Decide by experience, not by rule.", "Lead with your most relevant, recent roles.",
             f"Draft it in {name}.", "Trim anything that doesn't support the job.", "Export a clean one- or two-page PDF."],
            [{"q": "Should a resume be one page?", "a": "One page for under ~7 years' experience; two pages is fine when you have more."},
             {"q": "Is a two-page resume bad?", "a": "No — it's often preferred for experienced candidates, as long as every line is relevant."},
             {"q": "How long is a UK CV?", "a": "Usually about two pages."}])
    if ("photo" in q) and ("resume" in q or "cv" in q):
        return faq(
            "In the US, UK, Canada, Australia and Ireland, don't put a photo on your resume; in Japan, South Korea, Germany and France a photo is expected.",
            "Photo norms split sharply by country. In the US, UK, Canada, Australia and Ireland a photo is discouraged and can raise discrimination concerns, so it's left off. In Japan and South Korea a passport-style photo is effectively required, and in Germany and France it's customary. When applying abroad, follow the convention of the country where the job is based.",
            ["No photo for US/UK/CA/AU/IE resumes.", "Photo expected in JP/KR (and customary DE/FR).",
             "Follow the target country's norm.", "If used, a professional headshot only.", "Keep the rest of the header lean."],
            ["Check where the job is based.", "Apply that country's photo convention.",
             f"Build the resume in {name}.", "Add or omit the photo accordingly.", "Export a clean PDF."],
            [{"q": "Should a resume have a photo?", "a": "Not in the US/UK/Canada/Australia/Ireland; yes in Japan/South Korea and customarily in Germany/France."},
             {"q": "Why no photo in the US?", "a": "Anti-discrimination norms mean recruiters prefer resumes without photos."},
             {"q": "What if I apply abroad?", "a": "Follow the convention of the country where the role is based."}])
    if ("ats" in q) and ("what is" in q or "how" in q or "friendly" in q or "pass" in q or "beat" in q):
        result = faq(
            (
                "An ATS helps employers store and search applications, but systems and "
                "configurations differ. Use a score as a preflight estimate, not a pass prediction."
            ),
            (
                "UConn explains that an ATS does not automatically reject candidates and "
                "recommends following the employer's file instructions, using simple consistent "
                "formatting, and avoiding important information in headers, footers, tables or "
                "graphics. It also recommends weaving relevant terms from the posting into the "
                "resume where they accurately describe your qualifications. These steps can "
                "reduce avoidable issues, but they cannot reproduce a specific employer's setup."
            ),
            [
                "Follow the employer's requested file type first.",
                "Use familiar headings and a simple, consistent reading order.",
                "Keep important details out of graphics, headers, footers and text boxes.",
                "Use only truthful, relevant terms from the job posting.",
                "Inspect the exact exported file before submitting.",
            ],
            [
                "Read the application instructions.",
                "Check contact details and standard section headings.",
                "Compare the posting manually and keep every claim truthful.",
                "Reopen the export and verify selectable text and section order.",
                "Use any score to prioritize edits, not to predict an outcome.",
            ],
            [
                {
                    "q": "Does an ATS automatically reject my resume?",
                    "a": (
                        "UConn says an ATS does not automatically reject candidates. "
                        "Employers use different workflows and configurations."
                    ),
                },
                {
                    "q": "How do I make a resume easier to process?",
                    "a": (
                        "Follow the employer's file instructions, use familiar headings and "
                        "a simple reading order, and keep every job-related term truthful."
                    ),
                },
                {
                    "q": "Does formatting guarantee a pass?",
                    "a": (
                        "No. Simple formatting may reduce avoidable parsing problems, but no "
                        "format or score guarantees parsing, ranking, an interview or an offer."
                    ),
                },
            ],
        )
        result["page_title"] = (
            "Build an ATS-Conscious Resume on iPhone Without a Subscription"
        )
        result["meta_description"] = (
            "Use an ATS score as a resume preflight estimate, follow employer file "
            "instructions, and check CV Desk's current on-device features and pricing."
        )
        result["sources"] = [
            {
                "title": "UConn Center for Career Readiness: Applicant Tracking Systems",
                "url": "https://career.uconn.edu/applicant-tracking-systems/",
            },
            {
                "title": "CV Desk on the App Store",
                "url": "https://apps.apple.com/app/id6781337213",
            },
        ]
        return result
    if ("gap" in q) and ("resume" in q or "cv" in q or "employment" in q or "work" in q):
        return faq(
            "Explain an employment gap briefly and honestly — add a short 'Career Break' entry noting what you did (caregiving, study, travel) rather than hiding it.",
            "The clearest approach is to include a brief, honest 'Career Break' line in your chronological history with dates and a few words on what you did — caregiving, study, health, travel or freelancing. Hiding gaps tends to raise more questions than a short, matter-of-fact note. Focus on any skills or courses you kept up during the time.",
            ["A short, honest 'Career Break' entry.", "Dates and a brief reason.",
             "Any study, courses or freelance work done.", "Skills kept current.", "A neutral, confident tone."],
            ["Add a 'Career Break' entry with dates.", "Note briefly what you did.",
             "Highlight any learning or freelance work.", f"Keep it concise in {name}.", "Move on — don't over-explain."],
            [{"q": "How do I explain a gap on my resume?", "a": "Add a brief, honest 'Career Break' entry with dates and what you did, rather than hiding it."},
             {"q": "Should I hide an employment gap?", "a": "No — a short, matter-of-fact note reads better than an unexplained gap."},
             {"q": "What if I studied during the gap?", "a": "List the course or skills — it shows you stayed active."}])
    if "reference" in q and ("resume" in q or "cv" in q):
        return faq(
            "Don't put references — or 'references available on request' — on your resume. Keep a separate reference sheet and share it only when asked.",
            "'References available on request' is outdated and just wastes space, since recruiters assume you can provide them. Listing actual references on the resume is also unnecessary and exposes them to contact before you're a serious candidate. Prepare a separate, formatted reference sheet and hand it over only when an employer specifically asks, usually after an interview.",
            ["No references on the resume itself.", "Skip 'references available on request'.",
             "Keep a separate reference sheet ready.", "Share it only when requested.", "Use the space for achievements instead."],
            ["Remove references from the resume.", "Use the space for results and skills.",
             "Prepare a separate reference sheet.", "Provide it only when asked.", f"Keep the resume tight in {name}."],
            [{"q": "Should I put references on my resume?", "a": "No — keep a separate sheet and provide it only when an employer asks."},
             {"q": "Is 'references available on request' needed?", "a": "No — it's outdated and wastes space."},
             {"q": "When do I share references?", "a": "Usually after a first or second interview, when specifically requested."}])
    if ("bullet" in q) and ("resume" in q or "cv" in q or "job" in q):
        return faq(
            "Use about three to six bullet points per job, and write each as an achievement: action verb + what you did + a measurable result.",
            "Three to six bullets per role is the sweet spot — enough to show impact without overwhelming a recruiter who scans for only a few seconds. Write each bullet as an achievement, not a duty: start with a strong action verb, state what you did, and add a measurable result (a number, percentage or outcome) wherever you can. Put more bullets on recent, relevant roles and fewer on older ones.",
            ["3–6 bullets per role.", "Achievements, not duties.",
             "Action verb + task + measurable result.", "Numbers/percentages where possible.", "More detail on recent roles."],
            ["List each role's biggest wins.", "Start each bullet with an action verb.",
             "Add a number or outcome.", f"Tighten them in {name}.", "Trim older roles to 1–2 bullets."],
            [{"q": "How many bullet points per job?", "a": "About three to six, weighted toward your most recent roles."},
             {"q": "How do I write a good bullet?", "a": "Action verb + what you did + a measurable result."},
             {"q": "Duties or achievements?", "a": "Achievements — show impact, not just responsibilities."}])
    if ("chronological" in q or "functional" in q or "hybrid" in q) or ("resume format" in q or "cv format" in q) and ("which" in q or "best" in q or "vs" in q):
        return faq(
            "Use a reverse-chronological resume by default; a functional (skills-first) format only if you're changing careers or have big gaps; hybrid to blend both.",
            "Reverse-chronological — most recent role first — is what recruiters and ATS expect, and it's the right default for anyone with a steady, relevant history. A functional format leads with skills and downplays dates, which can help career-changers or those with large gaps, but recruiters often distrust it. A hybrid opens with a short skills summary, then a chronological history — a safe middle ground.",
            ["Reverse-chronological is the default.", "Functional only for big gaps/career change.",
             "Hybrid = skills summary + chronological.", "ATS handles chronological best.", "Match the format to your situation."],
            ["Assess your history and gaps.", "Pick chronological unless you have a reason not to.",
             "If changing careers, consider hybrid.", f"Build it in {name}.", "Keep it ATS-readable."],
            [{"q": "Which resume format is best?", "a": "Reverse-chronological for most people; hybrid if you're changing careers."},
             {"q": "Is a functional resume good?", "a": "Only for specific cases (big gaps, career change) — recruiters can be wary of it."},
             {"q": "What is a hybrid resume?", "a": "A short skills summary followed by a reverse-chronological history."}])
    if ("pdf" in q or "word" in q or "docx" in q or "file format" in q) and ("resume" in q or "cv" in q):
        return faq(
            "Send your resume as a PDF by default — it keeps your layout on every device — unless the posting or agency asks for Word (.docx).",
            "PDF is the safest default: it renders identically everywhere, preserves your fonts and layout, and can't be accidentally edited. Send Word (.docx) only when it's explicitly requested — some recruitment agencies add their own formatting, and a few older ATS portals parse Word more reliably. The rule is simple: follow the posting's instruction; if there isn't one, send PDF.",
            ["PDF by default for layout safety.", "Word (.docx) only when requested.",
             "Follow the posting's instruction.", "Keep the filename professional.", "Check the PDF opens cleanly."],
            ["Finish the resume.", f"Export a PDF from {name}.",
             "Name the file clearly (Name_Role.pdf).", "Send Word only if asked.", "Double-check it opens on desktop."],
            [{"q": "PDF or Word for a resume?", "a": "PDF by default; Word only when the posting or agency requests it."},
             {"q": "Why PDF?", "a": "It renders identically everywhere and can't be accidentally reformatted."},
             {"q": "When should I send Word?", "a": "When explicitly asked, e.g. by an agency that adds its own formatting."}])
    if ("tailor" in q or "keywords" in q) and ("resume" in q or "cv" in q or "job" in q):
        return faq(
            "Yes — tailor your resume to each job by mirroring the posting's keywords; a generic resume scores poorly against ATS and recruiters.",
            "Tailoring is one of the highest-impact steps: ATS scores your resume against the exact wording of the job description, so mirror the skills and terms it uses (using the real ones that apply to you). Reorder your bullets to lead with the most relevant experience for that role. A single generic resume sent everywhere consistently underperforms tailored versions.",
            ["Mirror the posting's keywords (honestly).", "Lead with the most relevant experience.",
             "Adjust the summary per role.", "Keep one master version to tailor from.", "Don't keyword-stuff."],
            ["Read the posting for key skills/terms.", "Match them in your resume where true.",
             "Reorder bullets by relevance.", f"Save tailored versions in {name}.", "Export a fresh PDF per application."],
            [{"q": "Should I tailor my resume to each job?", "a": "Yes — mirror the posting's keywords and lead with the most relevant experience."},
             {"q": "Why does tailoring matter?", "a": "ATS scores against the job description's exact language, so a generic resume ranks lower."},
             {"q": "Can I keyword-stuff?", "a": "No — use only real, relevant terms; stuffing is easy to spot and backfires."}])
    return None


# ---------------------------------------------------------------------------
# Task-scenario facts (scan / storage / voice / kids learning / focus …).
# Each entry: keywords that must appear, plus the content overlay factory.
# ---------------------------------------------------------------------------
def _scenario_facts(q: str, key: str, name: str, bullets: list[str]) -> dict[str, Any] | None:
    strengths = ", ".join(bullets[:3]) if bullets else "a focused, private design"

    def make(p1: str, look: list[str], steps: list[str], where: str, faq: list[dict]) -> dict[str, Any]:
        lead = p1.split(". ")[0].rstrip(".") + f" — {name} helps you do it on your iPhone."
        return {
            "meta_description": _snippet(p1, 200, tail=f" — with {name}."),
            "lead": lead,
            "short_answer_paragraphs": [
                p1,
                f"{name} is built for exactly this, with {strengths}. Test it on a real example before relying on it, and check the current App Store listing for pricing.",
            ],
            "what_to_look_for": look,
            "decision_steps": steps,
            "where_app_fits": where,
            "faq": faq,
        }

    def hourstag_spending() -> dict[str, Any]:
        return make(
            "To understand where your money went, record each completed expense and convert it into the work time required to earn that amount. Reviewing money and time together makes category patterns concrete without bank syncing.",
            [
                "Manual expense records converted into work hours.",
                "Hourly or monthly income setup using your own numbers.",
                "Spending history with categories and time-based breakdowns.",
                "Goals and wishlist progress expressed in work time.",
                "On-device data, no account, and a one-time purchase.",
            ],
            [
                "Set your hourly or monthly take-home income.",
                f"Log a completed expense in {name}.",
                "Choose its category and Need, Want, or Impulse tag.",
                "Review history and breakdowns in both money and work time.",
                "Track a goal to see the work time behind future progress.",
            ],
            f"{name} fits when you want to record and review existing spending as work time, with history and goals rather than bank syncing.",
            [
                {
                    "q": "Does it import transactions from my bank?",
                    "a": f"No. You enter expenses yourself, and {name} keeps the records on your device without an account.",
                },
                {
                    "q": "Is it a checkout blocker?",
                    "a": f"No. {name} records and reframes spending; it does not block stores, cards, or purchases.",
                },
                {
                    "q": "Is it a subscription?",
                    "a": "No. It is a one-time purchase.",
                },
            ],
        )

    if key == "scanto" and "receipt" in q and "scan" in q:
        return make(
            "To keep receipts for taxes, scan each one to a clear PDF, run OCR so amounts and dates become searchable text, and file them by category. On-device scanning keeps financial data private.",
            ["Auto edge-detection and de-skew for crumpled receipts.", "OCR so totals and dates are searchable.",
             "Batch multiple receipts into one PDF.", "On-device processing for private financial data.", "Easy export to Files, email or accounting apps."],
            ["Lay the receipt on a contrasting surface.", f"Scan it with {name} and let edges auto-detect.",
             "Enable OCR to capture the total and date.", "Tag by expense category.", "Export the PDF to your bookkeeping folder."],
            f"{name} fits when you want tax-ready, searchable receipt PDFs without a subscription.",
            [{"q": "Can I search text inside scanned receipts?", "a": "Yes — OCR turns the printed text into searchable, selectable content."},
             {"q": "Is it private?", "a": f"{name} processes scans on device, so receipts don't leave your iPhone unless you export them."},
             {"q": "Can I combine receipts?", "a": "Yes — batch several into a single PDF for each month or category."}])
    if key == "scanto" and "contract" in q and "scan" in q:
        return make(
            "To scan and sign a contract, capture each page to a crisp PDF, add your signature, and lock the file so only you can open it. Keeping it on device avoids uploading a sensitive document to a third-party cloud.",
            ["Sharp, multi-page PDF output with straightened edges.", "Add a signature directly on the page.",
             "Password/Face ID lock on the finished PDF.", "On-device processing — no forced cloud upload.", "Export to Files or email."],
            ["Scan every page in order.", "Straighten and clean each page.", "Drop your signature where needed.",
             "Lock the PDF with Face ID or a password.", "Share the signed, secured file."],
            f"{name} fits when you need a signed, secured contract PDF without sending it to an online service.",
            [{"q": "Can I sign inside the app?", "a": "Yes — add a signature onto the scanned page before exporting."},
             {"q": "Can I protect the PDF?", "a": f"{name} can lock the file behind Face ID or a password."},
             {"q": "Does it stay private?", "a": "Scanning happens on device, so the contract isn't uploaded unless you choose to share it."}])
    if key == "scanto" and "book" in q and "scan" in q:
        return make(
            "To scan book pages into a searchable PDF, flatten curved pages, remove shadows from the spine, and run OCR so you can search and copy the text later. Batch scanning many pages into one file keeps chapters together.",
            ["Curved-page flattening and shadow removal.", "OCR for searchable, copy-able text.",
             "Batch many pages into one PDF.", "Auto edge-detection to scan quickly.", "Export to Files, Books or notes apps."],
            ["Place the book flat under even light.", f"Scan pages in sequence with {name}.",
             "Let it flatten curvature and remove shadows.", "Run OCR for searchable text.", "Export the combined PDF."],
            f"{name} fits when you want a searchable PDF of book pages rather than a stack of photos.",
            [{"q": "Can I search the scanned text?", "a": "Yes — OCR makes the text searchable and selectable."},
             {"q": "Will curved pages look flat?", "a": "Page-flattening reduces the curve near the spine for cleaner scans."},
             {"q": "Can I scan a whole chapter?", "a": "Yes — batch many pages into a single PDF."}])
    if key == "picclear" and "live photo" not in q and not q.startswith(("why", "what", "does")) and ("duplicate" in q or "storage" in q or "large video" in q or "free up" in q) and ("photo" in q or "storage" in q or "video" in q):
        return make(
            "To free up space fast, target the biggest wins first: exact-duplicate photos, near-identical burst shots, blurry rejects, and large videos. Reviewing before deletion — and keeping the best of each group — avoids losing anything you wanted.",
            ["Finds exact duplicates and near-identical bursts.", "Sorts large videos by size so you see the space hogs.",
             "Groups similar shots so you keep the best one.", "Preview and confirm before anything is deleted.", "Works on device for privacy."],
            ["Scan the library for duplicates and similar shots.", "Sort videos by size to find the biggest.",
             "Review each group and keep the best.", "Confirm the selection before deleting.", "Empty 'Recently Deleted' to reclaim the space."],
            f"{name} fits when your storage is full and you want to clear gigabytes quickly without deleting the wrong photos.",
            [{"q": "Will it delete photos automatically?", "a": "No — you review and confirm; nothing is removed without your approval."},
             {"q": "Can it find large videos?", "a": "Yes — videos are sorted by size so you can clear the biggest first."},
             {"q": "Is it private?", "a": f"{name} scans on device, so your library isn't uploaded anywhere."}])
    if key == "sononote" and "interview" not in q and "podcast" not in q and ("transcribe" in q or "voice memo" in q or "voice notes" in q or "meeting" in q or "lecture" in q) and ("app" in q or "note" in q or "transcribe" in q or "record" in q):
        return make(
            "For spoken notes, look for accurate on-device transcription, a clean summary, and extracted action items — so a long recording becomes something you can actually use. On-device processing keeps private conversations off the cloud.",
            ["Accurate speech-to-text, ideally on device.", "Automatic summary of long recordings.",
             "Extracted action items and key points.", "Private processing for sensitive conversations.", "Export to your notes or tasks app."],
            ["Record or import the audio.", f"Let {name} transcribe it to text.",
             "Generate a short summary.", "Pull out action items and decisions.", "Export the notes where you need them."],
            f"{name} fits when you want clean notes and takeaways from a recording, not just a raw transcript.",
            [{"q": "Does it work offline?", "a": f"{name} focuses on on-device processing, so recordings stay private."},
             {"q": "Can it summarise a long recording?", "a": "Yes — it produces a concise summary plus action items."},
             {"q": "Can I export the notes?", "a": "Yes — send the summary and to-dos to your notes or tasks app."}])
    if key in {"lumiletters", "lumiletterspro"} and ("phonics" in q or "alphabet" in q or "letters" in q or "sight words" in q) and ("kid" in q or "child" in q or "toddler" in q or "preschool" in q or "kindergarten" in q or "read" in q or "4 year" in q or "5 year" in q):
        return make(
            "Early literacy sticks when it's playful and low-pressure: letter sounds (phonics) before letter names, correct stroke order for writing, and short, colourful activities that hold a young child's attention. No ads and no in-app pressure keep it safe.",
            ["Phonics (letter sounds), not just the ABC song.", "Correct letter formation and stroke order.",
             "Short, playful sessions suited to little attention spans.", "No ads and no unexpected in-app purchases.", "Progress that celebrates effort, not scores."],
            ["Start with a few letter sounds, not the whole alphabet.", "Keep sessions short and playful.",
             "Practise tracing for correct stroke order.", "Blend sounds into simple words.", "Celebrate small wins to keep it fun."],
            f"{name} fits when you want a safe, playful way to build early reading skills at home.",
            [{"q": "Is it ad-free and kid-safe?", "a": f"{name} is designed for young children without ads or pressure to buy."},
             {"q": "Does it teach phonics?", "a": "Yes — it focuses on letter sounds and blending, which is how children learn to read."},
             {"q": "Will my child learn to write letters?", "a": "Tracing activities guide correct letter formation and stroke order."}])
    if key in {"lumibopomofo", "lumibopomofopro"} and ("bopomofo" in q or "zhuyin" in q):
        return make(
            "To teach Zhuyin (bopomofo) at home — especially for overseas Chinese families — children do best with playful sound practice, correct stroke order for each symbol, and repetition through games rather than drills.",
            ["The 37 bopomofo symbols with correct pronunciation.", "Stroke-order practice for writing each symbol.",
             "Playful games instead of rote drills.", "Suitable for pre-schoolers and overseas learners.", "No ads and a kid-safe design."],
            ["Introduce a few symbols at a time.", "Practise the sound before the shape.",
             "Trace each symbol in the correct stroke order.", "Reinforce with short games.", "Revisit earlier symbols to build memory."],
            f"{name} fits when you want a playful, kid-safe way to teach bopomofo at home.",
            [{"q": "Is it good for overseas Chinese kids?", "a": f"Yes — {name} teaches bopomofo through play, which suits children learning outside a Mandarin-speaking environment."},
             {"q": "Does it teach writing?", "a": "Yes — stroke-order tracing helps children write each symbol correctly."},
             {"q": "Is it kid-safe?", "a": "It's designed for young children without ads."}])
    if key in {"lumimath", "lumimathpro"} and ("count" in q or "numbers" in q or "number bonds" in q or "math" in q) and ("kid" in q or "child" in q or "preschool" in q or "before school" in q or "young" in q or "5 year" in q):
        return make(
            "Early maths starts with counting, number recognition, and 'number bonds' (how small numbers combine) — taught through play, not worksheets. Short, colourful activities keep a young child engaged before school starts.",
            ["Counting and number recognition first.", "Number bonds and simple addition through play.",
             "Short, colourful, game-based activities.", "No ads or pressure to buy.", "Encouragement that builds confidence."],
            ["Practise counting to ten, then twenty.", "Match numbers to quantities.",
             "Introduce simple number bonds through games.", "Keep each session short and playful.", "Praise effort to build confidence."],
            f"{name} fits when you want a playful head start in early maths before school.",
            [{"q": "Is it suitable before school?", "a": f"Yes — {name} focuses on counting and early number sense for young children."},
             {"q": "Is it ad-free?", "a": "It's designed to be safe for children without ads."},
             {"q": "Does it use worksheets?", "a": "No — it teaches through short, playful, game-based activities."}])
    if key == "unblurry" and "profile" not in q and "linkedin" not in q and ("unblur" in q or "blurry" in q or "sharpen" in q or "out of focus" in q or "motion blur" in q or ("restore" in q and "photo" in q) or ("old" in q and "photo" in q)):
        return make(
            "To rescue a blurry or old photo, an app should sharpen soft detail, reduce motion blur, and enhance faces without turning the picture plastic or fake. Working on device keeps personal and family photos private.",
            ["Sharpening that recovers detail without heavy artefacts.", "Motion-blur and out-of-focus correction.",
             "Face and old-photo enhancement that still looks natural.", "Full-resolution output, not a downscaled preview.", "On-device processing for private family photos."],
            ["Pick the blurry or faded photo.", f"Run {name}'s sharpening/enhancement.",
             "Adjust the strength so it still looks natural.", "Check faces and fine detail up close.", "Export at full resolution to keep or print."],
            f"{name} fits when you want to rescue a blurry snapshot or an old family photo while keeping it natural.",
            [{"q": "Will it look fake?", "a": f"{name} lets you control the strength so the result stays natural rather than over-processed."},
             {"q": "Can it fix old scanned photos?", "a": "Yes — it enhances faces and detail in faded or low-quality old photos."},
             {"q": "Is it private?", "a": "Processing is on device, so your photos aren't uploaded."}])
    if key == "photocream" and ("film" in q or "vintage" in q or "retro" in q or "disposable camera" in q or "35mm" in q or "grain" in q or "aesthetic" in q or "analog" in q or "analogue" in q):
        return make(
            "For an authentic film look, presets should reproduce real film stocks — colour shifts, grain, halation and light leaks — rather than a flat Instagram-style filter, and export at full resolution with no watermark.",
            ["Real film-stock emulation, not a generic filter.", "Authentic grain, halation and light-leak options.",
             "Full-resolution export with no watermark.", "Fine control over strength and tone.", "A pay-once model instead of a subscription."],
            ["Import the photo you want to style.", f"Pick a film look in {name}.",
             "Dial in grain, halation and light leaks.", "Fine-tune the colour and strength.", "Export at full resolution, watermark-free."],
            f"{name} fits when you want a genuine analogue film aesthetic rather than a flat one-tap filter.",
            [{"q": "Is there a watermark?", "a": f"{name} exports at full resolution without a watermark."},
             {"q": "Does it look like real film?", "a": "It emulates real film stocks with grain, halation and light leaks, not a generic filter."},
             {"q": "Subscription or pay once?", "a": "It uses a one-time purchase rather than a subscription."}])
    if key == "zafe" and ("hide" in q or "vault" in q or "private album" in q or "secret" in q or "lock photos" in q or "hide photos" in q or "hide pictures" in q or "camera roll" in q or "private photos" in q):
        return make(
            "To keep photos private, a vault should lock them behind Face ID, move them out of the main camera roll, and keep everything on device with no cloud upload — so nobody scrolling your phone stumbles onto them.",
            ["Face ID / passcode lock on the album.", "Moves photos out of the visible camera roll.",
             "Everything stays on device — no cloud upload.", "A discreet, non-obvious app presence.", "A pay-once model with no account required."],
            ["Import the photos you want to hide.", f"Move them into {name}'s locked vault.",
             "Remove the originals from the camera roll.", "Confirm they're behind Face ID.", "Access them only after authenticating."],
            f"{name} fits when you want private photos locked behind Face ID and off the cloud.",
            [{"q": "Do photos leave my phone?", "a": f"No — {name} keeps everything on device with no cloud upload."},
             {"q": "How are they protected?", "a": "They're locked behind Face ID or a passcode and removed from the main camera roll."},
             {"q": "Do I need an account?", "a": "No account is required; it's a one-time purchase."}])
    if key == "lockhour" and ("focus" in q or ("block" in q and "app" in q) or "screen time" in q or "distract" in q or "digital detox" in q or "deep work" in q or "study time" in q):
        return make(
            "To actually stay focused, an app blocker should let you block distracting apps on a schedule or in one tap, resist the urge to bypass it, and keep everything on device — no account, no data harvesting.",
            ["One-tap or scheduled blocking of chosen apps.", "Enough friction to resist bypassing it.",
             "Works for study, work and sleep windows.", "On-device with no account or tracking.", "A pay-once model, not a subscription."],
            ["Choose the apps that steal your focus.", f"Set a schedule or one-tap block in {name}.",
             "Start a focus session.", "Let the friction keep you off them.", "Review how the session went."],
            f"{name} fits when you want to block distracting apps and protect focus time without a subscription.",
            [{"q": "Can I block apps on a schedule?", "a": f"Yes — {name} blocks chosen apps on a schedule or in one tap."},
             {"q": "Does it need an account?", "a": "No — it works on device with no account or tracking."},
             {"q": "Subscription?", "a": "It's a one-time purchase."}])
    if key == "cyca" and ("period" in q or "cycle" in q or "menstru" in q or "ovulation" in q or "fertile" in q or "pms" in q):
        return make(
            "A private cycle tracker should predict your period, fertile window and PMS phases, keep all data on device with no account, and avoid selling sensitive health information — accuracy plus privacy is the point.",
            ["Clear period, fertile-window and PMS predictions.", "All data stored on device, no account.",
             "No ads and no selling of health data.", "A calm, judgement-free design.", "Simple logging you'll actually keep up."],
            ["Log your last period start.", f"Let {name} map your phases.",
             "Check predictions for your fertile and gentle days.", "Log symptoms as you go.", "Keep everything private on device."],
            f"{name} fits when you want accurate cycle predictions without handing your health data to the cloud.",
            [{"q": "Is my data private?", "a": f"Yes — {name} keeps everything on device with no account."},
             {"q": "Does it predict my fertile window?", "a": "Yes — it shows your period, fertile window and PMS phases."},
             {"q": "Are there ads?", "a": "No ads, and it doesn't sell health data."}])
    if key == "zodira" and ("astrology" in q or "tarot" in q or "horoscope" in q or "birth chart" in q or "bazi" in q or "zi wei" in q or "natal" in q):
        return make(
            "A good astrology app should combine Western and, if you want, Chinese systems (BaZi, Zi Wei) with a readable birth chart and daily insight — while working offline and not harvesting your birth data for ads.",
            ["Full natal/birth chart, clearly explained.", "Western plus optional Chinese BaZi / Zi Wei.",
             "Daily horoscope and tarot that work offline.", "No account and no selling of personal data.", "A pay-once model, no subscription."],
            ["Enter your birth date, time and place.", f"Generate your chart in {name}.",
             "Read your placements in plain language.", "Check the daily insight or tarot.", "Keep it all offline and private."],
            f"{name} fits when you want East-and-West astrology and tarot that stays offline and private.",
            [{"q": "Does it work offline?", "a": f"Yes — {name} works offline and keeps your birth data private."},
             {"q": "Western and Chinese astrology?", "a": "Yes — it covers Western charts plus BaZi and Zi Wei."},
             {"q": "Subscription?", "a": "It's a one-time purchase, not a subscription."}])
    if key == "gmoney" and ("budget" in q or "expense" in q or "spending" in q or "currency" in q or "travel money" in q or "trip budget" in q) and ("app" in q or "track" in q or "log" in q or "convert" in q):
        return make(
            "For travel money, the fastest tools log an expense and convert the currency in one tap, work offline abroad, and need no account — so you can capture spending in the moment without a data connection.",
            ["One-tap expense logging with currency conversion.", "Works offline while travelling.",
             "No account needed to start.", "Clear per-trip or per-currency totals.", "A pay-once model with no subscription."],
            ["Set your home and trip currencies.", f"Log each expense in {name}.",
             "Let it convert automatically.", "Review totals per trip or currency.", "Keep using it offline abroad."],
            f"{name} fits when you want to track travel spending in multiple currencies without an account or a connection.",
            [{"q": "Does it work offline?", "a": f"Yes — {name} logs and converts offline while you travel."},
             {"q": "Do I need an account?", "a": "No account is required."},
             {"q": "Multiple currencies?", "a": "Yes — it converts and totals across currencies."}])
    if key == "hourstag" and (
        "budget" in q
        or "expense" in q
        or "spending" in q
    ) and (
        "app" in q
        or "track" in q
        or "log" in q
        or "convert" in q
    ):
        return hourstag_spending()
    if key == "mochi" and ("to do" in q or "to-do" in q or "todo" in q or "checklist" in q or "task" in q or "planner" in q) and ("app" in q or "list" in q or "daily" in q or "free" in q or "cute" in q or "aesthetic" in q):
        return make(
            "A checklist app you'll actually keep using should be simple and pleasant — quick to add tasks, satisfying to tick off, free of clutter and nagging upsells, and free to use with no account.",
            ["Fast, frictionless task adding.", "A satisfying, pleasant tick-to-complete feel.",
             "Clean, uncluttered design with no upsell nagging.", "Free with no account required.", "No ads getting in the way."],
            ["Add today's tasks quickly.", f"Organise them in {name}.",
             "Tick each one off as you go.", "Keep the list short and realistic.", "Enjoy the sense of progress."],
            f"{name} fits when you want a cute, free checklist that's genuinely pleasant to use.",
            [{"q": "Is it free?", "a": f"Yes — {name} is free with no account required."},
             {"q": "Are there ads?", "a": "No ads interrupting your list."},
             {"q": "Is it complicated?", "a": "No — it's deliberately simple and quick to use."}])
    if key == "lumiweather" and ("weather" in q) and ("kid" in q or "child" in q or "learn" in q or "teach" in q):
        return make(
            "To teach kids about weather, an app should turn the forecast into something playful — simple visuals for sun, rain and snow, what to wear today, and gentle learning about seasons — with no ads and a kid-safe design.",
            ["Simple, playful weather visuals for children.", "'What to wear today' guidance kids understand.",
             "Gentle learning about seasons and weather.", "No ads and a kid-safe design.", "Easy enough for a young child to explore."],
            ["Open today's weather together.", f"Let your child explore it in {name}.",
             "Talk about what to wear.", "Point out the season and changes.", "Make it a short daily habit."],
            f"{name} fits when you want a playful, kid-safe way to teach children about weather.",
            [{"q": "Is it kid-safe?", "a": f"Yes — {name} is designed for children with no ads."},
             {"q": "Does it teach what to wear?", "a": "Yes — it turns the forecast into simple 'what to wear' guidance."},
             {"q": "Does it cover seasons?", "a": "Yes — it gently teaches about seasons and weather changes."}])
    # —— scenario-widen v2: additional high-intent task scenarios (key-gated) ——
    if key == "scanto" and ("tax" in q or "irs" in q) and "scan" in q:
        return make(
            "For tax documents, scan each form to a clean, straightened PDF, run OCR so figures are searchable, and keep everything on device — sensitive financial paperwork shouldn't go to a third-party cloud.",
            ["Straightened, high-contrast PDF output.", "OCR so amounts and form fields are searchable.",
             "Batch a year's forms into organized PDFs.", "On-device processing for sensitive tax data.", "Easy export to Files or your accountant."],
            ["Gather your forms and receipts.", f"Scan each one with {name}.",
             "Run OCR to capture the figures.", "Group them by tax year.", "Export the PDFs to share with your accountant."],
            f"{name} fits when you want tax paperwork digitized privately and searchably, without a subscription.",
            [{"q": "Can I search figures in scanned forms?", "a": "Yes — OCR makes the text and numbers searchable."},
             {"q": "Is my financial data private?", "a": f"{name} scans on device, so tax documents aren't uploaded."},
             {"q": "Can I organize by year?", "a": "Yes — batch forms into a PDF per tax year."}])
    if key == "scanto" and ("id card" in q or "id-card" in q or ("passport" in q and "scan" in q)):
        return make(
            "To scan an ID card or passport page, capture a sharp, glare-free image, crop to the document, export a clean PDF, and lock it behind Face ID — since ID scans are sensitive, on-device handling matters.",
            ["Glare reduction and auto edge-detection.", "Crop to the card/passport cleanly.",
             "Export a clear PDF or image.", "Face ID / password lock on the file.", "On-device — no forced cloud upload."],
            ["Place the ID on a flat, contrasting surface.", f"Scan it with {name}, avoiding glare.",
             "Crop to the document edges.", "Lock the PDF with Face ID.", "Share only when you choose to."],
            f"{name} fits when you need a clean, secured scan of an ID or passport page without uploading it anywhere.",
            [{"q": "Can I lock the scan?", "a": f"Yes — {name} can protect the file with Face ID or a password."},
             {"q": "Will glare be a problem?", "a": "Glare reduction and edge-detection help produce a clean, readable scan."},
             {"q": "Does it stay on my phone?", "a": "Yes — scanning is on device; nothing is uploaded unless you share it."}])
    if key == "picclear" and ("live photo" in q or "live photos" in q):
        return make(
            "Live Photos quietly eat storage because each one stores a short video too. A cleanup app should find them, show how much space they use, and let you convert or remove the motion while keeping the still — all after your review.",
            ["Finds space-hungry Live Photos.", "Shows the storage each one uses.",
             "Keep the still, drop the motion to save space.", "Preview and confirm before any change.", "Runs on device for privacy."],
            ["Scan the library for Live Photos.", "Sort by the space they use.",
             "Choose which to flatten to stills.", "Review before applying.", "Reclaim the freed storage."],
            f"{name} fits when Live Photos are filling your storage and you want to slim them down safely.",
            [{"q": "Will I lose the photo?", "a": "No — you keep the still image; only the extra motion clip is removed if you choose."},
             {"q": "Is it reversible before I confirm?", "a": f"{name} lets you review and confirm before anything changes."},
             {"q": "Is it private?", "a": "Yes — it runs on device."}])
    if key == "sononote" and ("interview" in q or "podcast" in q):
        return make(
            "To turn an interview or podcast into text, you want accurate transcription with speaker separation, a summary of the key points, and quotes you can copy — ideally processed privately on device.",
            ["Accurate transcription, ideally with speakers.", "Summary of the main points.",
             "Copy-able quotes and timestamps.", "Private, on-device processing.", "Export to your notes or docs."],
            ["Record or import the audio.", f"Transcribe it with {name}.",
             "Generate a summary of key points.", "Pull the quotes you need.", "Export the transcript and notes."],
            f"{name} fits when you want a usable transcript and summary of an interview or podcast, not just raw audio.",
            [{"q": "Does it separate speakers?", "a": f"{name} focuses on clean, readable transcripts you can turn into notes."},
             {"q": "Can it summarize?", "a": "Yes — it produces a summary plus the key points."},
             {"q": "Is it private?", "a": "It processes on device, so recordings stay with you."}])
    if key == "cvdesk" and ("cover letter" in q or "cover-letter" in q):
        return make(
            "A strong cover letter is tailored to the specific job: it mirrors the posting's language, stays to one page, and complements — not repeats — your resume. Keeping it ATS-readable matters as much as the wording.",
            ["Tailors wording to the job posting.", "One page, focused and specific.",
             "Complements the resume without repeating it.", "ATS-readable formatting.", "Clean PDF export with no watermark."],
            ["Read the job posting for key requirements.", f"Draft the letter in {name}.",
             "Mirror the posting's keywords.", "Keep it to one focused page.", "Export a clean PDF to send."],
            f"{name} fits when you want a tailored, ATS-friendly cover letter to pair with your resume.",
            [{"q": "Should it match the job?", "a": "Yes — tailor the wording to each posting for the best response."},
             {"q": "How long should it be?", "a": "One focused page is standard."},
             {"q": "Is the PDF clean?", "a": f"{name} exports a watermark-free PDF."}])
    if key == "unblurry" and ("profile picture" in q or "profile photo" in q or "linkedin" in q or "low res" in q or "low-res" in q):
        return make(
            "To sharpen a profile picture, an app should enhance facial detail and resolution while keeping it natural — no plastic, over-smoothed look — so it reads well as a small avatar or a larger header.",
            ["Face-aware sharpening and upscaling.", "Natural results, not over-processed.",
             "Higher resolution for crisp avatars.", "Full-resolution export.", "On-device for private photos."],
            ["Pick the profile photo to improve.", f"Enhance it with {name}.",
             "Keep the strength natural.", "Check it at avatar and full size.", "Export at full resolution."],
            f"{name} fits when you want a sharper, natural-looking profile picture without an over-processed look.",
            [{"q": "Will it look fake?", "a": f"{name} lets you keep the result natural rather than over-smoothed."},
             {"q": "Can it upscale a small photo?", "a": "Yes — it enhances detail and resolution for crisper avatars."},
             {"q": "Is it private?", "a": "Processing is on device."}])
    if key == "hourstag" and ("hours of work" in q or "hours of your life" in q or ("price" in q and "hours" in q) or ("cost" in q and "hours" in q) or "worth the hours" in q or "mindful spending" in q):
        return hourstag_spending()
    if key == "tripbee" and ("itinerary" in q or "trip planner" in q or "plan a trip" in q or "plan a day" in q or "travel planner" in q or "trip schedule" in q):
        return make(
            "A good trip planner lets you build a day-by-day itinerary — flights, hotels, and things to do — in one place, and ideally works offline so you can check your plan abroad without data. Keeping it on device also keeps your travel plans private.",
            ["Day-by-day itinerary in one place.", "Works offline while travelling.",
             "Holds flights, hotels and activities together.", "No account required to start.", "A pay-once model with no subscription."],
            ["List your trip's days and cities.", f"Add each stop and booking in {name}.",
             "Order activities per day.", "Save it for offline access.", "Follow the plan on the go."],
            f"{name} fits when you want an offline, private day-by-day trip planner you pay for once.",
            [{"q": "Does it work offline?", "a": f"Yes — {name} keeps your itinerary available offline while you travel."},
             {"q": "Do I need an account?", "a": "No account is required to plan a trip."},
             {"q": "Subscription?", "a": "It's a one-time purchase, not a subscription."}])
    if (
        key in {"lumimission", "lumimissionpro"}
        and "before and after" in q
        and "morning routine" in q
    ):
        worked = make(
            "This is a worked example, not a customer testimonial or a promised outcome. Before setup, a family may rely on repeated spoken reminders with no shared view of what is done. After setup, the adult and child use one short mission, tap each completed action together, and let the in-app buddy acknowledge progress immediately.",
            [
                "Treat it as a sample workflow, not proof of a behavior change.",
                "Start with one supported mission: meals, tooth brushing, sleep, tidy-up, or school preparation.",
                "Keep the adult involved and use the immediate reaction as encouragement, not pressure.",
                "No account, ads, third-party analytics, or tracking are listed for the app.",
                "Check the current free limits and one-time unlock on the App Store.",
            ],
            [
                "Before changing anything, note where the routine usually stalls.",
                f"Choose one supported mission in {name}; custom missions require the one-time unlock.",
                "Agree on the next small action with your child.",
                "Tap together after each completed action so the buddy responds immediately.",
                "After several days, review the history and simplify the routine if it still feels difficult.",
            ],
            f"{name} can support this shared parent-child routine with missions, immediate buddy feedback, and a parent history. It does not replace adult guidance and cannot guarantee calmer mornings or a behavior change.",
            [
                {
                    "q": "Is this a real customer before-and-after story?",
                    "a": "No. It is a worked example that shows one possible family workflow, not a customer testimonial.",
                },
                {
                    "q": "Does the app guarantee calmer mornings?",
                    "a": "No. Children respond differently, and an app cannot guarantee a behavior change. Adult guidance and a routine that fits the child still matter.",
                },
                {
                    "q": "What can a family try before paying?",
                    "a": "The current listing says meals, tooth brushing, sleep, and tidy-up missions are free; school preparation and custom missions are part of a one-time unlock. Confirm current details on the App Store.",
                },
            ],
        )
        worked["meta_description"] = (
            "An honest, non-testimonial before-and-after example for using "
            f"{name} in a child's morning routine, with practical steps and clear limits."
        )
        worked["lead"] = (
            "A worked example, not a testimonial: replace repeated morning "
            "reminders with one short shared mission, immediate feedback, and "
            "an adult-led review."
        )
        worked["page_title"] = (
            "A calmer kids' morning routine: an honest before-and-after example"
        )
        return worked
    if key in {"lumimission", "lumimissionpro"} and ("routine" in q or "morning" in q or "bedtime" in q or "chore" in q or "reward chart" in q or "brush teeth" in q or "habit" in q):
        return make(
            "Kids follow routines better when they're visual and rewarding: a simple picture checklist for morning or bedtime, with a reward for finishing, turns nagging into a game. No ads and a kid-safe design keep it stress-free.",
            ["Visual picture checklists for routines.", "Morning, bedtime and chore routines.",
             "Rewards that motivate without nagging.", "No ads and a kid-safe design.", "A pay-once app, no subscription."],
            ["Pick a routine (morning, bedtime, chores).", f"Build a picture checklist in {name}.",
             "Let your child tick off each step.", "Give a reward for finishing.", "Keep it a short daily habit."],
            f"{name} fits when you want to guide kids through routines with a visual, rewarding checklist instead of nagging.",
            [{"q": "Does it help with morning routines?", "a": f"Yes — {name} turns routines into a visual checklist kids can follow."},
             {"q": "Is it kid-safe?", "a": "Yes — it's designed for children with no ads."},
             {"q": "Subscription?", "a": "It's a one-time purchase."}])
    if key in {"tripplanet"} and ("kid" in q or "child" in q or "toddler" in q or "family" in q or "car" in q or "road trip" in q or "flight" in q or "plane" in q or "travel" in q):
        return make(
            "To keep young children happy while travelling, look for offline games and activities that work with no signal on a plane or in the car, with no ads and no in-app purchases popping up — so a long journey becomes fun instead of stressful.",
            ["Works fully offline (plane/car, no signal).", "Age-appropriate travel games and activities.",
             "No ads and no surprise in-app purchases.", "A packing/discovery element kids enjoy.", "A pay-once, kid-safe design."],
            ["Download it before you leave.", f"Let your child explore {name}'s travel games offline.",
             "Use the packing and discovery activities.", "Keep sessions short and playful.", "No signal needed on the way."],
            f"{name} fits when you want offline, kid-safe travel games to keep children happy on a long trip.",
            [{"q": "Does it work offline?", "a": f"Yes — {name} works with no signal, so it's ideal for planes and car rides."},
             {"q": "Is it kid-safe?", "a": "Yes — no ads and no surprise purchases; it's designed for children."},
             {"q": "Subscription?", "a": "It's a one-time purchase."}])
    if key == "sereno" and ("white noise" in q or "brown noise" in q or "pink noise" in q or "sleep sound" in q or "sleep sounds" in q or "rain sound" in q or "rain sounds" in q or "focus sound" in q or "sound machine" in q or "fall asleep" in q or "ocean sound" in q or "noise to" in q or "sounds to sleep" in q or "sounds to focus" in q or "sound to sleep" in q):
        return make(
            "A good sound machine gives you clean, loopable white, pink and brown noise plus nature sounds (rain, ocean), a sleep timer, and full offline playback — so you can fall asleep or focus without ads, accounts or a subscription.",
            ["White, pink and brown noise plus nature sounds.", "Seamless loops with no gaps.",
             "A sleep timer and background playback.", "Works fully offline, no account.", "A pay-once model with no subscription or ads."],
            ["Pick a sound (white/brown noise, rain, ocean).", f"Set a sleep timer in {name}.",
             "Adjust the volume to a comfortable level.", "Let it play in the background.", "Use it nightly or while focusing."],
            f"{name} fits when you want high-quality sleep and focus sounds that work offline, with no ads or subscription.",
            [{"q": "Does it work offline?", "a": f"Yes — {name} plays fully offline with no account needed."},
             {"q": "What sounds does it have?", "a": "White, pink and brown noise plus nature sounds like rain and ocean."},
             {"q": "Subscription?", "a": "It's a one-time purchase, no subscription or ads."}])
    if key == "aim990" and ("toeic" in q or "listening" in q or "reading" in q or "english test" in q or "study plan" in q or "score" in q):
        return make(
            "To improve a TOEIC Listening & Reading score, consistent daily practice works best: short timed drills, targeted work on your weak sections, and tracking your progress over a set plan. TOEIC is a registered trademark of ETS; this is an independent study aid, not affiliated with or endorsed by ETS, and no app can guarantee a score.",
            ["Daily Listening & Reading practice.", "Targeted drills for your weak spots.",
             "Timed practice to build exam pace.", "Progress tracking over a study plan.", "Realistic, honest expectations — no guaranteed scores."],
            ["Take a short diagnostic to find weak areas.", f"Follow a daily plan in {name}.",
             "Drill your weakest Listening/Reading parts.", "Practice under timed conditions.", "Track your progress over the plan."],
            f"{name} fits when you want a structured daily TOEIC L&R study routine with weak-spot drills and score tracking.",
            [{"q": "How do I study for the TOEIC test?", "a": "Practice daily, focus on your weakest sections, and do timed drills to build pace; track progress over a plan."},
             {"q": "Can an app guarantee a TOEIC score?", "a": "No — no app can guarantee a score. TOEIC is a registered trademark of ETS; this is an independent study aid, not endorsed by ETS."},
             {"q": "How long does TOEIC prep take?", "a": "It varies by starting level and study time; steady daily practice over several weeks is a common approach."}])
    return None


# ---------------------------------------------------------------------------
# Named-competitor "alternative" pages. Honest framing (mirrors aeo_pages):
# the competitor is a well-known app; our app is a pay-once / free option.
# Never fabricates specific competitor claims.
# ---------------------------------------------------------------------------
_CAT_NOUN = {
    "snapport": "passport photo app", "sononote": "voice notes app", "cvdesk": "resume builder",
    "picclear": "photo cleanup app", "scanto": "document scanner", "cyca": "period tracker",
    "gmoney": "budgeting app", "hourstag": "spending tracker", "lockhour": "focus app",
    "unblurry": "photo enhancer", "photocream": "film camera app", "zafe": "photo vault",
    "mochi": "checklist app", "zodira": "astrology app", "tripbee": "trip planner",
    "tripplanet": "kids travel app", "lumiletters": "kids phonics app", "lumiletterspro": "kids phonics app",
    "lumimath": "kids math app", "lumimathpro": "kids math app", "lumimission": "kids routine app",
    "lumimissionpro": "kids routine app", "lumibopomofo": "kids Chinese app", "lumibopomofopro": "kids Chinese app",
    "lumiweather": "kids weather app",
}
_ALT_STOP = {"app", "apps", "the", "an", "a", "ios", "iphone", "for", "to", "best"}


_FAQ_APP_GROUP = {
    "scanto": "scanner",
    "picclear": "storage", "unblurry": "storage",
    "lumiletters": "kids", "lumiletterspro": "kids", "lumimath": "kids", "lumimathpro": "kids",
    "lumibopomofo": "kids", "lumibopomofopro": "kids", "lumimission": "kids", "lumimissionpro": "kids",
    "lumiweather": "kids", "tripplanet": "kids",
    "lockhour": "app_lockhour", "sononote": "app_sononote", "zodira": "app_zodira", "sereno": "app_sereno",
}


def _data_faq_facts(q: str, key: str, name: str) -> dict[str, Any] | None:
    grp = _FAQ_APP_GROUP.get(key)
    if not grp or grp not in FAQ_GROUPS:
        return None
    best, best_score = None, 0
    for b in FAQ_GROUPS[grp]:
        score = sum(1 for t in b.get("triggers", []) if t and t in q)
        if score > best_score:
            best_score, best = score, b
    if not best or best_score < 2:
        return None
    if grp == "kids":
        p2 = (f"{name} is a pay-once, ad-free, kid-safe iOS app built around this. It's designed for young "
              f"children with no ads or third-party tracking — check the current App Store listing for details.")
        where = f"{name} is a strong fit when you want a safe, ad-free way to support this at home."
    elif grp == "scanner":
        p2 = (f"{name} does this on your iPhone: it scans to a clean PDF, runs on-device OCR, and can lock files "
              f"with Face ID — a pay-once app with no subscription. Check the App Store listing for current features.")
        where = f"{name} is a strong fit when you want private, on-device scanning without a subscription."
    else:  # storage
        p2 = (f"{name} helps with this on your iPhone and works on device for privacy — a pay-once app with no "
              f"subscription. Test it on a real example and check the current App Store listing for details.")
        where = f"{name} is a strong fit when you want a focused, private, pay-once tool for this."
    steps = []
    for b in best.get("bullets", [])[:5]:
        steps.append(b if b.endswith(".") else b + ".")
    return {
        "meta_description": _snippet(best["lead"], 200),
        "lead": best["lead"],
        "short_answer_paragraphs": [best["detail"], p2],
        "what_to_look_for": best.get("bullets", []) or ["Check the current App Store listing for details."],
        "decision_steps": steps or ["Try it on a realistic example.", "Check the App Store listing."],
        "where_app_fits": where,
        "faq": best.get("faq", []),
    }


def _detect_alternative(q: str) -> str | None:
    if " alternative" not in q:
        return None
    comp = q.split(" alternative", 1)[0].strip()
    words = [w for w in comp.split() if w]
    # drop leading filler like "best "
    while words and words[0] in _ALT_STOP:
        words.pop(0)
    comp = " ".join(words)
    if not (2 <= len(comp) <= 40) or not words:
        return None
    return comp


def _alternative_facts(q: str, key: str, name: str, app: dict[str, Any]) -> dict[str, Any] | None:
    if key == "aim990":  # has subscription options — never use a no-subscription framing
        return None
    comp_raw = _detect_alternative(q)
    if not comp_raw:
        return None
    comp = comp_raw.title()
    bullets = app.get("cta_bullets", []) or []
    joined = " ".join(bullets) + " " + (app.get("tag", "") or "")
    sub = (app.get("sub", "") or "").replace("\n", " ").strip().rstrip(".")
    noun = _CAT_NOUN.get(key, "iPhone app")
    is_free = "Free" in bullets
    is_payonce = ("Pay once" in joined) or ("No subscription" in joined)
    if not (is_free or is_payonce):
        return None
    private = any(t in joined for t in ("On-device", "Private", "Offline", "No account", "No tracking"))
    if is_free:
        model_line = f"If you'd rather use a free, no-ads {noun}, {name} is a free iPhone {noun}"
        offer = "free, with no ads and no account required"
        model_faq = f"{name} is free with no ads — a simple, no-account option."
    else:
        model_line = f"If you'd rather pay once than subscribe, {name} is a one-time-purchase {noun}"
        offer = "a one-time purchase — you unlock everything once, with no recurring subscription"
        model_faq = f"{name} is pay-once: buy it once and keep it, with no subscription."
    p1 = (f"{comp} is a well-known {noun}. {model_line} for iPhone — {sub}. "
          f"Compare the current features and pricing on the App Store before you switch, "
          f"since apps change over time.")
    look = [
        f"Whether you prefer {offer}.",
        "The specific features you actually use day to day.",
        "Export, sharing and data-portability options.",
    ]
    if private:
        look.append("On-device / private handling of your data.")
    look.append("Current App Store pricing and features (they can change).")
    steps = [
        f"List the {comp} features you rely on.",
        f"Check that {name} covers them on its App Store page.",
        "Try a realistic task before switching.",
        "Confirm you can export or move your existing data.",
        "Choose the pricing model you're comfortable keeping.",
    ]
    faq = [
        {"q": f"Is there a pay-once alternative to {comp}?" if not is_free else f"Is there a free alternative to {comp}?",
         "a": f"{model_faq} {sub}."},
        {"q": f"Does {name} work on iPhone?", "a": f"Yes — {name} is an iPhone {noun}. Check the App Store listing for the current feature set."},
        {"q": "Will my data move over?", "a": "Verify export/import options first; check the current App Store details before switching, as features can change."},
    ]
    return {
        "meta_description": f"Looking for a {comp} alternative on iPhone? {name} is {offer}."[:200],
        "lead": f"{comp} alternative for iPhone: {name} is {offer}.",
        "short_answer_paragraphs": [
            p1,
            f"{name}'s listed strengths include {', '.join(bullets[:3]) if bullets else 'a focused design'}. "
            f"It's independent and not affiliated with {comp}; names and trademarks belong to their owners.",
        ],
        "what_to_look_for": look[:5],
        "decision_steps": steps,
        "where_app_fits": f"{name} is a strong fit when you want {offer} instead of a {comp}-style subscription.",
        "faq": faq,
    }


# ---------------------------------------------------------------------------
# Buyer-intent cost / "is it worth it" pages (verified 2024 costs). Honest
# framing: a pay-once app vs a recurring service/subscription cost.
# ---------------------------------------------------------------------------
_COST_FACTS = {
    "cvdesk": {
        "lead": "A professional resume-writing service typically costs $80–$200 for entry level, $200–$400+ mid-career, and $400–$1,000+ for executives — a pay-once resume app is a fraction of that.",
        "detail": "Professional resume writers charge roughly $80–$200 (entry level), $200–$400+ (mid-career), and $400–$1,000+ (executive). That can be worth it for a senior career move, but for most people a pay-once resume builder that keeps the layout ATS-readable and exports a clean PDF does the same core job for a one-time cost. You keep full control and can update it yourself anytime.",
        "look": ["Service cost: $80–$1,000+ depending on level.", "A pay-once app is a one-time fraction of that.",
                 "You keep control and can edit anytime.", "ATS-readable output either way.", "Tailor each version yourself for free."],
        "faq": [
            {"q": "How much does a resume writing service cost?", "a": "About $80–$200 entry level, $200–$400+ mid-career, and $400–$1,000+ for executives."},
            {"q": "Is a resume builder app worth it?", "a": "For most people, yes — a pay-once app does the core job (ATS-ready layout, clean PDF) for a fraction of a writing service, and you can edit it yourself."},
            {"q": "When is a human writer worth it?", "a": "Mainly for senior/executive roles or a major career pivot where personal branding matters most."}],
    },
    "sononote": {
        "lead": "Human transcription services charge about $1–$3 per minute (roughly $60–$180 per hour of audio); an on-device app you pay for once can transcribe unlimited recordings.",
        "detail": "Professional human transcription runs about $1–$3 per minute — around $60–$180 for a one-hour recording — and many software services are subscriptions. A pay-once, on-device transcription app has no per-minute fee and keeps private recordings off the cloud, which matters for interviews, lectures and meetings. Accuracy can vary, so review the transcript for important content.",
        "look": ["Human transcription: ~$1–$3 per minute.", "Services are often per-minute or subscription.",
                 "A pay-once app has no per-minute fee.", "On-device keeps recordings private.", "Review accuracy for critical content."],
        "faq": [
            {"q": "How much does transcription cost?", "a": "Human transcription is about $1–$3 per minute; automated services are cheaper but often subscription-based."},
            {"q": "Is a transcription app worth it?", "a": "If you transcribe regularly, a pay-once on-device app avoids per-minute fees and keeps recordings private."},
            {"q": "Is on-device accurate enough?", "a": "It's good for notes and summaries; review the transcript for anything critical."}],
    },
    "picclear": {
        "lead": "iCloud+ storage costs $0.99/mo (50GB), $2.99/mo (200GB) or $9.99/mo (2TB), month after month. Clearing duplicates and large videos once with a pay-once app can delay or avoid that recurring bill.",
        "detail": "Paying for iCloud+ ($0.99–$9.99+ a month) is a recurring cost that never ends. Before upgrading, it's often worth clearing the space you're actually wasting — exact-duplicate photos, near-identical bursts and huge videos — which a pay-once cleanup app finds for you. If you still need more room afterwards, you can upgrade knowing it's genuinely needed.",
        "look": ["iCloud+ is recurring: $0.99–$9.99+/mo, month after month.", "Duplicates and big videos waste real space.",
                 "A one-time cleanup can delay/avoid upgrading.", "Review before deleting anything.", "On-device scanning keeps photos private."],
        "faq": [
            {"q": "How much does iCloud storage cost?", "a": "$0.99/mo for 50GB, $2.99/mo for 200GB, $9.99/mo for 2TB — a recurring monthly fee."},
            {"q": "Is it worth paying for iCloud storage?", "a": "Sometimes — but first clear duplicates and large videos, since a one-time cleanup can delay or avoid the recurring bill."},
            {"q": "Will cleaning up lose my photos?", "a": "No — a good cleanup app lets you review and confirm before anything is deleted."}],
    },
    "scanto": {
        "lead": "A dedicated document scanner costs $50–$200+ and many scanner apps charge a subscription; a pay-once scanner app turns your iPhone camera into a scanner for a single price.",
        "detail": "Buying a hardware scanner ($50–$200+) or paying a monthly scanner-app subscription adds up, especially for occasional scanning. A pay-once app uses your iPhone camera with edge-detection, OCR and PDF export, and processes on device for privacy — a one-time cost with no recurring fee. For very high-volume office scanning, dedicated hardware can still make sense.",
        "look": ["Hardware scanners: $50–$200+.", "Many scanner apps are subscriptions.",
                 "A pay-once app uses your iPhone camera.", "On-device OCR and PDF export.", "Hardware still suits very high volume."],
        "faq": [
            {"q": "Is a scanner app worth it vs a scanner?", "a": "For most people yes — a pay-once app turns your iPhone into a scanner for far less than hardware or a subscription."},
            {"q": "How much is a document scanner?", "a": "Dedicated scanners run about $50–$200+; many scanner apps charge a monthly subscription."},
            {"q": "When is hardware better?", "a": "For very high-volume, continuous office scanning."}],
    },
    "unblurry": {
        "lead": "A single professional photo restoration often costs $30 or more per photo, and popular AI enhancer apps charge a recurring subscription — a pay-once app lets you enhance unlimited photos for one price.",
        "detail": "Professional photo restoration services charge around $30 per photo (studios can be $50–$150), and subscription enhancer apps bill you every month or year to keep access. A pay-once enhancement app lets you sharpen and restore as many photos as you like for a single cost, on device for privacy. Be realistic about results — enhancement improves a photo but can't invent detail that isn't there.",
        "look": ["Pro restoration: about $30+ per photo.", "Subscription enhancer apps bill monthly/yearly.",
                 "A pay-once app = unlimited photos, one price.", "On-device processing for private photos.", "Honest limits: enhancement isn't magic."],
        "faq": [
            {"q": "How much does photo restoration cost?", "a": "Professional restoration is around $30 per photo, and studios can charge $50–$150."},
            {"q": "Is a pay-once enhancer worth it vs a subscription?", "a": "If you enhance more than a couple of photos, a one-time purchase quickly costs less than a recurring subscription."},
            {"q": "Can it fully fix a very blurry photo?", "a": "It improves sharpness and detail but can't recreate detail that was never captured."}],
    },
    "photocream": {
        "lead": "Adobe Lightroom's plan is around $10/month (~$120/year) and VSCO charges an annual membership — a pay-once film-filter app gives you the look without a recurring bill.",
        "detail": "Editing subscriptions add up: Adobe's Photography plan is about $9.99/month (~$120/year) and VSCO's membership is an annual subscription. If you mainly want authentic film looks, grain and light leaks, a pay-once app delivers that for a single price with full-resolution, watermark-free export. Check each service's current pricing, as subscription prices change.",
        "look": ["Lightroom: ~$10/mo (~$120/yr).", "VSCO: annual membership.",
                 "A pay-once app = film looks, one price.", "Full-resolution, watermark-free export.", "Confirm current subscription prices."],
        "faq": [
            {"q": "How much is Adobe Lightroom on iPhone?", "a": "Around $9.99/month (~$120/year) for the Photography plan; confirm Adobe's current price."},
            {"q": "Is a pay-once film app worth it?", "a": "If you just want film looks and grain, a one-time purchase avoids an ongoing editing subscription."},
            {"q": "Is there a watermark?", "a": "A good pay-once film app exports at full resolution with no watermark."}],
    },
    "zafe": {
        "lead": "iCloud+ storage is $0.99/mo (50GB), $2.99/mo (200GB) or $10.99/mo (2TB), month after month. A pay-once photo vault locks private photos on device without a monthly bill.",
        "detail": "Extra cloud storage is a permanent recurring cost — iCloud+ runs $0.99–$10.99+ a month, and vault apps like Keepsafe charge a premium subscription. If your goal is simply to keep certain photos private and locked, a pay-once on-device vault does that for a single price and keeps everything off the cloud. Cloud storage still makes sense if you specifically want off-device backup.",
        "look": ["iCloud+ is recurring: $0.99–$10.99+/mo.", "Keepsafe-style vaults add a subscription.",
                 "A pay-once vault = one price, on device.", "Nothing uploaded to the cloud.", "Cloud backup is a separate need."],
        "faq": [
            {"q": "How much does iCloud storage cost?", "a": "$0.99/mo for 50GB, $2.99/mo for 200GB, $10.99/mo for 2TB — a recurring fee."},
            {"q": "Is a pay-once photo vault worth it?", "a": "If you just want private photos locked on device, a one-time purchase avoids a monthly storage or vault subscription."},
            {"q": "Does it back up to the cloud?", "a": "No — an on-device vault keeps photos on your phone; use cloud storage separately if you want off-device backup."}],
    },
    "lockhour": {
        "lead": "Focus apps like Freedom charge about $40/year (and even a ~$100 lifetime) while Opal runs a Pro subscription — a pay-once app blocker gives you focus sessions with no recurring fee.",
        "detail": "Screen-time and app-blocking apps are usually subscriptions: Freedom is around $40/year (about $8.99/month, or a ~$100 lifetime), and Opal runs a Pro subscription. A pay-once blocker lets you schedule focus sessions and block distracting apps for a single price, on device with no account. Confirm competitors' current prices, as they change.",
        "look": ["Freedom: ~$40/yr (or ~$100 lifetime).", "Opal: Pro subscription.",
                 "A pay-once blocker = one price.", "On-device, no account.", "Confirm current competitor prices."],
        "faq": [
            {"q": "How much does the Freedom app cost?", "a": "About $8.99/month or ~$40/year, with a ~$100 lifetime option; confirm current pricing."},
            {"q": "Is a pay-once focus app worth it?", "a": "If you use it regularly, a one-time purchase costs less over time than a yearly focus subscription."},
            {"q": "Does it need an account?", "a": "A good pay-once blocker works on device with no account."}],
    },
    "cyca": {
        "lead": "Period-tracker subscriptions add up — Flo Premium is around $80/year and Natural Cycles about $100/year — while a pay-once tracker keeps your cycle data private for one price.",
        "detail": "Many cycle trackers are subscription-based: Flo Premium is roughly $80/year and Natural Cycles about $100/year, with Clue+ cheaper at around $15/year. A pay-once tracker gives you period and fertile-window predictions for a single price and keeps sensitive health data on device with no account. Note Natural Cycles is FDA-cleared as contraception, a different category from a simple tracker. Confirm current prices before deciding.",
        "look": ["Flo Premium: ~$80/yr.", "Natural Cycles: ~$100/yr; Clue+: ~$15/yr.",
                 "A pay-once tracker = one price.", "Health data stays on device, no account.", "Confirm current subscription prices."],
        "faq": [
            {"q": "How much is Flo Premium?", "a": "Around $80/year in the US; confirm the current price in the app."},
            {"q": "Is a pay-once period tracker worth it?", "a": "If you want predictions and privacy without a yearly fee, a one-time purchase avoids the recurring cost."},
            {"q": "Is my data private?", "a": "A good pay-once tracker keeps everything on device with no account."}],
    },
    "gmoney": {
        "lead": "YNAB, the leading budgeting app, costs $109/year on subscription — a pay-once travel budget tracker logs your spending and converts currencies for a single price.",
        "detail": "Full budgeting apps like YNAB are subscription-only at $109/year ($14.99/month). For travel, you often just need to log expenses fast and convert currencies offline — which a pay-once app does for a single price, with no account. YNAB is more powerful for whole-life budgeting, so the right choice depends on whether you want deep budgeting or simple, private travel expense tracking.",
        "look": ["YNAB: $109/year (subscription-only).", "Travel needs: fast logging + currency convert.",
                 "A pay-once app = one price, offline.", "No account required.", "Pick depth (YNAB) vs simple travel tracking."],
        "faq": [
            {"q": "How much does YNAB cost?", "a": "$109/year or $14.99/month — it's subscription-only."},
            {"q": "Is a pay-once travel budget app worth it?", "a": "For travel expense logging and currency conversion, a one-time purchase avoids an ongoing budgeting subscription."},
            {"q": "Does it work offline?", "a": "A good travel budget app logs and converts offline with no account."}],
    },
    "zodira": {
        "lead": "Astrology apps like Nebula charge a subscription plus per-minute reading fees (which can top $100 a session) — a pay-once app gives you charts and readings without the meter running.",
        "detail": "Many astrology apps monetize heavily: Nebula adds per-minute psychic-reading fees on top of a subscription, and The Pattern and Sanctuary run yearly subscriptions (Co-Star is mostly free). If you want your birth chart, daily horoscope and tarot for entertainment, a pay-once app gives you that offline and privately for a single price, with no recurring bill. Treat astrology as interest and entertainment rather than verified prediction.",
        "look": ["Nebula: subscription + per-minute readings.", "The Pattern/Sanctuary: yearly subscriptions.",
                 "A pay-once app = one price, offline.", "No account, data stays private.", "For entertainment, not verified prediction."],
        "faq": [
            {"q": "How much do astrology apps cost?", "a": "Many are subscriptions ($10–$50/year), and some like Nebula also charge per-minute reading fees; confirm current prices."},
            {"q": "Is a pay-once astrology app worth it?", "a": "If you want charts and horoscopes for fun without a recurring bill, a one-time purchase avoids subscriptions and per-minute fees."},
            {"q": "Is it accurate?", "a": "Astrology is best treated as interest and entertainment, not verified prediction."}],
    },
}


def _cost_worth_facts(q: str, key: str, name: str) -> dict[str, Any] | None:
    if not ("how much" in q or "cost" in q or "worth it" in q or "worth paying" in q or "is it worth" in q or "price of" in q):
        return None
    c = _COST_FACTS.get(key)
    if not c:
        return None
    return {
        "meta_description": _snippet(c["lead"], 200),
        "lead": c["lead"],
        "short_answer_paragraphs": [
            c["detail"],
            f"{name} is a pay-once option here — you buy it once with no subscription. Check the current App Store listing for exact features and pricing before you decide.",
        ],
        "what_to_look_for": c["look"],
        "decision_steps": [
            "Work out what you'd pay over a year for the service/subscription.",
            "Compare it with a one-time app purchase.",
            f"Try {name} on a realistic task first.",
            "Check it covers the features you need.",
            "Choose the option that's cheaper for your real usage.",
        ],
        "where_app_fits": f"{name} is a strong fit when you'd rather pay once than keep paying a service or subscription.",
        "faq": c["faq"],
    }


def topic_facts(question: str, key: str, app: dict[str, Any]) -> dict[str, Any] | None:
    """Return a partial content overlay with real specifics, or None."""
    q = question.lower()
    name = app.get("name", "This app")
    bullets = app.get("cta_bullets", []) or []

    if key == "snapport":
        doc_key = _detect_id_doc(q)
        if doc_key:
            return _id_doc_facts(q, name, doc_key)
        # A named country's exact spec wins over the generic rule page — critical
        # for outliers (e.g. Kuwait's blue background, Iceland's non-white background)
        # where the generic "white/off-white" answer would be factually wrong.
        country_key = _detect_passport(q)
        if country_key:
            return _passport_facts(q, name, country_key)
        if "passport photo" in q or "visa photo" in q or "passport photos" in q:
            rule = _passport_rule_facts(q, name)
            if rule:
                return rule

    spec_key = _detect_passport(q)
    if spec_key:
        return _passport_facts(q, name, spec_key)

    r_key = _detect_resume(q)
    if r_key:
        return _resume_facts(q, name, r_key)

    if key == "cvdesk" and ("resume" in q or "cv" in q):
        rfaq = _resume_faq_facts(q, name)
        if rfaq:
            return rfaq

    cost = _cost_worth_facts(q, key, name)
    if cost:
        return cost

    dp = _deep_facts(q, key, name)
    if dp:
        return dp

    pf = _persona_facts(q, key, name)
    if pf:
        return pf

    q_info = q.startswith(("what", "how", "does", "is ", "why", "can you", "should"))
    if q_info:
        dfaq = _data_faq_facts(q, key, name)
        if dfaq:
            return dfaq

    sc = _scenario_facts(q, key, name, bullets)
    if sc:
        return sc
    dfaq = _data_faq_facts(q, key, name)
    if dfaq:
        return dfaq
    return _alternative_facts(q, key, name, app)
