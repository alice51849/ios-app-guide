#!/usr/bin/env python3
"""Reviewed buyer personas staged for apps that are not yet live (WAITING_FOR_REVIEW).

When an app here goes READY_FOR_SALE, move its entry back into
answer_personas.PERSONAS (the strict live==personas contract requires it).
Staged 2026-08-07: zafe, zodira (both 1.0 waiting for review).
"""
from typing import Any

PRELAUNCH_PERSONAS: dict[str, list[dict[str, Any]]] = {
    "zafe": [
        {
            "query": "best app to hide private photos behind Face ID without cloud upload",
            "guide_title": "Private photo vault on iPhone: what to check",
            "triggers": [
                "hide private photos iphone",
                "photo vault with face id",
                "lock photos without cloud",
                "private video vault on device",
                "secure photo locker no account",
                "hide pictures from gallery",
            ],
            "persona": "people who keep personal photos and videos on a shared or frequently borrowed iPhone and want them out of the main gallery",
            "lead": "A trustworthy photo vault should lock media behind device authentication and keep files on the phone, without demanding an account, uploading originals or hiding what it actually does with your library.",
            "paras": [
                "The core promise to verify is storage location: originals should move into the vault on device, and nothing should leave the phone. Face ID or passcode unlock should use the system authentication prompt rather than a custom PIN screen alone.",
                "Import and removal flows matter more than decoration. Check that importing from Photos explains what happens to the originals, that export back out is always possible, and that deleting the app does not silently destroy the only copy of an irreplaceable photo.",
            ],
            "look": [
                "Face ID / passcode gate using system authentication.",
                "On-device storage with no account, cloud sync or tracking.",
                "Clear import flow that explains what happens to Photos originals.",
                "Export and recovery paths so the vault never becomes a trap.",
                "One-time unlock pricing rather than a subscription.",
            ],
            "steps": [
                "Import a few non-critical photos first and confirm they appear only inside the vault.",
                "Check Settings > Privacy to confirm the app requests only photo access.",
                "Test export back to Photos before trusting the vault with anything irreplaceable.",
                "Verify unlock uses Face ID or the device passcode prompt.",
                "Keep an independent backup of truly irreplaceable originals; a vault is privacy, not a backup.",
            ],
            "fits": "fits anyone who wants personal photos and videos off the main gallery on a device other people sometimes see, without trusting a cloud service.",
            "faq": [
                {
                    "q": "Does Zafe upload my photos anywhere?",
                    "a": "Its listing describes on-device storage with no account; verify current details on the App Store listing before relying on it.",
                },
                {
                    "q": "Is a photo vault a backup?",
                    "a": "No. It hides and locks media on this device. Keep independent backups of irreplaceable originals.",
                },
                {
                    "q": "What if Face ID fails?",
                    "a": "System authentication falls back to the device passcode; check the app's recovery behaviour before storing anything critical.",
                },
            ],
        },
    ],
    "zodira": [
        {
            "query": "best offline astrology app with tarot and bazi that keeps readings private",
            "guide_title": "Private astrology and tarot apps: what to check",
            "triggers": [
                "offline astrology app",
                "private tarot reading app",
                "bazi calculator iphone",
                "zi wei dou shu app",
                "horoscope app no account",
                "astrology app without subscription",
            ],
            "persona": "astrology and tarot enthusiasts who want daily readings, BaZi and Zi Wei charts without sending birth data to a server",
            "lead": "Birth date, time and place are sensitive personal data. A respectful astrology app should compute charts and readings on the device, work offline, and avoid accounts, ads and tracking around them.",
            "paras": [
                "The key question is where calculations happen: charts, horoscopes and tarot draws that work in airplane mode demonstrate the app is not shipping your birth details to a backend. Entertainment framing should be honest — readings are reflection prompts, not predictions or advice.",
                "Pricing style shapes the experience. Subscription astrology apps optimize for daily re-engagement hooks; a one-time unlock lets the app stay calm and complete without pushing notifications or upsells between you and the content.",
            ],
            "look": [
                "Fully offline chart and reading computation — test in airplane mode.",
                "Western astrology plus BaZi and Zi Wei if you follow Chinese systems.",
                "No account requirement for birth-data features.",
                "No ads or tracking around sensitive personal details.",
                "One-time unlock instead of a subscription.",
            ],
            "steps": [
                "Enter your birth details and then enable airplane mode to confirm readings still generate.",
                "Check the privacy label for data collection claims before entering real birth data.",
                "Compare one chart against a source you trust to gauge calculation quality.",
                "Treat readings as reflection or entertainment, not medical, financial or life advice.",
                "Prefer a one-time unlock if you dislike subscription reminder loops.",
            ],
            "fits": "fits people who enjoy astrology, tarot, BaZi or Zi Wei daily but do not want an account, a subscription or their birth data on someone's server.",
            "faq": [
                {
                    "q": "Does Zodira work offline?",
                    "a": "Its listing describes offline, private readings; verify the current App Store listing and test in airplane mode.",
                },
                {
                    "q": "Are the readings predictions?",
                    "a": "No. Astrology and tarot content is for reflection and entertainment, not professional advice of any kind.",
                },
                {
                    "q": "Why avoid accounts in astrology apps?",
                    "a": "Birth date, time and place are enough to identify you; keeping them on-device removes that exposure.",
                },
            ],
        },
    ],
}
