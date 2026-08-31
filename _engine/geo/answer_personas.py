#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persona-scoped recommendation data (page type: "best [app] for [persona]").

Each entry is verified from app source/READMEs/store copy by the persona
research worker (2026-07-08). Content is structured around a single user
type's real objections and workflow, NOT a generic feature list with a
persona label. Honesty rules applied:
  - aim990: HAS a subscription and TOEIC/ETS is a trademark → NEVER framed as
    "no subscription"; includes not-affiliated + no-score-guarantee caveats.
  - unblurry: honest about what on-device sharpening can and cannot recover.
  - pay-once framing used only for genuinely pay-once / one-time-unlock apps.

Consumed by answer_facts._persona_facts(); queries fed from queries.py.
"""
from typing import Any

# app_key -> list of persona entries.
# Each entry:
#   query    : canonical persona query (also added to queries.py)
#   triggers : distinctive substrings; ANY match routes to this persona
#   persona  : short label
#   lead     : opening line (honest concession first where relevant)
#   paras    : 2 short-answer paragraphs
#   look     : what_to_look_for bullets (the persona's must-haves)
#   steps    : decision_steps
#   fits     : where_app_fits (conversion hook)
#   faq      : persona-specific Q/A (objection handling)
PERSONAS: dict[str, list[dict[str, Any]]] = {
    "scanto": [
        {
            "query": "best offline document scanner app no cloud for nurses",
            "triggers": ["for nurses", "for a nurse", "nurse", "patient consent", "medical paperwork"],
            "persona": "nurses & clinical staff",
            "lead": "If you scan patient consent forms, discharge paperwork or referrals, the scanner has to keep that paperwork on the device — never uploaded to someone else's cloud.",
            "paras": [
                "For clinical work the priority is confidentiality and speed: capture a consent form, discharge sheet or ID in one tap, keep it fully on-device, and lock it behind Face ID. A scanner that makes zero network requests is the only kind you can safely use for sensitive patient paperwork.",
                "It also needs to work when the ward Wi-Fi is flaky — everything should function offline, with sharp multi-page PDFs and OCR so a form is searchable later. Avoid any scanner that forces a cloud account or free-tier upload.",
            ],
            "look": [
                "Zero network requests — paperwork never leaves the phone.",
                "Face ID / password lock on finished PDFs.",
                "Works fully offline (no ward Wi-Fi needed).",
                "One-tap capture and sharp multi-page PDFs.",
                "OCR so forms are searchable, pay-once (no per-scan paywall).",
            ],
            "steps": [
                "Confirm the scanner makes no network requests.",
                "Scan a consent form and lock the PDF with Face ID.",
                "Check it works with Wi-Fi off.",
                "Verify OCR makes the text searchable.",
                "Keep the file on-device or export deliberately.",
            ],
            "fits": "fits nurses who need fast, private, offline scanning of sensitive paperwork without a cloud account.",
            "faq": [
                {"q": "Does anything get uploaded to a cloud?", "a": "No — a properly offline scanner processes on-device and makes no network requests, so patient paperwork stays on your phone."},
                {"q": "Can I lock a scanned form?", "a": "Yes — lock the finished PDF behind Face ID or a password before it's stored or shared."},
                {"q": "Will it work without hospital Wi-Fi?", "a": "Yes — scanning, OCR and export all work offline."},
            ],
        },
        {
            "query": "best document scanner app no subscription for students",
            "triggers": ["for students", "for a student", "student", "lecture notes", "handouts"],
            "persona": "students",
            "lead": "For scanning lecture notes and handouts, the thing that matters most to a student is that one purchase covers unlimited scans — no paywall reappearing mid-semester.",
            "paras": [
                "A student scanner should turn a stack of handwritten notes or printed handouts into a clean, searchable PDF in seconds, with OCR so you can find a topic before an exam. Batch multiple pages into one file per lecture.",
                "Pay-once matters here: a single purchase should give unlimited scans, with no monthly fee and no watermark on the exported PDF.",
            ],
            "look": [
                "Pay once — unlimited scans, no monthly fee.",
                "OCR so notes are searchable before exams.",
                "Batch many pages into one PDF per lecture.",
                "No watermark on exports.",
                "Fast auto edge-detection for quick capture.",
            ],
            "steps": [
                "Scan a page of notes and check the edges auto-detect.",
                "Batch a full lecture into one PDF.",
                "Enable OCR and search for a keyword.",
                "Confirm exports have no watermark.",
                "Verify it's a one-time purchase, not a subscription.",
            ],
            "fits": "fits students who want unlimited, searchable note scans from a single pay-once purchase.",
            "faq": [
                {"q": "Is there a monthly fee?", "a": "No — a pay-once scanner charges once and gives unlimited scans, which suits a student budget better than a subscription."},
                {"q": "Can I search my scanned notes?", "a": "Yes — OCR turns printed and clear handwritten text into searchable content."},
                {"q": "Can I combine a whole lecture?", "a": "Yes — batch several pages into one PDF per class."},
            ],
        },
    ],
    "snapport": [
        {
            "query": "best passport photo app for babies and toddlers at home",
            "triggers": ["for babies", "for a baby", "baby", "toddler", "infant", "newborn"],
            "persona": "parents of babies & toddlers",
            "lead": "Getting a compliant passport photo of a baby is the hard case: they won't sit still, can't hold a pose, and most countries relax the neutral-expression rule for infants — so the app has to help you crop and size, not force an adult pose.",
            "paras": [
                "For a baby photo, lay the child on a plain white sheet and shoot from directly above, or hold them against a plain background. The app's job is the fiddly part: detecting the face, cropping to the exact country size, and checking head proportions — since a wailing or sleeping infant is usually accepted.",
                "Country-specific templates matter because infant head-size ratios and dimensions differ. A home app that outputs the correct size for your country saves a trip to a studio that may not handle babies well anyway.",
            ],
            "look": [
                "Country-specific size templates (head ratio varies for infants).",
                "Face-alignment guides for an unposed baby.",
                "Plain-background handling / background removal.",
                "Export a single correctly-sized photo to print.",
                "Guidance on relaxed infant expression rules.",
            ],
            "steps": [
                "Lay the baby on a plain white sheet, shoot from directly above.",
                "Pick your country's template in the app.",
                "Let it detect the face and crop to size.",
                "Check head proportions against the guide.",
                "Export and print (or order prints).",
            ],
            "fits": "fits parents who need a compliant infant passport photo at home without wrestling a baby into a studio pose.",
            "faq": [
                {"q": "My baby won't hold a neutral expression — is that OK?", "a": "For infants most countries relax the neutral-expression and open-eyes rules; check your country's guidance, which the app's template reflects."},
                {"q": "How do I get a plain background with a baby?", "a": "Shoot against a plain white sheet or use background removal, then let the app crop to size."},
                {"q": "Will it be the right size for my country?", "a": "Yes — pick your country's template so the head ratio and dimensions match official requirements. Always confirm against the official spec."},
            ],
        },
        {
            "query": "best app to take professional id photo for resume",
            "triggers": ["for resume", "for a resume", "resume photo", "cv photo", "professional headshot", "id photo for job"],
            "persona": "job seekers",
            "lead": "For a resume or job-application headshot, you don't need a studio — you need a cropped, correctly-proportioned photo with a clean background that looks professional at a small size.",
            "paras": [
                "A resume-photo template crops to the right proportions and lets you swap a messy background for a plain one, so a phone snap becomes a tidy headshot. Shoot in soft, even light facing a window and keep a neutral, approachable expression.",
                "Because it's on-device, your photo isn't uploaded anywhere, and a single export gives you a file ready to drop into a CV or a LinkedIn/ID upload.",
            ],
            "look": [
                "Resume / ID headshot template with correct proportions.",
                "Background replacement to a clean, plain colour.",
                "On-device processing (photo isn't uploaded).",
                "Single-photo export ready for a CV or profile.",
                "Guidance on framing and expression.",
            ],
            "steps": [
                "Face a window in soft, even light.",
                "Use the resume/ID template to frame the crop.",
                "Swap the background for a plain colour.",
                "Keep a neutral, approachable expression.",
                "Export and place it on your CV or profile.",
            ],
            "fits": "fits job seekers who want a clean, professional headshot from their phone without a photo studio.",
            "faq": [
                {"q": "Do I need a studio backdrop?", "a": "No — background replacement gives you a clean plain background from any setting."},
                {"q": "Is my photo uploaded anywhere?", "a": "On-device processing keeps the photo on your phone unless you export it."},
                {"q": "What size should a resume photo be?", "a": "There's no single standard; a square or 3:4 headshot works for most CVs and profiles — the template keeps proportions right."},
            ],
        },
    ],
    "cvdesk": [
        {
            "query": "best resume builder app for career changers 2026",
            "triggers": ["career changer", "career change", "changing careers", "switching careers"],
            "persona": "career changers",
            "lead": "When you're switching fields, the resume problem is different: your experience is real but 'unrelated' on paper, and ATS filters reject you before a human reads it. The fix is reframing and keyword matching, not a prettier template.",
            "paras": [
                "A career-changer resume needs transferable skills surfaced and the target job's language mirrored. Paste the job description, see which required skills are missing from your draft, and rework your bullets to speak the new field's vocabulary — so the ATS scores you in range.",
                "Doing this on-device means you can iterate honestly on real experience without uploading your CV to a third-party server, and export an ATS-safe PDF with no watermark.",
            ],
            "look": [
                "Job-description keyword matcher (see missing skills).",
                "On-device ATS score and fix list.",
                "Reframe bullets to the target field's language.",
                "ATS-safe PDF export, no watermark.",
                "No CV data uploaded to a server.",
            ],
            "steps": [
                "Paste the target job description.",
                "See which required skills are missing.",
                "Rewrite bullets to mirror the new field's terms.",
                "Recheck the ATS score until it's in range.",
                "Export an ATS-safe PDF.",
            ],
            "fits": "fits career changers who need to reframe transferable experience so ATS systems don't filter them out.",
            "faq": [
                {"q": "How do I get past ATS with unrelated experience?", "a": "Mirror the target job's keywords and surface transferable skills; the keyword matcher shows exactly what's missing."},
                {"q": "Is my resume uploaded anywhere?", "a": "No — the ATS scoring and matching run on-device, so your CV stays on your phone."},
                {"q": "Will the PDF have a watermark?", "a": "No — exports are clean, ATS-safe PDFs."},
            ],
        },
        {
            "query": "best ats resume app to tailor applications for each job",
            "triggers": ["tailor applications", "tailor each job", "for recent graduates", "for new grads", "for graduates", "recent graduate"],
            "persona": "recent graduates",
            "lead": "New grads apply to a lot of roles with a thin work history, so the winning move is tailoring each application to the posting — not sending the same generic CV everywhere.",
            "paras": [
                "Paste each job description and immediately see which skills or keywords your resume is missing, then adjust before you submit. With limited experience, matching the posting's language is what gets you past the ATS filter to a human reviewer.",
                "Because matching runs on-device, you can tailor quickly for every application without sharing your CV with any third-party service, and export a clean ATS-safe PDF each time.",
            ],
            "look": [
                "Offline job-description keyword matcher.",
                "Instant view of missing skills per posting.",
                "On-device ATS score.",
                "Fast re-tailoring for many applications.",
                "No third-party upload of your CV.",
            ],
            "steps": [
                "Paste the job posting for the role.",
                "See the missing keywords vs your resume.",
                "Add the genuine skills you have that match.",
                "Confirm the ATS score improved.",
                "Export a tailored PDF for that application.",
            ],
            "fits": "fits recent graduates tailoring each application to beat ATS filters with a limited work history.",
            "faq": [
                {"q": "Should I really change my CV for every job?", "a": "Tailoring the keywords to each posting materially improves ATS pass rates, which matters most when your experience is thin."},
                {"q": "Does it share my CV with anyone?", "a": "No — matching and scoring are on-device."},
                {"q": "Is it a subscription?", "a": "It's a pay-once app — check the current App Store listing for exact pricing."},
            ],
        },
    ],
    "picclear": [
        {
            "query": "best app to free up iphone storage deleting duplicate photos",
            "triggers": ["running out of storage", "storage is full", "free up storage", "out of space", "iphone storage full"],
            "persona": "people out of storage",
            "lead": "When your iPhone says 'Storage Almost Full', the fastest wins are exact-duplicate photos, near-identical burst shots, big videos and old screenshots — cleared in that order, with a review step so you never lose the keeper.",
            "paras": [
                "An on-device Vision scan can find true duplicates and visually-similar groups across your whole library, plus surface the large videos quietly eating gigabytes. The important part is that you review and confirm — nothing is auto-deleted.",
                "Clearing the biggest groups first reclaims space quickly, and doing it on-device means your library is never uploaded to a service.",
            ],
            "look": [
                "On-device scan for exact + near-duplicate photos.",
                "Large videos sorted by size.",
                "Similar bursts grouped so you keep the best.",
                "Review-and-confirm — no auto-delete.",
                "Runs on-device (library not uploaded).",
            ],
            "steps": [
                "Scan the library for duplicates and similar shots.",
                "Sort videos by size to find the biggest.",
                "Review each group and keep the best one.",
                "Confirm before deleting.",
                "Empty 'Recently Deleted' to reclaim the space.",
            ],
            "fits": "fits anyone out of storage who wants gigabytes back fast without deleting the wrong photo.",
            "faq": [
                {"q": "Will it delete photos without asking?", "a": "No — you review each group and confirm; nothing is removed without approval."},
                {"q": "What frees the most space fastest?", "a": "Large videos and exact duplicates first, then near-identical bursts and old screenshots."},
                {"q": "Is my library uploaded?", "a": "No — scanning runs on-device."},
            ],
        },
        {
            "query": "best app to clean up thousands of old photos on iphone",
            "triggers": ["thousands of old photos", "years of photos", "for seniors", "for my parents", "not tech savvy", "clean up old photos"],
            "persona": "people with years of photos",
            "lead": "After years of photos, the risk isn't finding duplicates — it's accidentally deleting something you wanted. The right tool surfaces near-duplicates by how they look, and never removes anything without an explicit yes.",
            "paras": [
                "A visual-similarity scan groups shots that look alike (not just identical filenames), so you can keep the best of each moment and clear the rest. Handling a large recent library in one pass means you make real progress without scrolling forever.",
                "Because it never auto-deletes and shows a clear before/after, it's safe for someone who isn't especially tech-savvy — and it keeps everything on-device.",
            ],
            "look": [
                "Near-duplicate grouping by visual similarity.",
                "Handles a large library in one scan.",
                "Never auto-deletes — explicit approval only.",
                "Clear review so you keep the best of each moment.",
                "On-device and private.",
            ],
            "steps": [
                "Run a full-library similarity scan.",
                "Review groups of look-alike photos.",
                "Keep the best of each moment.",
                "Approve the rest for deletion.",
                "Empty 'Recently Deleted' to finish.",
            ],
            "fits": "fits people with years of accumulated photos who want a safe, guided cleanup they won't regret.",
            "faq": [
                {"q": "Is it safe if I'm not techy?", "a": "Yes — it only groups and suggests; you approve every deletion, and nothing goes automatically."},
                {"q": "Does it find look-alikes, not just identical files?", "a": "Yes — it groups by visual similarity, so near-duplicate bursts are caught too."},
                {"q": "Are my photos uploaded?", "a": "No — the scan runs on-device."},
            ],
        },
    ],
    "unblurry": [
        {
            "query": "best app to fix blurry photos of kids on iphone",
            "triggers": ["blurry photos of kids", "blurry photo of my", "for parents", "of my kids", "family photos blurry"],
            "persona": "parents & families",
            "lead": "Kids never hold still, so soft-focus and camera-shake shots are inevitable. On-device sharpening can improve many of these — with the honest caveat that mild blur responds best and severe motion blur may not fully clear.",
            "paras": [
                "For a slightly soft photo of your child, Auto Clear and Sharpen modes can improve visible clarity in seconds, and a before/after slider lets you see the real improvement before you save — so you keep the shot only if it genuinely looks better.",
                "It works on-device with no subscription, so family photos aren't uploaded anywhere. Set expectations honestly: it sharpens soft focus and mild shake best; a heavily smeared shot leaves less usable visual information.",
            ],
            "look": [
                "Auto Clear / Sharpen for soft-focus shots.",
                "Before/after slider to judge the real result.",
                "On-device — family photos not uploaded.",
                "Pay-once, no subscription.",
                "Honest limits: best on mild blur, not severe smear.",
            ],
            "steps": [
                "Open the soft or shaky photo of your child.",
                "Try Auto Clear, then Sharpen.",
                "Compare with the before/after slider.",
                "Save only if it genuinely looks better.",
                "For very blurry shots, keep expectations realistic.",
            ],
            "fits": "fits parents rescuing soft-focus or mildly shaky photos of their kids, with honest limits on severe blur.",
            "faq": [
                {"q": "Can it fix any blurry photo?", "a": "It works best on soft focus and mild camera shake; a severely motion-blurred photo has little usable visual information, so results vary."},
                {"q": "Are my family photos uploaded?", "a": "No — processing is on-device."},
                {"q": "Is it a subscription?", "a": "No — it's pay-once."},
            ],
        },
        {
            "query": "best app to sharpen and enhance product photos on iphone",
            "triggers": ["product photos", "for small business", "for a small business", "product shots", "enhance product"],
            "persona": "small business owners",
            "lead": "For product listings, a slightly soft or low-resolution shot costs sales. On-device sharpening and upscaling can improve edges and perceived detail — best used on decent-but-soft photos rather than tiny, badly-degraded ones.",
            "paras": [
                "Super Resolution and 4× Upscale modes can improve clarity and apparent detail in low-resolution product shots, and a Document mode crisps up text-heavy images like labels. A before/after slider keeps you honest about the result before you publish.",
                "It's on-device with no subscription, so you can batch through a catalogue without uploading anything or paying a monthly fee. Manage expectations: it enhances captured information; it can't recreate information that was never captured.",
            ],
            "look": [
                "Super Resolution / 4× Upscale for low-res shots.",
                "Document mode for labels and text.",
                "Before/after slider to verify quality.",
                "On-device, pay-once (no monthly fee).",
                "Honest limits: enhances, doesn't invent detail.",
            ],
            "steps": [
                "Open the soft or low-res product photo.",
                "Apply Sharpen or Super Resolution / 4× Upscale.",
                "Use Document mode for label text.",
                "Compare before/after.",
                "Export the sharper image for your listing.",
            ],
            "fits": "fits small business owners sharpening product photos for listings without a subscription or cloud upload.",
            "faq": [
                {"q": "Can it make a tiny photo look pro?", "a": "It can improve clarity in low-resolution shots, but it can't recreate information that was never captured — start from the best original you have."},
                {"q": "Does it upload my product images?", "a": "No — enhancement is on-device."},
                {"q": "Is there a monthly fee?", "a": "No — it's a pay-once app."},
            ],
        },
    ],
    "sononote": [
        {
            "query": "best voice notes app that summarizes meetings on iphone",
            "triggers": ["for remote workers", "for business professionals", "summarizes meetings", "summarize meetings", "meeting summary", "follow-up email"],
            "persona": "remote workers & professionals",
            "lead": "After a call you don't want a raw transcript — you want the summary, the action items, and a draft follow-up. And for client conversations, that processing should stay on your device.",
            "paras": [
                "Record or import a meeting, get an accurate transcript, then a concise summary with extracted action items and a draft follow-up email — turning an hour of talk into something you can act on in a minute. On-device processing means sensitive discussions never hit a cloud account.",
                "For remote work this replaces frantic note-taking during calls: let it capture and summarise while you stay present in the conversation.",
            ],
            "look": [
                "Accurate on-device transcription.",
                "Automatic summary + action items.",
                "Draft follow-up email generated for you.",
                "No cloud account — private by design.",
                "Export to your notes or tasks app.",
            ],
            "steps": [
                "Record or import the meeting audio.",
                "Let it transcribe on-device.",
                "Generate the summary and action items.",
                "Review the draft follow-up email.",
                "Export the notes where your team lives.",
            ],
            "fits": "fits remote workers who want summaries, action items and follow-ups from calls without a cloud account.",
            "faq": [
                {"q": "Does my meeting audio leave my phone?", "a": "No — recording, transcription and summarising happen on-device."},
                {"q": "Do I get action items, not just a transcript?", "a": "Yes — it extracts action items and a summary, and can draft a follow-up email."},
                {"q": "Can I share the notes?", "a": "Yes — export the summary and to-dos to your notes or tasks app."},
            ],
        },
        {
            "query": "best app to record lectures and get automatic notes",
            "triggers": ["record lectures", "record a lecture", "lecture notes automatically", "for college students", "study notes from audio"],
            "persona": "students",
            "lead": "For lectures, the win is turning an hour of audio into clean notes: a transcript plus the key points and a short summary — so revision takes minutes, not a re-listen.",
            "paras": [
                "Record the class, get a transcript, then one-tap bulleted key points and a concise summary you can study from. Reviewing a summary beats scrubbing through audio when exams are close.",
                "On-device processing keeps recordings private, and there's no per-recording paywall to worry about mid-term.",
            ],
            "look": [
                "Transcript of the full lecture.",
                "One-tap key points + summary.",
                "On-device (recordings stay private).",
                "No per-recording paywall.",
                "Export notes to study from.",
            ],
            "steps": [
                "Record the lecture (with permission).",
                "Transcribe it to text.",
                "Generate key points and a summary.",
                "Study from the summary before the exam.",
                "Export notes to your study app.",
            ],
            "fits": "fits students turning recorded lectures into clean, studyable notes fast.",
            "faq": [
                {"q": "Do I have to re-listen to the whole lecture?", "a": "No — you study from the auto-generated key points and summary instead."},
                {"q": "Are my recordings private?", "a": "Yes — processing is on-device."},
                {"q": "Should I record lectures?", "a": "Ask your lecturer's permission first; recording policies vary by institution."},
            ],
        },
    ],
    "lockhour": [
        {
            "query": "best app to block social media while studying iphone",
            "triggers": ["while studying", "during final exams", "for exams", "block tiktok", "block instagram", "block social media"],
            "persona": "students in exam season",
            "lead": "During exams, willpower isn't the tool — a hard timed block is. The app should shut off TikTok, Instagram and any distraction for a set study session and reopen them automatically when time's up.",
            "paras": [
                "Using Apple's Screen Time API, you can hard-block specific apps, whole categories or websites for a timed focus session, with an optional mode that stops you bailing out early. When the timer ends, everything unlocks on its own — no manual re-enabling.",
                "It's a pay-once focus tool with no monthly fee, which suits a student who just wants distraction gone during revision blocks.",
            ],
            "look": [
                "Hard block on apps, categories and websites.",
                "Timed sessions that auto-unlock when done.",
                "Optional Hard Mode (no early exit).",
                "Uses Apple Screen Time (system-level block).",
                "Pay-once, no monthly fee.",
            ],
            "steps": [
                "Pick the apps/categories to block (e.g. socials).",
                "Set the study session length.",
                "Optionally enable Hard Mode.",
                "Start the session and study.",
                "Everything unlocks automatically at the end.",
            ],
            "fits": "fits students who need social media hard-blocked during timed revision sessions.",
            "faq": [
                {"q": "Can I cheat and unlock early?", "a": "With Hard Mode enabled, early exit is prevented for the session; otherwise everything unlocks when the timer ends."},
                {"q": "Does it really block apps?", "a": "Yes — it uses Apple's Screen Time API for a system-level block, not just reminders."},
                {"q": "Is it a subscription?", "a": "No — it's pay-once."},
            ],
        },
        {
            "query": "best focus app to stop phone distractions working from home",
            "triggers": ["working from home", "work from home", "for remote workers", "deep work", "stop distractions at work"],
            "persona": "remote workers",
            "lead": "Working from home, the phone is the leak. A deep-work block that shields your chosen apps for a fixed stretch keeps you in uninterrupted focus without relying on self-control.",
            "paras": [
                "Choose the apps and categories that derail you, set a focus duration, and let a Deep Work mode shield them — with an optional Hard Mode that prevents early exit. It's the difference between 'I'll just check quickly' and an actual focus block.",
                "As a pay-once tool it fits a home-office setup without adding yet another monthly subscription.",
            ],
            "look": [
                "Deep Work mode shields chosen apps/categories.",
                "Set focus-block duration.",
                "Optional Hard Mode (no early exit).",
                "System-level block via Screen Time.",
                "Pay-once, no monthly fee.",
            ],
            "steps": [
                "Select the apps that distract you.",
                "Set a focus-block length.",
                "Enable Hard Mode if you need it.",
                "Start Deep Work and do the task.",
                "Apps return automatically when time's up.",
            ],
            "fits": "fits remote workers who want uninterrupted deep-work blocks without willpower battles.",
            "faq": [
                {"q": "Will it stop me 'just checking' my phone?", "a": "Hard Mode prevents early exit for the block, so a quick check isn't possible until it ends."},
                {"q": "Can I block whole categories?", "a": "Yes — block individual apps, categories or websites."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
        {
            "query": "app to stop doomscrolling at night and protect my sleep schedule",
            "guide_title": "Late-night doomscrolling: pre-committed friction beats 1 a.m. willpower",
            "triggers": [
                "doomscrolling at night",
                "stop doomscrolling",
                "protect my sleep schedule",
                "scrolling in bed at night",
                "phone before bed blocker",
                "sleep wind down mode",
            ],
            "persona": "shift workers and anyone whose bedtime dies to the feed",
            "lead": "At the end of a draining shift, willpower is at its weakest — the fix is not more discipline at 1 a.m. but friction you set up earlier, while you still meant it.",
            "paras": [
                "LockHour Pro's Sleep Wind Down mode locks the late-night scrolling apps for the window you choose, and Morning Reset keeps the feed shut until the day has actually started. Hard Mode adds a cooldown and a confirmation before an early unlock — calm friction, not an unbreakable cage — and when the window ends everything unlocks on its own, with a Widget, Lock Screen or Dynamic Island countdown showing how long is left.",
                "It is a one-time purchase with no subscription, no account, no ads and no tracking — usage data stays on the device. If Apple's built-in Screen Time limits already work for you, keep using them free; where LockHour earns its price is the wind-down ritual, the Hard Mode friction and focus statistics that make reclaimed evenings visible. It is not a medical or sleep-treatment tool: it adds friction, it does not promise behavior change.",
            ],
            "look": [
                "A wind-down window that locks the scrolling apps at the hour you chose earlier.",
                "A morning mode so the day does not start inside a feed.",
                "Optional Hard Mode: cooldown plus confirmation before early unlock.",
                "Automatic unlock when the window ends, with a visible countdown.",
                "Pay-once, no account, no ads, no tracking.",
            ],
            "steps": [
                "Pick the apps that eat your nights and set the wind-down window while you are still fresh.",
                "Add Morning Reset if waking up into the feed is part of the problem.",
                "Enable Hard Mode if a plain block is too easy to dismiss.",
                "Let everything unlock automatically at the end of the window.",
                "Check the focus statistics after a week to see what the evenings gave back.",
            ],
            "fits": "fits shift workers and late scrollers who need pre-committed friction at night rather than another test of 1 a.m. willpower.",
            "faq": [
                {
                    "q": "Isn't Apple's built-in Screen Time enough?",
                    "a": "If it works for you, use it — it is free. Its limits can be dismissed with a single tap, which is exactly what fails late at night; LockHour adds a deliberate cooldown, a wind-down ritual and visible statistics.",
                },
                {
                    "q": "Will it cure my scrolling habit?",
                    "a": "No app can promise behavior change, and this is not a medical or sleep-treatment tool. It makes opening the feed slower and more conscious, and makes the reclaimed time visible — that is all it claims.",
                },
                {
                    "q": "What happens when the block ends?",
                    "a": "Everything unlocks automatically — no manual re-enabling — and a widget or Lock Screen countdown shows how long is left.",
                },
            ],
        },
        {
            "query": "focus app for adults who impulsively open apps without thinking",
            "guide_title": "Impulse-opened apps: putting a pause between thumb and icon",
            "triggers": [
                "impulsively open apps",
                "open apps without thinking",
                "opening apps on autopilot",
                "catch myself in an app",
                "app blocker for impulse",
            ],
            "persona": "adults who catch themselves inside an app with no memory of opening it",
            "lead": "If the problem is opening apps on autopilot rather than using them too long, the useful tool is not a usage report — it is a pause inserted between the thumb and the icon.",
            "paras": [
                "LockHour Pro's Quick Focus starts a short block in one tap, Study Mode runs Pomodoro-style cycles with breaks, and Hard Mode puts a cooldown and a confirmation in front of an early unlock — turning an impulse into a conscious choice. Streaks and reclaimed-hours statistics make the change visible instead of vague.",
                "There is no account and no tracking, and it is a one-time purchase with no subscription. One honest limit: any iOS blocker can be removed by the person who set it up. LockHour's design makes unlocking slower and more deliberate, which is what helps with impulsive opens — no app can stop someone who has firmly decided to scroll. It is a focus utility, not an ADHD treatment or medical product; if attention issues affect your daily life, talk to a clinician.",
            ],
            "look": [
                "One-tap short blocks for the moment you notice the autopilot.",
                "A cooldown plus confirmation before early unlock, so an impulse must become a decision.",
                "Pomodoro-style focus cycles with breaks.",
                "Streaks and reclaimed-hours statistics you can actually see.",
                "No account, no tracking, pay-once.",
            ],
            "steps": [
                "Pick the two or three apps you open without thinking.",
                "Use Quick Focus the moment you catch the autopilot.",
                "Enable Hard Mode so an early unlock needs a cooldown and a confirmation.",
                "Run Study Mode cycles for longer work blocks.",
                "Watch the streak — the point is making the impulse visible.",
            ],
            "fits": "fits adults whose problem is unconscious opening rather than screen-time totals, and who want the unlock made slower and more deliberate.",
            "faq": [
                {
                    "q": "Couldn't I just disable the blocker?",
                    "a": "Yes — every iOS blocker can be removed by its owner. The design goal is to make that slower and more conscious, which is what interrupts an impulse; nothing can stop a firm decision to scroll.",
                },
                {
                    "q": "Is this an ADHD app?",
                    "a": "No. LockHour is a focus utility, not an ADHD treatment or a medical product. If attention issues affect your daily life, talk to a clinician.",
                },
                {
                    "q": "Is it a subscription?",
                    "a": "No — it is a single one-time purchase, with no account and no tracking.",
                },
            ],
        },
    ],
    "gmoney": [
        {
            "query": "best travel budget tracker app no subscription iphone",
            "triggers": ["travel budget", "for travelers", "for travellers", "track spending abroad", "trip budget"],
            "persona": "travelers",
            "lead": "On a trip you need a budget tracker that works offline in a country with no data, handles multiple currencies, and doesn't demand an account — organised by trip so each holiday is separate.",
            "paras": [
                "Log expenses per trip, convert each to your home currency at a saved rate, and see a per-category breakdown — all offline, so it works on a plane or in a dead-zone. Export a CSV afterwards if you want to reconcile.",
                "Pay-once with no account means no monthly fee and no sign-up friction while you're travelling.",
            ],
            "look": [
                "Organised by trip.",
                "Multi-currency with saved exchange rates.",
                "Fully offline (works with no data).",
                "Per-category breakdown + CSV export.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Create the trip.",
                "Set your home and local currencies.",
                "Log expenses as you go (offline is fine).",
                "Watch the per-category running total.",
                "Export a CSV when you're home.",
            ],
            "fits": "fits travellers who want offline, multi-currency, per-trip budgeting without an account or subscription.",
            "faq": [
                {"q": "Does it work with no signal abroad?", "a": "Yes — it's fully offline; entries and conversions don't need data."},
                {"q": "Multiple currencies per trip?", "a": "Yes — each expense converts to your home currency at a saved rate."},
                {"q": "Do I need an account?", "a": "No — it's pay-once with no sign-up."},
            ],
        },
        {
            "query": "best app to track daily spending abroad multiple currencies",
            "triggers": ["for backpackers", "budget travelers", "budget travellers", "daily spending abroad", "spending abroad", "airplane mode"],
            "persona": "backpackers",
            "lead": "Backpacking on a budget, you need to know how much you have left today — in your home currency — even in airplane mode.",
            "paras": [
                "Every expense converts to your home currency at a saved exchange rate, and a running daily average shows whether you're on budget. Because it's fully offline, it works on long-haul flights and in remote spots with no connection.",
                "No account and a single purchase keep it friction-free for months on the road.",
            ],
            "look": [
                "Converts every expense to home currency.",
                "Running daily average vs budget.",
                "Works in airplane mode / offline.",
                "Multi-currency for multi-country trips.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Set your daily budget and home currency.",
                "Log each expense in local currency.",
                "See the converted running daily average.",
                "Adjust spending to stay on budget.",
                "Repeat across countries and currencies.",
            ],
            "fits": "fits budget backpackers tracking daily multi-currency spend offline.",
            "faq": [
                {"q": "Will it work on a flight?", "a": "Yes — it's fully offline, so airplane mode is fine."},
                {"q": "Can it handle several currencies on one trip?", "a": "Yes — each entry converts to your home currency."},
                {"q": "Is there a subscription?", "a": "No — pay-once, no account."},
            ],
        },
    ],
    "gmoneylite": [
        {
            "query": "best free travel expense tracker with currency conversion for iphone",
            "guide_title": "Free travel expense trackers with currency conversion: what to check",
            "triggers": [
                "free travel expense tracker",
                "travel expenses with currency conversion",
                "track spending in local currency",
                "travel budget in home currency",
                "offline trip expense tracker",
                "travel money app no subscription",
            ],
            "persona": "travellers testing a private multi-currency budget before unlocking unlimited trips",
            "lead": "For a short trip, a useful free-to-start tracker should let you log a few local-currency expenses, see home-currency totals, and test a budget before deciding whether unlimited trips are worth a one-time unlock.",
            "paras": [
                "G+Money Lite includes one trip and up to three expenses free, together with rates, a budget, category statistics, and a summary. Enter each purchase in the local currency and see it in your home currency using a live, saved, or manually set rate; saved rates keep the workflow usable offline.",
                "If you need more entries or trips, a single one-time purchase removes those limits. There is no subscription, account, or tracking, and the App also supports a Home Screen widget and Apple Watch.",
            ],
            "look": [
                "A useful free allowance that includes one trip and three expenses.",
                "Local-currency entry with immediate home-currency totals.",
                "Budget, category statistics, and summary available before purchase.",
                "Saved or manual exchange rates for offline use.",
                "One one-time unlock with no subscription, account, or tracking.",
            ],
            "steps": [
                "Set your home currency and create the free trip.",
                "Choose a live, saved, or manual rate for the local currency.",
                "Log up to three expenses while testing the workflow.",
                "Review the budget, category statistics, and home-currency summary.",
                "Unlock unlimited expenses and trips once only if the free allowance fits your travel workflow.",
            ],
            "fits": "fits travellers who want to test a private local-to-home-currency expense workflow free, then remove trip and entry limits with a single one-time purchase.",
            "faq": [
                {
                    "q": "What can I use without paying?",
                    "a": "You can use rates, a budget, category statistics, and a summary for one trip with up to three expenses.",
                },
                {
                    "q": "Will it still work without data abroad?",
                    "a": "Yes — saved or manually set rates keep expense entry and conversion available offline. An internet connection is needed only when fetching updated public exchange rates.",
                },
                {
                    "q": "Is the full version a subscription?",
                    "a": "No — one optional one-time purchase unlocks unlimited expenses and trips.",
                },
            ],
        },
    ],
    "hourstag": [
        {
            "query": "best app to track where my money goes and save more",
            "triggers": ["save more", "building savings", "savings habit", "young professionals", "where my money goes"],
            "persona": "people building savings habits",
            "lead": "If saving feels abstract, tracking goals in hours-worked instead of dollars makes progress feel earned — you're not saving $500, you're saving 20 hours of your life toward something.",
            "paras": [
                "Set savings targets on a goals screen and track progress in hours needed, so an abstract number becomes concrete and motivating. Pairing this with the spend-as-time reframe builds a habit that sticks.",
                "It's pay-once and account-free, so it stays simple enough to actually check regularly.",
            ],
            "look": [
                "Goals/wishlist tracked in hours-worked.",
                "Progress feels earned, not abstract.",
                "Pairs with spend-as-time reframing.",
                "Simple enough to check daily.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Set your hourly wage.",
                "Add a savings goal on the goals screen.",
                "Track progress in hours needed.",
                "Reframe spends as hours to protect the goal.",
                "Watch the goal fill up over time.",
            ],
            "fits": "fits young professionals building a savings habit by measuring goals in hours, not just dollars.",
            "faq": [
                {"q": "How is this different from a budget app?", "a": "It measures both spending and savings goals in hours-of-work, which many people find more motivating than dollar figures."},
                {"q": "Does it track goals?", "a": "Yes — a goals/wishlist screen tracks savings targets in hours needed."},
                {"q": "Subscription?", "a": "No — pay-once, no account."},
            ],
        },
    ],
    "hourstaglite": [
        {
            "query": "best app to convert prices into work hours before buying",
            "guide_title": "Price-to-work-hours apps: what to check before buying",
            "triggers": [
                "price in work hours",
                "purchase cost in work hours",
                "stop impulse buying",
                "mindful spending before buying",
                "need want impulse tracker",
                "life cost calculator",
            ],
            "persona": "mindful shoppers deciding whether a purchase is worth their time",
            "lead": "Before buying, convert the price into take-home work hours, then label the choice as a need, want or impulse so the trade-off is clear before money leaves your account.",
            "paras": [
                "HoursTag Lite is a purchase-before Worth Lens rather than a bank-linked budget. It calculates life cost from your take-home value per work hour, keeps the choice and category visible, and builds private value insights from the decisions you save.",
                "One complete choice can be saved free. A single one-time unlock adds unlimited choices and edits, targets and progress, sharing, complete insights, and backup and restore without a subscription.",
            ],
            "look": [
                "Price converted into take-home work hours before purchase.",
                "Need, want and impulse labels beside each choice.",
                "Categories, value patterns and six-month insights.",
                "Targets, widgets and Apple Watch support.",
                "On-device data with no account or tracking.",
            ],
            "steps": [
                "Set your take-home income and working time.",
                "Enter the price before making the purchase.",
                "Review the resulting life cost in work hours.",
                "Mark the choice as a need, want or impulse and choose a category.",
                "Save the choice or compare it with a target before deciding.",
            ],
            "fits": "fits mindful shoppers who want a private pause before buying by comparing a price with the work time it costs.",
            "faq": [
                {
                    # 誠實鐵則:免費門頁面不可裸寫付費版名稱(free-first 稽核
                    # 會把「文案講付費版、商店連結是免費版」判為 identity
                    # mismatch);付費版以「the paid companion app」指稱即可。
                    "q": "Is this the same workflow as the paid companion app?",
                    "a": "No — HoursTag Lite is a purchase-before Worth Lens for evaluating a single choice, while the paid companion app focuses on converting existing spending into work time. The two are separate apps from the same developer.",
                },
                {
                    "q": "What can I save for free?",
                    "a": "You can save one complete choice free; the optional one-time unlock adds unlimited choices, targets, sharing, complete insights, and backup and restore.",
                },
                {
                    "q": "Does it require an account or subscription?",
                    "a": "No account or subscription is required. Core data stays on the device, and the optional premium upgrade is a one-time purchase.",
                },
            ],
        },
    ],
    "aim990": [
        {
            "query": "best toeic prep app offline study plan for iphone",
            "triggers": ["toeic prep", "toeic practice", "study for toeic", "toeic study plan", "for toeic test takers"],
            "persona": "TOEIC test-takers",
            "lead": "For a TOEIC-style prep app the useful thing is a structured plan plus a weakness engine that drills exactly the question types you keep missing — all workable offline. (Aim990 is an independent study app, not affiliated with or endorsed by ETS, and no score is guaranteed.)",
            "paras": [
                "A day-by-day plan covering reading, listening, vocabulary and mock tests keeps you moving, while a weakness engine focuses practice on your weakest parts instead of re-drilling what you already know. Working offline means you can practise on a commute with no data.",
                "Set expectations honestly: consistent practice improves familiarity with the format; results depend on your effort and starting level. Always check the current App Store listing for features and pricing.",
            ],
            "look": [
                "Day-by-day plan across all parts.",
                "Weakness engine targets weak question types.",
                "Full mock tests to build stamina.",
                "Works offline for commute practice.",
                "Independent of ETS; no score guarantee.",
            ],
            "steps": [
                "Take a baseline to find weak areas.",
                "Follow the day-by-day plan.",
                "Let the weakness engine drill weak parts.",
                "Sit periodic full mock tests.",
                "Track familiarity improving over time.",
            ],
            "fits": "fits TOEIC test-takers who want a structured, offline prep plan that targets their weak areas.",
            "faq": [
                {"q": "Is this an official ETS app?", "a": "No — it's an independent study app, not affiliated with or endorsed by ETS, and TOEIC is a trademark of ETS."},
                {"q": "Will it guarantee a high score?", "a": "No app can guarantee a score; results depend on your effort and starting level. It helps by drilling your weak areas and the test format."},
                {"q": "Does it work offline?", "a": "Yes — you can practise without a data connection, e.g. on a commute."},
            ],
        },
        {
            "query": "best app to study for toeic on the commute offline",
            "triggers": ["on the commute", "commute offline", "for busy professionals", "study on the subway", "esl learners toeic"],
            "persona": "commuters & working professionals",
            "lead": "If your only study window is the commute, an offline TOEIC-style app that needs no login lets you practise on the subway or a plane. (Aim990 is independent, not affiliated with ETS; no score is guaranteed.)",
            "paras": [
                "No login and full offline support mean you can open a session anywhere and pick up where you left off. Short, targeted drills from a weakness engine fit a 20-minute commute better than long open-ended study.",
                "Be realistic: steady daily practice builds format familiarity over weeks; the app targets your weak spots but the outcome depends on your effort. Confirm current pricing on the App Store.",
            ],
            "look": [
                "Fully offline, no login required.",
                "Short targeted drills for short windows.",
                "Weakness engine for efficient practice.",
                "Resume where you left off.",
                "Independent of ETS; no score guarantee.",
            ],
            "steps": [
                "Download so it's ready offline.",
                "Open a short drill on the commute.",
                "Focus on the weak areas it surfaces.",
                "Do a mock test on longer journeys.",
                "Keep a daily streak going.",
            ],
            "fits": "fits busy commuters who can only study TOEIC in short offline windows.",
            "faq": [
                {"q": "Do I need to log in or be online?", "a": "No — it works fully offline with no login, so it's ideal for a commute."},
                {"q": "Is it affiliated with the official test?", "a": "No — it's independent and not affiliated with ETS; TOEIC is an ETS trademark."},
                {"q": "Can it promise a score?", "a": "No — no score is guaranteed; it helps you practise your weak areas and the format."},
            ],
        },
    ],
    "aim990plus": [
        {
            "query": "best offline English listening and reading exam trainer for iPhone",
            "triggers": [
                "exam pressure trainer",
                "English listening and reading exam",
                "offline exam practice",
                "timed English practice",
            ],
            "persona": "adult English exam learners",
            "lead": (
                "For adult learners preparing under time pressure, useful practice "
                "needs original listening and reading questions, timed sets, mistake "
                "replay and offline progress without a recurring subscription."
            ),
            "paras": [
                (
                    "A focused routine should move from a short warm-up into a timed "
                    "pressure set, then bring every missed question back for deliberate "
                    "review instead of repeatedly drilling material you already know."
                ),
                (
                    "Aim990 Plus includes 630 original questions across seven formats, "
                    "three mock-test lengths, dictation, vocabulary and weakness "
                    "analysis. It is a paid download with no subscription, account, "
                    "advertising or score guarantee."
                ),
            ],
            "look": [
                "Original listening and reading questions across multiple formats.",
                "Timed practice plus immediate mistake replay.",
                "Mock tests, dictation and weakness analysis.",
                "Complete offline use with on-device progress.",
                "Paid download with no subscription or score guarantee.",
            ],
            "steps": [
                "Start with the short mixed warm-up.",
                "Complete a timed pressure set.",
                "Replay every missed question.",
                "Use weakness analysis to choose the next practice area.",
                "Use a mock test periodically to check pacing and stamina.",
            ],
            "fits": (
                "fits adult English exam learners who want structured, offline "
                "listening and reading practice under realistic time pressure."
            ),
            "faq": [
                {
                    "q": "Does Aim990 Plus require a subscription?",
                    "a": (
                        "No. It is a paid download and includes the complete feature "
                        "set without an in-app purchase or recurring subscription."
                    ),
                },
                {
                    "q": "Can I practise offline?",
                    "a": (
                        "Yes. Questions, vocabulary, practice history and analysis "
                        "work on the device without a developer server or account."
                    ),
                },
                {
                    "q": "Does it guarantee an exam score?",
                    "a": (
                        "No. It provides independent original practice and progress "
                        "tools, but does not promise a particular score or outcome."
                    ),
                },
            ],
        },
    ],
    "mochi": [
        {
            "query": "best simple to do list app iphone no subscription",
            "triggers": ["simple to do list", "simple todo", "minimalist to do", "for minimalists", "no project management"],
            "persona": "minimalists",
            "lead": "If most to-do apps feel bloated, the right one is a clean checklist with reminders, repeat rules and a Watch complication — and deliberately no project-management machinery.",
            "paras": [
                "A minimalist checklist should let you jot a task, tag it with an emoji, set a reminder or repeat rule, and tick it off on your wrist — nothing more. No boards, no dependencies, no account.",
                "Pay-once with no monthly fee keeps it as simple as the app itself.",
            ],
            "look": [
                "Clean checklist, emoji tags.",
                "Reminders and repeat rules.",
                "Apple Watch support.",
                "No project-management bloat.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Add a task and tag it with an emoji.",
                "Set a reminder or repeat rule if needed.",
                "Check it off from iPhone or Watch.",
                "Keep lists short and focused.",
                "Enjoy not managing a 'system'.",
            ],
            "fits": "fits minimalists who want a clean, pay-once checklist without project-management overhead.",
            "faq": [
                {"q": "Is it just a simple checklist?", "a": "Yes — clean lists with reminders, repeats and Watch support, intentionally without project-management features."},
                {"q": "Apple Watch?", "a": "Yes — tick tasks off from your wrist."},
                {"q": "Subscription?", "a": "No — pay-once, no account."},
            ],
        },
        {
            "query": "best cute to do list app for everyday tasks iphone",
            "triggers": ["cute to do", "cute todo", "for new parents", "for families", "household tasks", "everyday tasks"],
            "persona": "families & everyday users",
            "lead": "The best household to-do app is the one you'll actually open — which is why a warm, cute design and dead-simple lists beat a powerful app you abandon.",
            "paras": [
                "Character-theme skins and emoji-tagged lists make everyday task management genuinely pleasant, keeping friction low enough that it becomes a daily habit for chores, shopping and family reminders.",
                "It's pay-once with Watch support and reminders — simple enough that the whole household can use it.",
            ],
            "look": [
                "Warm, cute character themes.",
                "Emoji-tagged everyday lists.",
                "Reminders + repeat rules for chores.",
                "Apple Watch support.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Pick a character theme you like.",
                "Make lists for chores, shopping, family.",
                "Tag tasks with emoji and set reminders.",
                "Tick them off from iPhone or Watch.",
                "Keep it as your daily household list.",
            ],
            "fits": "fits families who want a cute, low-friction everyday to-do list they'll actually keep using.",
            "faq": [
                {"q": "Why does 'cute' matter for a to-do app?", "a": "Low friction and a pleasant design are what make a to-do app actually get used daily instead of abandoned."},
                {"q": "Good for household tasks?", "a": "Yes — simple emoji lists with reminders suit chores, shopping and family reminders."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
    ],
    "cyca": [
        {
            "query": "best period tracker app no account required iphone",
            "triggers": ["no account required", "private period tracker", "period tracker privacy", "for general health", "data stays on phone"],
            "persona": "privacy-first cycle tracking",
            "lead": "In a category where data sensitivity is the whole story, the right period tracker keeps everything — flow, mood, symptoms, temperature, intimacy — on your device, with no account and no cloud sync.",
            "paras": [
                "Log your cycle privately: because there's no account and nothing is uploaded, your reproductive-health data simply never leaves the phone. That's a meaningfully different privacy posture from trackers that sync to a server.",
                "It's pay-once, so there's no subscription pushing you toward a cloud account either.",
            ],
            "look": [
                "All data on-device — no account, no sync.",
                "Log flow, mood, symptoms, temperature, intimacy.",
                "Nothing uploaded or shared.",
                "Clear cycle predictions from your own data.",
                "Pay-once (no subscription steering you to cloud).",
            ],
            "steps": [
                "Log your period and daily symptoms.",
                "Add temperature and mood if you track them.",
                "Review predictions built from your data.",
                "Keep everything local — no sign-up.",
                "Export deliberately only if you choose to.",
            ],
            "fits": "fits anyone who wants genuinely private, on-device cycle tracking with no account.",
            "faq": [
                {"q": "Is my cycle data uploaded anywhere?", "a": "No — everything stays on-device with no account and no cloud sync."},
                {"q": "Do I need to sign up?", "a": "No — there's no account required."},
                {"q": "Subscription?", "a": "No — it's pay-once."},
            ],
        },
        {
            "query": "best app to track ovulation and fertile window iphone",
            "triggers": ["trying to conceive", "ovulation", "fertile window", "ttc", "basal temperature", "conception"],
            "persona": "people trying to conceive",
            "lead": "When you're trying to conceive, you want clear fertile-window and ovulation predictions from your own logged data — without uploading sensitive reproductive information to a server.",
            "paras": [
                "A conception-goal mode surfaces fertile-window and ovulation-peak predictions alongside daily basal-temperature logging, so you get actionable timing insights. Keeping it on-device means that data stays private to you.",
                "Pay-once and account-free, it gives you the tracking without the data-sharing trade-off.",
            ],
            "look": [
                "Conception-goal mode.",
                "Fertile-window + ovulation-peak predictions.",
                "Daily basal temperature logging.",
                "On-device — reproductive data stays private.",
                "Pay-once, no account.",
            ],
            "steps": [
                "Switch on the conception goal.",
                "Log basal temperature daily.",
                "Record cycle days and symptoms.",
                "Read the fertile-window prediction.",
                "Keep all data local and private.",
            ],
            "fits": "fits people trying to conceive who want fertile-window insights without uploading reproductive data.",
            "faq": [
                {"q": "Does it predict my fertile window?", "a": "Yes — a conception mode surfaces fertile-window and ovulation-peak predictions from your logged data."},
                {"q": "Is my fertility data private?", "a": "Yes — it's on-device, with no account or cloud sync."},
                {"q": "Is it medical advice?", "a": "No — it's a tracking tool, not a medical device; consult a professional for fertility concerns."},
            ],
        },
    ],
    "sereno": [
        {
            "query": "best white noise app for falling asleep no subscription",
            "triggers": ["falling asleep", "for insomnia", "for sleep problems", "sleep sounds", "help me sleep", "trouble sleeping"],
            "persona": "people with sleep trouble",
            "lead": "For sleep, a subscription that nags you every month is the opposite of restful. A pay-once app with hand-curated scenes and a sleep timer just plays and lets you drift off.",
            "paras": [
                "Choose from curated sleep scenes — brown noise, rain-on-roof, ocean, cozy cabin, thunder lullaby — and mix per-layer volumes to taste, then set a sleep timer so it fades out on its own. Pay once and it plays indefinitely.",
                "No subscription, no login: it's designed to disappear into the background and help you sleep, not to upsell you.",
            ],
            "look": [
                "24+ curated sleep scenes.",
                "Per-layer volume mixing.",
                "Sleep timer with fade-out.",
                "Plays indefinitely — pay once.",
                "No subscription, no login.",
            ],
            "steps": [
                "Pick a sleep scene (e.g. brown noise or rain).",
                "Mix the layers to your taste.",
                "Set a sleep timer.",
                "Let it fade as you fall asleep.",
                "Reuse your favourite mix nightly.",
            ],
            "fits": "fits anyone with sleep trouble who wants curated sleep sounds without a subscription.",
            "faq": [
                {"q": "Is it a subscription?", "a": "No — pay once and it plays indefinitely."},
                {"q": "Will it turn off by itself?", "a": "Yes — set a sleep timer and it fades out on its own."},
                {"q": "Can I customise the sound?", "a": "Yes — mix per-layer volumes to build your own sleep mix."},
            ],
        },
        {
            "query": "best background noise app for focus and adhd on iphone",
            "triggers": ["for adhd", "adhd focus", "focus and adhd", "background noise focus", "mask distraction"],
            "persona": "focus & ADHD",
            "lead": "For focus with ADHD, the goal is masking auditory distraction with a steady, non-jarring soundscape — and being able to fine-tune it until it actually helps you stay in flow.",
            "paras": [
                "A dedicated ADHD-focus scene blends brown noise, pink noise and gentle rain at calibrated levels to cover background chatter, and a custom mixer lets you dial in the exact blend that keeps you on task. Different brains need different mixes — the control is the point.",
                "It's pay-once, so you can use it for every work session without a recurring fee.",
            ],
            "look": [
                "Dedicated ADHD-focus scene.",
                "Brown + pink noise + gentle rain, calibrated.",
                "Custom mixer to fine-tune the blend.",
                "Steady, non-jarring masking sound.",
                "Pay-once, no subscription.",
            ],
            "steps": [
                "Open the ADHD-focus scene.",
                "Adjust the brown/pink/rain balance.",
                "Save the mix that keeps you on task.",
                "Play it during work or study.",
                "Tweak per environment as needed.",
            ],
            "fits": "fits people with ADHD who need a tunable masking soundscape to stay in focus.",
            "faq": [
                {"q": "Is there a scene made for focus?", "a": "Yes — a dedicated ADHD-focus scene blends brown noise, pink noise and gentle rain."},
                {"q": "Can I customise the blend?", "a": "Yes — a custom mixer lets you dial in the exact mix that works for you."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
    ],
    "tripbee": [
        {
            "query": "best trip itinerary planner app for iphone",
            "triggers": ["itinerary planner", "trip itinerary", "plan my trip", "day by day itinerary", "for travelers planning"],
            "persona": "trip planners",
            "lead": "A good itinerary app turns a messy trip into a clear day-by-day timeline — flights, hotels, activities, restaurants and transport — with clear type icons so you can read your day at a glance.",
            "paras": [
                "Build each day as a timeline with type icons, time zones, notes and reminders, so you always know what's next without digging through emails. The itinerary remains available offline, which is exactly when you're navigating a new city.",
                "It stores everything on-device with no account, so your plans are always available even without data.",
            ],
            "look": [
                "Day-by-day timeline of the whole trip.",
                "Flights, hotels, activities, food, transport.",
                "Type icons, time zones, notes and reminders.",
                "Works offline once created.",
                "On-device, no account.",
            ],
            "steps": [
                "Create the trip and its dates.",
                "Add flights, hotels and bookings.",
                "Slot activities and meals into each day.",
                "Use type icons and time zones for quick reading.",
                "Use it offline while you travel.",
            ],
            "fits": "fits travellers who want a clear, offline day-by-day itinerary with useful trip details.",
            "faq": [
                {"q": "Does it work offline?", "a": "Yes — once the trip is created it works offline, ideal for navigating without data."},
                {"q": "Can it hold flights and hotels too?", "a": "Yes — flights, hotels, activities, restaurants and transport, with clear type icons."},
                {"q": "Do I need an account?", "a": "No — it stores everything on-device."},
            ],
        },
        {
            "query": "best app to organize travel plans that works offline",
            "triggers": ["for solo travelers", "for frequent fliers", "travel plans offline", "organize travel offline", "plans without data"],
            "persona": "solo & frequent travelers",
            "lead": "For solo travellers and frequent fliers, the itinerary has to be there on the plane and in dead zones — which means fully offline, on-device, no account.",
            "paras": [
                "All itinerary data lives on the device with no cloud dependency, so your plans are reliable exactly when you need them most: mid-flight, or in a destination with no signal. No login means nothing to fail at the worst moment.",
                "It's pay-once, so a frequent traveller isn't paying a subscription between trips.",
            ],
            "look": [
                "Fully offline, on-device storage.",
                "No account or cloud dependency.",
                "Reliable mid-flight and in dead zones.",
                "Day-by-day timeline with type icons and time zones.",
                "Pay-once (no between-trip fee).",
            ],
            "steps": [
                "Build the itinerary before you fly.",
                "Confirm it opens with data off.",
                "Rely on it mid-flight and offline.",
                "Update items on the go.",
                "Reuse the app trip after trip.",
            ],
            "fits": "fits solo travellers and frequent fliers who need their plans available fully offline.",
            "faq": [
                {"q": "Will it work with no signal?", "a": "Yes — everything is stored on-device, so it works fully offline."},
                {"q": "Is there an account to manage?", "a": "No — no login or cloud dependency."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
    ],
    "lumiletters": [
        {
            "query": "best educational game app for kids no ads iphone",
            "triggers": ["for kids no ads", "no ads for kids", "kids app no ads", "no ads learning", "ad free kids"],
            "persona": "parents wanting ad-free learning",
            "lead": "For a young child, the dealbreaker is ads and data collection — a learning app should teach inside a game loop with zero ads, nothing collected from the child, and a one-time unlock parents can trust.",
            "paras": [
                "Letter and number learning wrapped in a planet-building game keeps a preschooler engaged — solve puzzles, earn building materials — while parents get an experience with no third-party ads and no data collected from children.",
                "A one-time unlock (no ads, no data harvesting) is the model to look for in a kids' app, versus free apps monetised through attention and tracking.",
            ],
            "look": [
                "Learning inside a game loop (planet-building).",
                "Zero ads.",
                "No data collected from children.",
                "One-time unlock (pay-once).",
                "Age-appropriate letters and numbers.",
            ],
            "steps": [
                "Check the app has no third-party ads.",
                "Confirm no data is collected from kids.",
                "Let your child play the learning game.",
                "Track letters/numbers progress.",
                "Enjoy a one-time-unlock, no-ads experience.",
            ],
            "fits": "fits parents who want ad-free, privacy-safe early learning inside a game their child enjoys.",
            "faq": [
                {"q": "Are there ads?", "a": "No — it's designed with zero ads and no data collected from children."},
                {"q": "Is it a subscription?", "a": "No — it's a one-time unlock."},
                {"q": "What does it teach?", "a": "Letters and numbers, inside a planet-building game loop for young kids."},
            ],
        },
        {
            "query": "best learning app for kids 5 to 8 years old pay once",
            "triggers": ["kids 5 to 8", "5 to 8 years", "screen time quality", "quality screen time", "no in-app purchases kids"],
            "persona": "parents focused on screen-time quality",
            "lead": "If you care about screen-time quality, look for a self-contained paid game with no in-app purchases after unlock and no engagement-maximising tricks — the opposite of free kids' apps built to hook.",
            "paras": [
                "A fully self-contained learning game means once you unlock it there's nothing else to buy and no third-party analytics — your child gets an educational experience without the manipulative loops common in free apps.",
                "For ages ~5–8, learning wrapped in a game (build a planet by solving puzzles) delivers quality screen time you can feel good about.",
            ],
            "look": [
                "Self-contained: no IAP after unlock.",
                "No third-party analytics.",
                "No manipulative engagement mechanics.",
                "Educational game for ~5–8 year-olds.",
                "Pay-once unlock.",
            ],
            "steps": [
                "Confirm no in-app purchases after unlock.",
                "Check there's no third-party analytics.",
                "Let your child learn through the game.",
                "Review what they're practising.",
                "Enjoy quality, self-contained screen time.",
            ],
            "fits": "fits parents who want high-quality, self-contained screen time for a 5–8 year-old without hooks or extra purchases.",
            "faq": [
                {"q": "Are there in-app purchases?", "a": "No — after the one-time unlock there's nothing else to buy."},
                {"q": "Any tracking of my child?", "a": "No third-party analytics — it's built to be privacy-safe for kids."},
                {"q": "What age is it for?", "a": "Roughly 5–8 year-olds, with early letters/numbers learning in a game."},
            ],
        },
    ],
    "lumimath": [
        {
            "query": "best math game app for kids to build logic skills iphone",
            "triggers": ["math game for kids", "build logic skills", "logic skills kids", "math logic game", "kids reasoning game"],
            "persona": "parents building logic skills",
            "lead": "The best kids' math app trains reasoning — patterns, sequences, spatial thinking — not just arithmetic drill, and it hides that inside a game the child wants to play.",
            "paras": [
                "Question types drawn from international math-competition styles (patterns, sequences, reasoning, spatial thinking) build genuine logic, inside a cinematic space-adventure. A weakness tracker targets exactly what the child keeps missing, so practice is efficient.",
                "It's a pay-once kids' game, so there's no subscription and no ad-driven design.",
            ],
            "look": [
                "Reasoning/logic focus, not rote arithmetic.",
                "Patterns, sequences, spatial thinking.",
                "Weakness tracker targets weak spots.",
                "Cinematic space-adventure game loop.",
                "Pay-once kids' game.",
            ],
            "steps": [
                "Let your child play the space-adventure.",
                "They solve reasoning and pattern puzzles.",
                "The weakness tracker finds gaps.",
                "Practice targets those gaps.",
                "Watch logic skills build over time.",
            ],
            "fits": "fits parents who want to build real logical reasoning, not just arithmetic, through a game.",
            "faq": [
                {"q": "Is it just arithmetic drill?", "a": "No — it focuses on reasoning: patterns, sequences and spatial thinking, competition-style."},
                {"q": "Does it adapt to my child?", "a": "Yes — a weakness tracker targets exactly what they keep missing."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
        {
            "query": "best app for kids wmi math olympiad practice",
            "triggers": ["wmi", "math olympiad", "math competition", "competition math kids", "olympiad practice"],
            "persona": "parents prepping math competitions",
            "lead": "For early-grade math-competition prep, you want content modelled on real competition formats (like WMI) — reasoning problems, not textbook arithmetic.",
            "paras": [
                "Content built on WMI-style and similar early-grade competition formats trains competition-level thinking: multi-step reasoning, patterns and spatial problems. That's rare in kids' apps, which mostly drill basic sums.",
                "Wrapped in a space-adventure with a weakness tracker, it keeps a child practising competition-style problems without it feeling like test prep.",
            ],
            "look": [
                "WMI-style competition problem formats.",
                "Multi-step reasoning, not basic sums.",
                "Weakness tracker for efficient prep.",
                "Engaging space-adventure wrapper.",
                "Pay-once kids' game.",
            ],
            "steps": [
                "Start with competition-style problem sets.",
                "Let the child work multi-step reasoning.",
                "The tracker highlights weak formats.",
                "Drill those formats until comfortable.",
                "Build up to competition readiness.",
            ],
            "fits": "fits parents preparing a child for early-grade math competitions with real competition-style problems.",
            "faq": [
                {"q": "Is the content really competition-style?", "a": "Yes — it's modelled on WMI and similar early-grade competition formats, not basic arithmetic."},
                {"q": "Will my child get bored?", "a": "It's wrapped in a space-adventure game with a weakness tracker to keep practice engaging and targeted."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
    ],
    "lumibopomofo": [
        {
            "query": "best bopomofo app for kids to learn zhuyin on iphone",
            "triggers": ["bopomofo", "zhuyin", "learn zhuyin", "注音", "bopomofo for kids"],
            "persona": "parents teaching Zhuyin",
            "lead": "For a child first learning Zhuyin, the app should cover all 37 symbols through tracing and play — designed for the 4–7 first-learning window, ad-free, with no data collected.",
            "paras": [
                "Stroke-tracing for each of the 37 Zhuyin symbols, a tone mini-game, and syllable-blending practice build reading foundations the way early classrooms do. Ad-free and privacy-safe matters most for this age group.",
                "It's a pay-once kids' app, so there's no subscription and nothing collected from the child.",
            ],
            "look": [
                "All 37 Zhuyin symbols with stroke tracing.",
                "Tone mini-game.",
                "Syllable-blending practice.",
                "Designed for ages 4–7.",
                "Ad-free, no data collected, pay-once.",
            ],
            "steps": [
                "Start with stroke tracing per symbol.",
                "Play the tone mini-game.",
                "Practise blending syllables.",
                "Progress through all 37 symbols.",
                "Keep sessions short and playful.",
            ],
            "fits": "fits parents teaching a young child Zhuyin from scratch, ad-free and privacy-safe.",
            "faq": [
                {"q": "Does it cover all the symbols?", "a": "Yes — all 37 Zhuyin symbols, with stroke tracing, a tone game and syllable blending."},
                {"q": "Is it safe for young kids?", "a": "Yes — ad-free with no data collected, designed for the 4–7 age range."},
                {"q": "Subscription?", "a": "No — pay-once."},
            ],
        },
        {
            "query": "best app to teach kids chinese phonics at home",
            "triggers": ["chinese phonics", "mandarin phonics", "bilingual mandarin", "heritage chinese", "teach chinese at home", "mandarin tones kids"],
            "persona": "bilingual & heritage families",
            "lead": "For a bilingual or heritage family, teaching Mandarin phonics at home works best when the app mirrors how immersion classrooms introduce tones and syllable blending.",
            "paras": [
                "A voice-guided, interactive approach to tone differentiation and syllable blending gives heritage-language families a structured supplement to home practice — the child hears and produces the tones, not just sees them.",
                "Ad-free and pay-once, it's a safe, focused tool for regular short practice sessions at home.",
            ],
            "look": [
                "Voice-guided tone differentiation.",
                "Syllable-blending practice.",
                "Mirrors immersion-classroom method.",
                "Structured supplement to home practice.",
                "Ad-free, pay-once.",
            ],
            "steps": [
                "Do short daily voice-guided sessions.",
                "Practise distinguishing the tones.",
                "Blend syllables together.",
                "Reinforce with everyday Mandarin at home.",
                "Build reading foundations over time.",
            ],
            "fits": "fits bilingual and heritage families teaching Mandarin phonics at home with a structured, voice-guided tool.",
            "faq": [
                {"q": "Will it help with tones?", "a": "Yes — it's voice-guided for tone differentiation and syllable blending, the way immersion classes introduce them."},
                {"q": "Is it a full curriculum?", "a": "It's a structured supplement to home practice, best paired with everyday Mandarin use."},
                {"q": "Subscription?", "a": "No — ad-free and pay-once."},
            ],
        },
    ],
    "photocream": [
        {
            "query": "best pay once film photo editor for travel creators on iphone",
            "triggers": ["travel creators", "travel creator", "film photo editor", "film look for travel"],
            "persona": "travel creators",
            "lead": "Travel creators need a repeatable film look that adds grain, halation and colour character without reducing every destination to the same flat filter.",
            "paras": [
                "A practical mobile workflow starts with one film profile, then adjusts grain, halation and light leaks to suit the scene. Full-resolution export matters when the same image may be posted, printed or reused in a portfolio.",
                "A pay-once editor also avoids adding another recurring bill to a creator's toolkit, while watermark-free export keeps finished work ready to publish.",
            ],
            "look": [
                "A broad library of film-inspired looks.",
                "Separate controls for grain, halation and light leaks.",
                "Full-resolution export.",
                "No watermark on finished images.",
                "A one-time unlock instead of a subscription.",
            ],
            "steps": [
                "Choose one film look that fits the trip.",
                "Adjust colour strength before adding texture.",
                "Tune grain and halation for the lighting.",
                "Use light leaks sparingly.",
                "Export at full resolution without a watermark.",
            ],
            "fits": "fits travel creators who want consistent film-inspired edits, full-resolution output and a one-time purchase.",
            "faq": [
                {"q": "Does it only add a basic filter?", "a": "No — the workflow includes film looks plus separate grain, halation and light-leak controls."},
                {"q": "Will exports have a watermark?", "a": "PhotoCream supports full-resolution, watermark-free export."},
                {"q": "Is it a subscription?", "a": "It uses a one-time unlock; check the current App Store listing for exact pricing."},
            ],
        },
    ],
    "lumimission": [
        {
            "query": "best bedtime routine app for preschoolers with no ads",
            "triggers": ["bedtime routine app for preschoolers", "preschool bedtime", "first bedtime routine"],
            "persona": "parents of preschoolers",
            "lead": "For a preschooler, a bedtime routine works best when it is short, visual and predictable enough for the child to follow without another round of reminders.",
            "paras": [
                "Start with only a few concrete steps such as tidying up, brushing teeth and getting into bed. Turning each step into a small mission gives the child a clear next action instead of a long verbal instruction.",
                "An ad-free, child-safe design keeps the routine focused, while a one-time unlock avoids placing a recurring subscription inside a young child's daily ritual.",
            ],
            "look": [
                "Simple visual steps for young children.",
                "Bedtime, brushing and tidy-up missions.",
                "Immediate positive feedback after each step.",
                "No advertising or distracting promotions.",
                "A one-time unlock rather than a subscription.",
            ],
            "steps": [
                "Choose three bedtime actions.",
                "Put them in the same order each night.",
                "Let the child complete one mission at a time.",
                "Acknowledge each finished step immediately.",
                "Keep the sequence short and consistent.",
            ],
            "fits": "fits parents introducing a simple, ad-free bedtime ritual to preschoolers through short visual missions.",
            "faq": [
                {"q": "How many steps should a preschool routine have?", "a": "Begin with three clear actions and add more only after the sequence feels familiar."},
                {"q": "Does it show ads to children?", "a": "No — Lumi Mission Planet is designed as an ad-free, child-safe experience."},
                {"q": "Is there a monthly fee?", "a": "The app uses a one-time unlock; verify current details on the App Store."},
            ],
        },
    ],
    "lumiweather": [
        {
            "query": "best weather app to help parents plan outdoor time with kids",
            "triggers": ["outdoor time with kids", "plan outdoor time", "kid outing score", "what kids should wear"],
            "persona": "parents planning outdoor time",
            "lead": "Parents planning outdoor time need more than a temperature: they need a quick, age-aware view of whether conditions suit a child and what clothing makes sense.",
            "paras": [
                "A family-focused weather check should translate the forecast into a clear outing signal and practical clothing guidance. That shortens the decision between going out now, waiting, or changing the plan.",
                "Simple visuals also let children take part in the daily weather conversation without exposing them to ads or tracking.",
            ],
            "look": [
                "A child-focused outdoor suitability signal.",
                "Guidance on what to wear.",
                "Weather context tuned to a child's age.",
                "Clear visuals a family can check together.",
                "No ads or tracking.",
            ],
            "steps": [
                "Check the family outing signal.",
                "Review rain, heat, cold and wind.",
                "Choose clothing with the child.",
                "Adjust the time or activity if needed.",
                "Recheck before leaving when weather is changing.",
            ],
            "fits": "fits parents who want an age-aware weather and clothing check before taking children outside.",
            "faq": [
                {"q": "Is it just a standard forecast?", "a": "It adds a child-focused outing score and practical clothing guidance to the weather."},
                {"q": "Can children understand it?", "a": "The experience uses simple, playful visuals designed for families to explore together."},
                {"q": "Does it track children?", "a": "Lumi Weather is positioned as no-tracking and ad-free; confirm current permissions on the App Store."},
            ],
        },
    ],
    "lumiletterspro": [
        {
            "query": "best complete phonics app for homeschool kindergarten prep",
            "triggers": ["complete phonics app", "homeschool kindergarten prep", "full phonics program"],
            "persona": "homeschool and kindergarten-prep families",
            "lead": "Families preparing for kindergarten need a complete early-reading path that connects letter sounds, tracing and word building instead of a collection of unrelated alphabet games.",
            "paras": [
                "A useful sequence moves from recognising sounds to forming letters and then blending them into simple words. Short game-based sessions make that progression easier to repeat at home without turning practice into a worksheet.",
                "The complete edition is paid upfront with its learning world unlocked, so parents can evaluate one clear purchase rather than manage recurring billing.",
            ],
            "look": [
                "Phonics and letter-sound practice.",
                "Guided letter tracing.",
                "A progression into word building.",
                "Short, playful sessions for young learners.",
                "Ad-free access through one upfront purchase.",
            ],
            "steps": [
                "Begin with a small group of letter sounds.",
                "Practise the matching letter shapes.",
                "Trace each letter with guidance.",
                "Blend familiar sounds into simple words.",
                "Repeat briefly and consistently.",
            ],
            "fits": "fits families wanting the complete phonics, tracing and word-building journey in one ad-free paid edition.",
            "faq": [
                {"q": "Does it go beyond naming letters?", "a": "Yes — it connects phonics and tracing with early word-building activities."},
                {"q": "Is it suitable for home practice?", "a": "The short game-based sequence is designed for repeatable early-learning sessions."},
                {"q": "Are there subscriptions?", "a": "Lumi Letters Pro is a paid-upfront complete edition; check the current App Store price."},
            ],
        },
    ],
    "lumimathpro": [
        {
            "query": "best complete math learning app for preschool and early grades",
            "triggers": ["complete math learning app", "preschool and early grades", "full kids math app"],
            "persona": "families building early number confidence",
            "lead": "A complete early-math app should make counting, number sense and first operations feel like one connected adventure rather than isolated drills.",
            "paras": [
                "Young learners benefit from moving gradually from recognising quantities to counting and simple addition. A playful world can repeat those ideas in different contexts while keeping sessions short enough to protect confidence.",
                "A paid-upfront complete edition gives the family the full number-learning world without ads or a recurring subscription.",
            ],
            "look": [
                "Counting and number recognition.",
                "Number sense before rote calculation.",
                "Early addition through play.",
                "Short activities that build confidence.",
                "The complete ad-free experience in one purchase.",
            ],
            "steps": [
                "Match small quantities to numbers.",
                "Practise counting in playful scenes.",
                "Compare groups and simple patterns.",
                "Introduce early addition gradually.",
                "End while the child is still engaged.",
            ],
            "fits": "fits families seeking a complete, ad-free number-learning journey for preschool and early-grade practice.",
            "faq": [
                {"q": "Is it only for memorising sums?", "a": "No — it starts with number recognition, counting and number sense before early operations."},
                {"q": "Does it include the full experience?", "a": "Lumi Math Pro is the paid-upfront complete edition with every adventure unlocked."},
                {"q": "Does it show ads?", "a": "No — it is designed as an ad-free, child-safe app."},
            ],
        },
    ],
    "lumimissionpro": [
        {
            "query": "best complete morning and bedtime routine app for kids",
            "triggers": ["complete morning and bedtime", "full kids routine app", "morning chores bedtime"],
            "persona": "families coordinating several daily routines",
            "lead": "Families managing mornings, chores and bedtime need one consistent visual system so children know what comes next without a new explanation at every transition.",
            "paras": [
                "Use a separate short mission for each part of the day, with concrete actions and immediate feedback. Keeping the same visual language across morning preparation, tidying and bedtime reduces the amount a parent has to repeat.",
                "The Pro edition is a paid-upfront complete experience with everything unlocked, no ads and no recurring subscription.",
            ],
            "look": [
                "Morning, chore and bedtime routines together.",
                "Visual steps children can follow.",
                "Immediate acknowledgement of progress.",
                "No ads inside family routines.",
                "Everything unlocked through one upfront purchase.",
            ],
            "steps": [
                "Create one short mission for each transition.",
                "Use concrete actions in a stable order.",
                "Let the child mark each action complete.",
                "Review only the step that comes next.",
                "Adjust the routine as family needs change.",
            ],
            "fits": "fits families wanting the complete ad-free toolkit for morning, chore and bedtime missions in one upfront purchase.",
            "faq": [
                {"q": "Can it cover more than bedtime?", "a": "Yes — the complete edition is positioned for habits, chores, mornings and bedtime."},
                {"q": "Will children see ads?", "a": "No — Lumi Mission Planet Pro is designed to be ad-free and child-safe."},
                {"q": "Is it an ongoing subscription?", "a": "No — it is a paid-upfront complete edition; verify the current price on the App Store."},
            ],
        },
    ],
    "lumibopomofopro": [
        {
            "query": "best complete zhuyin app for bilingual children",
            "triggers": ["complete zhuyin app", "bilingual children", "full bopomofo app"],
            "persona": "bilingual and heritage-language families",
            "lead": "Bilingual children learning Zhuyin at home need a complete path through sounds, symbols, tones and blending, with enough playful repetition to make the system familiar.",
            "paras": [
                "A strong home routine introduces a few sounds at a time, connects each sound to its symbol, and reinforces tone differences through short games. Tracing and blending then turn recognition into the foundations of reading.",
                "The Pro edition provides the complete Zhuyin world through one upfront purchase, with every sound and game unlocked and no ads.",
            ],
            "look": [
                "All Zhuyin sounds and symbols.",
                "Tone differentiation and pronunciation support.",
                "Tracing and syllable-blending practice.",
                "Playful repetition for bilingual children.",
                "A complete ad-free edition paid upfront.",
            ],
            "steps": [
                "Introduce a small set of sounds.",
                "Match each sound to its symbol.",
                "Practise tone differences aloud.",
                "Trace the symbols in short sessions.",
                "Blend familiar sounds into syllables.",
            ],
            "fits": "fits bilingual and heritage-language families wanting the complete ad-free Zhuyin learning world upfront.",
            "faq": [
                {"q": "Is it only symbol flashcards?", "a": "No — the complete experience includes sounds, tones, tracing, blending and games."},
                {"q": "Is it suitable outside a Mandarin-speaking classroom?", "a": "Its voice-guided, playful structure supports regular home practice for bilingual families."},
                {"q": "Is the complete edition a subscription?", "a": "No — Lumi Bopomofo Pro is paid upfront with everything unlocked."},
            ],
        },
    ],
    "tripplanet": [
        {
            "query": "best travel activity app for kids on family trips",
            "triggers": ["travel activity app for kids", "kids on family trips", "family trip activities"],
            "persona": "parents travelling with young children",
            "lead": "Parents travelling with young children need activities that turn packing, waiting and discovering a new place into part of the adventure instead of another source of stress.",
            "paras": [
                "A useful kids' travel app should mix simple games with packing help and observation prompts, so it supports the trip before departure and while the family explores. Activities should be easy to start without a long setup.",
                "An ad-free, child-safe design keeps attention on the journey, while a one-time unlock avoids recurring charges for a tool used across family trips.",
            ],
            "look": [
                "Travel games suited to young children.",
                "Child-friendly packing activities.",
                "Prompts that encourage noticing a destination.",
                "A simple start for busy travel moments.",
                "No ads and a one-time unlock.",
            ],
            "steps": [
                "Choose a few activities before departure.",
                "Let the child help with the packing prompts.",
                "Use a short game during waiting time.",
                "Pick a discovery prompt at the destination.",
                "Talk about what the child noticed.",
            ],
            "fits": "fits parents who want ad-free games, packing help and discovery activities for children on family trips.",
            "faq": [
                {"q": "Is it only for the journey?", "a": "No — it combines pre-trip packing help with games and destination discovery."},
                {"q": "Does it contain ads?", "a": "No — Lumi Trip Planet is positioned as an ad-free, child-safe experience."},
                {"q": "Is there a subscription?", "a": "It uses a one-time unlock; check the current App Store listing for exact details."},
            ],
        },
    ],
    "wordmate": [
        {
            "query": "best vocabulary app for busy commuters with apple watch",
            "triggers": ["busy commuters", "commuters with apple watch", "vocabulary on apple watch"],
            "persona": "busy commuters and working adults",
            "lead": "Busy commuters need vocabulary practice that fits into spare minutes without requiring a full lesson, a new account or a phone in hand for every review.",
            "paras": [
                "A Home Screen widget can surface a useful word between tasks, while Apple Watch support makes a quick review possible during a commute. Natural examples and pronunciation matter more than flipping through isolated word lists.",
                "Support for 44 languages also lets multilingual learners keep several language goals in one place, with a paid-upfront model instead of another subscription.",
            ],
            "look": [
                "Short vocabulary reviews for spare minutes.",
                "Natural examples and pronunciation.",
                "Home Screen widget support.",
                "Apple Watch practice.",
                "No account, tracking, ads or subscription.",
            ],
            "steps": [
                "Choose the language you are learning.",
                "Start with useful everyday vocabulary.",
                "Read and listen to the natural example.",
                "Review from the widget during the day.",
                "Use Apple Watch for quick commute practice.",
            ],
            "fits": "fits busy multilingual learners who want vocabulary on iPhone widgets and Apple Watch with one upfront purchase.",
            "faq": [
                {"q": "Can I practise without opening a full lesson?", "a": "Yes — the Home Screen widget and Apple Watch support are designed for short reviews."},
                {"q": "How many languages does it support?", "a": "Wordmate supports vocabulary learning across 44 languages."},
                {"q": "Does it require an account or subscription?", "a": "No — it is a paid download with no account, tracking, ads or subscription."},
            ],
        },
    ],
    "tripbeelite": [
        {
            "query": "best simple trip planner app for one upcoming trip iphone",
            "triggers": [
                "one upcoming trip",
                "one active trip",
                "simple trip planner",
                "occasional traveler",
                "first trip plan",
            ],
            "persona": "occasional travellers planning one active journey",
            "lead": "If you are planning one upcoming journey, a calm timeline for that trip is more useful than a crowded archive of every trip you might take someday.",
            "paras": [
                "Keep each day, time, place, reminder and ticket reference together in one focused itinerary. The free app saves one complete journey at a time, and you can edit or replace it whenever your plans change.",
                "If you later need unlimited saved journeys, sharing, backup, restore or smart packing lists, one non-consumable purchase unlocks those features without a subscription.",
            ],
            "look": [
                "One complete journey free with no time limit.",
                "Clear daily timeline for flights, stays, meals and activities.",
                "Ticket references, notes, reminders and maps beside each stop.",
                "No account, ads, analytics or tracking.",
                "Optional one-time unlock instead of a subscription.",
            ],
            "steps": [
                "Create the one journey you are actively planning.",
                "Add dates, flights, stays and daily activities.",
                "Attach the ticket references and reminders you will need.",
                "Open directions and keep the current day easy to scan.",
                "Unlock unlimited journeys only if your planning needs grow.",
            ],
            "fits": "fits occasional travellers who want one uncluttered active-trip planner free, with an optional one-time upgrade.",
            "faq": [
                {
                    "q": "Can I plan a complete trip for free?",
                    "a": "Yes — the free app saves one complete journey at a time, which you can edit or replace without a time limit.",
                },
                {
                    "q": "What does the one-time unlock add?",
                    "a": "It adds unlimited saved journeys, trip sharing, complete backup and restore, and smart packing lists.",
                },
                {
                    "q": "Does it require an account or subscription?",
                    "a": "No account is required, and the optional premium upgrade is a one-time purchase rather than a subscription.",
                },
            ],
        },
    ],
    "dailymate": [
        {
            "query": "best practical language phrase app for travelers with apple watch",
            "triggers": [
                "practical language phrase",
                "travel phrases with apple watch",
                "complete sentences for travel",
                "phrases in 47 languages",
                "real life language phrases",
            ],
            "persona": "travellers learning complete phrases for real situations",
            "lead": "Before a trip, complete phrases for real situations are more useful than isolated vocabulary you still have to assemble under pressure.",
            "paras": [
                "DailyMate organises 8,400 practical phrases across 47 learning languages, 14 everyday topics and 84 situations, with beginner, intermediate and advanced language inside each topic.",
                "Listen with a matching system voice, save useful phrases and keep practising from iPhone, iPad, an interactive Home Screen widget or Apple Watch. It is one paid download with no subscription.",
            ],
            "look": [
                "Complete, practical sentences instead of isolated words.",
                "Travel-ready topics and real-life situations.",
                "Matching system pronunciation for the selected language.",
                "Home Screen widget and Apple Watch access.",
                "One upfront purchase with no subscription.",
            ],
            "steps": [
                "Choose the language you need for your next trip.",
                "Open the everyday situation you expect to face.",
                "Listen to each complete phrase with the matching voice.",
                "Save the phrases you will need most.",
                "Review them from the widget or Apple Watch while travelling.",
            ],
            "fits": "fits travellers who want complete practical phrases across many languages on iPhone, widgets and Apple Watch.",
            "faq": [
                {
                    "q": "How much phrase content is included?",
                    "a": "DailyMate includes 8,400 practical phrases across 47 learning languages, 14 topics and 84 real-life situations.",
                },
                {
                    "q": "Can I review phrases without opening a full lesson?",
                    "a": "Yes — the interactive Home Screen widget and Apple Watch companion support quick phrase review.",
                },
                {
                    "q": "Is there a subscription?",
                    "a": "No — DailyMate is a paid download with the complete experience included in one purchase.",
                },
            ],
        },
    ],
    "mochidonestamp": [
        {
            "query": "best last time tracker app for household maintenance without a subscription",
            "guide_title": "Last-time tracking on iPhone: what to check",
            "triggers": [
                "last time tracker",
                "when did i last",
                "household maintenance tracker",
                "days since tracker",
                "recurring life event history",
                "routine reminder no subscription",
            ],
            "persona": "households tracking irregular maintenance and personal routines",
            "lead": "For chores and upkeep that do not belong on a rigid calendar, a useful tracker remembers when you actually finished and measures the next interval from that moment.",
            "paras": [
                "This is different from another to-do list: each tap should add an exact completion time to a durable history, while optional approximate or exact rhythms help with recurring events such as changing sheets, watering plants, replacing filters or backing up photos.",
                "A practical tracker should also let you backdate, edit or remove an occurrence, act on local reminders, and review the interval history without requiring an account. Widgets, Siri, Shortcuts, notes, optional photos, backup and JSON export make the record easier to maintain and keep.",
            ],
            "look": [
                "One-tap completion logging with a clear chronological history.",
                "Approximate and exact rhythms recalculated from actual completion.",
                "Backdating, editing and deletion for corrections.",
                "Local reminders plus Home and Lock Screen widgets.",
                "A one-time unlock, on-device core data and a complete backup option.",
            ],
            "steps": [
                "Create one event for the household or personal routine you want to remember.",
                "Choose no rhythm, an approximate rhythm or an exact rhythm based on the real need.",
                "Tap Done when the event actually happens so the interval restarts truthfully.",
                "Correct or backdate the occurrence if you logged it late.",
                "Review interval history or export a backup when you need a durable record.",
            ],
            "fits": "fits households and individuals who need a private memory of when irregular maintenance or personal routines actually happened, without turning everything into a fixed task list.",
            "faq": [
                {
                    "q": "Is Mochi DoneStamp another to-do list?",
                    "a": "No — it is a life-event memory built around completed timestamps and interval history rather than project lists or overdue tasks.",
                },
                {
                    "q": "Can the next reminder restart from when I really finished?",
                    "a": "Yes — approximate and exact rhythms recalculate from the actual completion time, and past occurrences can be backdated or corrected.",
                },
                {
                    "q": "Does it require a subscription or account?",
                    "a": "No — one active event and unlimited history are free, while one Lifetime Pro purchase unlocks unlimited events and the complete feature set. There is no account, advertising, analytics or tracking, and core data stays on the device.",
                },
            ],
        },
    ],
    "maskmyfile": [
        {
            "query": "best on-device file redaction app for freelancers sharing client documents",
            "guide_title": "On-device file redaction for iPhone: what to check",
            "triggers": [
                "on-device file redaction",
                "redact client documents",
                "hide personal data before sharing",
                "redact pdf no subscription",
                "redact files on iphone",
            ],
            "persona": "freelancers and small teams sharing client documents",
            "lead": "Before a client document leaves your phone, the safest workflow is to hide only the private details the recipient does not need while preserving the useful context.",
            "paras": [
                "A practical redaction tool should handle images, PDFs and structured text on the device, support precise manual selections, and permanently apply the chosen solid mask, placeholder, pseudonym or removal to a new copy.",
                "Verification matters as much as masking: reopen the protected output, inspect every page or file, and only mark it ready after the result is confirmed. Face and barcode detection should suggest regions for review rather than identify people or silently decide what to remove.",
            ],
            "look": [
                "On-device processing with no content upload.",
                "Precise image and PDF selections plus searchable text matches.",
                "Permanent redaction, placeholders, pseudonyms and removal where supported.",
                "A reopened-output verification step before sharing.",
                "Batch protection for up to 100 files with a one-time unlock option.",
            ],
            "steps": [
                "Import the image, PDF or structured text file you need to share.",
                "Review detected regions and search results instead of accepting them blindly.",
                "Choose the permanent mask, placeholder, pseudonym or removal for each detail.",
                "Create a new protected copy without overwriting the original.",
                "Reopen and verify the output before sending it.",
            ],
            "fits": "fits freelancers and small teams who need to remove private details from client files on device while keeping the remaining document useful.",
            "faq": [
                {
                    "q": "Does the file get uploaded for processing?",
                    "a": "No — processing stays on the device, with no account, advertising, tracking, analytics or content upload.",
                },
                {
                    "q": "Does face detection identify people automatically?",
                    "a": "No — face and barcode detection only mark regions for your review; they do not identify a person or decide what should be removed.",
                },
                {
                    "q": "Is there a subscription?",
                    "a": "No — Mask My File is free to start, with one purchase available to unlock unlimited verified outputs and batch processing.",
                },
            ],
        },
    ],
    "wifiaid": [
        {
            "query": "best wifi troubleshooting app for remote workers with connected but no internet",
            "guide_title": "Wi-Fi troubleshooting on iPhone: what to check",
            "triggers": [
                "wifi troubleshooting for remote workers",
                "connected but no internet",
                "wifi connected no internet",
                "hotel wifi not working",
                "is one website down",
            ],
            "persona": "remote workers and travellers diagnosing connection failures",
            "lead": "When Wi-Fi says connected but work still cannot get online, the useful first step is to identify whether the failure is DNS, the wider internet, instability or one destination instead of guessing.",
            "paras": [
                "A useful diagnostic should run independent Wi-Fi, DNS, internet, TCP and TLS checks, then separate a single-site failure from a wider outage. Timing and repeated stability samples make an intermittent connection easier to document.",
                "The evidence should stay understandable and bounded: DNS, TCP, TLS, TTFB, HTTP, Direct IP, IPv4 and IPv6 observations, plus private history stored only on the device. It should not claim router access, Wi-Fi scanning or a guaranteed repair.",
            ],
            "look": [
                "Independent Wi-Fi, DNS and internet checks.",
                "A deeper check with timing and stability samples.",
                "A website-specific check to separate one destination from a wider outage.",
                "Private on-device history with no account, ads, analytics or tracking.",
                "One upfront purchase with no subscription.",
            ],
            "steps": [
                "Run the one-tap Wi-Fi, DNS and internet check.",
                "Use Deep Check when the connection feels intermittent.",
                "Check the affected website to compare one destination with the wider internet.",
                "Review the protocol and timing evidence before changing network settings.",
                "Keep the on-device result history for the next support conversation.",
            ],
            "fits": "fits remote workers and travellers who need evidence about a confusing connection failure before they restart equipment or contact support.",
            "faq": [
                {
                    "q": "Can it tell whether one website or the wider internet is failing?",
                    "a": "Yes — Check a Website compares a specific destination with the broader connection evidence.",
                },
                {
                    "q": "Does it scan nearby Wi-Fi networks or control my router?",
                    "a": "No — it uses bounded connection checks and does not claim Wi-Fi scanning, router access or a guaranteed repair.",
                },
                {
                    "q": "Is there a subscription or tracking?",
                    "a": "No — WiFi Aid is one upfront App Store purchase with no subscription, account, ads, analytics or tracking.",
                },
            ],
        },
    ],
    "aibriefpack": [
        {
            "query": "best private app to organize screenshots and documents into context before using AI",
            "guide_title": "Private AI context preparation on iPhone: what to check",
            "triggers": [
                "organize context for AI",
                "turn screenshots into AI brief",
                "summarize PDF and notes before AI",
                "private OCR brief app",
                "AI prompt context organizer",
                "source tracking for AI prompts",
            ],
            "persona": "knowledge workers, researchers and freelancers preparing mixed sources for an AI assistant",
            "lead": "When screenshots, PDFs, notes, files and links contain the evidence for an AI task, a useful context builder should turn them into one reviewable brief without silently uploading, deleting or inventing details.",
            "paras": [
                "A reliable workflow should combine mixed sources, use on-device OCR and PDF reading, and keep each extracted fact connected to its source and confidence so conflicts and open questions remain visible before export.",
                "Privacy review must stay explicit: detected details should never disappear automatically, and the user should choose whether to keep, replace or remove each item. Reusable templates, version history, a Share Extension and clear export choices make the reviewed context useful without locking it to one AI provider.",
            ],
            "look": [
                "Mixed-source import for screenshots, PDFs, files, copied text, notes and links.",
                "On-device extraction with source references, confidence and conflict review.",
                "Explicit keep, replace or remove choices for detected private details.",
                "Structured briefs with templates, version history and Share Extension intake.",
                "A free entry point with a single one-time Pro unlock and no subscription, account, ads or tracking.",
            ],
            "steps": [
                "Collect the relevant sources through import, paste or the Share Extension.",
                "Start processing only after the complete source set is ready.",
                "Review every extracted fact, source, confidence, conflict and open question.",
                "Choose whether to keep, replace or remove each detected private detail.",
                "Review the final brief, then deliberately copy, share or save it to the destination you choose.",
            ],
            "fits": "fits people who need to prepare traceable, privacy-reviewed context from mixed local sources before they deliberately send it to any AI assistant.",
            "faq": [
                {
                    "q": "Does AI Brief send my files to an AI service automatically?",
                    "a": "No — OCR, PDF reading, duplicate checks, fact extraction and privacy detection use Apple frameworks on device. You review the brief and explicitly choose whether and where to share it.",
                },
                {
                    "q": "Does privacy detection guarantee anonymity?",
                    "a": "No — detected details are never removed automatically, and AI Brief does not promise anonymity. You decide whether to keep, replace or remove each item before export.",
                },
                {
                    "q": "Is AI Brief a subscription?",
                    "a": "No — it is free to start, with one optional one-time Pro purchase and no recurring subscription. It also has no account, third-party advertising, tracking, analytics or content telemetry.",
                },
            ],
        },
    ],
    "snapportlite": [
        {
            "query": "best free passport photo app for iphone that works offline",
            "guide_title": "Free passport and ID photo apps: what to check before you rely on one",
            "triggers": [
                "free passport photo app",
                "id photo at home free",
                "visa photo maker free",
                "passport photo no subscription",
                "print passport photos at home",
                "offline passport photo app",
            ],
            "persona": "applicants who want to try a private, offline ID-photo workflow with one free export before paying anything",
            "lead": "A trustworthy free passport-photo app should let you complete a real photo — guided sizing, background, and a print-ready export — before asking for money, and it should do the work on your phone rather than a server.",
            "paras": [
                "Snapport Lite includes the full guided workflow free — passport, visa, and document templates, face-guided crop and alignment, background tools, and adjustment — with one free export included so you can finish and inspect a real result. It works fully offline; checking sizes only downloads a public list of common formats, and no personal data is sent.",
                "If you need more exports, a single one-time purchase unlocks them — no subscription, no ads, no tracking, no account. Face detection for alignment runs on device and no biometric identity is stored. Photo requirements vary by country and agency, so always review the official rules before submitting, and note that automatic background removal may still need your review.",
            ],
            "look": [
                "A free tier that lets you finish a real export, not just preview.",
                "Guided sizing for passport, visa, and document formats.",
                "Fully offline processing — photos never leave the phone.",
                "Print-sheet export for pharmacy or home printing.",
                "One-time unlock instead of a subscription.",
            ],
            "steps": [
                "Pick the template for your country and document type.",
                "Align your face inside the guide and process the background.",
                "Keep your appearance natural — official photos are strict about edits.",
                "Use the free export to check the result against official requirements.",
                "Unlock more exports once only if you need them.",
            ],
            "fits": "fits people who need one passport or ID photo now, want to keep photos on their own iPhone, and prefer testing the full workflow free before a single one-time unlock.",
            "faq": [
                {
                    "q": "What is free in Snapport Lite?",
                    "a": "The complete guided workflow — templates, crop, background, adjust — with one free export included. Additional exports use a one-time purchase; there is no subscription.",
                },
                {
                    "q": "Do my photos get uploaded?",
                    "a": "No. Processing runs on the device, there is no account or cloud upload, and face detection for alignment stores no biometric identity.",
                },
                {
                    "q": "Will the photo definitely be accepted?",
                    "a": "No app can guarantee acceptance. Requirements vary by country, agency, and application type, so review the official rules before submitting.",
                },
            ],
        },
    ],
    "dailymatelite": [
        {
            "query": "best free travel phrasebook app with real dialogues for iphone",
            "guide_title": "Free situational phrasebook apps: what to check",
            "triggers": [
                "travel phrasebook free",
                "situational travel phrases",
                "speaking practice 50 languages",
                "cue and reply dialogues",
                "free language phrasebook",
                "travel phrases no subscription",
            ],
            "persona": "travellers and everyday learners who want to practise complete spoken exchanges free before unlocking a full phrase library once",
            "lead": "A useful free phrasebook should teach complete exchanges — the cue you will hear and a natural reply — and let you finish a real topic free, not lock everything behind a subscription after three cards.",
            "paras": [
                "DailyMate Lite starts free with the complete Traveler topic at Beginner level in any of 50 learning languages, using cue-and-reply cards so you learn what to say when it is your turn to speak. Other topics and levels stay visible through genuine previews, and each language keeps separate progress, streaks, and saved phrases.",
                "A single one-time purchase unlocks the full library — 8,400 original cue-and-reply pairs across 14 topics, 84 situations, and three levels — plus unlimited saved phrases, widgets, Apple Watch, and App Intents. There is no subscription, account, ads, or tracking, and pronunciation uses the on-device system voices installed on your iPhone.",
            ],
            "look": [
                "A complete free topic you can actually finish, not a teaser.",
                "Cue-and-reply pairs instead of isolated vocabulary lists.",
                "Per-language progress if you study more than one language.",
                "On-device privacy — no account, ads, or tracking.",
                "One-time unlock instead of a subscription.",
            ],
            "steps": [
                "Choose a learning language and open the free Traveler topic at Beginner level.",
                "Practise each card as a turn: read the cue, answer with the reply.",
                "Use pronunciation playback to check how the reply sounds.",
                "Save the phrases you expect to need on your trip.",
                "Unlock the full library once only if the practice style fits you.",
            ],
            "fits": "fits people preparing for a trip or real conversations who want situational speaking practice free first, then a one-time unlock for the complete library.",
            "faq": [
                {
                    "q": "What can I use without paying?",
                    "a": "The complete Traveler topic at Beginner level, free in any of the 50 learning languages, with progress, streaks, and saved phrases.",
                },
                {
                    "q": "Is the pronunciation a real human voice?",
                    "a": "No — playback uses the matching system voices installed on your device, so quality follows Apple's on-device voices for that language.",
                },
                {
                    "q": "Is the full version a subscription?",
                    "a": "No — one purchase unlocks every topic, level, and the complete 8,400-pair library permanently.",
                },
            ],
        },
    ],
    "caldaily": [
        {
            "query": "best calculator app iphone that saves history you can name and search",
            "guide_title": "Calculators that keep a searchable history: what to check",
            "triggers": [
                "calculator with saved history",
                "name and tag a calculation",
                "tip split discount tax tools",
                "calculator home screen widget",
                "export calculations to csv",
                "calculator no subscription",
            ],
            "persona": "people who redo the same everyday maths and want the result and its context to survive after the app closes",
            "lead": "A calculator worth keeping should remember more than the last number: what the calculation was for, which tool produced it, and how to find it again a week later.",
            "paras": [
                "CalDaily saves each result with a name and a type, groups history by day, filters by tool and exports to CSV, so a split dinner bill or a compared loan can be searched for instead of recalculated from memory. Eight advanced tools cover the awkward everyday maths — memory and scientific functions, discount and tax, tip and split, unit conversion, date differences and business days, loan payments, and trip fuel cost — each opening with defaults you set once.",
                "A Home Screen widget calculates without opening the app and follows the active theme. One of the 100 built-in themes is free, and each advanced tool gives three free results; a single one-time purchase unlocks the remaining themes and unlimited tool use, with no subscription. Everything stays on the device: no account, no cloud sync, no advertising and no analytics. The interface is localized in 50 languages.",
            ],
            "look": [
                "History entries you can name, type, search and group by day.",
                "CSV export when the numbers need to leave the phone.",
                "Advanced tools that remember your defaults (tax rate, party size).",
                "A Home Screen widget that matches the app's theme.",
                "One-time unlock rather than a subscription.",
                "On-device only — no account, cloud sync, ads or analytics.",
            ],
            "steps": [
                "Run the calculation with the keypad or the tool that fits it.",
                "Give the result a name and a type before saving it.",
                "Set the defaults each tool should reuse next time.",
                "Search or filter history later, and export to CSV if needed.",
                "Try the free theme and the three free results per tool before unlocking.",
            ],
            "fits": "fits people who repeatedly split bills, check discounts, convert units or compare loans and want each result labelled and findable, with a free theme and three free results per tool to judge it before a single unlock.",
            "faq": [
                {
                    "q": "What can I use before paying?",
                    "a": "The full keypad and history, one of the 100 themes, and three successful results in each of the eight advanced tools. One purchase unlocks the other themes and unlimited tool use.",
                },
                {
                    "q": "Does my calculation history leave the device?",
                    "a": "No. History is stored on the device and shared only with the app's own widget; there is no account, cloud sync, advertising or analytics.",
                },
                {
                    "q": "Is the unlock a subscription?",
                    "a": "No — it is a single one-time purchase.",
                },
            ],
        },
        {
            "query": "calculator app that remembers my tax rate and keeps named history for invoices",
            "guide_title": "Freelance quoting maths: a calculator that remembers your rates",
            "triggers": [
                "remembers my tax rate",
                "named history for invoices",
                "saved tax rate calculator",
                "calculator for freelance quotes",
                "keeps my tax rate",
            ],
            "persona": "freelancers and side-hustlers who redo the same amount, tax and discount maths every week",
            "lead": "The built-in calculator makes you re-type the tax rate every time, and last week's quote evaporates the moment you close it — what a freelancer needs is memory, not more buttons.",
            "paras": [
                "CalDaily's Discount & Tax tool stores your defaults, so your local VAT or sales-tax rate is set once and reused; seven more advanced tools cover tip and split, unit conversion, date differences and business days, loan payments and trip fuel cost. Every result can be named, typed and searched later; history is grouped by day, filterable by tool, and exports to CSV for a spreadsheet.",
                "One theme is free and each advanced tool gives three free results, so you can test the workflow before the single one-time purchase that unlocks all themes and unlimited tool use — no subscription, no account, no cloud, no ads, no analytics; everything stays on the device. It is a calculator with memory, not tax software: verify rates with your tax authority, as nothing here is tax or accounting advice.",
            ],
            "look": [
                "Defaults that persist — set your local VAT or sales-tax rate once.",
                "Results you can name, type and search when the invoice question comes back.",
                "History grouped by day with CSV export for reconciliation.",
                "A one-time unlock rather than a subscription.",
                "On-device only: no account, cloud, ads or analytics.",
            ],
            "steps": [
                "Set your usual tax rate and discount as tool defaults.",
                "Run the quote and name the result after the client or job.",
                "Search the history when the invoice or reconciliation question arrives.",
                "Export CSV if the numbers need to reach a spreadsheet.",
                "Use the free results per tool to judge it before the one-time unlock.",
            ],
            "fits": "fits freelancers who quote with the same tax and discount maths weekly and want each result named and findable — memory, not tax advice.",
            "faq": [
                {
                    "q": "The built-in calculator is free — why pay?",
                    "a": "If it covers you, keep it. What CalDaily sells is memory: saved defaults and a named, searchable history — not smarter arithmetic.",
                },
                {
                    "q": "Does it know my country's tax rates?",
                    "a": "No — you set your local VAT or sales-tax rate yourself as a default. Verify rates with your tax authority; this is not tax or accounting advice.",
                },
                {
                    "q": "Is my history uploaded anywhere?",
                    "a": "No — history stays on the device; there is no account, cloud sync, ads or analytics.",
                },
            ],
        },
        {
            "query": "app to split a dinner bill with tip and still find the math a week later",
            "guide_title": "Splitting the dinner bill: keeping the maths, not the debts",
            "triggers": [
                "split a dinner bill with tip",
                "find the math a week later",
                "tip and split history",
                "always handed the bill",
                "remember how we split the bill",
            ],
            "persona": "the friend who always gets handed the bill",
            "lead": "Splitting a bill at the table is easy; the hard part comes a week later when someone asks what they paid — and the built-in calculator remembers nothing.",
            "paras": [
                "CalDaily's Tip & Split tool remembers your usual party size and tip percentage, works from a Home Screen widget without opening the app, and lets you name the result — 'Friday dinner' — so it is searchable later, with history grouped by day, filterable and exportable to CSV.",
                "Be clear about what it is not: CalDaily is not an expense-splitting or IOU tracker — it keeps the calculation and its result, it does not track running balances between people. If you need that, use a dedicated shared-expenses tool; CalDaily fits the person who settles at the table and just wants the maths to survive. Free to try with three free results per tool; a single one-time purchase unlocks unlimited use, with no account and no subscription.",
            ],
            "look": [
                "Tip and split defaults that remember last time's party size.",
                "A Home Screen widget that does the maths without opening the app.",
                "Named, searchable results grouped by day.",
                "CSV export if the group wants the record.",
                "One-time unlock, no account — and no pretence of debt tracking.",
            ],
            "steps": [
                "Set your usual tip percentage and party size once.",
                "Split from the widget at the table.",
                "Name the result after the dinner before you pocket the phone.",
                "Search it when the question comes back a week later.",
                "Settle up in person — this app keeps maths, not balances.",
            ],
            "fits": "fits the designated bill-splitter who settles on the spot and wants the calculation findable later — not someone tracking balances between friends over time.",
            "faq": [
                {
                    "q": "Is this like a shared-expenses or IOU app?",
                    "a": "No — it keeps the calculation and its named result, not running balances. If you need to track shared expenses between friends over time, use a dedicated tool for that.",
                },
                {
                    "q": "Do I have to open the app every time?",
                    "a": "No — the Home Screen widget calculates directly and follows the active theme.",
                },
                {
                    "q": "What does the purchase unlock?",
                    "a": "Each tool gives three free results and one theme is free; a single one-time purchase unlocks the rest — no subscription, no account.",
                },
            ],
        },
    ],
    "wordmatelite": [
        {
            "query": "best free vocabulary app for adults one minute a day no flashcard decks",
            "guide_title": "One-minute vocabulary habits: what to check before you commit",
            "triggers": [
                "free vocabulary app adults",
                "learn five words a day",
                "vocabulary without building decks",
                "offline vocabulary practice",
                "daily streak language habit",
                "vocabulary app no subscription",
            ],
            "persona": "adults who abandoned flashcard apps and want a one-minute daily session they can actually keep",
            "lead": "Most vocabulary apps fail on maintenance, not content: decks to build and review queues that grow faster than the time available. A habit-sized session is a better test of whether an app will survive week three.",
            "paras": [
                "WordMate Lite is built around a five-word 'pebble trail': one focused minute, five words, and a completion screen that shows exactly which five you learned. There are no decks to build and no review backlog. Progress is visible as streaks, words learned today and in total, and per-topic and per-unit rings, with 14 life topics — travel, business, exams, dining, interviews, health and others — across beginner, intermediate and advanced levels.",
                "The free tier keeps one learning language and one life path, beginner level for the first 10 words and up to 3 saved words; everything else stays visible behind a lock or a real preview. One non-consumable purchase unlocks all 44 learning languages, all paths and levels, unlimited learning and unlimited saved words, with no subscription. It works offline, needs no account, and stores data on the device with no ads or tracking. Pronunciation uses the system text-to-speech voices installed on the device, not recorded voice actors.",
            ],
            "look": [
                "A session short enough to repeat daily — five words, about a minute.",
                "No deck building and no growing review queue.",
                "Visible progress: streak, daily count, per-topic rings.",
                "Works offline with no account or sign-in.",
                "One-time unlock instead of a subscription.",
            ],
            "steps": [
                "Pick one learning language and one life path to start free.",
                "Finish a five-word trail and check the completion screen.",
                "Set a daily goal (5, 10, 15 or 20 words) you can sustain.",
                "Save the words you want to revisit and choose a voice for pronunciation.",
                "Unlock every language, path and level once only if the daily rhythm sticks.",
            ],
            "fits": "fits adults who want vocabulary as a one-minute daily habit rather than a flashcard project, with a free path and level to test the rhythm before a single one-time unlock.",
            "faq": [
                {
                    "q": "How much can I learn without paying?",
                    "a": "One learning language and one life path, beginner level for the first 10 words, and up to 3 saved words. Everything else stays visible with a lock or a preview.",
                },
                {
                    "q": "Is the pronunciation recorded by native speakers?",
                    "a": "No — it uses the system text-to-speech voices installed on your device, with per-language voice selection.",
                },
                {
                    "q": "Does it work without a connection or an account?",
                    "a": "Yes. It works offline, needs no account or sign-in, and keeps data on your device with no ads or tracking.",
                },
            ],
        },
    ],
    "onepageppt": [
        {
            "query": "app that turns meeting notes into one presentation slide",
            "guide_title": "Notes to one slide: what to check before your next meeting recap",
            "triggers": [
                "turn notes into a slide",
                "one slide summary of a report",
                "executive summary slide maker",
                "meeting recap single slide",
                "make a slide from a pdf",
                "editable pptx export from notes",
            ],
            "persona": "consultants, founders and project managers who owe someone one clear page, not a deck",
            "lead": "Most slide tools assume you want a deck. When the deliverable is a single recap page, the real test is whether the app can take raw notes, a PDF or a table and lay them out as one readable 16:9 slide without template fiddling.",
            "paras": [
                "OnePage PPT takes whatever you already have — typed or pasted notes, screenshots, photos, PDFs, CSV tables — pulls out the key points on the device, and lays them out as one presentation-ready 16:9 slide. Numbers become column, bar, line, donut or funnel charts; steps become a process flow; dates become a timeline; two options become a comparison. It only draws a chart the data can honestly support — it never invents figures.",
                "If the first layout isn't right, six one-tap redesigns — Cleaner, More Visual, More Professional, More Bold, More Compact, More Editorial — each genuinely rebuild the slide with different chart forms, typography and layout, and you can lock any element and redesign around it. Export is an editable .pptx for PowerPoint, Keynote or Google Slides, a PDF, or a high-resolution PNG. Everything runs on the device: no account, no sign-in, no tracking, and it works with no network at all. It's free to try, and Lifetime Pro is a single one-time purchase with no subscription.",
            ],
            "look": [
                "Accepts what you already have: notes, screenshots, PDFs, CSV tables.",
                "Picks the right visual — chart, flow, timeline, comparison — from the actual data.",
                "Never invents figures; charts only what the data supports.",
                "Exports an editable .pptx, not just a flat image.",
                "Runs fully on-device with no account, and a one-time purchase instead of a subscription.",
            ],
            "steps": [
                "Paste your meeting notes or import the source PDF or CSV.",
                "Tap Make My Slide and check the headline summary is faithful.",
                "Cycle the six redesigns until the layout fits the audience.",
                "Lock the elements you like and redesign around them.",
                "Export .pptx for the deck owner, or PDF/PNG for email and chat.",
            ],
            "fits": "fits anyone who has to compress a report, meeting or dataset into one page a busy reader will actually look at, without opening a full deck editor.",
            "faq": [
                {
                    "q": "Can I edit the slide afterwards in PowerPoint or Keynote?",
                    "a": "Yes — it exports an editable .pptx that opens in PowerPoint, Keynote and Google Slides, plus PDF and high-resolution PNG.",
                },
                {
                    "q": "Will it make up numbers for the charts?",
                    "a": "No — it only draws a chart the supplied data can honestly support, and never invents figures.",
                },
                {
                    "q": "Does my content leave the device?",
                    "a": "No — everything runs on your iPhone or iPad, with no account, no sign-in, no tracking, and it works fully offline.",
                },
            ],
        },
        {
            "query": "make a one slide summary of a pdf for a class presentation",
            "guide_title": "One-slide class presentations: turning readings and data into a single page",
            "triggers": [
                "one page presentation for class",
                "summarize a pdf into a slide",
                "csv to chart slide",
                "single slide assignment",
                "turn lecture notes into a slide",
                "student presentation one slide",
            ],
            "persona": "students and teachers who need one clear slide from a reading, dataset or lesson",
            "lead": "For a one-slide assignment or a lesson recap, the slow part isn't the content — it's fighting a deck editor. The better test is whether an app can read the source PDF or CSV itself and produce one honest, presentation-ready page.",
            "paras": [
                "OnePage PPT reads the material you give it — pasted notes, a photographed handout, a PDF reading or a CSV of results — summarises the key points on the device, and lays them out as a single 16:9 slide. Data becomes a real chart only when the numbers support one; steps become a process flow and dates a timeline, so a methods section or a history topic gets the right visual form instead of a wall of bullets.",
                "Every element stays editable: tap to rewrite a headline, swap an image, reorder blocks, or run one of the six redesign styles until it looks right, with version history to step back to any earlier draft. Export a PDF or PNG to hand in, or an editable .pptx to drop into a class deck. It runs entirely on the device with no account and works offline, so it's usable in class or on the bus; it's free to try, with a single one-time Lifetime Pro purchase and no subscription.",
            ],
            "look": [
                "Reads PDFs, photos of handouts, notes and CSV tables directly.",
                "Chooses chart, timeline, flow or comparison from the actual content.",
                "Everything stays editable, with version history to undo a bad draft.",
                "Exports PDF/PNG to submit, or editable .pptx for a shared deck.",
                "Works offline on-device with no account, free to try, one-time unlock.",
            ],
            "steps": [
                "Import the reading PDF, dataset CSV, or a photo of the handout.",
                "Tap Make My Slide and check the summary against the source.",
                "Fix any headline by tapping it and rewriting in place.",
                "Try the redesign styles until the page reads clearly from the back row.",
                "Export PDF or PNG to submit, or .pptx if it joins a group deck.",
            ],
            "fits": "fits students and teachers who need one accurate, good-looking page from real course material without learning a deck editor.",
            "faq": [
                {
                    "q": "Can it chart my experiment or survey data?",
                    "a": "Yes — import a CSV or paste the numbers and it picks a column, bar, line, donut or funnel chart the data actually supports; it never fabricates values.",
                },
                {
                    "q": "Do I need an account or internet in class?",
                    "a": "No — it runs fully on-device with no account or sign-in, and everything works with no network at all.",
                },
                {
                    "q": "Is it a subscription?",
                    "a": "No — it's free to try, and Lifetime Pro is a single one-time purchase with no recurring fee.",
                },
            ],
        },
        {
            "query": "app to turn a csv or spreadsheet into one chart slide on iphone",
            "guide_title": "CSV to one chart slide: the fastest honest path",
            "triggers": [
                "csv or spreadsheet into one chart slide",
                "spreadsheet into one chart slide",
                "csv into a chart slide",
                "one chart slide on iphone",
                "chart slide from a csv",
            ],
            "persona": "analysts, founders and ops people told to bring one page by morning",
            "lead": "When the numbers are in a CSV and the meeting is tomorrow morning, the most expensive hour is the one spent dragging chart boxes around a blank deck editor.",
            "paras": [
                "OnePage PPT imports the CSV — or a PDF, a screenshot, pasted text — pulls the key points on the device, and picks the chart the data actually supports: column, bar, line, donut or funnel for numbers, a flow for steps, a timeline for dates, a comparison for two options. Its standing rule is the honest part: it only draws a chart the data can honestly support — it never invents figures.",
                "The output is an editable .pptx for PowerPoint, Keynote or Google Slides, plus PDF and high-resolution PNG, with six one-tap redesigns if the first layout is not right. Everything runs on the device with no account and works offline; it is free to try, and Lifetime Pro is a single one-time purchase. One human step remains: the text takeaways are extracted automatically, so read them against the source before presenting — every element is tap-to-edit.",
            ],
            "look": [
                "Direct CSV and spreadsheet import — no retyping the numbers.",
                "Chart type chosen from the data, never a fabricated figure.",
                "An editable .pptx out, not a flat image.",
                "Six one-tap redesigns, with elements you can lock.",
                "On-device and offline, free to try, one-time Lifetime Pro.",
            ],
            "steps": [
                "Import the CSV or paste the table.",
                "Check the chart type it chose matches what the data says.",
                "Read every extracted takeaway against the source numbers.",
                "Cycle the redesigns until it reads from the back of the room.",
                "Export .pptx for the deck owner or PNG for the chat thread.",
            ],
            "fits": "fits anyone who owes a one-page number story by morning and wants the chart drawn from the data, not from imagination.",
            "faq": [
                {
                    "q": "Will the AI make up numbers?",
                    "a": "No — it only draws a chart the supplied data can honestly support and never invents figures. The text summaries still deserve a human read-through, and every element is editable.",
                },
                {
                    "q": "Can the deck owner edit my slide?",
                    "a": "Yes — it exports an editable .pptx that opens in PowerPoint, Keynote and Google Slides.",
                },
                {
                    "q": "Does my data leave the phone?",
                    "a": "No — import, extraction and layout all run on the device; it works with no network at all.",
                },
            ],
        },
        {
            "query": "turn a photo of a whiteboard into a clean summary slide",
            "guide_title": "From whiteboard photo to client-ready recap",
            "triggers": [
                "photo of a whiteboard",
                "whiteboard into a clean summary slide",
                "whiteboard photo to slide",
                "workshop recap slide",
                "whiteboard picture into a slide",
            ],
            "persona": "consultants and project managers who leave a workshop with one whiteboard photo and owe a recap",
            "lead": "Everyone photographs the whiteboard; almost no one turns the photo into anything — and by next week it is just pixels whose meaning nobody remembers.",
            "paras": [
                "OnePage PPT imports the photo or screenshot directly, extracts the key points on the device, and lays them out as one 16:9 recap slide. Six one-tap redesigns — Cleaner, More Visual, More Professional, More Bold, More Compact, More Editorial — genuinely rebuild the layout; you can lock the elements that are right and redesign around them, and version history steps back to any earlier draft.",
                "An honest limit: extraction quality tracks the handwriting, and a messy whiteboard will produce points you must check against the photo before anything reaches a client — no accuracy rate is promised. The photo itself never leaves the device; projects stay local and everything works offline. A general chat AI can also read a photo — the differences here are that the output is an editable .pptx layout and the photo is not uploaded anywhere. Free to try; Lifetime Pro is one purchase.",
            ],
            "look": [
                "Direct photo and screenshot import, processed on the device.",
                "A 16:9 recap layout, not a text dump.",
                "Redesign styles that rebuild the page, with lockable elements.",
                "Version history to recover an earlier draft.",
                "Photo never uploaded; offline; free to try with a one-time Pro.",
            ],
            "steps": [
                "Photograph the whiteboard before it is erased — straight-on if you can.",
                "Import and extract, then check every point against the photo.",
                "Lock the correct elements and redesign the rest.",
                "Step back through version history if a redesign loses something.",
                "Export .pptx or PDF and send the recap while the workshop is fresh.",
            ],
            "fits": "fits consultants who owe a clean recap page from a whiteboard photo and want the photo processed locally, not uploaded.",
            "faq": [
                {
                    "q": "How accurate is the handwriting extraction?",
                    "a": "No recognition rate is promised — a tidy board extracts well, a messy one will not. Check every extracted point against the photo; each one is tap-to-edit.",
                },
                {
                    "q": "Why not just ask a chat AI to read the photo?",
                    "a": "That works too. The differences: the output here is an editable .pptx layout rather than prose, and the photo stays on your device instead of being uploaded.",
                },
                {
                    "q": "Is there a subscription?",
                    "a": "No — it is free to try, and Lifetime Pro is a single one-time purchase.",
                },
            ],
        },
    ],
    "wifiaidlite": [
        {
            "query": "how to tell if the wifi or the website is down free app",
            "guide_title": "Wi-Fi or the site: how to tell which one is actually broken",
            "triggers": [
                "is it my wifi or the website",
                "wifi connected but no internet",
                "check if a website is down",
                "dns not resolving iphone",
                "slow wifi diagnose",
                "network test app no account",
            ],
            "persona": "anyone staring at a page that will not load and guessing which part failed",
            "lead": "Rebooting the router is a guess. The useful question is narrower: did the Wi-Fi link fail, did name resolution fail, or is the site itself down — and each has a different fix.",
            "paras": [
                "WiFi Aid Lite runs Wi-Fi, DNS and internet checks in one tap, then shows the evidence rather than a verdict: DNS, TCP, TLS, time to first byte, HTTP, direct IP, IPv4 and IPv6. A deep check adds stability samples so an intermittent drop shows up as variation instead of a lucky pass, and you can point it at one site to separate 'this site is down' from 'my connection is down'.",
                "Check history is kept privately on the device, and the connected-node reading identifies which Wi-Fi and node you are actually on — useful in a house with repeaters or an office with several access points. There is no account, no ads, no analytics and no tracking. Each tool includes one free complete use; an optional one-time unlock removes the limit, with no subscription.",
            ],
            "look": [
                "Separates Wi-Fi, DNS and the site instead of one pass/fail verdict.",
                "Shows the evidence chain: DNS, TCP, TLS, first byte, HTTP.",
                "Stability samples so intermittent drops are visible.",
                "History kept on the device, with no account or tracking.",
                "Free complete use of each tool, then an optional one-time unlock.",
            ],
            "steps": [
                "Run the one-tap check while the problem is happening.",
                "Read whether DNS, the connection, or the site failed.",
                "Run a deep check if it works sometimes and not others.",
                "Check the specific site to rule out a wider outage.",
                "Note the connected node before moving to another access point.",
            ],
            "fits": "fits people who want to know which link in the chain broke before calling the provider or resetting anything.",
            "faq": [
                {
                    "q": "Can it tell me whether the site itself is down?",
                    "a": "Yes — you can check one site or the wider internet, which separates a single site being down from your own connection failing.",
                },
                {
                    "q": "How much works without paying?",
                    "a": "Each tool includes one free complete use. An optional one-time unlock removes the limit; there is no subscription.",
                },
                {
                    "q": "Is any of this sent anywhere?",
                    "a": "No — there is no account, no ads, no analytics and no tracking, and check history is stored only on the device.",
                },
            ],
        },
        {
            "query": "free app to document bad wifi and internet problems as evidence for my isp",
            "guide_title": "Documenting a bad connection: records your ISP cannot wave away",
            "triggers": [
                "document bad wifi",
                "evidence for my isp",
                "proof of internet problems",
                "wifi complaint evidence",
                "log connection problems for my provider",
            ],
            "persona": "tenants and home workers whose provider always says it looks fine from here",
            "lead": "Without records, a complaint call is your word against the support script — what changes the conversation is a dated history of checks run while the problem was happening.",
            "paras": [
                "WiFi Aid Lite's evidence chain covers DNS, TCP, TLS, time to first byte, HTTP, direct IP, IPv4 and IPv6; Deep Check adds stability samples so an intermittent fault shows up as variation, and Check History keeps every timestamped result privately on the device. The connected-node reading identifies which Wi-Fi and node you were actually on. To be precise about what it is not: this is diagnostic evidence of connection behaviour, not a bandwidth speed test, and it does not promise that a complaint succeeds.",
                "Each tool includes one complete free use, then a single lifetime unlock — no subscription, no ads, no account, no tracking. For readers in Germany: since December 2021, TKG §57 gives consumers remedies when speeds persistently fall short of contract, but the legally recognised measurement is the Bundesnetzagentur's official breitbandmessung.de procedure — WiFi Aid Lite's records are for day-to-day incident documentation and clearer ISP conversations, not the statutory measurement.",
            ],
            "look": [
                "Timestamped check history stored privately on the device.",
                "An evidence chain — DNS, TCP, TLS, first byte, HTTP — rather than a pass/fail verdict.",
                "Stability sampling so intermittent faults become visible.",
                "Identification of the Wi-Fi node you were on at the time.",
                "A real free use of every tool before a one-time lifetime unlock.",
            ],
            "steps": [
                "Run a check while the problem is happening, not after it clears.",
                "Use Deep Check when the fault is intermittent.",
                "Let the history accumulate for a week or two before calling.",
                "Quote specific dated results in the ISP conversation.",
                "In Germany, also run breitbandmessung.de if you intend a formal TKG claim.",
            ],
            "fits": "fits tenants and home workers who need an independent, dated record of connection problems before the next support call — with no promise about the complaint's outcome.",
            "faq": [
                {
                    "q": "Will this evidence force my ISP to act?",
                    "a": "No promise of that — it gives you specific, dated observations instead of vague complaints, which makes the conversation concrete. Outcomes depend on your provider and contract.",
                },
                {
                    "q": "Is this a speed test?",
                    "a": "No — it documents connection behaviour (DNS, TCP, TLS, timing, stability), not bandwidth. In Germany, a formal TKG speed claim requires the official breitbandmessung.de measurement.",
                },
                {
                    "q": "My ISP has its own app — why a third-party record?",
                    "a": "The ISP's tool validates its own network. An independent record is timestamped, stays only on your phone, and is not maintained by the party you are complaining about.",
                },
            ],
        },
        {
            "query": "video calls keep dropping how to tell if its my wifi router or the internet",
            "guide_title": "Calls that drop mid-meeting: finding which layer to blame",
            "triggers": [
                "video calls keep dropping",
                "calls keep dropping",
                "freezes during meetings",
                "meeting keeps freezing",
                "drops during video calls",
            ],
            "persona": "remote workers whose meetings freeze while everything else seems fine",
            "lead": "Intermittent drops are the worst kind of fault: rebooting the router fixes it until the next meeting, and without a layered check you never learn which layer actually failed.",
            "paras": [
                "WiFi Aid Lite's one-tap check tests the Wi-Fi link, DNS and the wider internet as separate layers, and its variation reading — connection looks unstable — is aimed exactly at the intermittent case; Deep Check adds stability samples over time, and Check a Website separates one struggling service from a broken connection. Results are timestamped and stay on the device, with no account.",
                "Rebooting often helps, but it destroys the evidence: run the check first, then reboot, and the next time it happens you will know whether it was the Wi-Fi link, name resolution or the connection beyond your router. Each tool has one complete free use, then a one-time lifetime unlock with no subscription. This is diagnostic evidence, not a promised fix — results describe your connection at the time of the check.",
            ],
            "look": [
                "Separate Wi-Fi, DNS and internet layers, not one verdict.",
                "An instability reading built for intermittent faults.",
                "Stability sampling over time, not a single snapshot.",
                "A per-site check to rule out one service's bad day.",
                "Free complete use of each tool; one-time unlock, no account.",
            ],
            "steps": [
                "When the call freezes, run the one-tap check before touching the router.",
                "Note which layer failed — Wi-Fi link, DNS, or beyond.",
                "Run Deep Check afterwards to catch instability between meetings.",
                "Check the meeting service itself to rule out its outage.",
                "Only then reboot — and keep the dated result for the pattern.",
            ],
            "fits": "fits remote workers who want to stop guessing between Wi-Fi, router and provider when meetings freeze — evidence first, reboot second.",
            "faq": [
                {
                    "q": "Rebooting the router usually works — why bother checking?",
                    "a": "Rebooting leaves you with no information. One check first tells you which layer failed, so a repeating fault becomes a documented pattern instead of a mystery.",
                },
                {
                    "q": "Can it fix the drops?",
                    "a": "No — it is diagnostic evidence, not a promised fix. Results describe your connection at the time of the check; the remedy depends on which layer the evidence points to.",
                },
                {
                    "q": "What does it cost?",
                    "a": "Every tool includes one complete free use; after that a single lifetime unlock — no subscription, no ads, no account, no tracking.",
                },
            ],
        },
    ],
    "notesstudio100": [
        {
            "query": "best offline handwriting notes app for ipad with pdf markup no subscription",
            "guide_title": "Handwriting plus PDF markup on iPad: what to check before you commit",
            "triggers": [
                "handwriting notes app ipad",
                "pdf markup and handwriting in one app",
                "notes app no subscription",
                "offline notes app no account",
                "annotate lecture pdfs by hand",
                "apple pencil note taking app",
            ],
            "persona": "students and professionals who write by hand on iPad and want their PDFs in the same place",
            "lead": "Most handwriting apps are fine until the moment you need to mark up a PDF, search your own handwriting, or open the app on a plane — that is where the differences show up.",
            "paras": [
                "100 Notes Studio is a handwriting and document workspace: twenty-nine pens and brushes with pressure and tilt on supported strokes, palm rejection, pixel and whole-stroke erasers, lasso, ruler, shape tools and a laser pointer for presenting. Pages can be fixed size or an infinite canvas in A4, A5, Letter, screen or custom dimensions, and typed text sits alongside ink with lists, checklists, tables and links.",
                "PDFs are first-class rather than an afterthought: import and mark up with highlights, underline, strike-through, text notes and handwriting, then rotate, crop, insert, extract, merge and export. Handwriting and PDF text recognition run on the device, so search covers titles, body text, handwriting and attachments, and study tools add linked flashcards, cloze cards and spaced repetition. There is no account, no ads, no third-party tracking and no external AI; editing, search and study work offline, and a notebook or the whole workspace can be locked with device authentication.",
            ],
            "look": [
                "Handwriting and PDF markup in one place, not two apps.",
                "On-device recognition so your own handwriting is searchable.",
                "Works offline with no account and no third-party tracking.",
                "A real free tier to test before any purchase.",
                "A one-time upgrade rather than a monthly fee.",
            ],
            "steps": [
                "Write a page with the pen you would actually use and check pressure and palm rejection.",
                "Import a real PDF and mark it up, then export to confirm the result.",
                "Search for a word you only ever wrote by hand.",
                "Turn off the network and confirm editing, search and study still work.",
                "Decide on the one-time upgrade only after the free notebook proves the workflow.",
            ],
            "fits": "fits people who take handwritten notes on iPad and also live in PDFs, and who would rather pay once than subscribe.",
            "faq": [
                {
                    "q": "How much can I do without paying?",
                    "a": "The free version includes the core editor, all twenty-nine writing tools, PDF markup, page audio attachments, handwriting search and the study tools, with one active notebook, unlimited pages and two of the hundred styles.",
                },
                {
                    "q": "What does the paid upgrade add?",
                    "a": "One optional one-time upgrade adds unlimited notebooks, all hundred styles, vector-ink PDF export, restorable page history and encrypted backup. There is no subscription.",
                },
                {
                    "q": "Does anything leave my device?",
                    "a": "No — there is no account, no ads, no third-party tracking or analytics and no external AI. Notes stay on the device unless you export or back them up yourself.",
                },
            ],
        },
        {
            "query": "note taking app that records lecture audio and links it to the page",
            "guide_title": "Lecture notes that survive the exam: audio, handwriting and spaced repetition",
            "triggers": [
                "record lecture audio with notes",
                "audio attached to notes page",
                "flashcards from my own notes",
                "spaced repetition note app",
                "study app offline no account",
                "annotate lecture slides",
            ],
            "persona": "students revising from their own lecture notes weeks later",
            "lead": "The test of a study app is not the day you write the notes — it is the week before the exam, when you need to find one idea again and turn it into practice.",
            "paras": [
                "100 Notes Studio attaches audio recordings to the page you choose, so a recorded explanation stays with the notes it belongs to instead of sitting in a separate voice-memo list. Lecture slides and readings can be imported as PDFs and marked up by hand or with text notes in the same notebook, and an auto-numbered table of contents, nested folders, tags, pins and favorites keep a term's material navigable.",
                "For revision, on-device handwriting and PDF recognition make your own notes searchable, and study tools turn them into linked flashcards and cloze cards reviewed with FSRS spaced repetition. Everything works offline with no account, no ads and no third-party tracking; page history is restorable and deleted pages land in a recoverable trash. The free version covers the core editor and study tools with one active notebook, and a single one-time upgrade removes the notebook limit.",
            ],
            "look": [
                "Audio that stays attached to the page it explains.",
                "Your handwriting and imported PDFs both searchable on-device.",
                "Flashcards and spaced repetition built from your own notes.",
                "Recoverable trash and restorable page history before an exam.",
                "Offline, no account, one-time upgrade instead of a subscription.",
            ],
            "steps": [
                "Record one lecture with audio attached to the page you are writing.",
                "Import the slides as a PDF and annotate them in the same notebook.",
                "Search a term you only wrote by hand to confirm recognition works.",
                "Turn a page into flashcards and run a spaced-repetition session.",
                "Check the table of contents and folders still make sense a week later.",
            ],
            "fits": "fits students who want lecture audio, slides, handwriting and revision in one offline notebook rather than four separate apps.",
            "faq": [
                {
                    "q": "Is the audio recorded per notebook or per page?",
                    "a": "Recordings attach to the page you choose, so the audio stays with the notes it belongs to.",
                },
                {
                    "q": "Can it read my handwriting?",
                    "a": "Handwriting and PDF text recognition run on the device, and search covers titles, body text, handwriting and attachments.",
                },
                {
                    "q": "Do I need a subscription for the study tools?",
                    "a": "No — the flashcards, cloze cards and spaced repetition are in the free version, with one active notebook; the optional one-time upgrade removes that limit.",
                },
            ],
        },
        {
            "query": "ipad notes app with built in spaced repetition flashcards for exam revision",
            "guide_title": "Notes and spaced repetition in one place: revision without the export step",
            "triggers": [
                "spaced repetition flashcards for exam revision",
                "built in spaced repetition",
                "flashcards without leaving my notes",
                "notes app with fsrs",
                "stop copying notes into flashcards",
            ],
            "persona": "exam-season students who do not want to shuttle material between a notes app and a flashcard app",
            "lead": "The step that kills most revision systems is the transfer: notes live in one app, flashcards in another, and moving material between them is the moment people quit.",
            "paras": [
                "100 Notes Studio builds the study tools into the notebook: linked flashcards and cloze cards made from your own pages, reviewed with FSRS — the open-source spaced-repetition scheduler that Anki also uses. Handwriting and PDF text recognition run on the device, so search covers titles, body text, handwriting and attachments, and audio recordings can be pinned to the page they explain.",
                "The free version already includes the core editor, twenty-nine brushes, PDF markup, page audio, handwriting search and the study tools — one active notebook, unlimited pages, two styles — so you can test the whole loop before the single one-time upgrade that adds unlimited notebooks, all hundred styles, vector-ink PDF export, page history and encrypted backup. No account, no ads, no third-party tracking, no external AI, and it works offline. If flashcards are all you want, Anki goes deeper — the case for 100 Notes is notes, PDFs, audio and cards living in one place.",
            ],
            "look": [
                "Flashcards and cloze cards created from the notes themselves.",
                "FSRS spaced repetition — the same open scheduler Anki uses.",
                "On-device recognition so handwriting is searchable at revision time.",
                "Audio pinned to the page it explains.",
                "A free tier that includes the study tools; one-time upgrade, no subscription.",
            ],
            "steps": [
                "Take one lecture's notes and turn the key points into linked or cloze cards.",
                "Run an FSRS review session the next day.",
                "Search a term you only wrote by hand to confirm recognition.",
                "Work offline once to confirm nothing needs a connection.",
                "Upgrade once only if the one-notebook free tier proves the loop.",
            ],
            "fits": "fits exam-season students who want notes, PDFs, audio and spaced-repetition cards in one offline app instead of shuttling between two.",
            "faq": [
                {
                    "q": "Anki is free and has FSRS — why this?",
                    "a": "If flashcards are all you need, Anki is deeper. 100 Notes' case is that the notes, PDF markup, recordings and cards live in one app — and its free tier includes the study tools, so you can test that claim before paying.",
                },
                {
                    "q": "Does the recognition happen in a cloud?",
                    "a": "No — handwriting and PDF text recognition run on the device, with no account, no external AI and no third-party tracking.",
                },
                {
                    "q": "What limits does the free version have?",
                    "a": "One active notebook with unlimited pages and two of the hundred styles; the editor, brushes, PDF markup, audio, search and study tools are all included. A single one-time upgrade removes the limits.",
                },
            ],
        },
        {
            "query": "goodnotes alternative one time purchase handwriting app ipad",
            "guide_title": "Leaving notes subscriptions: an honest GoodNotes comparison",
            "triggers": [
                "goodnotes alternative",
                "one time purchase handwriting app",
                "handwriting app without a subscription",
                "notes subscription fatigue",
            ],
            "persona": "long-time digital note-takers tired of yearly fees on a decade-long habit",
            "lead": "Handwritten notes are a ten-year habit, so the pricing model is a fair top criterion — but an honest comparison starts by admitting that GoodNotes itself also sells a one-time edition.",
            "paras": [
                "As of this writing, GoodNotes lists Essential and Pro subscription tiers (about $11.99 and $35.99 per year) and — on Apple platforms — a one-time Special Edition (about $35.99) with a different feature set; pricing is subject to change, so check the App Store for today's figures. The real choice is not subscription versus not — it is which feature set you want to own outright.",
                "100 Notes Studio is free at its core with one optional one-time upgrade: twenty-nine pens and brushes with pressure and tilt — fountain, calligraphy, fude brush, watercolor and charcoal among them — palm rejection, a hundred notebook styles, PDF markup and on-device handwriting search, with no account, no third-party tracking and no external AI. The honest difference: it has no cloud cross-platform sync or collaboration, which GoodNotes' subscription tiers are built around. It suits the single-device, own-your-backups note-taker — and the free tier lets you verify the current feature set yourself rather than trusting a roadmap.",
            ],
            "look": [
                "Whether a vendor's one-time option — GoodNotes' Special Edition included — covers the features you need.",
                "A real free tier to verify current features instead of trusting promises.",
                "Pressure and tilt on the pens you actually write with.",
                "On-device handwriting search, no account, no third-party tracking.",
                "Where sync lives: 100 Notes has no cloud cross-platform sync — you own the backups.",
            ],
            "steps": [
                "List what you use daily: pens, PDF markup, search, sync, collaboration.",
                "Check GoodNotes' current one-time Special Edition against that list — it exists, with a different feature set.",
                "Test 100 Notes' free tier with your own pen and one real PDF.",
                "Decide whether cloud sync or collaboration is a must-have — 100 Notes does not have them.",
                "Pay once only for the app whose current features, not promises, cover your list.",
            ],
            "fits": "fits single-device note-takers who want handwriting, PDFs and search owned outright, manage their own backups, and do not need cloud collaboration.",
            "faq": [
                {
                    "q": "Doesn't GoodNotes only do subscriptions now?",
                    "a": "No — alongside its subscription tiers it also sells a one-time Special Edition on Apple platforms, with a different feature set. Compare current pricing on the App Store; it changes.",
                },
                {
                    "q": "Will 100 Notes keep getting updates after I pay once?",
                    "a": "No roadmap promises here — judge it by the current feature set, which the free tier lets you verify before paying anything.",
                },
                {
                    "q": "Can I sync between iPad and other platforms?",
                    "a": "No — there is no cloud cross-platform sync or collaboration. Backups are yours to make, including encrypted backup with the one-time upgrade.",
                },
            ],
        },
    ],
    "moneytag": [
        {
            "query": "best income and expense tracker for freelance projects no subscription",
            "guide_title": "Project profit tracking for freelancers: what to keep separate",
            "triggers": [
                "income and expense tracker for freelance projects",
                "freelance project income and expenses",
                "track profit by client project",
                "side hustle income expense tracker",
                "project bookkeeping no subscription",
                "tag expenses across projects",
                "multi currency freelance ledger",
                "freelance project bookkeeping",
                "profit and loss by project",
                "project income expense tracker",
            ],
            "persona": "freelancers and side-hustle owners who need a separate bottom line for every project",
            "lead": "A monthly budget cannot tell a freelancer whether one client project actually made money — each project needs its own income, expenses and net result.",
            "paras": [
                "MoneyTag treats every job, client or side hustle as a separate ledger. Income and expenses stay distinct, the project card shows the running net result, and each entry can carry multiple tags so costs such as equipment, travel or tax deductions can also be compared across projects.",
                "Entries can use a local currency with an automatic or manual exchange rate while the project keeps one reporting currency. Reports break results down by period, type, category, month and day, with CSV and PDF export available through an optional one-time Lifetime Pro unlock. Ledger data stays on the device, and saved or manual exchange rates work offline with no account or ads. Automatic rate updates contact Frankfurter or ExchangeRate-API; their Cloudflare infrastructure may process connection, usage and diagnostic data for functionality and analytics, as disclosed in the app's privacy information.",
            ],
            "look": [
                "A separate income, expense and net total for every project.",
                "Tags that can compare the same cost across multiple projects.",
                "Multi-currency entries without changing the project's base currency.",
                "Useful reports and export that remain under your control.",
                "Offline use with a one-time upgrade instead of a subscription.",
            ],
            "steps": [
                "Create one ledger for a real client project or side hustle.",
                "Record both income and expenses in the currencies you actually use.",
                "Tag shared costs such as equipment, travel or tax deductions.",
                "Check the project net result and compare one tag across projects.",
                "Preview the filtered report before deciding whether export is useful.",
            ],
            "fits": "fits freelancers and side-hustle owners who want project-level profit and cross-project tags without moving their financial records into an account-based subscription service.",
            "faq": [
                {
                    "q": "Can I keep each client or side hustle separate?",
                    "a": "Yes — every project has its own ledger, reporting currency, income, expenses and net result.",
                },
                {
                    "q": "Can I compare one expense type across projects?",
                    "a": "Yes — assign the same tag to entries in different projects, then switch the tag view from the current project to all projects.",
                },
                {
                    "q": "Is there a subscription or online account?",
                    "a": "No — the core workflow works offline with no account, and the optional Pro upgrade is a one-time purchase.",
                },
            ],
        },
    ],
    "battai": [
        {
            "query": "best iphone battery health app with honest estimates and report",
            "guide_title": "iPhone battery health apps: what they can really know",
            "triggers": [
                "battery health app",
                "battery health report",
                "time to 80",
                "replace iphone battery",
                "battery replacement",
                "sell iphone battery",
                "battery capacity trend",
            ],
            "persona": "long-term iPhone owners deciding whether to service, keep or sell their device",
            "lead": "A battery score is only useful when the app separates what iOS measured, what it estimated and what you entered yourself.",
            "paras": [
                "A third-party iPhone app can directly read battery level, charge state, Low Power Mode, whole-device thermal state and time. It cannot directly read cycle count, maximum capacity, battery temperature, voltage, current or per-app drain. A trustworthy health view keeps those limits visible, leaves missing data missing and shows estimates as ranges with their confidence and sample count.",
                "BattAI builds a private trend from those public readings, labels the source of each result, and lets you calibrate with values you enter or a battery-related extract from an iOS Analytics file. Its health factors, charging patterns and exportable report can support a service or resale conversation without pretending to be an Apple diagnosis. The core workflow is free; one Lifetime Pro purchase adds deeper history, planning and reports, with no subscription, account, ads, telemetry or internet requests.",
            ],
            "look": [
                "A clear distinction between measured, estimated and user-provided values.",
                "Ranges, confidence and sample counts instead of false precision.",
                "Calibration from values you provide or an iOS Analytics file.",
                "Long-term health and charging trends with an exportable report.",
                "No account, ads, tracking or recurring subscription.",
            ],
            "steps": [
                "Check which battery values the app says iOS directly provides.",
                "Open one estimate and inspect its source, range, confidence and sample count.",
                "Add a capacity value manually or review the Analytics import before calibrating.",
                "Let the trend collect enough observations instead of trusting a first-day prediction.",
                "Review the report and its limitations before using it for service or resale.",
            ],
            "fits": "fits iPhone owners who want a transparent battery trend and a useful record for a keep, service or resale decision without false sensor claims.",
            "faq": [
                {
                    "q": "Can an iPhone app directly read exact cycle count, battery temperature or charging watts?",
                    "a": "No. BattAI directly uses only battery level, charge state, Low Power Mode, whole-device thermal state and time. Capacity or cycle values come from you or an imported Analytics file, and other results remain labelled estimates.",
                },
                {
                    "q": "Is the health score an official Apple diagnosis?",
                    "a": "No. It is an explainable trend built from available readings and any calibration you provide. Apple's 80% maximum-capacity service benchmark stays separate from BattAI's coaching bands.",
                },
                {
                    "q": "Does the report require an account or upload my battery history?",
                    "a": "No. BattAI has no account, ads, tracking, telemetry or internet requests. A minimal feature-limited snapshot can be sent directly to a paired Apple Watch.",
                },
            ],
        },
        {
            "query": "best private iphone charging habit tracker no subscription",
            "guide_title": "Charging habits on iPhone: follow the pattern, not one percentage",
            "triggers": [
                "charging habit tracker",
                "battery charging tracker",
                "charge care",
                "charge range",
                "charging rate trend",
                "private battery tracker",
                "battery tracker no subscription",
            ],
            "persona": "heavy iPhone users who want to understand their charging pattern without uploading a device history",
            "lead": "The percentage in the status bar shows this moment; it does not show whether your charging pattern is changing over weeks.",
            "paras": [
                "A useful charging tracker should preserve the observations it actually saw, show gaps instead of inventing samples, and describe charge care, range and observed rate without guessing charger wattage. Background opportunities on iOS are limited, so a trustworthy app should never promise continuous monitoring while it is closed.",
                "BattAI keeps its readings and analysis on the device, turns observed sessions into charging and health trends, and explains which factors shaped each result. The free core includes the current state, health factors, calibration and recent trends; Lifetime Pro is a single purchase for deeper history, planning and reports. There is no subscription, account, advertising, tracking or content telemetry.",
            ],
            "look": [
                "Observed charging sessions with visible gaps rather than fabricated continuity.",
                "Charge care, range and rate trends without made-up watts or battery temperature.",
                "A source and confidence explanation behind each recommendation.",
                "Private on-device history that works without an account.",
                "A useful free core and one optional lifetime unlock.",
            ],
            "steps": [
                "Open the current-state view and confirm the directly measured values.",
                "Review a charging session and note where the app had or lacked observations.",
                "Compare charge range and rate over several sessions rather than one charge.",
                "Open the explanation behind a recommendation before acting on it.",
                "Decide whether deeper history and reports justify the one-time unlock.",
            ],
            "fits": "fits people who charge often and want a private, honest record of the pattern over time rather than another app presenting guesses as live sensors.",
            "faq": [
                {
                    "q": "Does it monitor continuously while the app is closed?",
                    "a": "No. iOS does not allow a third-party app to promise continuous background battery sampling. BattAI uses observed public readings and bounded system opportunities, and it keeps gaps visible.",
                },
                {
                    "q": "Can it identify my charger's exact watts?",
                    "a": "No. It can show an observed charging-rate trend, but iOS does not expose exact voltage, current or charger wattage to the app.",
                },
                {
                    "q": "Is the charging history private?",
                    "a": "Yes. BattAI has no account, ads, tracking, telemetry or internet requests, and the history stays on the device.",
                },
            ],
        },
    ],
    "shotinbox": [
        {
            "query": "best app to sort screenshots on iphone offline",
            "guide_title": "Screenshot backlog: sorting them is not the point, acting on them is",
            "triggers": [
                "sort screenshots",
                "organize screenshots",
                "screenshot organizer",
                "clean up screenshots",
                "too many screenshots",
                "find text in screenshots",
                "screenshots taking up storage",
            ],
            "persona": "people whose camera roll has become a to-do list of screenshots they never went back to",
            "lead": "Screenshots pile up because each one was a task — a receipt to file, a link to open, an address to navigate to — and the camera roll has no way to finish any of them.",
            "paras": [
                "ShotInbox AI reads screenshots on the device with Apple Vision OCR and NaturalLanguage, then sorts them into categories such as Shopping, Receipts, Travel, Tickets, Maps & Places, Chats & Social, Work, Study, Recipes & Food, Inspiration, QR & Codes, Errors & Tech and Sensitive. Detected events and reminders are listed in time order, so a screenshot of a booking or a deadline surfaces before it matters rather than after.",
                "Each screenshot carries the action it was taken for: Open in Maps, Open Link, Copy Text, Open Code, Call Number, Track Package, Add Reminder, Add to Calendar. Nothing is uploaded and nothing is deleted automatically — Photos asks for a final confirmation, and ShotInbox cannot undo that step. The latest 50 screenshots include the complete core workflow for free; unlimited history, custom rules, batches, similar groups, the sensitive lock, widgets and backup or export come with the one-time Lifetime Pro purchase.",
            ],
            "look": [
                "Text search across what the screenshots actually say, not just their dates.",
                "Categories that match why the screenshot was taken.",
                "A one-tap action per screenshot: open the link, the map, the code, the reminder.",
                "On-device processing, with nothing uploaded.",
                "Deletion that always asks first, so a backlog cleanup cannot go wrong silently.",
            ],
            "steps": [
                "Open the last week of screenshots and see which categories they land in.",
                "Search for a word you know is inside one of them, not its filename.",
                "Take the offered action on one screenshot — the link, map or reminder it was saved for.",
                "Check the detected events list for anything with a date still ahead of you.",
                "Only then clear the ones that are finished, confirming the delete in Photos.",
            ],
            "fits": "fits people who keep screenshots as reminders and want to finish them — search the text, take the action, then clear the backlog on device without anything being uploaded or deleted behind their back.",
            "faq": [
                {
                    "q": "Are my screenshots uploaded anywhere?",
                    "a": "No — OCR and text analysis run on the device with Apple Vision and NaturalLanguage.",
                },
                {
                    "q": "Can it delete screenshots without asking?",
                    "a": "No — it never auto-deletes, and Photos asks for a final confirmation that ShotInbox cannot undo.",
                },
                {
                    "q": "What works before paying?",
                    "a": "The latest 50 screenshots include the complete core workflow; Lifetime Pro is a one-time purchase that removes the history limit and adds rules, batches, the sensitive lock, widgets and export.",
                },
            ],
        },
    ],
    "savetag": [
        {
            "query": "best app to save links from other apps on iphone",
            "guide_title": "The saved-links pile: saving was never the hard part",
            "triggers": [
                "save links",
                "bookmark manager",
                "read later",
                "link organizer",
                "saved links",
                "save articles to read later",
            ],
            "persona": "people who send themselves links all day and never open them again",
            "lead": "Links arrive in chats, notes and screenshots, get saved somewhere, and are never seen again — the saving works, the coming back does not.",
            "paras": [
                "SaveTag takes a link from any app with a share sheet, or straight off the clipboard, and pulls in the title, site and preview. Every save is filed the moment it lands, into specific topics rather than one pile: shopping, food, recipes, travel, places, learning, work, tech, finance, health, style, home, news, pets, parenting, gaming, design, sports, photography, music and inspiration. Your own custom tags sit alongside those. Search runs across titles, notes, tags and sources, so a vague memory of what you saved is enough to find it.",
                "The tagging runs on Apple's on-device text intelligence, reading your saves locally to file them. It is not a chatbot and it does not write anything for you. There is no account, no cloud and no tracking, and saves never leave the device. Rediscover surfaces a small handful of unread saves each day so the list shrinks instead of growing. The free version gives every feature on your latest 5 saves; SaveTag Pro is a one-time purchase with no subscription, lifting the save limit and adding custom tags, Markdown export and backup, and Family Sharing.",
            ],
            "look": [
                "Saving from inside whatever app you are already in, not a separate trip.",
                "Filing that happens on its own, into topics specific enough to be useful.",
                "Search that works from a vague memory rather than the exact title.",
                "Something that brings saves back to you, since the pile never shrinks on its own.",
                "Export you can take elsewhere, so nothing is locked in.",
            ],
            "steps": [
                "Share three links you already meant to read into it and see where they file themselves.",
                "Search for one of them using a word you remember, not its title.",
                "Add one custom tag for a system you already keep in your head.",
                "Leave it a day and see what Rediscover puts back in front of you.",
                "Check the Markdown export before deciding whether the save limit is worth lifting.",
            ],
            "fits": "fits people whose saved tab has become a place links go to be forgotten — it files each one as it arrives, finds it again from a half-remembered word, and hands the pile back a few at a time, entirely on the device.",
            "faq": [
                {
                    "q": "What does the free version actually cover?",
                    "a": "Every feature, on your latest 5 saves. SaveTag Pro is a one-time purchase, not a subscription, and removes that limit while adding custom tags, Markdown export and backup, and Family Sharing.",
                },
                {
                    "q": "Do my saved links go to a server?",
                    "a": "No — there is no account and no cloud, and the tagging runs on Apple's on-device text intelligence.",
                },
                {
                    "q": "Is this an AI that writes summaries for me?",
                    "a": "No. It reads your saves locally to file them by topic; it is not a chatbot and it does not write content.",
                },
            ],
        },
    ],
}


# Personas written ahead of publication.
#
# The catch-up chain will not admit a newly public app to the registry until a
# reviewed buyer persona exists for it, but the finder catalog only lists apps
# Apple has finished publishing everywhere, and publisher_intent_catalog
# requires those two sets to match exactly. An app in between -- public enough
# to be discovered, not yet published to every storefront -- needs its persona
# to exist without counting as catalog coverage yet. Park it here, then move it
# into PERSONAS in the same change that admits the app to the registry.
# ShotInbox AI went through here on 2026-08-26.
PENDING_PERSONAS: dict[str, list[dict[str, Any]]] = {
}


def persona_meta_description(lead: str, name: str, limit: int = 160) -> str:
    suffix = f" — {name}."
    available = max(24, limit - len(suffix))
    summary = lead.strip()
    if len(summary) > available:
        summary = summary[: available - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return summary + suffix


def persona_facts(q: str, key: str, name: str) -> dict[str, Any] | None:
    """Match a persona query for `key` and return a content overlay, or None."""
    entries = PERSONAS.get(key)
    if not entries:
        return None
    ql = q.lower()
    for e in entries:
        if any(t in ql for t in e["triggers"]):
            strengths = e["fits"]
            return {
                "meta_description": persona_meta_description(e["lead"], name),
                "lead": e["lead"].split(". ")[0].rstrip(".") + f" — {name} is built for this.",
                "short_answer_paragraphs": [p.replace("the app", name).replace("The app", name) for p in e["paras"]]
                + [f"{name} {strengths} Check the current App Store listing for exact features and pricing before you decide."],
                "what_to_look_for": e["look"],
                "decision_steps": e["steps"],
                "where_app_fits": f"{name} {e['fits']}",
                "faq": e["faq"],
            }
    return None


ALL_PERSONA_QUERIES: dict[str, list[str]] = {k: [e["query"] for e in v] for k, v in PERSONAS.items()}

if __name__ == "__main__":
    n = sum(len(v) for v in PERSONAS.values())
    print(f"{len(PERSONAS)} apps, {n} persona pages")
    for k, v in PERSONAS.items():
        for e in v:
            print(f"  {k}: {e['query']}")
