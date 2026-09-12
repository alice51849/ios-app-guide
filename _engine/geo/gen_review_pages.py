#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Honest app review pages targeting "[app name] review 2026" queries.
Schema: Review + FAQPage. Honest developer disclosure. No fake praise.
"""
import html as html_lib
import json, os, sys
from pathlib import Path

HERE = Path(__file__).parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
sys.path.insert(0, str(HERE / ".." / "social"))
from videogen.registry import APPS, APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
import paid_upfront_surfaces  # noqa: E402

GEO_SITE = os.getenv("GEO_SITE", PUBLIC_SITE)
DEVELOPER_NOTE = "This review is written by the developer of the app being reviewed. All claims are factual — the limitations section describes real trade-offs."

REVIEWS = [
    {
        "key": "zafe",
        "slug": "zafe-private-photo-vault-review-2026",
        "title": "Zafe: Private Photo Vault Review 2026 — Is It Worth It?",
        "desc": "Honest review of Zafe Private Photo Vault for iPhone. What it does well, its real limitations, pricing, and who should (and shouldn't) download it.",
        "rating": 4,
        "verdict": "A straightforward, privacy-first photo vault that does exactly what it says. Best for users who want photos off the main camera roll without paying monthly.",
        "pros": [
            "One-time purchase — no subscription",
            "Face ID / Touch ID protection with encrypted storage",
            "No account or cloud upload required",
            "Clean, simple interface that doesn't get in the way",
        ],
        "cons": [
            "No cloud backup — if you delete the app or lose your phone, vault photos are gone unless you export them first",
            "Import is manual; no auto-import from camera roll",
            "No video recording inside the app",
        ],
        "who_for": "Anyone who wants a private space for sensitive photos — personal documents, private photos, screenshots of passwords — without a subscription.",
        "who_not_for": "Users who primarily want cloud backup of private photos; iCloud Private folder (iOS 16+) may be sufficient for some.",
        "faqs": [
            ("Is Zafe: Private Photo Vault safe?",
             "Photos in Zafe are encrypted and protected by Face ID or PIN on your device. The app does not connect to the internet or upload any photos to a server."),
            ("What happens to my photos if I delete Zafe?",
             "If you delete the app without first exporting your photos, they are gone. Always export important photos before uninstalling."),
            ("Is there a free version of Zafe?",
             "There is no separate free version. The app is available as a one-time purchase on the App Store."),
            ("Does Zafe back up photos to iCloud?",
             "No. Zafe deliberately does not use iCloud backup. Photos stay only on the device unless you manually share or export them."),
        ],
    },
    {
        "key": "scanto",
        "slug": "scanto-pro-pdf-scanner-review-2026",
        "title": "ScanTo Pro PDF Scanner Review 2026 — Offline-First Document Scanning",
        "desc": "Honest review of ScanTo Pro for iPhone. Truly offline PDF scanning vs. Adobe Scan and Scanner Pro — who needs it and who doesn't.",
        "rating": 4,
        "verdict": "The best choice for users who explicitly do not want scanned documents uploaded to any cloud service. Covers all standard scanning needs with a simple, one-time purchase.",
        "pros": [
            "Fully offline — no cloud upload, no account required",
            "Good auto-edge detection and perspective correction",
            "Exports clean multi-page PDFs",
            "One-time purchase",
        ],
        "cons": [
            "No cloud sync — cross-device access requires manual sharing",
            "OCR (text recognition) is basic compared to cloud-based scanners",
            "No direct integration with third-party cloud storage (Dropbox, etc.)",
        ],
        "who_for": "Lawyers, accountants, anyone handling confidential documents who doesn't want scans leaving the device. Travel use for passport / visa scanning.",
        "who_not_for": "Users who need OCR-powered search across scanned documents at scale, or who want automatic cloud sync to Dropbox or Google Drive.",
        "faqs": [
            ("Does ScanTo Pro upload scans to the internet?",
             "No. ScanTo Pro is fully offline. Scans are stored on your device only and are not uploaded to any server unless you manually share them."),
            ("How does ScanTo Pro compare to Adobe Scan?",
             "Adobe Scan syncs scans to Adobe's cloud and requires an Adobe account. ScanTo Pro keeps everything on-device and charges a one-time fee with no subscription."),
            ("Can ScanTo Pro recognize text in scans (OCR)?",
             "ScanTo Pro includes basic OCR. For high-volume, searchable document archives, a cloud-based solution with dedicated OCR is more capable."),
            ("Is ScanTo Pro free?",
             "ScanTo Pro is a one-time purchase. There is no free trial, but it is priced as a single payment with no renewal."),
        ],
    },
    {
        "key": "hourstag",
        "slug": "hourstag-review-2026-is-it-worth-it",
        "title": "HoursTag Product Guide — Work-Time Costs, Saved Spending and Goals",
        "desc": "First-party guide to the paid HoursTag app: convert spending into work hours, save history, tag purchases, review categories and track goals.",
        "rating": None,
        "verdict": "HoursTag is a paid download for converting spending into your own work hours and keeping the history. Saved records, Need/Want/Impulse tags, category insights, goals and a wishlist are part of the original app, not a separate upgrade.",
        "pros": [
            "Set hourly or monthly income and convert a price into work time",
            "Save spending records with Need, Want or Impulse tags",
            "Review monthly category insights and create custom categories",
            "Track goals and a wishlist in work hours; back up and restore data",
            "Paid download with no subscription, hidden upgrade or account",
        ],
        "cons": [
            "Income and spending are entered manually; this is not bank-transaction syncing",
            "Conversions depend on the income and price you enter",
            "Records stay on your device; make a backup before changing devices",
            "Seeing a time cost does not guarantee savings or a change in behaviour",
        ],
        "who_for": "People who want to understand recorded spending in work hours, review its categories and follow savings or wishlist goals over time.",
        "who_not_for": "People who need automatic bank imports or a guaranteed savings outcome. The original HoursTag should not be confused with HoursTag Lite's separate purchase-decision workflow.",
        "faqs": [
            ("Does HoursTag track my spending history?",
             "Yes. Save records, apply Need/Want/Impulse tags and custom categories, and review monthly category insights and goals. It is not limited to a one-off calculation."),
            ("What does the calculation look like?",
             "For example, an hourly income of $25 and a $100 expense gives four work hours. These are illustrative inputs, not the app's price or a promised saving. Save the expense, classify it and revisit the monthly breakdown."),
            ("Do I download it free and then pay to unlock history?",
             "No. This page concerns the original paid HoursTag download. One purchase includes its features, with no subscription or hidden upgrade."),
            ("Where can I see the original workflow?",
             "The existing HoursTag guide covers spending-to-time conversion, records, categories and goals. Use the guide linked below; this page does not claim an unverified Share Sheet extension."),
        ],
    },
    {
        "key": "aim990",
        "slug": "aim990-toeic-review-2026",
        "title": "Aim990 TOEIC App Review 2026 — Honest Score-Focused Assessment",
        "desc": "Honest review of Aim990 for iPhone TOEIC preparation. Listening & Reading practice, weak-spot drills, and the realistic expectations you need before downloading.",
        "rating": 4,
        "verdict": "Aim990 is focused and practical — it addresses the specific Listening and Reading components of TOEIC without extra features you won't use. Best for test-takers who already know the format.",
        "pros": [
            "Targeted Listening & Reading drill structure matching real TOEIC format",
            "Weak-spot identification helps focus study time efficiently",
            "One-time purchase — no subscription",
            "Offline access to practice materials",
        ],
        "cons": [
            "Does not cover TOEIC Speaking & Writing sections",
            "Best suited for intermediate–advanced learners; complete beginners may find it jumps in too fast",
            "No AI feedback on Speaking or Writing",
        ],
        "who_for": "TOEIC test-takers targeting 700–990 in Listening & Reading who want structured, test-format practice without a monthly subscription.",
        "who_not_for": "Beginners with very limited English foundation, or students also preparing for TOEIC Speaking & Writing sections.",
        "faqs": [
            ("What TOEIC sections does Aim990 cover?",
             "Aim990 covers the TOEIC Listening & Reading (L&R) test. It does not currently include TOEIC Speaking & Writing (S&W) practice."),
            ("Is Aim990 suitable for beginners?",
             "Aim990 is best suited for intermediate to advanced learners targeting a specific score. Complete beginners would benefit more from general English learning apps first."),
            ("Does Aim990 include a full mock TOEIC test?",
             "Yes. Aim990 includes simulation tests designed to match the format and difficulty of the real TOEIC L&R test."),
            ("What is the difference between Aim990 and Aim990 Plus?",
             "Aim990 covers standard L&R practice. Aim990 Plus adds advanced content tracks specifically designed for learners targeting scores above 900."),
        ],
    },
    {
        "key": "snapport",
        "slug": "snapport-passport-photo-app-review-2026",
        "title": "Snapport Product Guide — Paid Photo Exports and Print Layouts",
        "desc": "First-party guide to the paid Snapport app: size and alignment tools, JPEG/PNG/PDF exports and print sheets, with no government acceptance guarantee.",
        "rating": None,
        "verdict": "One paid Snapport download includes photo sizing, alignment, optional background tools, JPEG/PNG/PDF export and 4×6, A4 or Letter multiple-copy layouts. The app prepares files; it does not certify a photo or guarantee acceptance.",
        "pros": [
            "Common size templates and custom dimensions with face-alignment guides",
            "On-device processing, with the original photo kept safe",
            "JPEG, PNG and PDF exports; multiple-copy print layouts and cut guides",
            "One upfront purchase, no subscription or charge per export",
            "Optional template updates download a public size list, not your photo",
        ],
        "cons": [
            "Lighting, pose, print quality and final dimensions still need checking",
            "A background or touch-up tool is not permission to alter an official document photo",
            "Requirements vary by country, agency and application type",
            "Where an approved digital submission channel is required, self-printing is not a substitute",
        ],
        "who_for": "People who want private photo preparation and complete export/print tools, and will verify the receiving authority's rules before submitting.",
        "who_not_for": "Anyone needing guaranteed government acceptance or an approved digital submission service. Snapport is not a substitute for such a service.",
        "faqs": [
            ("What can I export after buying Snapport?",
             "JPEG, PNG or PDF, including multiple-copy layouts for 4×6, A4 and Letter. For a U.S. paper-photo application, you can arrange 2×2-inch copies on a 4×6 sheet. Check actual print size and official paper requirements."),
            ("Can I replace the background for a passport photo?",
             "Do not assume that editing is allowed. Capture the required background and lighting in the original photo. Use background or touch-up tools for an official document only if its receiving authority explicitly permits them."),
            ("Is this the free Snapport Lite app?",
             "No. This page and its App Store link refer to the paid Snapport app. Its complete output tools do not use Snapport Lite's free limits, watermark or unlock rules."),
            ("Does a template guarantee acceptance?",
             "No. Snapport is independent of government agencies and does not guarantee acceptance. Confirm current rules for the country, agency, application and child's age where relevant; recheck the final file or print before submitting."),
        ],
    },
    {
        "key": "cvdesk",
        "slug": "cv-desk-resume-builder-review-2026",
        "title": "CV Desk Resume Builder Review 2026 — ATS Score & iPhone PDF Export",
        "desc": "Honest review of CV Desk for iPhone. ATS resume scoring, instant feedback and PDF export — what it does well and who should use it.",
        "rating": 4,
        "verdict": "CV Desk fills a specific gap: an on-device ATS scorer and resume editor that doesn't require a subscription or account. Most useful for early-career job seekers who want a quick ATS diagnostic before submitting.",
        "pros": [
            "Instant ATS score shows what filters might reject your resume",
            "Clean PDF export with no watermark",
            "One-time purchase — no subscription, no account",
            "Works offline",
        ],
        "cons": [
            "Template variety is more limited than web-based resume builders",
            "ATS scoring reflects common patterns; specific employer ATS systems may vary",
            "Collaboration features (sharing for feedback) require manual PDF export",
        ],
        "who_for": "Job seekers who want a quick ATS audit before submitting, or freelancers who need a clean PDF resume quickly from an iPhone.",
        "who_not_for": "Users who want real-time collaboration on resume editing, or who need extensive template design options.",
        "faqs": [
            ("How accurate is CV Desk's ATS score?",
             "CV Desk's ATS score reflects common parsing patterns used by typical applicant tracking systems. It is a useful diagnostic — not a guarantee that any specific employer's ATS will behave identically."),
            ("Does CV Desk store my resume data on its servers?",
             "No. CV Desk processes everything on-device. Resume content is not uploaded to any server."),
            ("Can I use CV Desk to build a resume from scratch?",
             "Yes. CV Desk supports building a resume from a template or importing existing content, then refining it with ATS feedback."),
            ("Is CV Desk available on iPad?",
             "CV Desk is an iPhone app. It runs on iPad via compatibility mode but is optimised for iPhone screen sizes."),
        ],
    },
    {
        "key": "sononote",
        "slug": "sono-note-voice-notes-review-2026",
        "title": "Sono Note Review 2026 — On-Device Voice Transcription for iPhone",
        "desc": "Honest review of Sono Note for iPhone. On-device voice recording and transcription — privacy, accuracy and the right use cases explained.",
        "rating": 4,
        "verdict": "Sono Note does one thing well: record and transcribe audio without sending anything to the cloud. Best for anyone handling sensitive conversations who can't afford a data breach risk.",
        "pros": [
            "Fully on-device transcription — audio never leaves your phone",
            "No account required, no subscription",
            "Works offline",
            "Good for meeting notes, ideas, client calls",
        ],
        "cons": [
            "On-device transcription accuracy is lower than cloud-based AI transcription services",
            "No speaker identification or diarisation",
            "Not suitable as a substitute for certified legal transcription",
        ],
        "who_for": "Professionals handling confidential conversations (lawyers, healthcare, finance), journalists, freelancers on client calls.",
        "who_not_for": "Users who need the highest-accuracy transcription available and are comfortable uploading audio to a cloud service.",
        "faqs": [
            ("How accurate is Sono Note's transcription?",
             "On-device transcription is accurate for clear speech in quiet conditions. It is less accurate than cloud-based services in noisy environments or with accented speech."),
            ("Does Sono Note send audio to Apple or any cloud service?",
             "No. Sono Note performs transcription entirely on your device using on-device machine learning models. No audio is sent to any external server."),
            ("Can I export transcripts from Sono Note?",
             "Yes. You can share transcripts as text files or copy them to other apps manually from Sono Note."),
            ("What languages does Sono Note support for transcription?",
             "Sono Note supports the languages available through the on-device Speech framework on your iOS version. English is the most reliable; other languages depend on your device's local speech models."),
        ],
    },
    {
        "key": "lockhour",
        "slug": "lockhour-pro-app-blocker-review-2026",
        "title": "LockHour Pro App Blocker Review 2026 — Does It Actually Help You Focus?",
        "desc": "Honest review of LockHour Pro for iPhone. Timed focus sessions that block distracting apps — who it helps and why it won't fix distraction without habit change.",
        "rating": 4,
        "verdict": "LockHour Pro works as intended — it blocks apps during focus sessions using iOS Screen Time. The honest caveat: no app can replace the underlying habit of choosing to focus.",
        "pros": [
            "Clean focus session setup with app blocking",
            "Works within iOS Screen Time — system-level, effective",
            "One-time purchase",
            "Good for Pomodoro-style work blocks",
        ],
        "cons": [
            "Determined users can still override Screen Time if they know the passcode",
            "Doesn't solve the root cause of distraction — requires behaviour change alongside",
            "iOS Screen Time limitations apply",
        ],
        "who_for": "Students, remote workers and anyone who struggles to stay off social media during defined work or study blocks.",
        "who_not_for": "Users looking for a magic fix to chronic distraction; app blocking works best when paired with intentional habit-setting.",
        "faqs": [
            ("Can LockHour Pro block any app on my iPhone?",
             "LockHour Pro uses iOS Screen Time to block apps during focus sessions. It can block most third-party apps; some system apps may have limitations based on iOS Screen Time rules."),
            ("Can I bypass the block during a session?",
             "It is possible to override Screen Time blocks if you know the Screen Time passcode. LockHour Pro relies on iOS Screen Time, so its effectiveness depends on you not overriding your own settings."),
            ("Is LockHour Pro a subscription?",
             "No. LockHour Pro is a one-time purchase."),
            ("How does LockHour Pro compare to Freedom?",
             "Freedom charges an annual subscription and blocks apps at the network level. LockHour Pro is a one-time purchase and uses iOS Screen Time. Both are effective; the right choice depends on whether you prefer network-level blocking or a native iOS approach."),
        ],
    },
    {
        "key": "maskmyfile",
        "slug": "mask-my-file-review-2026-redact-personal-info",
        "title": "Mask My File Review 2026 — Redact Personal Info Before Sharing Documents on iPhone",
        "desc": "Honest review of Mask My File for iPhone. On-device personal information detection and masking in documents — what it catches, what it misses, and who needs it.",
        "rating": 4,
        "verdict": "Mask My File addresses a specific, practical need: redacting obvious personal identifiers (phone numbers, emails, ID numbers, addresses) from documents before sharing. Best for occasional sensitive document sharing.",
        "pros": [
            "On-device detection — no document content sent to a server",
            "Catches the most common personal data types automatically",
            "One-time purchase",
            "Simple workflow: import → detect → mask → export",
        ],
        "cons": [
            "Detection accuracy varies for unusual formats or non-standard number patterns",
            "Not a substitute for professional legal redaction in high-stakes contexts",
            "Handwritten text in scanned documents is not reliably detected",
        ],
        "who_for": "Anyone sharing invoices, contracts, forms or identity documents who wants to strip obvious personal data before sending. HR, small business, personal finance.",
        "who_not_for": "Legal teams requiring court-admissible redaction; that context requires specialised tools with audit trails.",
        "faqs": [
            ("Does Mask My File send my documents to a server for processing?",
             "No. Mask My File processes all detection and masking entirely on your device. Document content never leaves your iPhone."),
            ("What types of personal data does Mask My File detect?",
             "Mask My File detects phone numbers, email addresses, ID/passport numbers and home addresses in common formats. It may miss unusual formatting or non-Western patterns."),
            ("Can Mask My File handle scanned PDFs?",
             "Mask My File works with text-based PDFs. Scanned image-only PDFs require OCR first. Detection accuracy in scanned documents depends on OCR quality."),
            ("Is Mask My File approved for legal redaction?",
             "No. Mask My File is a convenience tool for everyday document sharing. For legal proceedings requiring certified redaction, use purpose-built legal document software."),
        ],
    },
    {
        "key": "gmoney",
        "slug": "gmoney-travel-budget-app-review-2026",
        "title": "G+Money Product Guide — Everyday Expenses, Currencies and CSV",
        "desc": "First-party guide to the paid G+Money app: daily expenses, custom categories, optional trips, currency conversion and text/CSV export.",
        "rating": None,
        "verdict": "G+Money is the original paid everyday expense tracker and currency converter, not a travel-only free tier. One purchase includes categories, a daily limit, date/category/trip filters and text or CSV export. Assigning an expense to a trip is optional.",
        "pros": [
            "Log everyday expenses and create categories with icons and colours",
            "Set a daily limit and see totals in your home currency",
            "Filter by date, category or optional trip/event; see grouped subtotals",
            "Use saved or manual exchange rates offline; refresh live rates when connected",
            "Export plain text or CSV; use the original app on iPhone and iPad",
            "Paid download with no subscription, account or later feature upgrade",
        ],
        "cons": [
            "Transactions are entered manually; G+Money does not connect to your bank",
            "Fetching fresh exchange rates needs a connection; saved/manual rates are not live quotes",
            "A spending record or export is not financial advice",
        ],
        "who_for": "People who want a private daily ledger with categories and exports, plus currency conversion and optional trip organisation when travelling.",
        "who_not_for": "People who require automatic bank imports, investment management or guaranteed budgeting outcomes. G+Money Lite is a separate product, not an upgrade step inside this paid app.",
        "faqs": [
            ("Can I use it for ordinary expenses without a trip?",
             "Yes. For example, log groceries, choose a category and leave the trip unassigned. Later filter by date or category and export the records as text or CSV. A trip is an optional grouping, not the whole product."),
            ("Do category filters or CSV need a paid upgrade?",
             "No. The original G+Money is a paid download with these features included. It is not a free app followed by a reporting upgrade."),
            ("Can I work offline?",
             "You can log spending and use saved or manually entered exchange rates without a connection. Refreshing live rates needs internet access."),
            ("Is G+Money available for iPad?",
             "Yes. The original app supports iPhone and iPad; it should not be described as an iPhone-only compatibility-mode app."),
            ("Does G+Money connect to my bank account?",
             "No. G+Money is a manual expense logger. You enter expenses yourself; it does not connect to bank accounts or financial institutions."),
        ],
    },
    {
        "key": "cyca",
        "slug": "cyca-period-tracker-review-2026",
        "title": "Cyca Period & Cycle Tracker Review 2026 — Private, On-Device Tracking",
        "desc": "Honest review of Cyca for iPhone. On-device period and cycle tracking with no cloud sync, no account, no ads — who needs it and what it can't do.",
        "rating": 4,
        "verdict": "Cyca does exactly what it promises: track menstrual cycles on-device with no data leaving your iPhone. The right choice for anyone uncomfortable with health data in the cloud.",
        "pros": [
            "Fully on-device — no cloud sync, no server, no account",
            "No subscription, no ads",
            "Clean interface focused on cycle tracking",
            "Predictions for next period and fertile window",
        ],
        "cons": [
            "No AI-powered symptoms or mood correlation features",
            "No wearable sync (Apple Watch, Fitbit)",
            "Data cannot be exported to share with a gynaecologist digitally",
        ],
        "who_for": "Anyone who wants period tracking without their health data going to a company's servers. Privacy-first users, people in regions with data protection concerns.",
        "who_not_for": "Users who want deep symptom tracking, wearable integration or AI cycle prediction models that require cloud processing.",
        "faqs": [
            ("Does Cyca sync period data to iCloud or any server?",
             "No. Cyca stores all data on your device only. It does not use iCloud, any cloud service or any Cyca server."),
            ("Is Cyca free?",
             "Cyca is available as a paid one-time purchase with no subscription or in-app advertising."),
            ("Can Cyca predict my next period?",
             "Yes. Cyca calculates predictions based on your logged cycle history. Prediction accuracy improves with more data entries."),
            ("What happens to my Cyca data if I delete the app?",
             "Since Cyca stores data only on your device, deleting the app removes all data. There is no cloud backup to restore from."),
        ],
    },
    {
        "key": "wifiaid",
        "slug": "wifi-aid-review-2026-iphone-network-diagnostic",
        "title": "WiFi Aid Review 2026 — iPhone Network Diagnostic Tool (Is It Worth It?)",
        "desc": "Honest review of WiFi Aid for iPhone. DNS, TCP and TLS diagnostics without requiring technical knowledge — the real use cases and limitations.",
        "rating": 4,
        "verdict": "WiFi Aid is genuinely useful for non-technical users who want to understand why a WiFi connection is slow or unreliable, without reading router admin panels.",
        "pros": [
            "Runs independent DNS, TCP and TLS checks",
            "Identifies whether the issue is local (router) or remote (ISP/server)",
            "No technical background required to interpret results",
            "One-time purchase, works offline once downloaded",
        ],
        "cons": [
            "Cannot fix network problems — only diagnoses them",
            "Advanced network engineers will find it less detailed than dedicated tools",
            "Some diagnostics depend on network access to function",
        ],
        "who_for": "Travellers with slow hotel WiFi, home users troubleshooting ISP issues, non-technical users who want actionable diagnostic results.",
        "who_not_for": "Network engineers who need packet capture, VLAN analysis or enterprise-level diagnostics.",
        "faqs": [
            ("What does WiFi Aid actually check?",
             "WiFi Aid runs DNS resolution tests, TCP connection tests to known endpoints, and TLS certificate checks to identify where a connection is failing or slow."),
            ("Can WiFi Aid fix my WiFi problems?",
             "No. WiFi Aid diagnoses where the problem is (router, ISP, remote server) so you know who to contact or what to check — it does not reconfigure your network."),
            ("Does WiFi Aid require an internet connection to run?",
             "Some tests require partial connectivity to reach test endpoints. Tests that check local router connectivity work without full internet access."),
            ("Is WiFi Aid free?",
             "WiFi Aid is a one-time purchase. There is no subscription or ongoing fee."),
        ],
    },
    {
        "key": "picclear",
        "slug": "picclear-photo-cleaner-review-2026",
        "title": "PicClear Photo Cleaner Review 2026 — Honest Assessment of the Photo Enhancer",
        "desc": "Honest review of PicClear for iPhone. On-device photo enhancement and cleanup — what it improves, what it can't fix, and who should use it.",
        "rating": 4,
        "verdict": "PicClear handles the most common photo cleanup needs — noise reduction, sharpening, basic enhancement — without requiring a subscription. Best for casual photo improvement, not professional editing.",
        "pros": [
            "On-device processing — photos stay private",
            "Handles noise reduction and basic sharpening well",
            "One-time purchase",
            "Simple enough for non-photographers",
        ],
        "cons": [
            "Not a replacement for Lightroom or professional photo editing apps",
            "Enhancement is algorithmic — results vary with photo type",
            "No layer-based editing or advanced RAW support",
        ],
        "who_for": "Casual photographers wanting to quickly clean up slightly blurry, noisy or dull photos without learning complex editing tools.",
        "who_not_for": "Professional photographers who need RAW processing, layered editing or colour grading tools.",
        "faqs": [
            ("Does PicClear upload photos to a server for processing?",
             "No. PicClear processes all enhancements on-device. Photos are not sent to any external server."),
            ("What kinds of photo problems does PicClear fix?",
             "PicClear addresses noise reduction, sharpening, and basic exposure correction. It is most effective on mildly degraded photos rather than heavily damaged images."),
            ("Is PicClear a subscription?",
             "No. PicClear is a one-time purchase with no recurring fee."),
            ("Can PicClear restore very old or badly damaged photos?",
             "PicClear can improve moderately degraded photos but is not a photo restoration tool for heavily damaged or historical images. Dedicated restoration apps handle that better."),
        ],
    },
    {
        "key": "dailymate",
        "slug": "dailymate-habit-tracker-review-2026",
        "title": "DailyMate Product Guide — Complete Language Phrases, Widget and Watch",
        "desc": "First-party guide to the paid DailyMate language app: complete practical phrases, listening, saved phrases, language progress, Widget and Apple Watch.",
        "rating": None,
        "verdict": "DailyMate teaches complete phrases for real-life situations, not habit tracking or isolated vocabulary. One paid download includes the full experience on iPhone, iPad, the interactive Home Screen Widget and Apple Watch.",
        "pros": [
            "8,400 practical phrases across 47 learning languages, 14 topics and 84 situations",
            "Beginner, intermediate and advanced phrases within every topic",
            "Listen using the system voice matched to the learning language",
            "Save useful phrases and keep progress separate for each language",
            "View, advance or save a phrase from the interactive Widget",
            "Apple Watch phrases, listening, saved items and progress included",
        ],
        "cons": [
            "A curated phrase-learning app, not a live translator for arbitrary conversations",
            "Not a habit, task, mood or health tracker despite this legacy URL",
            "System-voice availability depends on the selected language and device",
            "47 learning languages is distinct from this site's 50 content locales",
        ],
        "who_for": "Travellers and language learners who want ready-to-practise complete sentences, listening and saved phrases close at hand on their phone, Home Screen or wrist.",
        "who_not_for": "People who need real-time translation, a custom flashcard authoring system or habit-task reminders. Those are not DailyMate's product promise.",
        "faqs": [
            ("Is DailyMate a habit tracker?",
             "No. DailyMate is a language-phrase app. This existing URL was retained to correct the old description rather than create another page. The app teaches complete practical sentences, not recurring tasks or habits."),
            ("What does the paid download include?",
             "The complete phrase experience on iPhone and iPad, the interactive Widget and Apple Watch, with listening, saved phrases and per-language progress. There is no subscription."),
            ("How do I use it before a real conversation?",
             "Choose a language and situation, listen to the matching system voice and save useful phrases. The Widget can show the next phrase or save it; Apple Watch also provides phrases, listening and progress."),
            ("Will it translate anything I say in real time?",
             "No. It provides curated phrases for practice and reference, not live translation of arbitrary speech."),
        ],
    },
    {
        "key": "sereno",
        "slug": "sereno-sleep-sounds-review-2026",
        "title": "Sereno Sleep Sounds Review 2026 — Offline White Noise & Sleep Audio for iPhone",
        "desc": "Honest review of Sereno for iPhone. Offline sleep and focus sounds — white noise, rain, nature — without a subscription or internet connection.",
        "rating": 4,
        "verdict": "Sereno covers the core sleep sound use case well: reliable offline playback of white noise, rain and nature sounds without ongoing subscription costs.",
        "pros": [
            "Fully offline — sounds play without internet connection",
            "No subscription, no account",
            "Timer function for sleep use",
            "One-time purchase",
        ],
        "cons": [
            "Smaller sound library than cloud-streaming apps like Calm or Headspace",
            "No guided meditation or breathing exercises",
            "No personalised sleep analysis",
        ],
        "who_for": "Light sleepers, travellers, people who work in noisy environments and want background sounds without a subscription.",
        "who_not_for": "Users who want guided meditation, personalised sleep coaching or large curated sound libraries that justify a subscription.",
        "faqs": [
            ("Does Sereno work in airplane mode?",
             "Yes. Sereno's sounds are stored on-device and play fully offline, including in airplane mode — useful for flights."),
            ("Is Sereno a subscription?",
             "No. Sereno is a one-time purchase. There is no ongoing fee to access the included sounds."),
            ("How many sounds does Sereno include?",
             "Sereno includes a curated set of sleep and focus sounds including white noise, brown noise, rain and nature recordings. The exact count is listed on the App Store page."),
            ("Can I use Sereno during the day for focus, not just sleep?",
             "Yes. Sereno works for focus sessions, study and background noise masking, not just sleep."),
        ],
    },
]


def stars(n):
    return "★" * n + "☆" * (5 - n)


def render(r, *, pages=None):
    app = APPS.get(r["key"])
    if not app:
        return None
    aid = APPSTORE.get(r["key"], "")
    name = app.get("name", r["key"])
    sub = app.get("sub", "")
    price = app.get("price_usd", 0)
    first_party = r["key"] in paid_upfront_surfaces.contract()["reviews"].values()
    if first_party:
        base_url = paid_upfront_surfaces.require_available(
            r["key"], "en-US", Path(pages) if pages is not None else PAGES
        )
        badge = "Paid download · One upfront purchase · No subscription"
        store_url = f"{base_url}?pt=118326163&ct=geo_pick&mt=8"
    else:
        badge = "Free" if not price else f"${price:.2f} · one-time purchase"
        store_url = f"https://apps.apple.com/app/id{aid}?ct=iag_review" if aid else "#"
    store_url = html_lib.escape(store_url, quote=True)
    disclosure = (
        "First-party product guide by Lumi Studio, the app developer, based on "
        "the public App Store description and product requirements. This is not "
        "an independent review, a rating or an effectiveness test. Confirm the "
        "current features, device requirements and local download price on the App Store."
        if first_party else DEVELOPER_NOTE
    )
    rating_html = "" if first_party else f"  <span>{r['rating']}/5</span>"

    pros_html = "".join(f"<li>{p}</li>" for p in r["pros"])
    cons_html = "".join(f"<li>{c}</li>" for c in r["cons"])

    faqs_html = ""
    faqs_ld = []
    for q, a in r["faqs"]:
        visible_q = html_lib.escape(q) if first_party else q
        visible_a = html_lib.escape(a) if first_party else a
        faqs_html += f'<details class="faq"><summary><strong>{visible_q}</strong></summary><p>{visible_a}</p></details>\n'
        faqs_ld.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})

    editorial = (
        {"@context": "https://schema.org", "@type": "Article",
         "headline": r["title"], "description": r["desc"],
         "url": f"{GEO_SITE}/reviews/{r['slug']}.html",
         "mainEntityOfPage": f"{GEO_SITE}/reviews/{r['slug']}.html",
         "author": {"@type": "Organization", "name": "Lumi Studio"}}
        if first_party else
        {"@context": "https://schema.org", "@type": "Review",
         "itemReviewed": {"@type": "MobileApplication", "name": name,
                          "operatingSystem": "iOS", "applicationCategory": "UtilitiesApplication",
                          "offers": {"@type": "Offer", "price": str(price or 0), "priceCurrency": "USD"}},
         "reviewRating": {"@type": "Rating", "ratingValue": r["rating"], "bestRating": 5},
         "author": {"@type": "Organization", "name": "iOS App Guide"}}
    )
    ld = json.dumps([
        editorial,
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs_ld}
    ], ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{r['title']}</title>
<meta name="description" content="{r['desc']}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{GEO_SITE}/reviews/{r['slug']}.html">
<style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222}}
h1{{font-size:1.4rem;line-height:1.3}}
.meta{{display:flex;align-items:center;gap:1rem;margin:.5rem 0 1.5rem;font-size:.9rem;color:#555}}
.stars{{color:#f5a623;font-size:1.2rem}}
.badge{{color:#007aff}}
.verdict{{background:#f0f7ff;border-left:4px solid #007aff;padding:.8rem 1rem;border-radius:0 6px 6px 0;margin:1.5rem 0;font-style:italic}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin:1.5rem 0}}
@media(max-width:500px){{.cols{{grid-template-columns:1fr}}}}
.col h3{{margin-top:0;font-size:.95rem}}
ul{{padding-left:1.2rem;margin:.5rem 0}}
li{{margin:.4rem 0;font-size:.9rem}}
.who{{background:#f9f9f9;border-radius:8px;padding:1rem;margin:1.5rem 0}}
.who p{{margin:.4rem 0;font-size:.9rem}}
.cta{{display:inline-block;background:#007aff;color:#fff;padding:.7rem 1.4rem;border-radius:8px;text-decoration:none;font-weight:600;margin:1rem 0}}
.faq{{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}}
.faq summary{{cursor:pointer;font-size:.95rem}}
.faq p{{margin:.5rem 0 0;color:#444;font-size:.9rem}}
.disclosure{{font-size:.78rem;color:#999;margin-top:2rem;border-top:1px solid #eee;padding-top:1rem}}
</style>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<p><a href="{GEO_SITE}/en-US/">← App Guide</a></p>
<h1>{r['title']}</h1>
{f'<p class="disclosure">{disclosure}</p>' if first_party else ''}
<div class="meta">
{rating_html}
  <span class="badge">{badge}</span>
</div>
<p class="verdict">{r['verdict']}</p>
<div class="cols">
  <div class="col">
    <h3>✓ What it does well</h3>
    <ul>{pros_html}</ul>
  </div>
  <div class="col">
    <h3>✗ Real limitations</h3>
    <ul>{cons_html}</ul>
  </div>
</div>
<div class="who">
  <p><strong>Who it's for:</strong> {r['who_for']}</p>
  <p><strong>Who should skip it:</strong> {r['who_not_for']}</p>
</div>
<a href="{store_url}" class="cta" rel="noopener">View {name} on App Store →</a>
{f'<p><a href="{GEO_SITE}/guides/{r["key"]}.html">Read the existing {name} guide</a> · <a href="{GEO_SITE}/en-US/{r["key"]}.html">Product details</a></p>' if first_party else ''}
<h2>Frequently asked questions</h2>
{faqs_html}
<p class="disclosure">{disclosure}</p>
</body>
</html>"""
    return html


def main():
    out = PAGES / "reviews"
    out.mkdir(exist_ok=True)
    created = []
    for r in REVIEWS:
        html = render(r)
        if not html:
            continue
        path = out / f"{r['slug']}.html"
        path.write_text(html, encoding="utf-8")
        created.append(r["slug"])

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f'<url><loc>{GEO_SITE}/reviews/{s}.html</loc></url>' for s in created)
    sitemap += "\n</urlset>\n"
    (PAGES / "sitemap_reviews.xml").write_text(sitemap, encoding="utf-8")
    print(json.dumps({"review_pages": len(created), "slugs": created}))


if __name__ == "__main__":
    main()
