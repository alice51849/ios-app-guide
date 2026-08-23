"""Frozen source specification for the Google Images real-task canary."""

from __future__ import annotations


def _asset(
    app: str,
    number: str,
    sha256: str,
    screen_description: str,
) -> dict[str, object]:
    asset_id = f"{app}-{number}"
    return {
        "id": asset_id,
        "source_path": f"00_GrowthEngine/social/assets/{app}/{number}.png",
        "public_path": f"media/google-images-canary/{asset_id}.png",
        "sha256": sha256,
        "width": 1320,
        "height": 2868,
        "locale": "en-US",
        "source_type": "app_store_screenshot",
        "screen_description": screen_description,
    }


def _task(
    task_id: str,
    asset: str,
    title: str,
    problem: str,
    steps: tuple[str, str, str],
    result: str,
    image_context: str,
) -> dict[str, object]:
    return {
        "id": task_id,
        "asset": asset,
        "title": title,
        "problem": problem,
        "steps": list(steps),
        "result": result,
        "image_context": image_context,
    }


APPS = [
    {
        "key": "unblurry",
        "name": "Unblurry",
        "category": "Photo & utility",
        "schema_category": "PhotographyApplication",
        "app_store_id": "6782275018",
        "app_store_url": "https://apps.apple.com/app/id6782275018",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/unblurry.html",
        "campaign_token": "gimg_unblurry",
        "value_prop": "Blurry photo? Make it crystal clear.",
        "limitation": (
            "Enhancement can make existing edges and texture easier to see, but "
            "it cannot recover detail the camera never captured. Inspect faces, "
            "text, and fine patterns at full size before keeping the export."
        ),
        "assets": [
            _asset(
                "unblurry",
                "01",
                "64bb6b91dfdeccc39c346917ee879951b71d68521ec8e77b5bd620d3bf35e851",
                "before-and-after comparison screen",
            ),
            _asset(
                "unblurry",
                "02",
                "dd3bfb73acf0c2138db0a800ffff39427ca448147aaf0b2ba7591421c6f3dd46",
                "on-device enhancement progress screen",
            ),
            _asset(
                "unblurry",
                "03",
                "7e38edfee93b59d01c99d7a5d4b1212329faa711652e7ae1741dde489176301c",
                "enhancement-mode selection screen",
            ),
        ],
    },
    {
        "key": "scanto",
        "name": "ScanTo Pro",
        "category": "Productivity",
        "schema_category": "BusinessApplication",
        "app_store_id": "6779977651",
        "app_store_url": "https://apps.apple.com/app/id6779977651",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/scanto.html",
        "campaign_token": "gimg_scanto",
        "value_prop": (
            "Scan, organize, search, and protect documents on the device."
        ),
        "limitation": (
            "A phone scan is a convenient working copy, not automatically a "
            "certified original. Review every crop and OCR result, and follow "
            "the recipient's rules for signatures, identity, and retention."
        ),
        "assets": [
            _asset("scanto", "01", "71c7bac254649187f70738613e8a01173852efd99e277e888452164a35843922", "scan-or-import home screen"),
            _asset("scanto", "02", "a070f3d955bb82ce322e58b9263ed7bef0a8fa28442a44dd54b07a3ec22584fa", "organized document library"),
            _asset("scanto", "04", "65763461a4b18467f43c74ebb857252bcb4bb6c260a78b6c288fed8720baf973", "document viewer and quality controls"),
            _asset("scanto", "05", "6bde55759e6d74575a404655ddd1e52bad1ce2361c6bd9ad206a46e6cadbf4e4", "on-device OCR search results"),
            _asset("scanto", "06", "f74fc856574f9354281d341a061041030baa2c0114930059fbe4accb2ab60754", "Face ID document lock"),
            _asset("scanto", "07", "686f0b0bf515dfc1b3d821eba2ae6b5f7aac19f1328413909ae71e38343b12f1", "password-protected PDF sharing"),
            _asset("scanto", "08", "a6d4eef91a9d55e55745e69d6fbdc24a426645785d90767379490695f2969d12", "sharp multipage PDF preview"),
            _asset("scanto", "09", "8c069a0b8c34f8a34f218b64d09b8401a48e6e43caa03cbff8b5118f75cbc9a0", "private on-device processing explanation"),
            _asset("scanto", "10", "cb73c13e592c4dd78455434e569b9560d5a2dc424428e475116ad65783820c23", "workflow and app-lock settings"),
        ],
    },
    {
        "key": "cyca",
        "name": "Cyca",
        "category": "Health",
        "schema_category": "HealthApplication",
        "app_store_id": "6782251621",
        "app_store_url": "https://apps.apple.com/app/id6782251621",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/cyca.html",
        "campaign_token": "gimg_cyca",
        "value_prop": "A warm, private way to understand your cycle.",
        "limitation": (
            "Cycle estimates are informational patterns, not diagnosis, "
            "contraception, or a promise about fertility. Record what actually "
            "happens and consult a qualified clinician about concerning changes."
        ),
        "assets": [
            _asset("cyca", "01", "b4944573aed8cc5392d9aacf356eb9c7c18b24f6d51d2f0802180e01d88cad77", "today and current-cycle overview"),
            _asset("cyca", "02", "7edd4d28dbe30c76f314f422fbbb72f99013c4e6fcc67a147df1156e1ea9d779", "daily body forecast"),
            _asset("cyca", "03", "83b213f151f36090b20c11293ce1a15f04f18ed02fcc0f5989322ed2c2a32087", "cycle calendar"),
            _asset("cyca", "04", "3e0b9b76c906f0b0535fd930f808a4a239c677a77297453d8c51a4223121cb45", "personal rhythm insights"),
            _asset("cyca", "05", "436cdef7e2c0bf2dc69225f0aaa7c05da4106f9c8583d188e9237b4e17a00afb", "gentle daily-care suggestions"),
            _asset("cyca", "06", "14e20ff804c76383419cdd9093b8c090c714da7cbf71559fe126bfc50df979b4", "smart planner"),
        ],
    },
    {
        "key": "gmoney",
        "name": "G+Money",
        "category": "Money & travel",
        "schema_category": "FinanceApplication",
        "app_store_id": "6755782939",
        "app_store_url": "https://apps.apple.com/app/id6755782939",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/gmoney.html",
        "campaign_token": "gimg_gmoney",
        "value_prop": "Convert and log travel spending in one place, including offline.",
        "limitation": (
            "G+Money is a manual travel ledger, not a bank feed or accounting "
            "system. Exchange-rate totals are planning aids; verify card fees, "
            "cash conversions, receipts, and official reimbursement rules."
        ),
        "assets": [
            _asset("gmoney", "01", "57c8bb957fb06854cbc924a836f31ea84c513eb149c934e7bff30dc99f0bf47b", "currency conversion and expense-entry screen"),
            _asset("gmoney", "02", "e82becbf3266942714e780dddaeab62f2ee7a3b34d8911cac7ec8f07738c3264", "trip spending summary and category view"),
            _asset("gmoney", "03", "12424580b64282fe1e8d9af5700fc2c7399b059fac25409d8448b3128abc8623", "private offline travel ledger"),
        ],
    },
    {
        "key": "lumiletters",
        "name": "Lumi Letters",
        "category": "Kids & learning",
        "schema_category": "EducationalApplication",
        "app_store_id": "6778748533",
        "app_store_url": "https://apps.apple.com/app/id6778748533",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/lumiletters.html",
        "campaign_token": "gimg_lumiletters",
        "value_prop": "Playful phonics, tracing, and letter practice for young learners.",
        "limitation": (
            "The activities support practice but do not guarantee a reading "
            "milestone or replace an educator's assessment. An adult should "
            "choose a short session, observe comfort, and stop before frustration."
        ),
        "assets": [
            _asset("lumiletters", "01", "f676e1409dfea8cb20f72f018a9cfc9d2ffaae3a1d39de6ada8d4ea7163cdfc4", "letter-learning adventure home"),
            _asset("lumiletters", "02", "8c714932367f2e99e3d00f99ea8e47a95e1dd301d7faf1fbb4d28cdfa1f39b20", "single-letter sound and word activity"),
            _asset("lumiletters", "03", "41e2e1bbe0bad3c83823b8863c35eb1868c78b075d755136e8241444a704a79f", "uppercase and lowercase letter grid"),
            _asset("lumiletters", "04", "63b5139dbe0a0cc08b92f146d0a6206963fcf691545d92a0948b44f87dc0db3d", "learning-progress dashboard"),
            _asset("lumiletters", "05", "50834f77d39eb5f1341db02f0dd55b6d593f97b6bab3181232d845279cad9cb5", "guided letter tracing"),
            _asset("lumiletters", "06", "d98d43250356d0be8da041481b909aa16a718d4b873816e46b8c1aa3c8e5826e", "letter-galaxy reward screen"),
            _asset("lumiletters", "07", "4f45d07eed9c911bbb9f2b3e03b31476a265b8e5c17b51c869c3f2c8f2698241", "printable letter worksheet"),
            _asset("lumiletters", "08", "6c65796796f20e242fb20f4e9f96c61a2a8507083bc3f99a5ac5c926dd6622f4", "matching-letter game"),
            _asset("lumiletters", "09", "3ccd32fce1867162811c07500d8ee967fc97c4b57b2ae0da25dfca814978bfcd", "listen-and-find letter-sound game"),
            _asset("lumiletters", "10", "f98d44c0beb2370771983f7438be4692ba45db21027b22d07d3cee4d07ab0ecb", "parent sound, music, and language settings"),
        ],
    },
    {
        "key": "aim990",
        "name": "Aim990",
        "category": "Education",
        "schema_category": "EducationalApplication",
        "app_store_id": "6784974530",
        "app_store_url": "https://apps.apple.com/app/id6784974530",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/aim990.html",
        "campaign_token": "gimg_aim990",
        "value_prop": "Daily listening and reading plans, weak-spot drills, and progress tracking.",
        "limitation": (
            "Aim990 supports study planning and practice; it does not guarantee "
            "a score or represent ETS. TOEIC is a trademark of ETS, which does "
            "not sponsor or endorse this page or app."
        ),
        "assets": [
            _asset("aim990", "01", "7bea8645ba3f2fefdf8929a636bf3d7ab041b2858af43d5d0065325a9b2b22bb", "30-day target-score plan"),
            _asset("aim990", "02", "c039534c272261a301f5cc5475ef231c908543cd5f3683f7b3cf3021c7c9be50", "timed listening and reading practice"),
            _asset("aim990", "03", "c911923ce3586e206967f28dcd03486f1cc14bdc7649a181d4ea74f33c5661ab", "weak-skill analysis"),
            _asset("aim990", "04", "1fb1449f0b4e62020d7f1ea9194e7dd431c9d20151ec67c65520d5af082f5e4d", "full and mini mock-test choices"),
        ],
    },
    {
        "key": "sereno",
        "name": "Sereno",
        "category": "Sleep & focus",
        "schema_category": "HealthApplication",
        "app_store_id": "6788236641",
        "app_store_url": "https://apps.apple.com/app/id6788236641",
        "guide_url": "https://alice51849.github.io/ios-app-guide/en-US/sereno.html",
        "campaign_token": "gimg_sereno",
        "value_prop": "Layer living sounds for sleep, focus, and calm, including offline.",
        "limitation": (
            "Sereno is an ambient-sound tool, not treatment for insomnia, "
            "tinnitus, anxiety, or another condition. Keep volume comfortable, "
            "preserve awareness when safety matters, and seek professional care "
            "for persistent symptoms."
        ),
        "assets": [
            {
                **_asset("sereno", "01", "3ef0e6cacd0084a2c247665aca417798c7de464e17bfe3c4fb0c9380215b2fa9", "living-sound library"),
                "width": 1290,
                "height": 2802,
            },
            {
                **_asset("sereno", "02", "c0e36f12c009ff8ee2bb1378a76a3535645f09fb810013e46a3879a3235fd1ac", "ready-made ambient scene"),
                "width": 1290,
                "height": 2802,
            },
            {
                **_asset("sereno", "03", "c3035f9e3fbdf5077558ee286ce78d6e091786f93b1a05513aba10ccd60560b3", "layered sound mixer"),
                "width": 1290,
                "height": 2802,
            },
        ],
    },
]


PAIRS = [
    {
        "id": "unblurry-p01",
        "app": "unblurry",
        "variants": [
            _task("unblurry-soft-portrait", "unblurry-01", "How can I check a slightly soft portrait before sharing it?", "A favorite portrait looks soft around the eyes, but aggressive sharpening could make skin and hair look artificial.", ("Open the original portrait rather than a social-media copy.", "Run one conservative enhancement and use the comparison control around eyes, hair, and edges.", "Keep the export only if facial detail looks natural at full size."), "You get a reviewed portrait candidate, not an automatic promise that every blurred facial detail has been restored.", "checking a soft portrait before export"),
            _task("unblurry-moving-pet", "unblurry-02", "Can I improve a pet photo with mild motion softness?", "The pet moved as the shutter fired, leaving usable color and shape but soft fur and eyes.", ("Choose the least-compressed original in Photos.", "Apply one enhancement pass and wait for the on-device preview.", "Compare fur, whiskers, and eye boundaries before saving a separate copy."), "The useful outcome is a cleaner keepsake when source detail exists, while the untouched original remains available.", "reviewing mild motion softness in a pet photo"),
        ],
    },
    {
        "id": "unblurry-p02",
        "app": "unblurry",
        "variants": [
            _task("unblurry-old-family-scan", "unblurry-03", "How should I test enhancement on an old family-photo scan?", "A small scan has compression and soft edges, and the goal is a cleaner viewing copy without rewriting faces.", ("Duplicate the highest-resolution scan.", "Try the mode that best matches the amount of softness, then inspect the preview.", "Compare eyes, jewelry, fabric, and printed text before exporting."), "You finish with a cautiously reviewed derivative suitable for viewing, while preserving the archival scan.", "testing an old family-photo scan"),
            _task("unblurry-messaged-travel-photo", "unblurry-01", "Can a compressed travel photo be made easier to view?", "A travel photo sent through messaging has lost crispness even though the landmark and people remain recognizable.", ("Find the least-compressed version available.", "Enhance it once and move the comparison line across faces and architectural edges.", "Export only after checking for halos and invented-looking texture."), "The result is a separate viewing copy whose improvement has been visually checked against the source.", "comparing a compressed travel photo"),
        ],
    },
    {
        "id": "unblurry-p03",
        "app": "unblurry",
        "variants": [
            _task("unblurry-digital-zoom-landscape", "unblurry-03", "Which enhancement mode fits a digitally zoomed landscape?", "Digital zoom preserved the scene but softened foliage, rooflines, and distant signs.", ("Start with the original zoomed frame.", "Test one mode at a time instead of stacking repeated processing.", "Judge branches, roof edges, and lettering at 100% before keeping a result."), "You select the least artificial version based on visible edges rather than a generic sharpness claim.", "choosing a mode for a digitally zoomed landscape"),
            _task("unblurry-school-stage-photo", "unblurry-02", "How can I review a soft school-stage photo safely?", "Distance and indoor light made a stage photo soft, and faces are too small for blind sharpening.", ("Use the original camera file and keep a backup.", "Run a single on-device enhancement pass.", "Zoom into faces, costumes, and stage lettering, then reject the export if details look fabricated."), "The process produces either a verified improvement or an honest decision to keep the original.", "reviewing a distant school-stage photo"),
        ],
    },
    {
        "id": "unblurry-p04",
        "app": "unblurry",
        "variants": [
            _task("unblurry-product-listing", "unblurry-01", "How do I check a soft product photo before listing an item?", "A product image is readable but soft around labels, seams, or surface texture that a buyer may inspect.", ("Open the full-resolution source.", "Compare the enhanced and original views around labels and material edges.", "Use the result only when it remains faithful to the item being sold."), "You obtain a clearer candidate without treating enhancement as permission to misrepresent condition or detail.", "checking product labels and texture"),
            _task("unblurry-profile-crop", "unblurry-03", "Can I prepare a sharper profile-photo crop without overprocessing?", "Cropping a portrait reduces available pixels and can make the final profile image look soft.", ("Crop from the largest original first.", "Choose a restrained enhancement mode for the cropped image.", "Inspect skin, hair, glasses, and background edges at the final display size."), "The result is a reviewed profile crop that keeps a natural appearance.", "preparing a profile-photo crop"),
        ],
    },
    {
        "id": "unblurry-p05",
        "app": "unblurry",
        "variants": [
            _task("unblurry-low-light-dinner", "unblurry-02", "What is a careful workflow for a soft low-light dinner photo?", "Low light introduced both softness and noise, so stronger processing may sharpen noise instead of the people.", ("Select the original frame with the least motion.", "Run one enhancement and let the preview complete.", "Check faces and dark backgrounds separately before deciding whether to export."), "You make an evidence-based keep-or-reject decision instead of assuming every low-light image can be rescued.", "checking a low-light dinner photo"),
            _task("unblurry-indoor-birthday", "unblurry-01", "How can I compare an enhanced indoor birthday photo?", "An indoor birthday moment matters, but candles and movement left edges softer than expected.", ("Keep the original untouched.", "Move the before-and-after control across faces, candles, and lettering.", "Save a new copy only when the comparison remains believable."), "The reviewed copy can be easier to view while the original memory remains intact.", "comparing an indoor birthday photo"),
        ],
    },
    {
        "id": "unblurry-p06",
        "app": "unblurry",
        "variants": [
            _task("unblurry-group-photo", "unblurry-01", "How do I inspect enhancement across a group photo?", "A group photo contains many small faces, so a result that looks good in the center may fail at the edges.", ("Use the highest-resolution group photo.", "Compare the center and every edge face rather than judging only the overall preview.", "Reject artifacts around glasses, teeth, hair, or repeated patterns before saving."), "You finish with a group-wide quality check rather than a misleading center-only comparison.", "reviewing every face in a group photo"),
            _task("unblurry-wedding-guest-crop", "unblurry-03", "Can I improve a cropped wedding-guest photo?", "A guest appears only in a small part of a larger frame, so the crop has limited real detail.", ("Make the crop from the original file.", "Try a restrained mode and avoid repeated enhancement passes.", "Inspect clothing texture, facial edges, and venue lines before export."), "The output is accepted only when it looks consistent with the source rather than newly invented.", "testing a wedding-guest crop"),
        ],
    },
    {
        "id": "unblurry-p07",
        "app": "unblurry",
        "variants": [
            _task("unblurry-small-print", "unblurry-03", "How can I prepare a small photo for a modest print?", "A low-resolution photo may look acceptable on a phone but reveal softness when printed larger.", ("Set a realistic print size before enhancement.", "Choose one mode and inspect the preview at an equivalent zoom.", "Order a small proof instead of assuming screen sharpness guarantees print detail."), "You get a print candidate with a clear quality checkpoint and a preserved original.", "preparing a modest print candidate"),
            _task("unblurry-lock-screen", "unblurry-02", "Can I clean up a soft photo for an iPhone Lock Screen?", "A favorite image becomes visibly soft after a tight Lock Screen crop.", ("Crop for the intended screen aspect from the original.", "Run one on-device enhancement pass.", "Preview the crop with clock and widget areas before saving the final copy."), "The result is evaluated in its actual Lock Screen context, where small source limits are easier to spot.", "preparing an iPhone Lock Screen image"),
        ],
    },
    {
        "id": "unblurry-p08",
        "app": "unblurry",
        "variants": [
            _task("unblurry-mode-test", "unblurry-03", "How do I choose between enhancement modes without guessing?", "Several enhancement choices are available, but the strongest option is not automatically the most faithful.", ("Pick one representative detail such as an eye, edge, or sign.", "Preview each relevant mode once against that same detail.", "Choose the mildest result that improves clarity without halos or plastic texture."), "You select a mode through a repeatable comparison instead of maximizing an abstract setting.", "comparing enhancement modes"),
            _task("unblurry-export-check", "unblurry-01", "What should I inspect before exporting an enhanced photo?", "A preview can appear impressive at fit-to-screen size while hiding artifacts in fine detail.", ("Sweep the comparison control across the whole frame.", "Inspect faces, text, repeating patterns, and high-contrast boundaries at full size.", "Export as a separate copy only after all checks pass."), "The final file has passed a concrete visual review and the source remains recoverable.", "performing a final before-and-after export check"),
        ],
    },
    {
        "id": "scanto-p01",
        "app": "scanto",
        "variants": [
            _task("scanto-trip-receipts", "scanto-01", "How can I scan travel receipts before they fade?", "Small paper receipts are easy to lose and thermal print can fade before an expense review.", ("Place each receipt flat in even light and scan the full edges.", "Name or categorize it while the purchase is still recognizable.", "Open the resulting page and verify merchant, date, and total before filing."), "You create a readable working archive tied to the trip while keeping any originals required for reimbursement.", "capturing travel receipts"),
            _task("scanto-tax-receipt-batch", "scanto-02", "How do I organize a batch of tax receipts on iPhone?", "A mixed pile of receipts becomes difficult to review when files have generic names and no grouping.", ("Scan one receipt per clear page or logical multipage document.", "Group and label scans by year and expense purpose.", "Open a sample from every group and verify the important amounts are legible."), "You get a navigable receipt set for later review, not a substitute for tax or record-retention advice.", "organizing a tax-receipt library"),
        ],
    },
    {
        "id": "scanto-p02",
        "app": "scanto",
        "variants": [
            _task("scanto-lease-copy", "scanto-04", "How can I make a readable working copy of a lease?", "A long lease needs clean page edges and readable clauses, but the signed paper may still be the authoritative original.", ("Scan pages in order on a flat, evenly lit surface.", "Review crop, contrast, and page sequence in the document viewer.", "Export a working PDF and retain the signed original as required."), "The result is a readable reference copy with page order checked.", "reviewing a lease scan"),
            _task("scanto-signed-form", "scanto-07", "How should I share a scanned signed form more carefully?", "A signed form may contain personal details and should not be sent as an unprotected, unchecked file.", ("Scan the complete form and verify signatures and dates.", "Create the PDF and set a password when the recipient supports it.", "Send the password through a separate agreed channel and keep the original."), "You produce a reviewed, password-protected working copy while respecting the recipient's submission rules.", "sharing a signed form with a password"),
        ],
    },
    {
        "id": "scanto-p03",
        "app": "scanto",
        "variants": [
            _task("scanto-lecture-notes", "scanto-05", "How can I turn printed lecture notes into searchable study material?", "Printed handouts are hard to search when revising for a specific term or definition.", ("Scan pages flat and in order.", "Run on-device OCR, then search for a known heading as a quality check.", "Correct or annotate any OCR mistakes before relying on quoted text."), "You gain a searchable study copy while the original page remains the authority.", "searching OCR text in lecture notes"),
            _task("scanto-research-handout", "scanto-08", "How do I scan a multipage research handout without losing page order?", "A handout with charts and references becomes confusing if pages are cropped inconsistently or reordered.", ("Capture every page with the same orientation.", "Review the sharp multipage preview from first page to references.", "Re-scan any unreadable chart label before exporting one PDF."), "You get a page-ordered working PDF whose visual quality has been checked.", "checking a multipage research handout"),
        ],
    },
    {
        "id": "scanto-p04",
        "app": "scanto",
        "variants": [
            _task("scanto-travel-document-copy", "scanto-06", "How can I keep a private reference scan of a travel document?", "A reference copy can be useful during travel, but identity information needs stronger local protection.", ("Confirm that making a copy is permitted for your use.", "Scan every required edge and verify names and numbers.", "Lock the document behind Face ID and keep the physical original secure."), "You retain a protected reference copy without treating it as a replacement for the original document.", "locking a travel-document reference"),
            _task("scanto-insurance-packet", "scanto-07", "How should I package insurance paperwork for secure sharing?", "Insurance paperwork can combine identifiers, signatures, and several pages that must arrive together.", ("Scan the packet in the requested order.", "Review completeness and create one PDF.", "Add a password if accepted, then communicate it separately from the attachment."), "The recipient gets one checked packet with an added access barrier.", "protecting an insurance PDF"),
        ],
    },
    {
        "id": "scanto-p05",
        "app": "scanto",
        "variants": [
            _task("scanto-meeting-pack", "scanto-08", "How can I combine a meeting paper pack into one clean PDF?", "Loose agenda pages and handouts are difficult to retrieve as separate camera photos.", ("Scan the agenda first and append supporting pages in discussion order.", "Review every page boundary and rotate pages consistently.", "Export one file with a descriptive meeting name and date."), "You create a single ordered reference pack that is easier to reopen and search.", "assembling a meeting paper pack"),
            _task("scanto-paper-forms", "scanto-02", "How do I separate several paper forms after scanning?", "Scanning multiple forms without names or categories makes the digital pile as confusing as the paper pile.", ("Scan each form as its own document.", "Name it by purpose rather than sensitive content where possible.", "Place it in the correct category and open one page to verify the assignment."), "You finish with distinct, findable form records instead of an anonymous camera roll.", "sorting scanned paper forms"),
        ],
    },
    {
        "id": "scanto-p06",
        "app": "scanto",
        "variants": [
            _task("scanto-search-manual", "scanto-05", "Can I search a scanned appliance manual for one error code?", "A long printed manual is slow to browse when only one model number or error code matters.", ("Scan the relevant manual pages sharply.", "Run OCR and search a heading you can see to confirm recognition quality.", "Search the target code and verify the result against the scanned page."), "You reach the relevant page faster without assuming OCR text is error-free.", "finding an error code with OCR"),
            _task("scanto-quote-extraction", "scanto-10", "How can I extract a short quote from a scanned document responsibly?", "Copying text from a scan saves typing, but OCR can silently change punctuation, names, or numbers.", ("Use settings appropriate to the page language and layout.", "Run OCR and copy only the needed passage.", "Compare every character of the quote with the page image before using it."), "You obtain editable text with a mandatory source-image verification step.", "configuring an OCR extraction workflow"),
        ],
    },
    {
        "id": "scanto-p07",
        "app": "scanto",
        "variants": [
            _task("scanto-client-handoff", "scanto-07", "How can a freelancer hand off a scanned client document?", "A client document needs a clear filename, complete pages, and an agreed protection method.", ("Scan and review all required pages.", "Export the PDF with a neutral, descriptive filename and password if requested.", "Confirm receipt, then follow the agreed retention and deletion policy."), "The handoff is complete, checked, and aligned with the client's security expectations.", "preparing a client document handoff"),
            _task("scanto-private-archive", "scanto-09", "How do I keep a small document archive on the device?", "Some personal documents need to remain available without creating an unnecessary cloud copy.", ("Scan only the documents you genuinely need.", "Review on-device processing and lock settings before filing.", "Periodically remove expired records according to your own retention obligations."), "You maintain a smaller local working archive with deliberate privacy and retention choices.", "keeping a private on-device archive"),
        ],
    },
    {
        "id": "cyca-p01",
        "app": "cyca",
        "variants": [
            _task("cyca-today-context", "cyca-01", "How can I see today's cycle context without treating it as a diagnosis?", "A single day can feel different from the last, and a concise context view may help with personal notes.", ("Open today's overview and read the phase as an estimate.", "Record what you actually observe rather than forcing it to match the forecast.", "Escalate unusual or concerning symptoms to a qualified clinician."), "You get a private daily context plus a clearer separation between observation and prediction.", "reviewing today's cycle context"),
            _task("cyca-calendar-pattern", "cyca-03", "How do I review a cycle calendar for a personal pattern?", "Remembering dates from several weeks ago is unreliable when looking for a recurring personal pattern.", ("Open the calendar and review recorded dates across more than one cycle.", "Note changes in timing without labelling them normal or abnormal yourself.", "Bring the record, not a self-diagnosis, to a clinician if you are concerned."), "The calendar becomes an organized observation record rather than medical proof.", "reviewing a cycle calendar pattern"),
        ],
    },
    {
        "id": "cyca-p02",
        "app": "cyca",
        "variants": [
            _task("cyca-energy-notes", "cyca-04", "How can I compare my energy notes with cycle timing?", "Energy changes are easy to remember selectively, so an on-device timeline can make the review more concrete.", ("Record energy in simple, consistent language.", "Review the rhythm insight only after several entries exist.", "Treat any apparent relationship as a personal observation, not a medical conclusion."), "You obtain a repeatable self-observation that can guide planning without overstating causality.", "comparing energy notes with personal rhythm"),
            _task("cyca-symptom-log", "cyca-01", "How should I record a symptom alongside today's cycle view?", "A symptom matters most when its timing, severity, and change are recorded accurately.", ("Open today's context and add the observation in your own words.", "Include when it started and whether it changed, without relying on a forecast label.", "Seek care promptly for severe, new, or worrying symptoms."), "You retain a time-linked note that is more useful than memory alone.", "recording a symptom with today's context"),
        ],
    },
    {
        "id": "cyca-p03",
        "app": "cyca",
        "variants": [
            _task("cyca-busy-day-plan", "cyca-06", "How can I plan a busy day around how I actually feel?", "A fixed schedule may be unrealistic on a low-energy day, but a cycle estimate should not dictate the day either.", ("Check today's context and your actual energy.", "Move one flexible task or break in the planner if needed.", "Keep fixed commitments visible and reassess rather than assuming the forecast is certain."), "You create a modest, adjustable plan based on current capacity.", "planning a busy day with the smart planner"),
            _task("cyca-travel-week", "cyca-02", "How should I use a cycle forecast when preparing a travel week?", "Travel packing and breaks can be easier with advance context, but predicted timing may shift.", ("Review the forecast as a range, not a guarantee.", "Pack practical supplies and build flexible breaks into the itinerary.", "Update the record with what actually happens during the trip."), "You prepare for plausible needs while keeping the travel plan flexible.", "preparing a travel week with a body forecast"),
        ],
    },
    {
        "id": "cyca-p04",
        "app": "cyca",
        "variants": [
            _task("cyca-gentle-day", "cyca-05", "How can I choose a gentler routine on a low-energy day?", "A demanding routine can feel mismatched when energy is low, yet app suggestions cannot assess health or safety.", ("Check your actual condition before reading any suggestion.", "Choose one low-stakes adjustment such as rest, hydration, or a shorter task.", "Stop and seek advice if symptoms are severe or unusual."), "You make one reversible comfort adjustment without turning a suggestion into treatment.", "reviewing gentle daily-care suggestions"),
            _task("cyca-workout-adjustment", "cyca-04", "Can I use personal rhythm notes to adjust a workout plan?", "Past notes may help with pacing, but they do not replace medical or training guidance.", ("Review your own recent energy and symptom entries.", "Choose a flexible intensity range rather than a fixed prediction-based target.", "Change or stop the session based on current signs and professional guidance."), "The plan stays responsive to real-time condition instead of being controlled by a forecast.", "checking personal rhythm before exercise"),
        ],
    },
    {
        "id": "cyca-p05",
        "app": "cyca",
        "variants": [
            _task("cyca-regularity-review", "cyca-04", "How do I review cycle-length changes without self-diagnosing?", "A single short or long cycle can draw attention, but a reliable discussion needs dates and context.", ("Review recorded cycle lengths over time.", "Note material changes and any related observations without assigning a cause.", "Share the record with a qualified clinician if the pattern concerns you."), "You prepare a factual timeline for discussion rather than a diagnostic label.", "reviewing recorded cycle lengths"),
            _task("cyca-appointment-notes", "cyca-03", "How can I prepare cycle dates for a healthcare appointment?", "Remembering exact dates during an appointment can be difficult, especially when several cycles are relevant.", ("Open the calendar and identify the date range requested.", "Write down the recorded dates and uncertainties.", "Bring those observations and let the clinician interpret them in context."), "You arrive with a concise date record while keeping clinical interpretation with the professional.", "preparing calendar dates for an appointment"),
        ],
    },
    {
        "id": "cyca-p06",
        "app": "cyca",
        "variants": [
            _task("cyca-private-journal", "cyca-01", "How can I keep cycle observations as a private personal journal?", "Sensitive observations should be recorded only when the storage and sharing choices feel appropriate.", ("Review the app's on-device and access settings.", "Record only the detail useful to you.", "Revisit old entries and remove information you no longer want to retain."), "You keep a deliberately scoped personal record rather than an uncontrolled data dump.", "maintaining a private cycle journal"),
            _task("cyca-reminder-check", "cyca-06", "How should I set a gentle planning reminder?", "A reminder can help with preparation, but too many alerts can create pressure or expose private context.", ("Choose one practical task that benefits from a reminder.", "Use neutral wording and a reasonable time.", "Disable or revise the reminder if it is no longer useful or private enough."), "You get a limited, respectful prompt tied to a real planning need.", "setting a private planning reminder"),
        ],
    },
    {
        "id": "cyca-p07",
        "app": "cyca",
        "variants": [
            _task("cyca-forecast-review", "cyca-02", "How do I compare a forecast with what actually happened?", "Forecasts are estimates and become misleading if remembered predictions replace recorded events.", ("Review the forecast before the date without treating it as certain.", "Record the actual event or feeling when it occurs.", "Compare later and rely on the observed record for future discussions."), "You separate predicted context from actual history and can see where they differed.", "comparing forecast and observed history"),
            _task("cyca-week-priorities", "cyca-06", "Can I use the planner to rebalance one week's priorities?", "A crowded week needs realistic pacing, but cycle context is only one input among deadlines, sleep, and current health.", ("List fixed commitments first.", "Use current energy and the planner to move one flexible item.", "Review the plan daily and change it when real conditions differ."), "The week becomes more adaptable without allowing a forecast to make decisions for you.", "rebalancing weekly priorities"),
        ],
    },
    {
        "id": "gmoney-p01",
        "app": "gmoney",
        "variants": [
            _task("gmoney-cash-purchase", "gmoney-01", "How can I log a small cash purchase abroad before I forget it?", "Small cash expenses disappear from memory quickly and never arrive through a bank feed.", ("Enter the amount in the currency you paid.", "Choose the relevant trip and category while the receipt is in hand.", "Check the home-currency estimate and retain the receipt if needed."), "The purchase is visible in the trip total instead of becoming an unexplained gap.", "logging a cash purchase abroad"),
            _task("gmoney-card-purchase", "gmoney-02", "How should I record a card purchase with a pending final conversion?", "A card terminal amount is known immediately, but the issuer's final home-currency charge and fees may arrive later.", ("Log the local amount and category at purchase time.", "Use the displayed conversion as a planning estimate.", "Reconcile it against the settled card charge and fee later."), "You preserve the transaction context while clearly separating an estimate from the bank's final amount.", "reviewing a card purchase in the trip summary"),
        ],
    },
    {
        "id": "gmoney-p02",
        "app": "gmoney",
        "variants": [
            _task("gmoney-multi-country-trip", "gmoney-02", "How can I keep spending visible on a multi-country trip?", "Switching currencies makes it difficult to compare today's spending with the rest of the trip.", ("Create or select the trip before logging expenses.", "Enter each purchase in its paid currency and assign a consistent category.", "Review the home-currency summary while remembering rates and fees can differ."), "You get one manual cross-currency view of the trip without connecting a bank account.", "reviewing a multi-country trip total"),
            _task("gmoney-day-trip", "gmoney-01", "What is a lightweight way to track a one-day trip budget?", "Meals, tickets, and transport can exceed a day budget even when each purchase feels small.", ("Set the day's practical spending limit.", "Log each purchase as it happens in local currency.", "Check the running home-currency estimate before the next optional purchase."), "You can see the day's remaining room while decisions are still reversible.", "logging a one-day trip budget"),
        ],
    },
    {
        "id": "gmoney-p03",
        "app": "gmoney",
        "variants": [
            _task("gmoney-student-abroad", "gmoney-02", "How can a student compare weekly spending abroad?", "Groceries, transport, and social spending happen in local currency while the overall budget may be in a home currency.", ("Use stable categories for the whole week.", "Log cash and card purchases in the paid currency.", "Review category totals and reconcile them with actual account charges."), "You obtain a weekly planning view that shows where manual spending was concentrated.", "reviewing a student travel budget"),
            _task("gmoney-family-day", "gmoney-01", "How do I track shared costs during a family day out?", "Tickets, food, and transport are paid at different moments, making the final outing cost easy to underestimate.", ("Create one outing or trip context.", "Record each paid amount and category immediately.", "Review the total together and note any expense someone else still needs to add."), "The family gets a more complete manual total without claiming automatic bill splitting.", "logging family outing costs"),
        ],
    },
    {
        "id": "gmoney-p04",
        "app": "gmoney",
        "variants": [
            _task("gmoney-rate-check", "gmoney-01", "How should I use an exchange-rate estimate before buying?", "A quick conversion helps with a decision, but merchant markup and card fees can change the settled price.", ("Enter the local price and confirm the currency.", "Read the home-currency estimate as a comparison aid.", "Check the merchant's payment option and your issuer's final rate before reconciling."), "You make the purchase decision with a useful estimate and an explicit fee check.", "checking an exchange-rate estimate"),
            _task("gmoney-cash-exchange", "gmoney-03", "How can I record spending after exchanging cash?", "The app's reference conversion may not match the rate and commission actually paid at an exchange desk.", ("Record the real cash obtained and total home-currency cost separately.", "Log purchases in the local currency as they occur.", "Use your actual exchange receipt when calculating final travel cost."), "The ledger remains useful without pretending a reference rate equals your real cash rate.", "keeping an offline cash ledger"),
        ],
    },
    {
        "id": "gmoney-p05",
        "app": "gmoney",
        "variants": [
            _task("gmoney-food-vs-transport", "gmoney-02", "How can I compare food and transport spending on a trip?", "Frequent small meals and rides are difficult to compare from receipts alone.", ("Use the same food and transport categories throughout the trip.", "Log every cash and card purchase manually.", "Review both category totals and inspect missing days before drawing a conclusion."), "You see a comparable category split while acknowledging that unlogged purchases remain absent.", "comparing food and transport categories"),
            _task("gmoney-shopping-boundary", "gmoney-01", "How do I set a visible boundary for optional travel shopping?", "Optional purchases can consume the remaining trip budget before essential costs are considered.", ("Reserve expected transport, lodging, and food first.", "Set an optional-shopping amount in the trip plan.", "Check the running estimate before each nonessential purchase."), "The boundary stays visible at the moment of choice instead of appearing only after the trip.", "checking optional shopping against a trip budget"),
        ],
    },
    {
        "id": "gmoney-p06",
        "app": "gmoney",
        "variants": [
            _task("gmoney-flight-mode", "gmoney-03", "Can I keep logging expenses while my phone is offline?", "Flights, roaming limits, or weak coverage should not force a gap in the manual travel record.", ("Confirm the trip and needed currencies before losing connectivity.", "Enter local amounts and categories offline as purchases happen.", "Review rates and reconcile final charges when a trusted connection returns."), "You keep the event sequence intact offline while postponing rate verification.", "logging travel expenses offline"),
            _task("gmoney-remote-market", "gmoney-01", "How can I record market purchases with no reliable signal?", "A remote market may use cash and have no connectivity, making later recall of many small purchases unreliable.", ("Enter each amount in the paid currency before leaving the stall.", "Add a simple category or note that does not expose unnecessary details.", "Review the day's entries later against remaining cash."), "The offline ledger captures the purchases while they are still easy to verify.", "recording purchases without a network"),
        ],
    },
    {
        "id": "gmoney-p07",
        "app": "gmoney",
        "variants": [
            _task("gmoney-work-trip-export", "gmoney-02", "How can I prepare a work-trip spending summary for review?", "A manager or spreadsheet may need dates, categories, currencies, and totals rather than a pile of mixed receipts.", ("Check every work-trip entry against its receipt.", "Filter to the trip and review category and home-currency totals.", "Export the available text or CSV record, then follow the employer's official template and rate rules."), "You create a review-ready working ledger while keeping official reimbursement decisions outside the app.", "reviewing a work-trip summary"),
            _task("gmoney-post-trip-reconcile", "gmoney-02", "What should I reconcile after returning from a trip?", "Manual entries, cash, card settlements, and fees may differ after all transactions have posted.", ("Compare card entries with settled statements.", "Check cash spending against starting and remaining cash.", "Correct omissions and retain receipts required for your records."), "You finish with a more accurate trip total and a clear list of any unresolved differences.", "reconciling a completed trip"),
        ],
    },
    {
        "id": "lumiletters-p01",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-first-sound", "lumiletters-02", "How can a child practice one letter sound without a long lesson?", "A young learner may benefit more from one focused sound than from moving quickly through the whole alphabet.", ("Choose one familiar letter.", "Listen to the sound and connect it with the pictured word.", "End after a successful repeat or recognition attempt."), "The session has one clear sound-letter goal and a natural stopping point.", "practicing one letter sound"),
            _task("lumiletters-upper-lower", "lumiletters-03", "How can we compare uppercase and lowercase forms?", "A child may know a capital letter but not recognize the lowercase shape in books.", ("Pick one uppercase and lowercase pair from the letter grid.", "Say the shared sound while pointing to both forms.", "Find the same pair once more, then stop or switch activities."), "The child practices visual equivalence without turning the session into a test.", "comparing uppercase and lowercase letters"),
        ],
    },
    {
        "id": "lumiletters-p02",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-trace-uppercase", "lumiletters-05", "How can a child trace one uppercase letter carefully?", "Repeated tracing is less useful when the child rushes or loses the intended stroke path.", ("Choose one uppercase letter and watch the starting point.", "Trace slowly along the guide with a comfortable finger movement.", "Repeat only while the child remains relaxed and interested."), "The activity becomes a short stroke-order practice rather than a volume target.", "tracing an uppercase letter"),
            _task("lumiletters-trace-lowercase", "lumiletters-05", "What is a gentle way to practice a lowercase trace?", "Lowercase shapes can require different curves and starting points from capitals.", ("Select one lowercase letter after the uppercase form is familiar.", "Follow the guided path once without racing.", "Compare the finished shape, praise effort, and pause before another attempt."), "The child completes one attentive lowercase trace with low pressure.", "tracing a lowercase letter"),
        ],
    },
    {
        "id": "lumiletters-p03",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-match-shape", "lumiletters-08", "How can a matching game reinforce letter shape?", "A child may recognize a letter in isolation but hesitate when several shapes appear together.", ("Name the target letter before choices appear.", "Let the child compare curves and lines and choose the matching shape.", "If the choice is wrong, describe one visual clue and try once more."), "The game practices discrimination with feedback rather than memorized guessing.", "matching a target letter shape"),
            _task("lumiletters-find-sound", "lumiletters-09", "How can we practice hearing and finding a letter sound?", "Listening and visual recognition need to connect without adding too many choices at once.", ("Play one letter sound.", "Ask the child to find the matching letter among the visible options.", "Replay the sound and say it together before moving on."), "The child links one heard sound with one written form in a contained activity.", "finding the letter that matches a sound"),
        ],
    },
    {
        "id": "lumiletters-p04",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-five-minute-session", "lumiletters-01", "How can we make a five-minute letter-practice routine?", "Long sessions can turn a playful activity into resistance for a young learner.", ("Let the child choose one activity from the home screen.", "Practice one letter or one short challenge.", "Stop while engagement is still positive and note what to revisit."), "The routine stays brief, predictable, and easier to repeat another day.", "starting a short letter-learning session"),
            _task("lumiletters-one-challenge", "lumiletters-08", "How can we use one letter challenge without pressure?", "A challenge can motivate, but repeated correction may feel like a score-focused test.", ("Choose a familiar letter challenge.", "Allow time to look and respond without prompting the answer.", "Celebrate the attempt, explain one clue if needed, and finish after one round."), "The child gets a small retrieval practice with emotional room to stop.", "completing one matching challenge"),
        ],
    },
    {
        "id": "lumiletters-p05",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-review-progress", "lumiletters-04", "How can a parent use progress without turning it into a grade?", "A progress screen can guide the next activity, but percentages do not define a child's ability or readiness.", ("Review which activities were attempted and which were repeated.", "Choose one comfortable next step rather than chasing completion.", "Observe the child directly and adjust pace when the screen and behavior differ."), "Progress becomes a planning clue, not a label or promise about learning.", "reviewing letter-practice progress"),
            _task("lumiletters-revisit-letter", "lumiletters-03", "How do we choose one letter to revisit?", "Moving through the alphabet in order may miss a letter the child is currently confusing.", ("Look at recent play and choose one confused or interesting letter.", "Open that letter's sound or tracing activity.", "Finish with an easy recognition round to keep the session encouraging."), "The next practice responds to observed need while remaining small and positive.", "choosing a letter from the alphabet grid"),
        ],
    },
    {
        "id": "lumiletters-p06",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-print-worksheet", "lumiletters-07", "How can we move one letter from screen practice to paper?", "A child may benefit from feeling pencil movement after learning the shape on screen.", ("Choose a worksheet for one familiar letter.", "Print it and set up a comfortable pencil grip and surface.", "Do a small number of traces, then keep or recycle the sheet based on the child's interest."), "The same letter is practiced in a screen-free format without requiring a long worksheet session.", "using a printable letter worksheet"),
            _task("lumiletters-offline-table", "lumiletters-07", "What is a simple screen-free letter activity for the table?", "Families sometimes want a quiet paper activity without introducing a new lesson.", ("Print a worksheet for a letter already encountered in the app.", "Ask the child to find and trace just that letter.", "Talk about one word that begins with its sound, then finish."), "The table activity reinforces known material instead of becoming extra homework.", "preparing a screen-free table activity"),
        ],
    },
    {
        "id": "lumiletters-p07",
        "app": "lumiletters",
        "variants": [
            _task("lumiletters-sound-settings", "lumiletters-10", "How can a parent set comfortable sound for letter practice?", "Music or effects can help engagement for one child and distract another.", ("Open parent settings before handing over the device.", "Set music and effects to a comfortable level for the room.", "Observe one activity and revise the balance if speech or focus is harder."), "The audio environment is intentionally adjusted to the child and setting.", "adjusting parent sound settings"),
            _task("lumiletters-reward-wrapup", "lumiletters-06", "How can we use an in-app reward to end a session well?", "A reward screen can become a cue to continue indefinitely unless the stopping point is clear.", ("Agree on one final activity before starting.", "Acknowledge the earned in-app progress or reward.", "Close the session and name what the child enjoyed rather than demanding another level."), "The reward supports a positive ending instead of extending screen time automatically.", "ending practice at the letter-galaxy reward screen"),
        ],
    },
    {
        "id": "aim990-p01",
        "app": "aim990",
        "variants": [
            _task("aim990-thirty-day-plan", "aim990-01", "How can I turn a 30-day TOEIC study target into daily work?", "A target score is not a plan unless available days and listening or reading needs become specific sessions.", ("Complete the diagnostic or baseline review honestly.", "Use the daily plan to identify one listening and one reading priority.", "Record completion and revise the next week from actual performance."), "You get a concrete sequence of practice days without a guarantee that the target score will be reached.", "reviewing a 30-day target-score plan"),
            _task("aim990-busy-week", "aim990-01", "How should I adjust a TOEIC plan during a busy week?", "A rigid plan often collapses when work or school removes several study blocks.", ("Keep the highest-priority weak area visible.", "Shorten sessions while preserving a mix of listening and reading.", "Reschedule missed work rather than marking unattempted material as complete."), "The plan remains honest and achievable enough to continue after the busy week.", "adjusting the daily study plan"),
        ],
    },
    {
        "id": "aim990-p02",
        "app": "aim990",
        "variants": [
            _task("aim990-listening-weakness", "aim990-03", "How can I act on a weak listening category?", "A total practice score hides whether errors come from pace, vocabulary, detail, or a specific question format.", ("Open the weak-skill view and choose one listening category.", "Complete a focused drill under realistic audio conditions.", "Review why each missed answer was tempting before selecting the next drill."), "You convert one weakness label into a specific practice-and-review loop.", "reviewing a weak listening skill"),
            _task("aim990-reading-weakness", "aim990-03", "How do I turn a weak reading result into a focused drill?", "Repeating full sets may waste time when one reading task repeatedly causes errors.", ("Identify the weakest reading category from recorded practice.", "Run a short drill for that task under a measured time limit.", "Classify misses as language, inference, or pacing issues and plan the next attempt."), "The weak result becomes a targeted reading action instead of a discouraging score.", "reviewing a weak reading skill"),
        ],
    },
    {
        "id": "aim990-p03",
        "app": "aim990",
        "variants": [
            _task("aim990-timed-part", "aim990-02", "How can I practice one TOEIC part under time pressure?", "Untimed accuracy alone does not reveal where pacing breaks down.", ("Choose one listening or reading part rather than a full exam.", "Use the available timer and answer without pausing to research.", "Review both errors and where time was spent before repeating."), "You obtain a bounded pacing sample that can guide the next practice block.", "running a timed exam-part drill"),
            _task("aim990-mini-mock", "aim990-04", "When is a mini mock test more useful than a full mock?", "A full mock can be too costly when the goal is a quick pacing check or the available time is short.", ("Choose the mini mock that fits the available block.", "Complete it under uninterrupted test-like conditions.", "Review the result by skill and schedule follow-up practice instead of extrapolating a guaranteed score."), "You get a compact performance snapshot with an immediate review step.", "choosing a mini mock test"),
        ],
    },
    {
        "id": "aim990-p04",
        "app": "aim990",
        "variants": [
            _task("aim990-error-review", "aim990-02", "What should I do after a TOEIC practice set?", "A completed set has little value if wrong answers are only counted and not explained.", ("Review every missed and guessed response.", "Write the cue, rule, or vocabulary item that would have changed the answer.", "Choose one short follow-up drill that tests the same weakness differently."), "The practice result becomes a reusable error pattern and a next action.", "reviewing a completed practice set"),
            _task("aim990-weak-spot-loop", "aim990-03", "How can I confirm that a weak spot is improving?", "One better score may reflect easier questions rather than a stable skill change.", ("Practice the same weak category on more than one set.", "Compare accuracy and time across attempts.", "Keep the category active until performance is steadier, then reassess with mixed questions."), "You use repeated evidence rather than declaring a weakness solved after one result.", "tracking a weak-skill loop"),
        ],
    },
    {
        "id": "aim990-p05",
        "app": "aim990",
        "variants": [
            _task("aim990-progress-trend", "aim990-03", "How should I read a TOEIC practice trend?", "A trend can be distorted by different test lengths, difficulty, or interrupted sessions.", ("Compare results from similar practice conditions.", "Look at skill-level accuracy and pacing, not only the headline score.", "Use several attempts before changing the study plan."), "The trend becomes a cautious planning signal rather than a score prediction.", "reviewing practice progress by skill"),
            _task("aim990-target-checkpoint", "aim990-01", "How can I run a weekly target checkpoint?", "A target set at the start of the month may stop matching actual weak areas and available time.", ("Review completed sessions and current weak skills.", "Choose one realistic listening and reading priority for the next seven days.", "Adjust workload without rewriting completed history."), "You begin the next week with priorities grounded in recorded work.", "checking the next week of a target plan"),
        ],
    },
    {
        "id": "aim990-p06",
        "app": "aim990",
        "variants": [
            _task("aim990-sentence-completion", "aim990-02", "How can I review sentence-completion mistakes?", "A wrong sentence-completion answer may come from grammar, word form, collocation, or rushing.", ("Complete a short set without looking up answers.", "Label the reason for each miss after review.", "Create a follow-up drill around the most common reason, not every topic at once."), "You turn mixed mistakes into one focused language objective.", "practicing sentence-completion questions"),
            _task("aim990-listening-detail", "aim990-02", "How can I practice listening for a missed detail?", "Replaying audio without a plan may improve familiarity without fixing why the detail was missed.", ("Answer once under normal timing.", "Review whether the missed cue was vocabulary, distractor, or attention.", "Try a new item with the same listening objective before replaying excessively."), "The review targets the listening process rather than memorizing one recording.", "practicing listening questions"),
        ],
    },
    {
        "id": "aim990-p07",
        "app": "aim990",
        "variants": [
            _task("aim990-full-mock", "aim990-04", "How should I prepare for a full TOEIC mock session?", "A full mock is useful only when time, interruptions, and review are planned realistically.", ("Reserve an uninterrupted block and prepare the same basic conditions each time.", "Complete the mock without pausing or checking answers.", "Schedule a separate review block for errors, guesses, and pacing."), "You obtain a more comparable practice sample, not an official or guaranteed score.", "selecting a full mock test"),
            _task("aim990-rest-day-adjustment", "aim990-01", "How can I adjust the plan after a missed study day?", "Trying to double the next day's workload can create another miss and hide what was actually completed.", ("Leave the missed session visible.", "Move only its highest-priority drill into the next available block.", "Reduce lower-priority volume and keep the weekly checkpoint honest."), "The plan recovers without pretending the missed work happened or creating an unrealistic catch-up load.", "rebalancing a daily study plan"),
        ],
    },
    {
        "id": "sereno-p01",
        "app": "sereno",
        "variants": [
            _task("sereno-quiet-room", "sereno-01", "How can I add gentle background sound to a room that feels too quiet?", "A very quiet room can make small household noises feel more noticeable, but louder sound is not automatically better.", ("Choose one neutral sound from the library.", "Start at a low, comfortable volume.", "Listen for several minutes and lower or stop it if it masks important sounds or feels tiring."), "You create a modest, reversible ambient layer without claiming a sleep treatment.", "choosing a gentle sound for a quiet room"),
            _task("sereno-noisy-apartment", "sereno-03", "How can I build an ambient mix for an intermittently noisy apartment?", "Uneven outside noise can be distracting, but an overly dense mix may become another source of fatigue.", ("Choose one steady base sound.", "Add only one complementary layer and balance both at a comfortable volume.", "Keep alarms and safety-relevant sounds audible and revise the mix as conditions change."), "The room gains a consistent background layer while awareness and comfort remain priorities.", "mixing sound around intermittent apartment noise"),
        ],
    },
    {
        "id": "sereno-p02",
        "app": "sereno",
        "variants": [
            _task("sereno-bedtime-scene", "sereno-02", "How can I use one ambient scene as a bedtime cue?", "A repeatable cue can support a routine, but sound alone does not diagnose or cure sleep difficulty.", ("Choose one calm scene before getting into bed.", "Set a low volume and pair it with the same wind-down steps.", "Stop using it if it becomes irritating or interferes with hearing what matters."), "You establish a consistent environmental cue without making a medical promise.", "using a ready-made bedtime scene"),
            _task("sereno-focus-scene", "sereno-02", "How can I choose an ambient scene for a focused work block?", "Changing tracks repeatedly can become more distracting than the room itself.", ("Pick one unobtrusive scene before the work block.", "Set the volume below speech and notification prominence.", "Leave it unchanged until the block ends, then assess whether it helped or distracted."), "You test one stable focus environment with a clear start and stop.", "using a ready-made focus scene"),
        ],
    },
    {
        "id": "sereno-p03",
        "app": "sereno",
        "variants": [
            _task("sereno-ocean-rain", "sereno-03", "How can I balance ocean and rain in one sound mix?", "Two textured sounds can combine well, but equal volume may make the mix crowded.", ("Start with ocean as the base at low volume.", "Add rain gradually until it is present but not dominant.", "Listen from the actual resting position and rebalance before leaving the mixer."), "You get a deliberate two-layer mix whose balance was checked in context.", "balancing ocean and rain layers"),
            _task("sereno-cabin-mix", "sereno-03", "How can I make a warm cabin-style ambient mix?", "Adding many attractive sounds at once can blur the scene and raise overall volume.", ("Choose one warm base sound.", "Add one subtle environmental layer.", "Mute each layer briefly to confirm it contributes before keeping the combination."), "The final mix contains only layers with a clear purpose.", "building a warm cabin-style mix"),
        ],
    },
    {
        "id": "sereno-p04",
        "app": "sereno",
        "variants": [
            _task("sereno-timed-winddown", "sereno-02", "How can I keep a wind-down sound from playing all night?", "A continuous sound may be unnecessary after the intended routine or work block ends.", ("Choose the scene and comfortable volume first.", "Set a timer that covers only the intended wind-down period.", "Confirm the ending behavior before putting the phone aside."), "The sound has a defined endpoint instead of becoming an unattended all-night default.", "timing a wind-down scene"),
            _task("sereno-study-stop", "sereno-01", "How can I use sound to mark the end of a study block?", "Without a clear stopping cue, background audio can continue while attention and volume are no longer monitored.", ("Start one sound with the planned study interval.", "Keep the level comfortable and avoid changing it during the block.", "Stop the sound when the interval ends and take the intended break."), "The audio becomes a bounded study cue rather than an endless stream.", "choosing a sound for a bounded study block"),
        ],
    },
    {
        "id": "sereno-p05",
        "app": "sereno",
        "variants": [
            _task("sereno-offline-flight", "sereno-01", "How can I prepare ambient sound for an offline flight?", "Connectivity may disappear in the air, and headphones must still allow safety announcements and comfort.", ("Choose the needed sounds while preparing for the trip.", "Confirm they work offline before boarding.", "Use a conservative volume and pause whenever crew instructions or awareness require it."), "You have an offline ambient option without compromising safety instructions.", "preparing the sound library for offline travel"),
            _task("sereno-private-routine", "sereno-03", "How can I build a sound routine without creating an account?", "A simple personal sound mix may not need cloud history or a profile.", ("Choose and balance the layers on the device.", "Use the mix during one defined routine.", "Recreate or adjust it from direct experience rather than relying on a health claim or social profile."), "You keep the routine focused on local sound choices and observed comfort.", "building an on-device sound routine"),
        ],
    },
    {
        "id": "sereno-p06",
        "app": "sereno",
        "variants": [
            _task("sereno-reading-background", "sereno-02", "How can I test ambient sound while reading?", "Sound with too much variation can compete with language processing during reading.", ("Choose a scene with a steady character.", "Set it well below the level that draws attention.", "Read one short section, then compare comprehension and comfort with silence."), "You decide from a small personal test whether the scene supports or distracts from reading.", "testing a steady scene while reading"),
            _task("sereno-breathing-pause", "sereno-01", "Can ambient sound frame a short breathing pause?", "A short pause may benefit from a consistent environment, but sound is not therapy or a substitute for care.", ("Choose one calm sound and a brief interval.", "Keep volume comfortable while breathing naturally without forcing a target.", "End the sound when the interval finishes and notice only your immediate comfort."), "The sound marks a short, low-pressure pause without claiming a clinical effect.", "choosing sound for a short breathing pause"),
        ],
    },
    {
        "id": "sereno-p07",
        "app": "sereno",
        "variants": [
            _task("sereno-volume-balance", "sereno-03", "How do I prevent a layered sound mix from becoming too loud?", "Several individually comfortable layers can sum to an uncomfortable overall level.", ("Set the device volume conservatively before adding layers.", "Introduce one layer at a time and compare with all layers playing.", "Reduce individual levels or remove a layer if the combined mix masks speech or feels tiring."), "The mix remains intentionally quiet enough for the actual room and listening setup.", "checking the total level of a layered mix"),
            _task("sereno-scene-comparison", "sereno-02", "How can I compare two ambient scenes fairly?", "Switching rapidly between scenes favors novelty and makes it hard to judge sustained comfort.", ("Listen to the first scene at a fixed low volume for a short block.", "Take a quiet break, then test the second at the same volume.", "Choose based on distraction and comfort in the intended activity, not visual appeal."), "You compare scenes under similar conditions and keep the more suitable one for that context.", "comparing two ready-made ambient scenes"),
        ],
    },
]


SPEC = {
    "schema": "lumi.google-images-canary-experiment/v1",
    "experiment_id": "google-images-real-task-canary-2026-08-23",
    "created_at": "2026-08-23",
    "assignment_salt": "lumi-gimg-canary-v1-frozen",
    "observation_window_days": {"minimum": 42, "maximum": 56},
    "apps": APPS,
    "pairs": PAIRS,
}
