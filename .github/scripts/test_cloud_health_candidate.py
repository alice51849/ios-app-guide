from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "_engine" / "cloud_health"
WORKFLOW = ROOT / ".github" / "workflow-candidates" / "cloud-health-daily.yml"
INTEGRATION = (
    ROOT / ".github" / "workflow-candidates" / "cloud-health-daily.integration.json"
)
V3_SHA = "339f48d201b11698c366836899f75d9bca125246abd80f1798be3dd458b7b03d"


class CloudHealthGuideCandidateTests(unittest.TestCase):
    def test_candidate_is_inactive_and_read_only(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        self.assertNotEqual(WORKFLOW.parent.name, "workflows")
        text = WORKFLOW.read_text()
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("upload-artifact", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("curl -X POST", text)
        self.assertIn("actions: read", text)
        self.assertIn("contents: read", text)

    def test_approved_fixture_digest_is_mirrored(self) -> None:
        fixture = ENGINE / "tests" / "fixtures" / "cloud-health-audit.v3.json"
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), V3_SHA)

    def test_integration_record_is_explicitly_inactive(self) -> None:
        value = json.loads(INTEGRATION.read_text())
        self.assertIs(value["active"], False)
        self.assertEqual(value["network_methods"], ["GET"])
        self.assertIs(value["model_used"], False)
        self.assertIs(value["dispatch_or_rerun"], False)
        self.assertEqual(
            value["growth_engine_candidate"],
            "3a57716f06d99457ffe5307944495a2293f2d763",
        )

    def test_mirror_config_is_exact46(self) -> None:
        config = json.loads((ENGINE / "config.json").read_text())
        keys = sorted(config["live_dates"])
        digest = hashlib.sha256(
            json.dumps(keys, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(len(keys), 46)
        self.assertEqual(
            digest,
            "3e2a4e8e85e7a30af7335028d8ed2d6bd05576847c168ddc26c5552941bf7b6e",
        )


if __name__ == "__main__":
    unittest.main()
