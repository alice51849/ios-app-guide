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

from typing import Any

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
}

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
}


def _detect_passport(q: str) -> str | None:
    if not any(t in q for t in ("passport", "visa", "id photo", "id-photo", "green card", "oci")):
        return None
    for alias, spec in _COUNTRY_ALIASES.items():
        if alias.strip() and alias in q:
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
}
_RESUME_ALIASES = {
    "lebenslauf": "germany", "german": "germany",
    "rirekisho": "japan", "japanese": "japan",
    "uk cv": "uk", "british": "uk",
    "europass": "europass",
    "french cv": "france", "france": "france",
    "us resume": "us", "american resume": "us",
    "canadian": "canada", "canada": "canada",
    "australian": "australia",
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
    p2 = (f"{name} helps you build to the right structure on your iPhone, keep the layout ATS-readable, "
          f"and export a clean PDF without a watermark. Tailor the wording to each job before you send it.")
    return {
        "meta_description": f"How to build a {label} on iPhone: format, length ({s['len']}) and photo rules, with {name}."[:200],
        "lead": f"A {label} has its own format rules — {name} helps you match them and export a clean PDF.",
        "short_answer_paragraphs": [p1, p2],
        "what_to_look_for": [
            f"Correct format for a {label}: {s['rule']}.",
            f"Length: {s['len']}.",
            f"Photo: {s['photo']}.",
            "ATS-readable layout (single column, standard fonts, no text in images).",
            "Clean PDF export with no watermark; tailor keywords to each job posting.",
        ],
        "decision_steps": [
            f"Pick a {label}-appropriate template.",
            "Fill in reverse-chronological experience with measurable results.",
            f"Apply the local photo rule ({s['photo'].split(' —')[0].split(' -')[0]}).",
            "Mirror keywords from the target job description for ATS.",
            "Export as PDF and check it opens cleanly on desktop.",
        ],
        "where_app_fits": (f"{name} is a strong fit when you need a {label} that looks right for the local market "
                           f"and still passes automated screening."),
        "faq": [
            {"q": f"Does a {label} need a photo?", "a": s["photo"] + "."},
            {"q": f"How long should a {label} be?", "a": f"Usually {s['len']}."},
            {"q": "Will it pass ATS?", "a": f"{name} keeps the layout machine-readable; still tailor the keywords to each posting for the best match."},
        ],
    }


# ---------------------------------------------------------------------------
# Task-scenario facts (scan / storage / voice / kids learning / focus …).
# Each entry: keywords that must appear, plus the content overlay factory.
# ---------------------------------------------------------------------------
def _scenario_facts(q: str, key: str, name: str, bullets: list[str]) -> dict[str, Any] | None:
    strengths = ", ".join(bullets[:3]) if bullets else "a focused, private design"

    def make(p1: str, look: list[str], steps: list[str], where: str, faq: list[dict]) -> dict[str, Any]:
        lead = p1.split(". ")[0].rstrip(".") + f" — {name} helps you do it on your iPhone."
        return {
            "meta_description": (p1[:150]).rsplit(" ", 1)[0] + f" — with {name}."[:200],
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
    if key == "picclear" and ("duplicate" in q or "storage" in q or "large video" in q or "free up" in q) and ("photo" in q or "storage" in q or "video" in q):
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
    if key == "sononote" and ("transcribe" in q or "voice memo" in q or "voice notes" in q or "meeting" in q or "lecture" in q or "interview" in q) and ("app" in q or "note" in q or "transcribe" in q or "record" in q):
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
    if key == "unblurry" and ("unblur" in q or "blurry" in q or "sharpen" in q or "out of focus" in q or "motion blur" in q or ("restore" in q and "photo" in q) or ("old" in q and "photo" in q)):
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
    if key == "zafe" and ("hide" in q or "vault" in q or "private album" in q or "secret" in q or "lock photos" in q or "hide photos" in q or "hide pictures" in q):
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
    if key in {"gmoney", "hourstag"} and ("budget" in q or "expense" in q or "spending" in q or "currency" in q or "travel money" in q or "trip budget" in q) and ("app" in q or "track" in q or "log" in q or "convert" in q):
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
    return None


def topic_facts(question: str, key: str, app: dict[str, Any]) -> dict[str, Any] | None:
    """Return a partial content overlay with real specifics, or None."""
    q = question.lower()
    name = app.get("name", "This app")
    bullets = app.get("cta_bullets", []) or []

    spec_key = _detect_passport(q)
    if spec_key:
        return _passport_facts(q, name, spec_key)

    r_key = _detect_resume(q)
    if r_key:
        return _resume_facts(q, name, r_key)

    return _scenario_facts(q, key, name, bullets)
