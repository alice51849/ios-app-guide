#!/usr/bin/env python3
import unittest

import owner_decisions as od


def doc():
    return {"owner_actions": [{"id": "a", "title": "x", "status": "todo"},
                              {"id": "b", "title": "y", "status": "todo"},
                              {"id": "c", "title": "z", "status": "done", "done_at": "2026-10-01T00:00:00Z"}]}


class ApplyTest(unittest.TestCase):
    def test_three_buttons(self):
        d = doc()
        changed = od.apply(d, {"a": {"decision": "done", "at": "2026-10-15T00:55:33.018Z"},
                               "b": {"decision": "ai", "at": "2026-10-15T01:00:00.000Z"}})
        a, b, c = d["owner_actions"]
        self.assertEqual(("done", "2026-10-15T00:55:33Z", "done"), (a["status"], a["done_at"], a["resolution"]))
        self.assertEqual(("in_progress", "ai"), (b["status"], b["resolution"]))
        self.assertNotIn("resolution", c)
        self.assertEqual(["a", "b"], changed)

    def test_declined_closes_and_reopen_restores(self):
        d = doc()
        od.apply(d, {"a": {"decision": "declined", "at": "2026-10-15T00:00:00Z"}})
        self.assertEqual(("done", "declined"), (d["owner_actions"][0]["status"], d["owner_actions"][0]["resolution"]))
        self.assertEqual(["a"], od.apply(d, {}))
        self.assertEqual({"id": "a", "title": "x", "status": "todo"}, d["owner_actions"][0])

    def test_rows_closed_by_hand_are_left_alone(self):
        d = doc()
        self.assertEqual([], od.apply(d, {}))
        self.assertEqual("done", d["owner_actions"][2]["status"])

    def test_unchanged_decision_reports_nothing(self):
        d = doc()
        dec = {"a": {"decision": "done", "at": "2026-10-15T00:00:00Z"}}
        od.apply(d, dec)
        self.assertEqual([], od.apply(d, dec))


if __name__ == "__main__":
    unittest.main()
