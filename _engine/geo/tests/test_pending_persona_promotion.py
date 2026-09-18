#!/usr/bin/env python3
"""Launch candidates: staged personas, catalog gate, promotion and honesty."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "geo", ROOT / "social"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import answer_personas  # noqa: E402
import catalog_audit  # noqa: E402

# key -> (App Store id, name catch-up derives from ASC: text before ":")
LAUNCH_CANDIDATES = {
    "dbhalo": ("6806826699", "dB Halo"),
    "qrcodehalo": ("6806779853", "QR Code Halo"),
    "ledmovingtext": ("6806639602", "LED Moving Text"),
    "countdaysnow": ("6807079789", "CountDaysNow"),
    "gbago": ("6804564400", "GBAGo"),
    "studydown": ("6807335593", "Studydown"),
}
FIELDS = {"query", "guide_title", "triggers", "persona", "lead", "paras",
          "look", "steps", "fits", "faq"}
# Claims the apps cannot back up (verified against each repository).
FORBIDDEN = {
    "dbhalo": ("free sound meter", "osha compliant", "osha-compliant",
               "class 1", "medical-grade", "diagnos", "hearing test"),
    "qrcodehalo": ("detects phishing", "blocks phishing", "protects you from",
                   "guarantee", "unlimited free", "reputation check"),
    "ledmovingtext": ("typefaces", "100 fonts", "hundred", "haptic",
                      "sound effect"),
    "countdaysnow": ("fully offline", "never leaves", "offline-only",
                     "standby", "every second"),
    "gbago": ("download roms", "free roms", "rewind", "remap", "keyboard",
              "time machine", "pokemon", "zelda", "mario", "game boy"),
    "studydown": ("proximity", "icloud", "in the background", "unlimited free",
                  "blocks apps", "screen time limit"),
}
REQUIRED = {
    "dbhalo": ("not a certified",),
    "qrcodehalo": ("three free successful scans", "does not look up link reputation"),
    "ledmovingtext": ("one saved board", "cannot go beyond"),
    "countdaysnow": ("three active events", "icloud"),
    "gbago": ("contains no games", "not affiliated with"),
    "studydown": ("five minutes of recorded time", "does not use screen time"),
}


def _copy(entries):
    return str(entries).lower()


class PendingPersonaTests(unittest.TestCase):
    def test_launch_candidates_are_staged_until_registered(self):
        registered = answer_personas._registered_auto_keys()
        for key in LAUNCH_CANDIDATES:
            with self.subTest(key=key):
                if key in registered:
                    self.assertIn(key, answer_personas.PERSONAS)
                    self.assertNotIn(key, answer_personas.PENDING_PERSONAS)
                else:
                    self.assertIn(key, answer_personas.PENDING_PERSONAS)
                    self.assertNotIn(key, answer_personas.PERSONAS)

    def test_entries_follow_the_persona_schema(self):
        staged = {**answer_personas.PERSONAS, **answer_personas.PENDING_PERSONAS}
        for key in LAUNCH_CANDIDATES:
            with self.subTest(key=key):
                entry = staged[key][0]
                self.assertEqual(FIELDS, set(entry))
                self.assertGreaterEqual(len(entry["triggers"]), 3)
                self.assertEqual(2, len(entry["paras"]))
                self.assertEqual(5, len(entry["look"]))
                self.assertEqual(5, len(entry["steps"]))
                self.assertGreaterEqual(len(entry["faq"]), 3)
                for item in entry["faq"]:
                    self.assertEqual({"q", "a"}, set(item))

    def test_catalog_audit_accepts_each_launch_candidate(self):
        registry = {}
        for key, (app_id, name) in LAUNCH_CANDIDATES.items():
            keywords = catalog_audit.persona_keywords(key, name)
            self.assertGreaterEqual(len(keywords), 3, key)
            registry[key] = {
                "appstore_id": app_id, "name": name,
                "keyword_source": "reviewed_persona", "keywords": keywords,
            }
        self.assertEqual(
            sorted(LAUNCH_CANDIDATES),
            catalog_audit.validate_registry(
                registry, strict_review_keys=set(LAUNCH_CANDIDATES)
            ),
        )

    def test_catalog_audit_still_blocks_an_app_without_a_persona(self):
        # Control group: the gate that held Zipbox for days must stay closed.
        registry = {"unreviewedapp": {
            "appstore_id": "6800000001", "name": "Unreviewed App",
            "keyword_source": "reviewed_persona",
            "keywords": ["alpha tool", "beta tool", "gamma tool"],
        }}
        with self.assertRaisesRegex(
            catalog_audit.CatalogAuditError, "persona is missing or incomplete"
        ):
            catalog_audit.validate_registry(registry)

    def test_registration_promotes_only_registered_candidates(self):
        pending = copy.deepcopy(answer_personas.PENDING_PERSONAS)
        personas = {"existing": [{"query": "q"}]}
        promoted = answer_personas.promote_registered_personas(
            pending, personas, frozenset({"gbago", "existing", "unrelated"})
        )
        self.assertEqual(["gbago"], promoted)
        self.assertIn("gbago", personas)
        self.assertNotIn("gbago", pending)
        self.assertEqual({"query": "q"}, personas["existing"][0])
        # Only the candidates that are still staged can stay staged: once a
        # candidate is registered in the automatic registry its persona is
        # promoted at import time and is no longer in PENDING_PERSONAS.
        staged = set(LAUNCH_CANDIDATES) & set(answer_personas.PENDING_PERSONAS)
        self.assertIn("gbago", staged)
        for key in staged - {"gbago"}:
            self.assertIn(key, pending)
        self.assertEqual([], answer_personas.promote_registered_personas(
            pending, personas, frozenset()
        ))

    def test_invalid_automatic_registry_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry_auto.json"
            self.assertEqual(frozenset(), answer_personas._registered_auto_keys(path))
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                answer_personas._registered_auto_keys(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                answer_personas._registered_auto_keys(path)

    def test_triggers_do_not_capture_other_personas(self):
        staged = {**answer_personas.PERSONAS, **answer_personas.PENDING_PERSONAS}
        phrases = {}
        for key, entries in staged.items():
            for entry in entries:
                for phrase in [*entry["triggers"], entry["query"]]:
                    phrases.setdefault(phrase.lower(), set()).add(key)
        for key in LAUNCH_CANDIDATES:
            for entry in staged[key]:
                for phrase in [*entry["triggers"], entry["query"]]:
                    phrase = phrase.lower()
                    for other, owners in phrases.items():
                        if owners == {key}:
                            continue
                        with self.subTest(key=key, phrase=phrase, other=other):
                            self.assertFalse(other in phrase or phrase in other)

    def test_copy_stays_within_verified_claims(self):
        staged = {**answer_personas.PERSONAS, **answer_personas.PENDING_PERSONAS}
        for key in LAUNCH_CANDIDATES:
            copy_text = _copy(staged[key])
            for claim in FORBIDDEN[key]:
                with self.subTest(key=key, forbidden=claim):
                    self.assertNotIn(claim, copy_text)
            for claim in REQUIRED[key]:
                with self.subTest(key=key, required=claim):
                    self.assertIn(claim, copy_text)


if __name__ == "__main__":
    unittest.main()
