"""General price rule: print a storefront price only when a live readback agrees.

Covers 11-25 ruling 1707 item 8 (b): a stale snapshot, a missing or
disagreeing readback, or an unconfirmed zero price must print no price
(and never "Free"), for every app alike.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import app_store_storefronts as stores  # noqa: E402
import refresh_storefront_availability as refresher  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


NOW = dt.datetime(2026, 11, 25, 12, 0, tzinfo=dt.timezone.utc)
CHECKED = "2026-11-25T09:16:02Z"
OLD_ZERO = "2026-11-20T00:00:00Z"
PAID = {"price": "90", "currency": "TWD", "formatted_price": "$90.00"}
FREE = {"price": "0", "currency": "TWD", "formatted_price": "免費"}
RB_PAID = {"price_readback": "90", "currency_readback": "TWD"}
RB_ZERO = {"price_readback": "0", "currency_readback": "TWD"}


def _write(directory, details, checked_at, paid_seen=None) -> None:
    payload: dict[str, object] = {"version": 2, "details": details}
    if checked_at is not None:
        payload["checked_at"] = checked_at
    if paid_seen is not None:
        payload["paid_seen"] = paid_seen
    (Path(directory) / stores.STATE_FILE).write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _load(details, checked_at=CHECKED, paid_seen=None):
    with tempfile.TemporaryDirectory() as directory:
        _write(directory, details, checked_at, paid_seen)
        return stores.load_storefront_details(directory, now=NOW)


class PriceReadbackRuleTests(unittest.TestCase):
    def test_confirmed_paid_price_is_printed_without_readback_fields(self):
        loaded = _load({"tw": {"111": {**PAID, **RB_PAID}}})
        self.assertEqual(PAID, loaded["tw"]["111"])

    def test_missing_readback_prints_no_price(self):
        self.assertEqual({}, _load({"tw": {"111": dict(PAID)}})["tw"])

    def test_disagreeing_readback_prints_no_price(self):
        self.assertEqual({}, _load({"tw": {"111": {**PAID, **RB_ZERO}}})["tw"])

    def test_readback_in_another_currency_prints_no_price(self):
        detail = {**PAID, "price_readback": "90", "currency_readback": "USD"}
        self.assertEqual({}, _load({"tw": {"111": detail}})["tw"])

    def test_zero_without_zero_since_is_not_free(self):
        self.assertEqual({}, _load({"tw": {"111": {**FREE, **RB_ZERO}}})["tw"])

    def test_zero_confirmed_for_less_than_twelve_hours_is_not_free(self):
        detail = {**FREE, **RB_ZERO, "zero_since": "2026-11-25T00:00:00Z"}
        self.assertEqual({}, _load({"tw": {"111": detail}})["tw"])

    def test_zero_confirmed_for_twelve_hours_is_free(self):
        detail = {**FREE, **RB_ZERO, "zero_since": OLD_ZERO}
        loaded = _load({"tw": {"111": detail}})
        self.assertEqual(FREE, loaded["tw"]["111"])
        localized = stores.localized_storefront_detail(
            loaded["tw"]["111"], "zh-Hant"
        )
        self.assertEqual(
            stores.FREE_LABELS["zh-Hant"], localized["formatted_price"]
        )

    def test_once_paid_listing_is_never_free(self):
        detail = {**FREE, **RB_ZERO, "zero_since": OLD_ZERO}
        loaded = _load({"tw": {"111": detail}}, paid_seen={"tw": ["111"]})
        self.assertEqual({}, loaded["tw"])
        # Paid in any other storefront also blocks "Free" here.
        loaded = _load({"tw": {"111": detail}}, paid_seen={"us": ["111"]})
        self.assertEqual({}, loaded["tw"])
        loaded = _load({"tw": {"111": detail}}, paid_seen={"us": ["222"]})
        self.assertEqual(FREE, loaded["tw"]["111"])

    def test_unnormalized_zero_is_treated_as_zero(self):
        detail = {**FREE, "price": "0.00", "price_readback": "0.00",
                  "currency_readback": "TWD"}
        self.assertEqual({}, _load({"tw": {"111": detail}})["tw"])

    def test_stale_missing_or_future_checked_at_prints_no_prices(self):
        details = {"tw": {"111": {**PAID, **RB_PAID}}}
        for checked_at in (
            "2026-11-23T14:58:26Z",  # older than 36 hours
            None,
            "not-a-date",
            "2026-11-25T09:16:02",  # no timezone
            "2026-11-26T12:00:00Z",  # in the future
        ):
            with self.subTest(checked_at=checked_at):
                self.assertEqual({}, _load(details, checked_at))

    def test_naive_now_is_read_as_utc(self):
        with tempfile.TemporaryDirectory() as directory:
            _write(directory, {"tw": {"111": {**PAID, **RB_PAID}}}, CHECKED)
            loaded = stores.load_storefront_details(
                directory, now=NOW.replace(tzinfo=None)
            )
        self.assertEqual(PAID, loaded["tw"]["111"])

    def test_rule_is_not_an_app_id_special_case(self):
        for module in (stores, refresher):
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("6819061896", source)

    def test_raw_mode_keeps_unconfirmed_records_for_the_refresher(self):
        with tempfile.TemporaryDirectory() as directory:
            _write(directory, {"tw": {"111": {**FREE, **RB_ZERO}}},
                   "2020-01-01T00:00:00Z")
            raw = stores.load_storefront_details(directory, verified=False)
        self.assertEqual({**FREE, **RB_ZERO}, raw["tw"]["111"])


class RefreshWritesReadbackTests(unittest.TestCase):
    APP_KEY = "lumibopomofo"
    PAID_READ = [{"price": "90", "formatted": "$90.00"}]
    ZERO_READ = [{"price": "0", "formatted": "免費"}]
    START = dt.datetime(2026, 11, 25, 0, 0, tzinfo=dt.timezone.utc)

    def _refresh(self, directory, readings, *, at=None, missing=()):
        """One refresh; ``readings`` per lookup call (None = network error)."""
        app_id = str(APPSTORE[self.APP_KEY])
        calls: list[str] = []

        def lookup(ids, country):
            index = calls.count(country)
            calls.append(country)
            reading = readings[min(index, len(readings) - 1)]
            if reading is None or country in missing:
                raise RuntimeError("network down")
            return {
                str(value): {
                    "price": float(reading["price"]),
                    "currency": "TWD",
                    "formattedPrice": reading["formatted"],
                }
                for value in ids
            }

        patches = [
            mock.patch.object(
                refresher, "live_app_keys", return_value={self.APP_KEY}
            ),
            mock.patch.object(
                refresher, "_lookup_country_records", side_effect=lookup
            ),
        ]
        if at is not None:
            patches.append(
                mock.patch.object(refresher, "_utc_now", return_value=at)
            )
        for patch in patches:
            patch.start()
        try:
            refresher.refresh(directory, force=True)
        finally:
            for patch in reversed(patches):
                patch.stop()
        payload = json.loads(
            (Path(directory) / stores.STATE_FILE).read_text(encoding="utf-8")
        )
        now = at or dt.datetime.now(dt.timezone.utc)
        loaded = stores.load_storefront_details(directory, now=now)
        return app_id, payload, loaded

    def test_paid_then_persistent_zero_never_republishes_free(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, _, loaded = self._refresh(
                directory, self.PAID_READ, at=self.START
            )
            self.assertEqual("90", loaded["tw"][app_id]["price"])
            # Paid, then zero every day for four days: never "Free".
            for day in range(1, 5):
                _, payload, loaded = self._refresh(
                    directory, self.ZERO_READ,
                    at=self.START + dt.timedelta(days=day),
                )
                self.assertNotIn(app_id, loaded["tw"])
        self.assertIn(app_id, payload["paid_seen"]["tw"])
        self.assertEqual(
            "0", payload["details"]["tw"][app_id]["price_readback"]
        )

    def test_paid_history_survives_a_missing_storefront(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, _, _ = self._refresh(
                directory, self.PAID_READ, at=self.START
            )
            state = Path(directory) / stores.STATE_FILE
            # The record vanishes (storefront skipped with no cache).
            state.write_text(
                json.dumps({
                    **json.loads(state.read_text(encoding="utf-8")),
                    "countries": {},
                    "details": {},
                }),
                encoding="utf-8",
            )
            _, payload, _ = self._refresh(
                directory, self.ZERO_READ,
                at=self.START + dt.timedelta(days=1), missing=("tw",),
            )
            self.assertIn(app_id, payload["paid_seen"]["tw"])
            for day in (2, 3):
                _, payload, loaded = self._refresh(
                    directory, self.ZERO_READ,
                    at=self.START + dt.timedelta(days=day),
                )
                self.assertNotIn(app_id, loaded["tw"])

    def test_back_to_back_forced_refreshes_cannot_confirm_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            for minutes in (0, 5, 10):
                app_id, payload, loaded = self._refresh(
                    directory, self.ZERO_READ,
                    at=self.START + dt.timedelta(minutes=minutes),
                )
                self.assertNotIn(app_id, loaded["tw"])
            self.assertEqual(
                "2026-11-25T00:00:00Z",
                payload["details"]["tw"][app_id]["zero_since"],
            )

    def test_free_app_is_free_after_twelve_hours_of_confirmed_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, _, first = self._refresh(
                directory, self.ZERO_READ, at=self.START
            )
            self.assertNotIn(app_id, first["tw"])
            _, _, second = self._refresh(
                directory, self.ZERO_READ,
                at=self.START + dt.timedelta(hours=13),
            )
        self.assertEqual("0", second["tw"][app_id]["price"])

    def _fresh_payload(self, detail, *, checked, paid_seen=None):
        app_id = str(APPSTORE[self.APP_KEY])
        payload = {
            "version": 2,
            "checked_at": checked.isoformat().replace("+00:00", "Z"),
            "app_count": 1,
            "app_ids": [app_id],
            "storefronts": sorted(stores.AVAILABILITY_STOREFRONTS),
            "countries": {"tw": [app_id]},
            "details": {"tw": {app_id: detail}},
        }
        if paid_seen is not None:
            payload["paid_seen"] = paid_seen
        return app_id, payload

    def test_unconfirmed_zero_is_refetched_once_twelve_hours_pass(self):
        # 11-27: a snapshot that starts a zero chain cannot confirm it, so
        # waiting out MAX_AGE (20h) kept every free listing unprinted for 20h
        # instead of the rule's 12h.  The refresher re-fetches as soon as a
        # re-fetch could confirm it; before that the snapshot stays fresh.
        zero_since = self.START.isoformat().replace("+00:00", "Z")
        detail = {**FREE, **RB_ZERO, "zero_since": zero_since}
        app_id, payload = self._fresh_payload(detail, checked=self.START)
        ids = {app_id}
        self.assertTrue(refresher._is_fresh(
            payload, self.START + dt.timedelta(hours=11, minutes=59), ids
        ))
        self.assertFalse(refresher._is_fresh(
            payload, self.START + dt.timedelta(hours=12), ids
        ))

    def test_confirmed_or_once_paid_zero_never_forces_a_refetch(self):
        zero_since = self.START.isoformat().replace("+00:00", "Z")
        detail = {**FREE, **RB_ZERO, "zero_since": zero_since}
        later = self.START + dt.timedelta(hours=13)
        # Already confirmed in this snapshot: nothing to gain.
        app_id, payload = self._fresh_payload(detail, checked=later)
        self.assertTrue(refresher._is_fresh(
            payload, later + dt.timedelta(hours=6), {app_id}
        ))
        # Once seen paid: never printed "Free", so no refresh loop.
        app_id, payload = self._fresh_payload(
            detail, checked=self.START, paid_seen={"tw": [app_id]}
        )
        self.assertTrue(refresher._is_fresh(payload, later, {app_id}))
        # Zero without a matching readback: not a confirmable chain.
        app_id, payload = self._fresh_payload(
            {**FREE, **RB_PAID, "zero_since": zero_since}, checked=self.START
        )
        self.assertTrue(refresher._is_fresh(payload, later, {app_id}))

    def test_availability_only_storefront_zero_never_forces_a_refetch(self):
        # hk/mo are queried for availability but are not in
        # LOCALE_STOREFRONTS: their zero_since restarts on every refresh, so
        # they must never make a refresh due (that would loop every 12h).
        extra = sorted(
            set(stores.AVAILABILITY_STOREFRONTS)
            - set(stores.LOCALE_STOREFRONTS.values())
        )
        self.assertTrue(extra)
        zero_since = self.START.isoformat().replace("+00:00", "Z")
        later = self.START + dt.timedelta(hours=13)
        for country in extra:
            app_id, payload = self._fresh_payload(
                {**FREE, **RB_ZERO, "zero_since": zero_since},
                checked=self.START,
            )
            payload["countries"] = {country: [app_id]}
            payload["details"] = {
                country: payload["details"]["tw"]
            }
            with self.subTest(country=country):
                self.assertTrue(
                    refresher._is_fresh(payload, later, {app_id})
                )

    def test_two_due_refreshes_in_a_row_leave_a_fresh_snapshot(self):
        app_id = str(APPSTORE[self.APP_KEY])

        def lookup(ids, country):
            return {
                str(value): {
                    "price": 0.0,
                    "currency": "TWD",
                    "formattedPrice": "免費",
                }
                for value in ids
            }

        with tempfile.TemporaryDirectory() as directory:
            for hours in (0, 12):
                at = self.START + dt.timedelta(hours=hours)
                with mock.patch.object(
                    refresher, "live_app_keys", return_value={self.APP_KEY}
                ), mock.patch.object(
                    refresher, "_utc_now", return_value=at
                ), mock.patch.object(
                    refresher, "_lookup_country_records", side_effect=lookup
                ):
                    refresher.refresh(directory, force=hours == 0)
            payload = json.loads(
                (Path(directory) / stores.STATE_FILE).read_text(
                    encoding="utf-8"
                )
            )
        ids = {app_id}
        second = self.START + dt.timedelta(hours=12)
        self.assertEqual(
            second.isoformat().replace("+00:00", "Z"), payload["checked_at"]
        )
        # Every storefront (hk/mo included) read zero both times; after the
        # second (due) refresh only MAX_AGE may make the snapshot stale.
        for hours in (1, 12, 13, 19):
            self.assertTrue(refresher._is_fresh(
                payload, second + dt.timedelta(hours=hours), ids
            ))
        self.assertFalse(refresher._is_fresh(
            payload, second + refresher.MAX_AGE, ids
        ))

    def test_due_refetch_confirms_zero_without_relaxing_the_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, _, first = self._refresh(
                directory, self.ZERO_READ, at=self.START
            )
            self.assertNotIn(app_id, first["tw"])
            # Unforced refresh 12h later: due, so it re-reads twice and
            # the 12h-old confirmed zero becomes printable.
            at = self.START + dt.timedelta(hours=12)
            with mock.patch.object(
                refresher, "live_app_keys", return_value={self.APP_KEY}
            ), mock.patch.object(
                refresher, "_utc_now", return_value=at
            ), mock.patch.object(
                refresher,
                "_lookup_country_records",
                side_effect=lambda ids, country: {
                    str(value): {
                        "price": 0.0,
                        "currency": "TWD",
                        "formattedPrice": "免費",
                    }
                    for value in ids
                },
            ) as lookup:
                refresher.refresh(directory)
            self.assertTrue(lookup.called)
            loaded = stores.load_storefront_details(directory, now=at)
        self.assertEqual("0", loaded["tw"][app_id]["price"])

    def test_disagreeing_second_pass_prints_no_price(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, payload, loaded = self._refresh(
                directory, [self.ZERO_READ[0], self.PAID_READ[0]]
            )
        detail = payload["details"]["tw"][app_id]
        self.assertEqual("90", detail["price_readback"])
        self.assertNotIn("zero_since", detail)
        self.assertNotIn(app_id, loaded["tw"])

    def test_failed_readback_prints_no_price(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, payload, loaded = self._refresh(
                directory, [self.PAID_READ[0], None]
            )
        self.assertNotIn("price_readback", payload["details"]["tw"][app_id])
        self.assertNotIn(app_id, loaded["tw"])

    def test_retained_cached_details_lose_their_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            app_id, _, _ = self._refresh(directory, self.PAID_READ)
            _, payload, loaded = self._refresh(directory, [None])
        self.assertNotIn("price_readback", payload["details"]["tw"][app_id])
        self.assertNotIn(app_id, loaded["tw"])


class GeneratorEndToEndTests(unittest.TestCase):
    """A wrong "Free" already on a page must be removed, not left behind."""

    KEY = "lumibopomofo"
    SITE = "https://example.com/guide"
    FREE_US = {
        "price": "0", "currency": "USD", "formatted_price": "Free",
        "price_readback": "0", "currency_readback": "USD",
        "zero_since": "2026-01-01T00:00:00Z",
    }

    def _state(self, detail, checked_at=None, paid_seen=False):
        app_id = str(APPSTORE[self.KEY])
        payload = {
            "version": 2,
            "checked_at": checked_at
            or dt.datetime.now(dt.timezone.utc).isoformat(),
            "countries": {"us": [app_id]},
            "details": {"us": {app_id: detail}},
        }
        if paid_seen:
            payload["paid_seen"] = {"us": [app_id]}
        return json.dumps(payload)

    def _bad_states(self):
        return {
            "stale snapshot": self._state(
                self.FREE_US, checked_at="2026-11-23T14:58:26Z"
            ),
            "once paid, now zero": self._state(self.FREE_US, paid_seen=True),
            "no readback": self._state(
                {"price": "0", "currency": "USD", "formatted_price": "Free"}
            ),
        }

    def test_facts_and_decision_card_source_drop_free(self):
        import gen_app_decision_cards as cards
        import gen_app_store_facts as facts
        from test_app_store_facts import _page

        app_id = str(APPSTORE[self.KEY])
        for label, bad_state in self._bad_states().items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                pages = Path(tmp)
                path = pages / "en-US" / f"{self.KEY}.html"
                path.parent.mkdir(parents=True)
                path.write_text(
                    _page(self.SITE, "en-US", self.KEY, app_id),
                    encoding="utf-8",
                )
                state_path = pages / stores.STATE_FILE
                # A previously published "Free" block is on the page.
                state_path.write_text(
                    self._state(self.FREE_US), encoding="utf-8"
                )
                facts.generate(
                    pages, live_keys={self.KEY}, locales=("en-US",),
                    site=self.SITE,
                )
                self.assertIn(">Free</data>", path.read_text(encoding="utf-8"))
                state_path.write_text(bad_state, encoding="utf-8")
                result = facts.generate(
                    pages, live_keys={self.KEY}, locales=("en-US",),
                    site=self.SITE,
                )
                source = path.read_text(encoding="utf-8")
                self.assertEqual(0, result["facts"])
                self.assertNotIn(facts.FACT_START, source)
                self.assertNotRegex(source, r"(?i)\bfree\b")
                # Decision cards read the facts block (run after facts).
                self.assertIsNone(cards._storefront_fact(source, False))

    def test_decision_card_must_run_after_facts_to_drop_free(self):
        import gen_app_decision_cards as cards
        import gen_app_store_facts as facts
        from test_app_store_facts import _page

        token = mock.patch.dict(
            os.environ, {"APP_STORE_PROVIDER_TOKEN": "123456789"}
        )
        token.start()
        self.addCleanup(token.stop)
        app_id = str(APPSTORE[self.KEY])
        availability = {"us": frozenset({app_id})}
        body = (
            "<main><h1>Lumi Bopomofo</h1>"
            '<p class="lead">Learn Zhuyin step by step.</p>'
            f'<a href="https://apps.apple.com/us/app/id{app_id}">App Store</a>'
            "</main>"
        )

        def card(source):
            content = cards._page_content(
                source, self.KEY, app_id, False, "en-US", availability
            )
            return cards.card_block(self.KEY, app_id, content)

        def run_facts(pages):
            facts.generate(
                pages, live_keys={self.KEY}, locales=("en-US",),
                site=self.SITE,
            )

        for label, bad_state in self._bad_states().items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                pages = Path(tmp)
                path = pages / "en-US" / f"{self.KEY}.html"
                path.parent.mkdir(parents=True)
                path.write_text(
                    _page(self.SITE, "en-US", self.KEY, app_id).replace(
                        "<main>Verified app</main>", body
                    ),
                    encoding="utf-8",
                )
                state_path = pages / stores.STATE_FILE
                state_path.write_text(
                    self._state(self.FREE_US), encoding="utf-8"
                )
                run_facts(pages)
                self.assertRegex(card(path.read_text()), r"\bFree\b")
                state_path.write_text(bad_state, encoding="utf-8")
                # Wrong order: cards built before facts still carry "Free".
                self.assertRegex(card(path.read_text()), r"\bFree\b")
                # Required order: facts first, then cards: "Free" is gone.
                run_facts(pages)
                rebuilt = card(path.read_text())
                self.assertNotRegex(rebuilt, r"(?i)\bfree\b")
                self.assertNotIn("<data", rebuilt)

    def test_webmcp_payload_drops_free(self):
        import gen_webmcp_install_tools as tools
        from test_webmcp_install_tools import _page, _payload

        token = mock.patch.dict(
            os.environ, {"APP_STORE_PROVIDER_TOKEN": "123456789"}
        )
        token.start()
        self.addCleanup(token.stop)
        for label, bad_state in self._bad_states().items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                pages = Path(tmp)
                path = pages / "en-US" / f"{self.KEY}.html"
                path.parent.mkdir(parents=True)
                path.write_text(
                    _page(self.SITE, "en-US", self.KEY, "Verified app"),
                    encoding="utf-8",
                )
                state_path = pages / stores.STATE_FILE
                state_path.write_text(
                    self._state(self.FREE_US), encoding="utf-8"
                )
                tools.generate(
                    pages, live_keys={self.KEY}, locales=("en-US",),
                    site=self.SITE,
                )
                self.assertIn(
                    "storefront_facts",
                    _payload(path.read_text(encoding="utf-8")),
                )
                state_path.write_text(bad_state, encoding="utf-8")
                tools.generate(
                    pages, live_keys={self.KEY}, locales=("en-US",),
                    site=self.SITE,
                )
                payload = _payload(path.read_text(encoding="utf-8"))
                self.assertNotIn("storefront_facts", payload)
                self.assertNotRegex(json.dumps(payload), r"(?i)\bfree\b")

    def test_social_preview_proof_drops_free(self):
        import gen_social_previews as previews

        app_id = str(APPSTORE[self.KEY])
        for label, bad_state in self._bad_states().items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / stores.STATE_FILE).write_text(
                    bad_state, encoding="utf-8"
                )
                detail = previews._storefront_detail(
                    app_id,
                    "en-US",
                    {"us": frozenset({app_id})},
                    stores.load_storefront_details(tmp),
                )
                self.assertIsNone(detail)
                self.assertEqual("", previews._storefront_proof(detail))


if __name__ == "__main__":
    unittest.main()
