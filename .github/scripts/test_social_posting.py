#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the social posting automations."""

import base64
import datetime as dt
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import devto_post
import portfolio_daily
import social_post_common as common
import telegram_post
import threads_post


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def http_error(status, body=b""):
    return urllib.error.HTTPError(
        "https://example.com/item",
        status,
        "error",
        {},
        io.BytesIO(body),
    )


def linkset_payload(*apps):
    root = {
        "anchor": f"{portfolio_daily.SITE_URL}/index.html",
        "item": [],
    }
    entries = [root]
    for slug, name, app_id in apps:
        guide_url = f"{portfolio_daily.SITE_URL}/guides/{slug}.html"
        root["item"].append(
            {
                "href": guide_url,
                "title*": [{"value": name, "language": "en"}],
            }
        )
        entries.append(
            {
                "anchor": guide_url,
                "related": [
                    {
                        "href": (
                            f"https://apps.apple.com/app/id{app_id}"
                            "?ct=iag_linkset"
                        )
                    }
                ],
            }
        )
    return {"linkset": entries}


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(HERE, "telegram_posts.json"), encoding="utf-8"
        ) as pool_file:
            json.load(pool_file)
        cls.pool = telegram_post.load_pool()

    def _at(self, day, hour):
        return dt.datetime(2026, 1, 1, hour, tzinfo=dt.timezone.utc) + dt.timedelta(
            days=day
        )

    def test_every_route_completes_its_full_daily_cycle(self):
        routes = (
            (telegram_post.pick, 1, telegram_post.TZ_LANGS["asia"]),
            (telegram_post.pick, 9, telegram_post.TZ_LANGS["eu_me"]),
            (telegram_post.pick, 15, telegram_post.TZ_LANGS["americas"]),
            (threads_post.pick, 3, threads_post.TZ_LANGS["asia"]),
            (threads_post.pick, 7, threads_post.TZ_LANGS["eu_me2"]),
            (threads_post.pick, 14, threads_post.TZ_LANGS["west"]),
            (threads_post.pick, 19, threads_post.TZ_LANGS["americas"]),
        )
        expected_ids = {common.app_key(item) for item in self.pool}
        for picker, hour, languages in routes:
            with self.subTest(hour=hour, expected_size=len(expected_ids)):
                picks = [
                    picker(self.pool, self._at(day, hour))
                    for day in range(len(expected_ids))
                ]
                self.assertEqual(
                    expected_ids, {common.app_key(item) for item in picks}
                )
                for item in picks:
                    has_localized_copy = any(
                        common.app_key(candidate) == common.app_key(item)
                        and candidate.get("lang") in languages
                        for candidate in self.pool
                    )
                    if has_localized_copy:
                        self.assertIn(item["lang"], languages)

    def test_all_channels_choose_different_apps_on_the_same_day(self):
        for day in range(1000):
            picks = (
                telegram_post.pick(self.pool, self._at(day, 1)),
                threads_post.pick(self.pool, self._at(day, 3)),
                threads_post.pick(self.pool, self._at(day, 7)),
                telegram_post.pick(self.pool, self._at(day, 9)),
                threads_post.pick(self.pool, self._at(day, 14)),
                telegram_post.pick(self.pool, self._at(day, 15)),
                threads_post.pick(self.pool, self._at(day, 19)),
            )
            self.assertEqual(7, len({common.app_key(item) for item in picks}))

    def test_combined_channels_cover_every_app_in_minimum_days(self):
        expected = {common.app_key(item) for item in self.pool}
        routes = (
            (telegram_post.pick, 1),
            (threads_post.pick, 3),
            (threads_post.pick, 7),
            (telegram_post.pick, 9),
            (threads_post.pick, 14),
            (telegram_post.pick, 15),
            (threads_post.pick, 19),
        )
        days = (len(expected) + len(routes) - 1) // len(routes)
        observed = set()
        for day in range(days):
            observed.update(
                common.app_key(picker(self.pool, self._at(day, hour)))
                for picker, hour in routes
            )
        self.assertEqual(expected, observed)

    def test_all_market_eligible_locales_are_published_within_13_days(self):
        routes = (
            (telegram_post.pick, 1),
            (threads_post.pick, 3),
            (threads_post.pick, 7),
            (telegram_post.pick, 9),
            (threads_post.pick, 14),
            (telegram_post.pick, 15),
            (threads_post.pick, 19),
        )
        launch = dt.datetime.combine(
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE,
            dt.time(),
            tzinfo=dt.timezone.utc,
        )
        selected = []
        for day in range(common.FULL_LOCALE_SOCIAL_LAUNCH_DAYS):
            selected.extend(
                picker(
                    self.pool,
                    (launch + dt.timedelta(days=day)).replace(hour=hour),
                )
                for picker, hour in routes
            )
        app_ids = {str(item["app"]) for item in self.pool}
        eligible_locales = {
            locale
            for locale in common.OFFICIAL_SOCIAL_LOCALES
            if any(
                not telegram_post.market.is_unavailable(locale, app_id)
                for app_id in app_ids
            )
        }
        self.assertEqual(
            eligible_locales,
            {item["lang"] for item in selected},
        )
        self.assertTrue(
            all(
                item.get("source") == "publisher_intent_catalog"
                for item in selected
            )
        )

    def test_every_app_reaches_every_live_region_within_366_days(self):
        """每支 App 每年都要在每個區域被推到。

        原本的合約是「每個 App×語言組合 366 天內輪到」,那在目前規模已經
        數學上不可能:41 支 App × 25 個歐洲語言 = 1,025 組,而該區一天只有
        一個時段(366 次/年)。硬撐這個承諾的代價是把子彈平均灑在 ASC 顯示
        零曝光的語言上,主力市場反而每 2.8 年才輪到一次。

        現在的合約:每支 App 每年在每個區域都會出現(不餓死任何 App),而
        語言由 ASC 實證的主力市場加權(見 PREFERRED_LOCALE_WEIGHT),長尾
        語言仍在輪替中、只是頻率低。
        """
        routes = (
            (telegram_post.pick, 1),
            (threads_post.pick, 3),
            (threads_post.pick, 7),
            (telegram_post.pick, 9),
            (threads_post.pick, 14),
            (telegram_post.pick, 15),
            (threads_post.pick, 19),
        )
        launch = dt.datetime.combine(
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE,
            dt.time(),
            tzinfo=dt.timezone.utc,
        )
        locale_region = {
            locale: region
            for region, locales in common.REGION_LOCALES.items()
            for locale in locales
        }
        observed = set()
        for day in range(366):
            for picker, hour in routes:
                item = picker(
                    self.pool,
                    (launch + dt.timedelta(days=day)).replace(hour=hour),
                )
                if item.get("source") == "publisher_intent_catalog":
                    observed.add(
                        (str(item["app"]), locale_region[item["lang"]])
                    )
        expected = {
            (common.app_key(item), locale_region[item["lang"]])
            for item in self.pool
            if item.get("source") == "publisher_intent_catalog"
        }
        self.assertEqual(expected, observed)

    def test_long_tail_locales_stay_in_the_rotation(self):
        """加權不得把任何語言永久排除在輪替之外。"""
        for region, locales in common.REGION_LOCALES.items():
            items = [
                {"app_key": "lumibopomofo", "lang": locale}
                for locale in locales
            ]
            cycle = common._prioritized_locales(items, locales)
            with self.subTest(region=region):
                self.assertEqual(set(locales), set(cycle))

    def test_private_asc_signal_reorders_only_post_launch_locale_cycle(self):
        app_id = "7000000000"
        pool = [
            {
                "lang": locale,
                "app": app_id,
                "app_key": "alpha",
                "text": locale,
                "url": f"https://apps.apple.com/app/id{app_id}",
            }
            for locale in common.ASIA_LOCALES
        ]
        launch_day = (
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE - common.BASE_DATE
        ).days
        with mock.patch.object(
            common,
            "ASC_MARKET_LOCALES",
            {"alpha": ("ko", "ja")},
        ):
            launch_signal = common._copy_candidates(
                pool,
                "telegram:asia",
                launch_day,
                app_index=0,
                app_count=28,
            )[0]["lang"]
            post_launch_signal = [
                (
                    day,
                    common._copy_candidates(
                        pool,
                        "telegram:asia",
                        day,
                        app_index=0,
                        app_count=28,
                    )[0]["lang"],
                )
                for day in range(launch_day + 13, launch_day + 200)
            ]
        with mock.patch.object(common, "ASC_MARKET_LOCALES", {}):
            launch_default = common._copy_candidates(
                pool,
                "telegram:asia",
                launch_day,
                app_index=0,
                app_count=28,
            )[0]["lang"]
            changed = next(
                (
                    day,
                    locale,
                    common._copy_candidates(
                        pool,
                        "telegram:asia",
                        day,
                        app_index=0,
                        app_count=28,
                    )[0]["lang"],
                )
                for day, locale in post_launch_signal
                if locale == "ko"
                and common._copy_candidates(
                    pool,
                    "telegram:asia",
                    day,
                    app_index=0,
                    app_count=28,
                )[0]["lang"]
                != locale
            )
        self.assertEqual(launch_default, launch_signal)
        self.assertEqual("ko", changed[1])
        self.assertNotEqual(changed[1], changed[2])

    def test_uneven_copy_counts_cannot_bias_app_rotation(self):
        pool = []
        for app_index in range(7):
            app_id = str(7_000_000_000 + app_index)
            for copy_index in range(30 if app_index == 0 else 1):
                pool.append(
                    {
                        "lang": "en",
                        "app": app_id,
                        "text": f"app {app_index} copy {copy_index}",
                        "url": f"https://apps.apple.com/app/id{app_id}",
                    }
                )
        expected = {str(7_000_000_000 + index) for index in range(7)}
        for channel in common.CHANNEL_ORDER:
            picks = {
                common.app_key(
                    common.channel_candidates(
                        pool, channel, self._at(day, 15)
                    )[0]
                )
                for day in range(7)
            }
            self.assertEqual(expected, picks)


class FooterAndSelectionTests(unittest.TestCase):
    def test_private_asc_signal_is_validated_without_exposing_metrics(self):
        raw = json.dumps(
            {
                "version": 1,
                "generated_at": "2026-07-19T11:26:27+00:00",
                "valid_until": "2026-07-22",
                "app_count": 2,
                "apps": {
                    "alpha": {
                        "action": "SCALE",
                        "locales": ["zh-Hant", "en-US"],
                    },
                    "beta": {
                        "action": "DOWNLOAD_CONVERT",
                        "locales": [],
                    },
                },
            }
        )
        locales, actions = common._load_asc_growth_signals(
            raw,
            today=dt.date(2026, 7, 20),
        )
        self.assertEqual(
            {"alpha": ("zh-Hant", "en-US"), "beta": ()},
            locales,
        )
        self.assertEqual(
            {"alpha": "SCALE", "beta": "DOWNLOAD_CONVERT"},
            actions,
        )
        with mock.patch.dict(
            os.environ,
            {
                "ASC_GROWTH_SIGNALS_B64": base64.b64encode(
                    raw.encode("utf-8")
                ).decode("ascii")
            },
            clear=False,
        ):
            self.assertEqual(
                (locales, actions),
                common._load_asc_growth_signals(
                    today=dt.date(2026, 7, 20)
                ),
            )

    def test_expired_private_asc_signal_keeps_deterministic_rotation(self):
        warning = io.StringIO()
        raw = json.dumps(
            {
                "version": 1,
                "generated_at": "2026-07-15T00:00:00+00:00",
                "valid_until": "2026-07-18",
                "app_count": 0,
                "apps": {},
            }
        )
        with mock.patch.object(common.sys, "stderr", warning):
            locales, actions = common._load_asc_growth_signals(
                raw,
                today=dt.date(2026, 7, 20),
            )
        self.assertEqual(({}, {}), (locales, actions))
        self.assertIn("signals expired", warning.getvalue())

    def test_every_supported_language_has_its_own_footer(self):
        expected_languages = {
            "en",
            "zh-Hant",
            "zh-Hans",
            "ja",
            "ko",
            "ms",
            "de",
            "fr",
            "es",
            "pt-BR",
            "ru",
            "ar",
            "pl",
        }
        self.assertEqual(expected_languages, set(common.FOOTERS))
        self.assertEqual(len(common.FOOTERS), len(set(common.FOOTERS.values())))
        for lang in expected_languages:
            with self.subTest(lang=lang):
                item = {
                    "lang": lang,
                    "text": "Quality copy",
                    "app": "7000000000",
                    "url": "https://apps.apple.com/app/id7000000000",
                }
                footer = common.footer_for(lang)
                self.assertTrue(telegram_post.compose_text(item).endswith(footer))
                self.assertTrue(threads_post.compose_text(item).endswith(footer))
                if not lang.startswith("zh-"):
                    self.assertNotIn("獨立開發者", footer)
                    self.assertNotIn("買斷", footer)
                    self.assertNotIn("訂閱", footer)

    def test_social_ctas_keep_direct_low_cardinality_attribution(self):
        item = {
            "lang": "en",
            "text": "Quality copy",
            "app": "7000000000",
            "url": "https://apps.apple.com/app/id7000000000",
        }
        for token, composer in (
            ("soc_tg_guide", telegram_post.compose_text),
            ("soc_th_guide", threads_post.compose_text),
        ):
            with self.subTest(token=token):
                text = composer(item)
                url = next(
                    part for part in text.split() if part.startswith("https://")
                )
                parsed = urllib.parse.urlsplit(url)
                query = urllib.parse.parse_qs(parsed.query)
                self.assertEqual("apps.apple.com", parsed.netloc)
                self.assertEqual("/app/id7000000000", parsed.path)
                self.assertEqual(["118326163"], query["pt"])
                self.assertEqual([token], query["ct"])
                self.assertEqual(["8"], query["mt"])

    def test_official_locale_partition_is_complete_and_disjoint(self):
        locales = (
            *common.ASIA_LOCALES,
            *common.EUROPE_MIDDLE_EAST_LOCALES,
            *common.AMERICAS_LOCALES,
        )
        self.assertEqual(50, len(locales))
        self.assertEqual(50, len(set(locales)))
        self.assertEqual(
            set(common.OFFICIAL_SOCIAL_LOCALES),
            set(locales),
        )

    def test_single_post_selection_does_not_probe_every_app_store_url(self):
        now = dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc)
        pool = [
            {
                "lang": "zh-Hant",
                "app": str(7_000_000_000 + index),
                "text": f"post {index}",
                "url": f"https://apps.apple.com/app/id{7_000_000_000 + index}",
            }
            for index in range(8)
        ]
        expected = telegram_post.candidates(pool, now)[0]
        with mock.patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("selection must not make HTTP requests"),
        ) as opener:
            selected = telegram_post.pick_postable(pool, now)
        self.assertEqual(
            common.item_key(expected),
            common.item_key(selected),
        )
        opener.assert_not_called()

    def test_dead_apps_preserve_unique_cross_channel_assignments(self):
        pool = [
            {
                "lang": "en",
                "app": str(7_000_000_000 + index),
                "text": f"post {index}",
                "url": f"https://apps.apple.com/app/id{7_000_000_000 + index}",
            }
            for index in range(9)
        ]
        live_pool = common.filter_reachable_pool(
            pool,
            validator=lambda url: not (
                url.endswith("7000000000") or url.endswith("7000000001")
            ),
        )
        picks = [
            common.channel_candidates(
                live_pool, channel, dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
            )[0]
            for channel in common.CHANNEL_ORDER
        ]
        self.assertEqual(7, len({common.app_key(item) for item in picks}))

    def test_url_validator_classifies_404_without_retry(self):
        opener = mock.Mock(side_effect=http_error(404))
        sleeper = mock.Mock()
        self.assertFalse(
            common.validate_url(
                "https://example.com/missing",
                opener=opener,
                sleeper=sleeper,
            )
        )
        self.assertEqual(1, opener.call_count)
        sleeper.assert_not_called()

    def test_threads_skips_overlong_copy_without_truncating(self):
        long_item = {
            "lang": "en",
            "app": "7000000000",
            "text": "x" * 500,
            "url": "https://apps.apple.com/app/id7000000000",
        }
        short_item = {
            "lang": "en",
            "app": "7000000001",
            "text": "Complete, polished copy.",
            "url": "https://apps.apple.com/app/id7000000001",
        }
        with (
            mock.patch.object(
                threads_post, "candidates", return_value=[long_item, short_item]
            ),
            mock.patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError(
                    "selection must not make HTTP requests"
                ),
            ) as opener,
        ):
            selected, text = threads_post.pick_postable([long_item, short_item])
        self.assertIs(selected, short_item)
        self.assertIn(short_item["text"], text)
        self.assertLessEqual(len(text), threads_post.MAX_POST_CHARS)
        opener.assert_not_called()


class RetryTests(unittest.TestCase):
    def test_transient_api_error_retries_at_most_three_times(self):
        opener = mock.Mock(
            side_effect=(
                urllib.error.URLError("temporary"),
                http_error(599, b"busy"),
                FakeResponse(b'{"ok": true}'),
            )
        )
        sleeper = mock.Mock()
        result = common.request_json(
            urllib.request.Request("https://example.com/api"),
            label="test API",
            timeout=1,
            opener=opener,
            sleeper=sleeper,
        )
        self.assertEqual({"ok": True}, result)
        self.assertEqual(3, opener.call_count)
        self.assertEqual([mock.call(1), mock.call(2)], sleeper.call_args_list)

    def test_transient_url_failure_is_not_treated_as_a_dead_link(self):
        opener = mock.Mock(side_effect=urllib.error.URLError("offline"))
        with self.assertRaisesRegex(common.RequestError, "after 3 attempts"):
            common.validate_url(
                "https://example.com/app",
                opener=opener,
                sleeper=mock.Mock(),
            )
        self.assertEqual(3, opener.call_count)

    def test_threads_platform_transient_marker_is_recognized(self):
        self.assertTrue(
            threads_post._threads_transient(
                400, '{"error":{"is_transient":true}}'
            )
        )

    def test_threads_image_post_uses_public_jpeg(self):
        image_url = (
            "https://open.cait518.cc/ios-app-guide/"
            "social/img/aim990-share.jpg"
        )
        with mock.patch.object(
            threads_post,
            "_post",
            side_effect=({"id": "container"}, {"id": "post"}),
        ) as post:
            result = threads_post.publish_post(
                "token",
                "user",
                "Buyer-intent copy",
                image_url=image_url,
                sleeper=mock.Mock(),
            )
        self.assertEqual("post", result)
        payload = post.call_args_list[0].args[1]
        self.assertEqual("IMAGE", payload["media_type"])
        self.assertEqual(image_url, payload["image_url"])
        self.assertEqual("Buyer-intent copy", payload["text"])

    def test_telegram_photo_uses_public_jpeg_and_caption(self):
        image_url = (
            "https://open.cait518.cc/ios-app-guide/"
            "social/img/aim990-share.jpg"
        )
        with mock.patch.object(
            telegram_post,
            "request_json",
            return_value={"ok": True, "result": {"message_id": 1}},
        ) as request:
            telegram_post._send_photo(
                "token",
                "chat",
                "Buyer-intent copy",
                image_url,
            )
        sent = urllib.parse.parse_qs(
            request.call_args.args[0].data.decode("utf-8")
        )
        self.assertIn("/sendPhoto", request.call_args.args[0].full_url)
        self.assertEqual([image_url], sent["photo"])
        self.assertEqual(["Buyer-intent copy"], sent["caption"])

    def test_telegram_local_photo_upload_uses_multipart_jpeg(self):
        with tempfile.TemporaryDirectory() as temporary:
            image_path = Path(temporary) / "aim990-share.jpg"
            image_path.write_bytes(b"verified-jpeg")
            with (
                mock.patch.object(
                    telegram_post.secrets,
                    "token_hex",
                    return_value="fixed",
                ),
                mock.patch.object(
                    telegram_post,
                    "request_json",
                    return_value={"ok": True, "result": {"message_id": 2}},
                ) as request,
            ):
                telegram_post._send_photo_file(
                    "token",
                    "chat",
                    "Buyer-intent copy",
                    image_path,
                )
        sent = request.call_args.args[0]
        self.assertIn("/sendPhoto", sent.full_url)
        self.assertEqual(
            "multipart/form-data; boundary=LumiTelegramfixed",
            sent.headers["Content-type"],
        )
        self.assertIn(b'name="chat_id"\r\n\r\nchat', sent.data)
        self.assertIn(b'name="caption"\r\n\r\nBuyer-intent copy', sent.data)
        self.assertIn(
            b'name="photo"; filename="aim990-share.jpg"',
            sent.data,
        )
        self.assertIn(b"Content-Type: image/jpeg", sent.data)
        self.assertIn(b"verified-jpeg", sent.data)

    def test_telegram_confirmed_remote_failure_uses_local_photo(self):
        item = {
            "image_url": (
                "https://open.cait518.cc/ios-app-guide/"
                "social/img/aim990-share.jpg"
            )
        }
        local_path = Path("/tmp/aim990-share.jpg")
        with (
            mock.patch.object(
                telegram_post,
                "_send_photo",
                side_effect=common.HTTPStatusError(
                    "Telegram sendPhoto",
                    400,
                ),
            ),
            mock.patch.object(
                telegram_post,
                "_local_image_path",
                return_value=local_path,
            ),
            mock.patch.object(
                telegram_post,
                "_send_photo_file",
                return_value={"ok": True, "result": {"message_id": 3}},
            ) as local_send,
            mock.patch.object(telegram_post, "_send_message") as text_send,
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            result = telegram_post._publish_item(
                "token",
                "chat",
                "Buyer-intent copy",
                item,
            )
        self.assertEqual(3, result["result"]["message_id"])
        local_send.assert_called_once_with(
            "token",
            "chat",
            "Buyer-intent copy",
            local_path,
        )
        text_send.assert_not_called()

    def test_telegram_confirmed_local_failure_falls_back_to_text(self):
        item = {
            "image_url": (
                "https://open.cait518.cc/ios-app-guide/"
                "social/img/aim990-share.jpg"
            )
        }
        with (
            mock.patch.object(
                telegram_post,
                "_send_photo",
                side_effect=common.HTTPStatusError(
                    "Telegram sendPhoto",
                    400,
                ),
            ),
            mock.patch.object(
                telegram_post,
                "_local_image_path",
                return_value=Path("/tmp/aim990-share.jpg"),
            ),
            mock.patch.object(
                telegram_post,
                "_send_photo_file",
                side_effect=common.HTTPStatusError(
                    "Telegram local sendPhoto",
                    400,
                ),
            ),
            mock.patch.object(
                telegram_post,
                "_send_message",
                return_value={"ok": True, "result": {"message_id": 4}},
            ) as text_send,
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            result = telegram_post._publish_item(
                "token",
                "chat",
                "Buyer-intent copy",
                item,
            )
        self.assertEqual(4, result["result"]["message_id"])
        text_send.assert_called_once_with(
            "token",
            "chat",
            "Buyer-intent copy",
        )

    def test_telegram_uncertain_local_failure_does_not_double_post(self):
        item = {
            "image_url": (
                "https://open.cait518.cc/ios-app-guide/"
                "social/img/aim990-share.jpg"
            )
        }
        with (
            mock.patch.object(
                telegram_post,
                "_send_photo",
                side_effect=common.HTTPStatusError(
                    "Telegram sendPhoto",
                    400,
                ),
            ),
            mock.patch.object(
                telegram_post,
                "_local_image_path",
                return_value=Path("/tmp/aim990-share.jpg"),
            ),
            mock.patch.object(
                telegram_post,
                "_send_photo_file",
                side_effect=common.RequestError("connection reset"),
            ),
            mock.patch.object(telegram_post, "_send_message") as text_send,
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            with self.assertRaisesRegex(
                common.RequestError,
                "connection reset",
            ):
                telegram_post._publish_item(
                    "token",
                    "chat",
                    "Buyer-intent copy",
                    item,
                )
        text_send.assert_not_called()


def lookup_payload(screenshots_by_app):
    """iTunes lookup shape; None means the listing has no screenshotUrls field."""
    results = []
    for app_id, count in screenshots_by_app.items():
        result = {
            "trackId": int(app_id),
            "ipadScreenshotUrls": [f"https://example.com/ipad{n}.png" for n in range(5)],
        }
        if count is not None:
            result["screenshotUrls"] = [
                f"https://example.com/{app_id}-{n}.png" for n in range(count)
            ]
        results.append(result)
    return json.dumps(
        {"resultCount": len(results), "results": results}
    ).encode("utf-8")


class TelegramPageReadyGateTests(unittest.TestCase):
    """hourstaglite-03: < 3 iPhone screenshots skips the App; Apple down fails open."""

    APPS = tuple(str(7_000_000_000 + index) for index in range(10))
    NOW = dt.datetime(2026, 10, 14, 1, 5, tzinfo=dt.timezone.utc)

    def pool(self):
        return [
            {
                "app": app_id,
                "lang": locale,
                "text": f"Fixture {app_id} {locale}",
                "url": f"https://apps.apple.com/app/id{app_id}",
                "source": "publisher_intent_catalog",
            }
            for app_id in self.APPS
            for locale in common.OFFICIAL_SOCIAL_LOCALES
        ]

    def empty_ledger(self):
        return {"receipts": {}, "intents": {}}

    def test_only_listings_under_three_iphone_screenshots_are_skipped(self):
        apps = {
            "7000000001": 1,     # HoursTag Lite today: 1 iPhone + 1 iPad shot
            "7000000002": 0,
            "7000000003": 3,     # exactly the threshold is ready
            "7000000004": 6,
            "7000000005": None,  # field missing: unknown, never blocked
        }
        opener = mock.Mock(return_value=FakeResponse(lookup_payload(apps)))
        sleeper = mock.Mock()
        unready = telegram_post.page_unready_apps(
            [*apps, "7000000006", "not-an-id"], opener=opener, sleeper=sleeper,
        )
        self.assertEqual(frozenset({"7000000001", "7000000002"}), unready)
        self.assertEqual(1, opener.call_count)
        sleeper.assert_not_called()
        request = opener.call_args.args[0]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        self.assertEqual("GET", request.get_method())
        self.assertTrue(request.full_url.startswith(telegram_post.APPLE_LOOKUP_URL))
        self.assertEqual(
            [",".join(sorted([*apps, "7000000006"]))], query["id"]
        )
        self.assertEqual([telegram_post.PAGE_READY_STOREFRONT], query["country"])
        self.assertIn("Macintosh", request.get_header("User-agent"))

    def test_unreachable_or_refusing_lookup_fails_open_after_one_request(self):
        for failure in (
            urllib.error.URLError("offline"),
            TimeoutError("timed out"),
            http_error(403),
            http_error(429),
            http_error(503),
            FakeResponse(b"<html>not json</html>"),
            FakeResponse(b"[]"),
            FakeResponse(b'{"resultCount": 0}'),
        ):
            with self.subTest(failure=repr(failure)):
                opener = mock.Mock(side_effect=[failure])
                with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    unready = telegram_post.page_unready_apps(
                        self.APPS, opener=opener, sleeper=mock.Mock(),
                    )
                self.assertEqual(frozenset(), unready)
                self.assertEqual(1, opener.call_count)
                self.assertIn("fail open", stderr.getvalue())

    def test_batches_pause_two_seconds_and_stop_on_rate_limit(self):
        opener = mock.Mock(side_effect=[
            FakeResponse(lookup_payload({"7000000000": 1, "7000000001": 5})),
            http_error(429),
            AssertionError("must stop asking Apple after HTTP 429"),
        ])
        sleeper = mock.Mock()
        with (
            mock.patch.object(telegram_post, "PAGE_READY_BATCH", 2),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            unready = telegram_post.page_unready_apps(
                self.APPS[:6], opener=opener, sleeper=sleeper,
            )
        # Known evidence from the first batch is kept; the unknown rest passes.
        self.assertEqual(frozenset({"7000000000"}), unready)
        self.assertEqual(2, opener.call_count)
        sleeper.assert_called_once_with(2)
        self.assertGreaterEqual(telegram_post.PAGE_READY_PAUSE_SECONDS, 2)

    def test_ready_apps_keep_exactly_the_same_slot_choice(self):
        pool = self.pool()
        for hour in telegram_post.SLOT_HOURS:
            now = self.NOW.replace(hour=hour)
            with self.subTest(hour=hour):
                baseline = telegram_post.choose_unpublished(
                    pool, self.empty_ledger(), now
                )
                gated = telegram_post.choose_unpublished(
                    pool, self.empty_ledger(), now, skip_apps=frozenset()
                )
                self.assertEqual(baseline, gated)

    def test_unready_app_is_never_chosen_and_next_ready_app_is(self):
        pool = self.pool()
        for hour in telegram_post.SLOT_HOURS:
            now = self.NOW.replace(hour=hour)
            zone = telegram_post._zone(hour)
            with self.subTest(hour=hour):
                baseline = telegram_post.choose_unpublished(
                    pool, self.empty_ledger(), now
                )
                skipped = frozenset({str(baseline["app"])})
                item = telegram_post.choose_unpublished(
                    pool, self.empty_ledger(), now, skip_apps=skipped
                )
                self.assertIsNotNone(item)
                self.assertNotIn(str(item["app"]), skipped)
                self.assertIn(item["lang"], telegram_post.TZ_LANGS[zone])
                self.assertIsNone(
                    telegram_post.choose_unpublished(
                        pool, self.empty_ledger(), now,
                        skip_apps=frozenset(self.APPS),
                    )
                )

    def test_taiwan_bopomofo_traffic_never_routes_to_pro(self):
        # lumibopomofopro-07: zh-Hant goes to the free-to-start Lite; Pro stays
        # eligible in every other locale (overseas / no in-app purchase).
        pro, lite = "6775773117", "6773017109"
        self.assertTrue(telegram_post.routed_away({"lang": "zh-Hant", "app": pro}))
        self.assertFalse(telegram_post.routed_away({"lang": "zh-Hant", "app": lite}))
        self.assertFalse(telegram_post.routed_away({"lang": "en-US", "app": pro}))
        pool = [
            {
                "app": app_id,
                "lang": locale,
                "text": f"Fixture {app_id} {locale}",
                "url": f"https://apps.apple.com/app/id{app_id}",
                "source": "publisher_intent_catalog",
            }
            for app_id in (*self.APPS, pro, lite)
            for locale in common.OFFICIAL_SOCIAL_LOCALES
        ]
        asia = self.NOW.replace(hour=1)
        only_pro = frozenset((*self.APPS, lite))
        chosen = []
        while True:
            item = telegram_post.choose_unpublished(
                pool, self.empty_ledger(), asia, skip_apps=only_pro
            )
            if item is None:
                break
            chosen.append((item["lang"], str(item["app"])))
            pool = [entry for entry in pool if entry is not item]
        self.assertTrue(chosen)  # Pro still posts in the other Asia locales.
        self.assertNotIn(("zh-Hant", pro), chosen)

    def test_publish_once_forwards_the_gate_to_candidate_selection(self):
        context = {
            "slot": "2026-10-14T01:00:00+00:00",
            "now": self.NOW,
        }
        with (
            mock.patch.object(
                telegram_post, "choose_unpublished", return_value=None
            ) as choose,
            mock.patch.object(telegram_post, "_publish_item") as send,
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            telegram_post.publish_once(
                [], self.empty_ledger(), mock.Mock(), context, "token",
                {"id": -1}, unready_apps=frozenset({"7000000001"}),
            )
        self.assertEqual(
            frozenset({"7000000001"}), choose.call_args.kwargs["skip_apps"]
        )
        send.assert_not_called()

    def test_daily_run_still_posts_when_apple_lookup_is_unreachable(self):
        pool = self.pool()
        cases = (
            (urllib.error.URLError("offline"), frozenset()),
            (http_error(429), frozenset()),
            (
                FakeResponse(lookup_payload({"7000000001": 1, "7000000002": 4})),
                frozenset({"7000000001"}),
            ),
        )
        for lookup, expected in cases:
            store = mock.Mock(spec=telegram_post.GitHubLedger)
            store.load.return_value = self.empty_ledger()
            with self.subTest(lookup=repr(lookup)):
                with (
                    mock.patch.dict(os.environ, {
                        "TELEGRAM_BOT_TOKEN": "fixture-token",
                        "TELEGRAM_CHAT_ID": "@fixture",
                        "GITHUB_TOKEN": "fixture-github",
                    }),
                    mock.patch.object(
                        telegram_post, "production_context",
                        return_value={"source_sha": "1" * 40},
                    ),
                    mock.patch.object(telegram_post, "load_pool", return_value=pool),
                    mock.patch.object(
                        telegram_post, "GitHubLedger", return_value=store
                    ),
                    mock.patch.object(
                        telegram_post, "read_native_chat", return_value={"id": -1}
                    ),
                    mock.patch.object(telegram_post, "reconcile_pending"),
                    mock.patch.object(telegram_post, "publish_once") as publish,
                    mock.patch.object(
                        urllib.request, "urlopen", side_effect=[lookup]
                    ) as opener,
                    mock.patch("sys.stdout", new_callable=io.StringIO),
                    mock.patch("sys.stderr", new_callable=io.StringIO),
                ):
                    self.assertEqual(0, telegram_post.main([]))
                self.assertEqual(1, opener.call_count)
                publish.assert_called_once()
                self.assertEqual(expected, publish.call_args.kwargs["unready_apps"])


class DailyPortfolioCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = portfolio_daily.load_public_apps()

    def test_telegram_spotlight_rotates_reviewed_posts_without_duplicate_digest_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.apps[0]
            other = self.apps[1]
            Path(tmp, "app-posts.json").write_text(json.dumps({"posts": [
                {"app_id": app.app_id, "lang": "zh-Hant", "ct": "spot_a", "text": "故事 A"},
                {"app_id": other.app_id, "lang": "zh-Hant", "ct": "spot_b", "text": "故事 B"},
                {"app_id": other.app_id, "lang": "ja", "ct": "spot_c", "text": "日本語"},
                {"app_id": "1", "lang": "zh-Hant", "ct": "spot_d", "text": "下架 App"},
                {"app_id": app.app_id, "lang": "zh-Hant", "ct": "x", "text": "含連結 https://example.com"},
            ]}), encoding="utf-8")
            posts = portfolio_daily.load_spotlight_posts(self.apps, tmp)
            self.assertEqual(["故事 A", "故事 B"], [post["text"] for post in posts])
            day = dt.date(2026, 10, 14)
            block = portfolio_daily.spotlight_block(self.apps, day, tmp)
            expected = posts[day.toordinal() % 2]
            self.assertIn(expected["text"], block)
            self.assertNotIn("https://", block)
            with mock.patch.object(portfolio_daily, "GROWTH_DIR", Path(tmp)):
                messages = portfolio_daily.telegram_messages(self.apps, today=day)
            portfolio_daily.validate_coverage("telegram", self.apps, messages)
            self.assertIn("🔦 今日焦點", messages[0].text)
            self.assertTrue(all("今日焦點" not in m.text for m in messages[1:]))
            self.assertTrue(all(len(m.text) <= portfolio_daily.TELEGRAM_LIMIT for m in messages))

    def test_telegram_spotlight_prefers_focus_app_until_its_window_ends(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.apps[0]
            other = self.apps[1]
            Path(tmp, "app-posts.json").write_text(json.dumps({"posts": [
                {"app_id": app.app_id, "lang": "zh-Hant", "ct": "spot_a", "text": "故事 A"},
                {"app_id": other.app_id, "lang": "zh-Hant", "ct": "spot_b", "text": "衝榜 B1"},
                {"app_id": other.app_id, "lang": "zh-Hant", "ct": "spot_c", "text": "衝榜 B2"},
            ]}), encoding="utf-8")
            Path(tmp, "focus.json").write_text(json.dumps({"apps": [
                {"app_id": other.app_id, "spotlight_until": "2026-10-27"},
            ]}), encoding="utf-8")
            for offset in range(4):
                day = dt.date(2026, 10, 14) + dt.timedelta(days=offset)
                self.assertIn("衝榜 B", portfolio_daily.spotlight_block(self.apps, day, tmp))
            skipped = portfolio_daily.spotlight_block(
                self.apps, dt.date(2026, 10, 14), tmp, skip_apps=frozenset({other.app_id}))
            self.assertIn("故事 A", skipped)
            self.assertEqual("", portfolio_daily.spotlight_block(
                self.apps, dt.date(2026, 10, 14), tmp,
                skip_apps=frozenset({app.app_id, other.app_id})))
            after = portfolio_daily.spotlight_block(self.apps, dt.date(2026, 10, 28), tmp)
            self.assertTrue("故事 A" in after or "衝榜 B" in after)
            self.assertEqual(set(), portfolio_daily.spotlight_focus_ids(dt.date(2026, 10, 28), tmp))

    def test_current_live_registry_is_covered_without_a_static_post_pool(self):
        selected_ids = {app.app_id for app in self.apps}
        self.assertEqual(
            selected_ids,
            {app.app_id for app in portfolio_daily.load_public_apps()},
        )
        pool = telegram_post.load_pool()
        self.assertEqual(
            selected_ids,
            {str(item["app"]) for item in pool},
        )
        for item in pool:
            expected = f"https://apps.apple.com/app/id{item['app']}"
            self.assertEqual(expected, item["url"])
        for app_id in selected_ids:
            languages = {
                item["lang"]
                for item in pool
                if str(item["app"]) == app_id
            }
            for channel, spec in common.CHANNEL_SPECS.items():
                with self.subTest(app_id=app_id, channel=channel):
                    self.assertTrue(languages.intersection(spec["langs"]))

    def test_intent_pool_covers_every_market_eligible_live_app(self):
        pool = [
            item
            for item in telegram_post.load_pool()
            if item.get("source") == "publisher_intent_catalog"
        ]
        selected_ids = {app.app_id for app in self.apps}
        expected = {
            (app_id, locale)
            for app_id in selected_ids
            for locale in common.OFFICIAL_SOCIAL_LOCALES
            if not telegram_post.market.is_unavailable(locale, app_id)
        }
        self.assertEqual(len(expected), len(pool))
        self.assertEqual(
            expected,
            {(str(item["app"]), item["lang"]) for item in pool},
        )
        self.assertNotIn("bn-BD", {item["lang"] for item in pool})
        for item in pool:
            self.assertLessEqual(
                len(threads_post.compose_text(item)),
                threads_post.MAX_POST_CHARS,
            )
            self.assertEqual(
                item["image_url"],
                common.item_image_url(item),
            )
            self.assertTrue(item["footer"].startswith("— Lumi Studio · "))

    def test_linkset_discovers_unknown_new_live_apps(self):
        selected = portfolio_daily.parse_public_apps(
            linkset_payload(
                ("known", "Current App", "7000000001"),
                ("brand-new", "Brand New App", "7000000002"),
            ),
            apps={
                "known": {
                    "name": "Registry Name",
                    "category": "productivity",
                }
            },
            appstore={"known": "7000000001"},
        )
        by_id = {app.app_id: app for app in selected}
        self.assertEqual({"7000000001", "7000000002"}, set(by_id))
        self.assertEqual("Current App", by_id["7000000001"].name)
        self.assertEqual("productivity", by_id["7000000001"].category)
        self.assertEqual("Brand New App", by_id["7000000002"].name)
        self.assertEqual("other", by_id["7000000002"].category)
        self.assertEqual("brand-new", by_id["7000000002"].key)

    def test_live_app_without_a_unique_context_fails_loudly(self):
        payload = linkset_payload(("known", "Known", "7000000001"))
        payload["linkset"] = payload["linkset"][:1]
        with self.assertRaisesRegex(
            portfolio_daily.CoverageError, "exactly one linkset context"
        ):
            portfolio_daily.parse_public_apps(
                payload,
                apps={},
                appstore={},
            )

    def test_confirmed_dead_daily_link_is_excluded(self):
        validator = mock.Mock(side_effect=(True, False))
        reachable = portfolio_daily.filter_reachable_apps(
            self.apps[:2], validator=validator, max_workers=1
        )
        self.assertEqual([self.apps[0]], reachable)
        self.assertEqual(2, validator.call_count)

    def test_transient_daily_link_failure_blocks_publication(self):
        validator = mock.Mock(side_effect=common.RequestError("offline"))
        with self.assertRaisesRegex(common.RequestError, "offline"):
            portfolio_daily.filter_reachable_apps(
                self.apps[:1], validator=validator, max_workers=1
            )

    def test_each_platform_covers_every_live_app_exactly_once(self):
        for platform, builder, limit in (
            (
                "telegram",
                portfolio_daily.telegram_messages,
                portfolio_daily.TELEGRAM_LIMIT,
            ),
            (
                "threads",
                portfolio_daily.threads_messages,
                portfolio_daily.THREADS_LIMIT,
            ),
        ):
            with self.subTest(platform=platform):
                messages = builder(self.apps)
                portfolio_daily.validate_coverage(platform, self.apps, messages)
                combined = "\n".join(message.text for message in messages)
                campaign = portfolio_daily.PLATFORM_CAMPAIGNS[platform]
                for app in self.apps:
                    self.assertIn(app.name, combined)
                    self.assertEqual(
                        1, combined.count(app.appstore_url(campaign))
                    )
                self.assertIn("?pt=118326163&ct=", combined)
                self.assertIn("&mt=8", combined)
                self.assertTrue(all(len(message.text) <= limit for message in messages))
                if platform == "threads":
                    self.assertTrue(
                        all(
                            len(message.app_ids)
                            <= portfolio_daily.THREADS_LINK_LIMIT
                            for message in messages
                        )
                    )
                    self.assertTrue(
                        all(
                            message.text.count("https://") <= 5
                            for message in messages
                        )
                    )
                    self.assertNotIn(
                        portfolio_daily.DEVELOPER_URL, combined
                    )

    def test_large_portfolio_splits_without_losing_coverage(self):
        apps = [
            portfolio_daily.PublicApp(
                key=f"app-{index}",
                app_id=str(index),
                name=f"Portfolio Utility {index:03d}",
                category="productivity",
            )
            for index in range(120)
        ]
        for platform, builder in (
            ("telegram", portfolio_daily.telegram_messages),
            ("threads", portfolio_daily.threads_messages),
        ):
            messages = builder(apps)
            self.assertGreater(len(messages), 1)
            portfolio_daily.validate_coverage(platform, apps, messages)

    def test_same_day_platform_success_prevents_duplicate_digest(self):
        now = dt.datetime(
            2026, 7, 13, 13, 0, tzinfo=dt.timezone.utc
        )
        calls = []

        def fetcher(url, token):
            calls.append((url, token))
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-13T04:30:00Z",
                        },
                        {
                            "id": 200,
                            "created_at": "2026-07-13T12:00:00Z",
                        },
                    ]
                }
            if "/runs/100/jobs" in url:
                return {
                    "jobs": [
                        {
                            "name": "telegram",
                            "conclusion": "success",
                            "completed_at": "2026-07-13T07:46:14Z",
                        },
                        {
                            "name": "threads",
                            "conclusion": "failure",
                            "completed_at": "2026-07-13T07:46:48Z",
                        },
                    ]
                }
            raise AssertionError(f"unexpected URL: {url}")

        self.assertTrue(
            portfolio_daily.already_published_today(
                "telegram",
                now=now,
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                token="test-token",
                fetcher=fetcher,
            )
        )
        calls.clear()
        self.assertFalse(
            portfolio_daily.already_published_today(
                "threads",
                now=now,
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                token="test-token",
                fetcher=fetcher,
            )
        )
        self.assertTrue(
            all(token == "test-token" for _, token in calls)
        )
        self.assertTrue(
            any("jobs?filter=all&per_page=100" in url for url, _ in calls)
        )

    def test_previous_day_success_does_not_skip_today(self):
        def fetcher(url, _token):
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-12T04:30:00Z",
                        }
                    ]
                }
            return {
                "jobs": [
                    {
                        "name": "threads",
                        "conclusion": "success",
                        "completed_at": "2026-07-12T04:31:00Z",
                    }
                ]
            }

        self.assertFalse(
            portfolio_daily.already_published_today(
                "threads",
                now=dt.datetime(
                    2026, 7, 13, 0, 1, tzinfo=dt.timezone.utc
                ),
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                fetcher=fetcher,
            )
        )

    def test_ambiguous_success_timestamp_blocks_duplicate(self):
        def fetcher(url, _token):
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-13T04:30:00Z",
                        }
                    ]
                }
            return {
                "jobs": [
                    {
                        "name": "threads",
                        "conclusion": "success",
                        "completed_at": None,
                    }
                ]
            }

        with self.assertRaisesRegex(
            portfolio_daily.CoverageError, "valid completed_at"
        ):
            portfolio_daily.already_published_today(
                "threads",
                now=dt.datetime(
                    2026, 7, 13, 13, 0, tzinfo=dt.timezone.utc
                ),
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                fetcher=fetcher,
            )

    def test_daily_workflow_runs_both_platforms(self):
        workflow = os.path.join(
            portfolio_daily.REPO_ROOT,
            ".github",
            "workflows",
            "portfolio-daily.yml",
        )
        with open(workflow, encoding="utf-8") as workflow_file:
            text = workflow_file.read()
        self.assertIn('cron: "30 4 * * *"', text)
        self.assertIn('workflows: ["Daily GEO content"]', text)
        self.assertIn(
            "github.event.workflow_run.conclusion == 'success'", text
        )
        self.assertIn("actions: read", text)
        self.assertEqual(2, text.count("GITHUB_TOKEN:"))
        self.assertIn("--platform telegram", text)
        self.assertIn("--platform threads", text)

    def test_geo_workflow_generates_new_app_surfaces_before_linkset(self):
        workflow = os.path.join(
            portfolio_daily.REPO_ROOT,
            ".github",
            "workflows",
            "geo-daily.yml",
        )
        with open(workflow, encoding="utf-8") as workflow_file:
            text = workflow_file.read()
        commands = (
            "python3 ensure_live_guides.py",
            "python3 gen_webstories.py",
            "python3 gen_linkset.py",
            "python3 gen_social_previews.py",
            "python3 gen_image_sitemap.py",
        )
        positions = [text.index(command) for command in commands]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            positions[-1],
            text.index("python3 -m unittest discover"),
        )

    def test_geo_workflow_checks_out_latest_main_after_queue_wait(self):
        workflow = os.path.join(
            portfolio_daily.REPO_ROOT,
            ".github",
            "workflows",
            "geo-daily.yml",
        )
        with open(workflow, encoding="utf-8") as workflow_file:
            text = workflow_file.read()
        checkout = text.split(
            "- uses: actions/checkout@v5", 1
        )[1].split("- uses:", 1)[0]
        self.assertIn("ref: main", checkout)
        self.assertIn("fetch-depth: 0", checkout)


class TelegramDailyCatalogTests(unittest.TestCase):
    """The all-App catalog goes out every day, once, from either workflow."""

    PAGE_GATED_KEYS = ("unblurry", "hourstaglite", "savetag")

    @classmethod
    def setUpClass(cls):
        cls.apps = portfolio_daily.load_public_apps()

    @staticmethod
    def _workflow(name):
        path = os.path.join(
            portfolio_daily.REPO_ROOT, ".github", "workflows", name
        )
        with open(path, encoding="utf-8") as workflow_file:
            return workflow_file.read()

    @staticmethod
    def _fetcher(portfolio_jobs, telegram_jobs):
        def fetcher(url, _token):
            if "/workflows/portfolio-daily.yml/" in url:
                return {"workflow_runs": [
                    {"id": 100, "created_at": "2026-10-16T04:30:00Z"},
                ]}
            if "/workflows/telegram-daily.yml/" in url:
                return {"workflow_runs": [
                    {"id": 300, "created_at": "2026-10-16T01:00:00Z"},
                    {"id": 400, "created_at": "2026-10-16T09:00:00Z"},
                ]}
            if "/runs/100/jobs" in url:
                return {"jobs": portfolio_jobs}
            if "/runs/300/jobs" in url:
                return {"jobs": telegram_jobs}
            raise AssertionError(f"unexpected URL: {url}")

        return fetcher

    def _published(self, portfolio_jobs, telegram_jobs, platform="telegram"):
        return portfolio_daily.already_published_today(
            platform,
            now=dt.datetime(2026, 10, 16, 9, 5, tzinfo=dt.timezone.utc),
            repository="alice51849/ios-app-guide",
            current_run_id="400",
            token="test-token",
            fetcher=self._fetcher(portfolio_jobs, telegram_jobs),
        )

    def test_catalog_slot_success_today_prevents_a_second_catalog(self):
        done = {
            "name": "catalog", "conclusion": "success",
            "completed_at": "2026-10-16T01:04:00Z",
        }
        post_only = {
            "name": "post", "conclusion": "success",
            "completed_at": "2026-10-16T01:03:00Z",
        }
        self.assertTrue(self._published([], [post_only, done]))
        # The single-App post job of the slot does not count as the catalog.
        self.assertFalse(self._published([], [post_only]))
        # A failed catalog leaves the day open for the next slot.
        self.assertFalse(self._published([], [
            post_only, {**done, "conclusion": "failure"},
        ]))
        # Yesterday's catalog does not cover today.
        self.assertFalse(self._published([], [
            {**done, "completed_at": "2026-10-15T15:04:00Z"},
        ]))
        # portfolio-daily's own job still counts (no double post on the day of
        # the switch-over), and Threads never looks at the Telegram catalog.
        self.assertTrue(self._published([{
            "name": "telegram", "conclusion": "success",
            "completed_at": "2026-10-16T04:33:00Z",
        }], []))
        self.assertFalse(self._published([], [done], platform="threads"))

    def test_catalog_has_its_own_tracking_token_on_every_link(self):
        campaign = portfolio_daily.PLATFORM_CAMPAIGNS["telegram"]
        self.assertEqual("soc_tg_digest", campaign)
        self.assertNotEqual("soc_tg_guide", campaign)
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16)
        )
        portfolio_daily.validate_coverage("telegram", self.apps, messages)
        combined = "\n".join(message.text for message in messages)
        links = [
            line.strip() for line in combined.splitlines()
            if line.strip().startswith("https://apps.apple.com/app/id")
        ]
        self.assertEqual(len(self.apps), len(links))
        self.assertTrue(all("ct=soc_tg_digest" in link for link in links))
        self.assertNotIn("ct=soc_tg_guide", combined)

    def test_catalog_lists_the_tracked_play_link_of_every_android_app(self):
        campaign = portfolio_daily.PLATFORM_CAMPAIGNS["telegram"]
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16)
        )
        portfolio_daily.validate_coverage("telegram", self.apps, messages)
        android = common.android_apps()
        on_play = [app for app in self.apps if app.app_id in android]
        self.assertTrue(on_play)
        self.assertTrue([app for app in self.apps if app.app_id not in android])
        combined = "\n".join(message.text for message in messages)
        play_lines = [
            line.strip() for line in combined.splitlines()
            if line.strip().startswith("Google Play: ")
        ]
        self.assertEqual(len(on_play), len(play_lines))
        for app in on_play:
            key = android[app.app_id]["key"]
            with self.subTest(app=key):
                expected = (
                    f"Google Play: {android[app.app_id]['play_url']}&referrer="
                    f"utm_source%3D{campaign}%26utm_campaign%3D{key}"
                )
                self.assertIn(expected, play_lines)
                # The Play line sits right under the App's own App Store line.
                store = app.appstore_url(campaign)
                self.assertIn(f"  {store}\n  {expected}", combined)
        self.assertNotIn("lumi_social", combined)

    def test_catalog_refuses_a_missing_play_link(self):
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16)
        )
        broken = [
            portfolio_daily.DigestMessage(
                "\n".join(
                    line for line in message.text.splitlines()
                    if not line.strip().startswith("Google Play: ")
                ),
                message.app_ids,
            )
            for message in messages
        ]
        with self.assertRaises(portfolio_daily.CoverageError):
            portfolio_daily.validate_coverage("telegram", self.apps, broken)

    def test_catalog_covers_every_live_app_once_split_under_telegram_limit(self):
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16)
        )
        self.assertGreaterEqual(len(messages), 1)
        self.assertTrue(all(
            len(message.text) <= portfolio_daily.TELEGRAM_LIMIT < 4096
            for message in messages
        ))
        listed = [app_id for message in messages for app_id in message.app_ids]
        self.assertEqual(sorted(app.app_id for app in self.apps), sorted(listed))
        self.assertNotIn("lensafe", {app.key for app in self.apps})

    def test_page_gated_apps_stay_in_the_catalog_but_never_lead_it(self):
        by_key = {app.key: app for app in self.apps}
        gated = frozenset(
            by_key[key].app_id for key in self.PAGE_GATED_KEYS if key in by_key
        )
        self.assertTrue(gated)
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16), skip_spotlight_apps=gated,
        )
        portfolio_daily.validate_coverage("telegram", self.apps, messages)
        listed = {app_id for message in messages for app_id in message.app_ids}
        self.assertLessEqual(gated, listed)
        spotlight = messages[0].text.split("🌏", 1)[0]
        for key in self.PAGE_GATED_KEYS:
            if key in by_key:
                self.assertNotIn(f"今日焦點｜{by_key[key].name}\n", spotlight)

    def test_catalog_list_lines_have_no_price_free_or_superlative(self):
        messages = portfolio_daily.telegram_messages(
            self.apps, today=dt.date(2026, 10, 16)
        )
        entries = [
            line for message in messages for line in message.text.splitlines()
            if line.startswith("• ")
        ]
        self.assertEqual(len(self.apps), len(entries))
        for line in entries:
            with self.subTest(line=line):
                for banned in ("$", "NT", "元", "免費", "Free", "free", "最", "best", "#1", "No.1"):
                    self.assertNotIn(banned, line)

    def test_telegram_daily_runs_the_catalog_after_every_slot(self):
        text = self._workflow("telegram-daily.yml")
        self.assertIn(
            "should_post: ${{ steps.slot.outputs.should_post }}", text
        )
        catalog = text.split("\n  catalog:\n", 1)[1]
        self.assertIn("needs: post", catalog)
        self.assertIn("always()", catalog)
        self.assertIn("needs.post.outputs.should_post == 'true'", catalog)
        self.assertIn("github.event_name == 'schedule'", catalog)
        self.assertIn("group: telegram-portfolio-digest", catalog)
        self.assertIn("cancel-in-progress: false", catalog)
        self.assertIn("actions: read", catalog)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", catalog)
        self.assertLess(
            catalog.index("test_social_posting.py -q -b"),
            catalog.index("portfolio_daily.py --platform telegram"),
        )
        self.assertNotIn("--dry-run", catalog)
        self.assertNotIn("continue-on-error", catalog)
        portfolio = self._workflow("portfolio-daily.yml")
        telegram_job = portfolio.split("\n  telegram:\n", 1)[1].split("\n  threads:\n", 1)[0]
        self.assertIn("group: telegram-portfolio-digest", telegram_job)


class PlayReferrerTests(unittest.TestCase):
    """Google Play links carry the sibling App Store ct as utm_source and the
    snapshot key as utm_campaign (00_GrowthEngine agent/ct_codes.py play_referrer_url)."""

    MOCHI = "6785004775"  # Android-live in _engine/geo/data/android_live_snapshot.json
    IOS_ONLY = "1000000001"
    MOCHI_PLAY = "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"

    def test_canonical_referrer_shape(self):
        self.assertEqual(
            self.MOCHI_PLAY
            + "&referrer=utm_source%3Dh7_mochi_th%26utm_campaign%3Dmochi",
            common.play_store_url(self.MOCHI, "h7_mochi_th"),
        )
        apps = {"77": {"ios_app_id": "77", "key": "usagenow",
                       "play_url": "https://play.google.com/store/apps/details?id=com.a.B"}}
        with mock.patch.object(common, "android_apps", return_value=apps):
            self.assertEqual(
                "https://play.google.com/store/apps/details?id=com.a.B"
                "&referrer=utm_source%3Dh7_usagenow_th%26utm_campaign%3Dusagenow",
                common.play_store_url("77", "h7_usagenow_th"),
            )

    def test_referrer_decodes_to_ct_and_app_key(self):
        for ct in ("soc_tg_guide", "soc_tg_digest", "cd_tg", "ut_aim990_tg", "rp_th", "bm_mochi_us_th"):
            with self.subTest(ct=ct):
                url = common.play_store_url(self.MOCHI, ct)
                referrer = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["referrer"][0]
                self.assertEqual(
                    {"utm_source": [ct], "utm_campaign": ["mochi"]},
                    urllib.parse.parse_qs(referrer),
                )
                self.assertNotIn("lumi_social", url)
                # The referrer value is fully percent-encoded: one & and one = outside it.
                self.assertEqual(1, url.count("&"))

    def test_invalid_campaign_tokens_are_refused(self):
        for ct in ("", "has space", "a&b", "x=y", "a" * 41, "ünicode", None):
            with self.subTest(ct=ct), self.assertRaises(ValueError):
                common.play_store_url(self.MOCHI, ct)
        self.assertTrue(common.play_store_url(self.MOCHI, "a-b_C9" + "x" * 34))

    def test_apps_off_android_get_no_play_link(self):
        self.assertIsNone(common.play_store_url(self.IOS_ONLY, "soc_tg_guide"))
        self.assertIsNone(common.play_store_url("", "soc_tg_guide"))

    def test_snapshot_drives_the_links(self):
        apps = {"88": {"ios_app_id": "88", "key": "newapp",
                       "play_url": "https://play.google.com/store/apps/details?id=com.a.New"}}
        with mock.patch.object(common, "android_apps", return_value=apps):
            self.assertIn("utm_campaign%3Dnewapp", common.play_store_url("88", "cd_tg"))
            self.assertIsNone(common.play_store_url(self.MOCHI, "cd_tg"))

    def _item(self, app):
        return {"app": app, "url": f"https://apps.apple.com/app/id{app}", "text": "Pain line",
                "lang": "en"}

    def test_telegram_single_and_threads_reply_carry_the_tracked_play_link(self):
        text = telegram_post.compose_text(self._item(self.MOCHI))
        self.assertIn("ct=soc_tg_guide", text)
        self.assertIn(
            "🤖 Google Play: " + self.MOCHI_PLAY
            + "&referrer=utm_source%3Dsoc_tg_guide%26utm_campaign%3Dmochi",
            text,
        )
        self.assertNotIn("play.google.com", telegram_post.compose_text(self._item(self.IOS_ONLY)))
        body = threads_post.compose_body(self._item(self.MOCHI))
        self.assertNotIn("http", body)
        links = threads_post.compose_links(self._item(self.MOCHI)).splitlines()
        self.assertTrue(links[0].startswith("App Store: ") and "ct=soc_th_guide" in links[0])
        self.assertEqual(
            "Google Play: " + self.MOCHI_PLAY
            + "&referrer=utm_source%3Dsoc_th_guide%26utm_campaign%3Dmochi",
            links[1],
        )
        self.assertEqual(1, len(threads_post.compose_links(self._item(self.IOS_ONLY)).splitlines()))

    def test_threads_queued_reply_uses_the_series_token_for_play_too(self):
        links = threads_post.queued_links({"app_id": self.MOCHI, "ct": "bm_mochi_us_th"})
        self.assertIn("ct=bm_mochi_us_th", links)
        self.assertIn("utm_source%3Dbm_mochi_us_th%26utm_campaign%3Dmochi", links)

    def test_posts_with_the_older_play_shape_still_count_as_sent(self):
        item = self._item(self.MOCHI)
        legacy = telegram_post.compose_text(item, legacy_play=True)
        self.assertIn("utm_source%3Dlumi_social%26utm_campaign%3Dsoc_tg_guide", legacy)
        self.assertNotEqual(legacy, telegram_post.compose_text(item))
        self.assertIn(telegram_post._digest(legacy), telegram_post._sent_digests(item))
        self.assertIn(telegram_post._digest(telegram_post.compose_text(item, ct="soc_tg_guide", legacy_play=True)),
                      telegram_post._sent_digests(item))


class DevToGateTests(unittest.TestCase):
    POOL = (
        {"title": "First", "body": "one"},
        {"title": "Second", "body": "two"},
    )

    def test_social_workflows_buffer_test_output(self):
        for name in (
            "portfolio-daily.yml",
            "telegram-daily.yml",
            "threads-post.yml",
        ):
            with self.subTest(workflow=name):
                workflow = os.path.join(
                    portfolio_daily.REPO_ROOT,
                    ".github",
                    "workflows",
                    name,
                )
                with open(workflow, encoding="utf-8") as workflow_file:
                    text = workflow_file.read()
                self.assertNotIn("test_social_posting.py -q\n", text)
                self.assertIn("test_social_posting.py -q -b", text)

    def test_published_history_uses_private_authenticated_endpoint(self):
        with mock.patch.object(
            devto_post,
            "request_json",
            return_value=[{"title": "Published"}],
        ) as request_json:
            articles = devto_post.published_articles("secret-key")

        self.assertEqual([{"title": "Published"}], articles)
        request = request_json.call_args.args[0]
        self.assertEqual(
            "https://dev.to/api/articles/me/published?per_page=100&page=1",
            request.full_url,
        )
        self.assertEqual("secret-key", request.get_header("Api-key"))

    def test_72_hour_gate_across_a_month_boundary(self):
        published = (
            {
                "title": "First",
                "published_at": "2026-01-30T10:00:00Z",
            },
        )
        before = dt.datetime(2026, 2, 2, 9, 59, 59, tzinfo=dt.timezone.utc)
        boundary = dt.datetime(2026, 2, 2, 10, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(devto_post.publication_due(self.POOL, published, before))
        self.assertTrue(devto_post.publication_due(self.POOL, published, boundary))
        self.assertEqual(
            "Second",
            devto_post.next_unpublished(self.POOL, published)["title"],
        )

    def test_unrelated_recent_article_does_not_delay_pool(self):
        published = (
            {
                "title": "First",
                "published_at": "2026-02-01T00:00:00Z",
            },
            {
                "title": "Unrelated",
                "published_at": "2026-02-04T07:00:00Z",
            },
        )
        now = dt.datetime(2026, 2, 4, 8, 0, tzinfo=dt.timezone.utc)
        self.assertTrue(devto_post.publication_due(self.POOL, published, now))

    def test_dead_article_url_is_skipped_until_it_becomes_live(self):
        pool = (
            {
                "title": "Unavailable",
                "body": "Download https://example.com/missing",
            },
            {
                "title": "Ready",
                "body": "Read https://example.com/live",
            },
        )
        with mock.patch.object(
            devto_post, "validate_url", side_effect=(False, True)
        ):
            selected = devto_post.next_publishable(pool, ())
        self.assertEqual("Ready", selected["title"])

    def test_authenticated_history_read_403_is_an_explicit_failure(self):
        error = common.HTTPStatusError(
            "Dev.to authenticated articles read (page 1)",
            403,
        )
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "test-key"}),
            mock.patch.object(
                devto_post,
                "published_articles",
                side_effect=error,
            ),
        ):
            self.assertEqual(1, devto_post.main())

    def test_missing_api_key_preserves_queue_and_fails_closed(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(1, devto_post.main())
        self.assertIn("queue preserved", stderr.getvalue())

    def test_rejected_api_key_preserves_queue_and_fails_closed(self):
        error = common.HTTPStatusError(
            "Dev.to authenticated articles read (page 1)",
            401,
        )
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "expired-key"}),
            mock.patch.object(
                devto_post,
                "published_articles",
                side_effect=error,
            ),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(1, devto_post.main())
        self.assertIn("HTTP 401", stderr.getvalue())
        self.assertIn("queue preserved", stderr.getvalue())

    def test_publish_401_preserves_queue_and_fails_closed(self):
        error = common.HTTPStatusError("Dev.to publish", 401)
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "expired-key"}),
            mock.patch.object(devto_post, "published_articles", return_value=[]),
            mock.patch.object(
                devto_post, "next_unpublished", return_value={"title": "Ready"}
            ),
            mock.patch.object(
                devto_post, "latest_pool_publication", return_value=None
            ),
            mock.patch.object(
                devto_post,
                "next_publishable",
                return_value={"title": "Ready", "body": "body"},
            ),
            mock.patch.object(devto_post, "_publish", side_effect=error),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(1, devto_post.main())
        self.assertIn("HTTP 401", stderr.getvalue())
        self.assertIn("queue preserved", stderr.getvalue())

    def test_publish_403_preserves_queue_and_fails_closed(self):
        error = common.HTTPStatusError("Dev.to publish", 403)
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "test-key"}),
            mock.patch.object(devto_post, "published_articles", return_value=[]),
            mock.patch.object(
                devto_post, "next_unpublished", return_value={"title": "Ready"}
            ),
            mock.patch.object(
                devto_post, "latest_pool_publication", return_value=None
            ),
            mock.patch.object(
                devto_post,
                "next_publishable",
                return_value={"title": "Ready", "body": "body"},
            ),
            mock.patch.object(devto_post, "_publish", side_effect=error),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(1, devto_post.main())
        self.assertIn("HTTP 403", stderr.getvalue())
        self.assertIn("did not publish", stderr.getvalue())

    def test_main_calculates_latest_pool_publication_once(self):
        latest = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "test-key"}),
            mock.patch.object(devto_post, "published_articles", return_value=[]),
            mock.patch.object(
                devto_post, "next_unpublished", return_value={"title": "Ready"}
            ),
            mock.patch.object(
                devto_post,
                "latest_pool_publication",
                return_value=latest,
            ) as latest_publication,
        ):
            self.assertEqual(0, devto_post.main())
        latest_publication.assert_called_once()


class TelegramReviewLinkTests(unittest.TestCase):
    """review_links.json: the daily Telegram post carries the existing-user review link only for the
    App x locale pairs whose category leader has <= 20 ratings; posts sent before it stay used."""

    USAGENOW, MOCHI = "6818607603", "6785004775"
    NOW = dt.datetime(2026, 10, 16, 1, 5, tzinfo=dt.timezone.utc)

    def item(self, app, lang):
        return {"app": app, "lang": lang, "text": "Quality copy", "url": f"https://apps.apple.com/app/id{app}",
                "source": "publisher_intent_catalog"}

    def test_only_listed_pairs_get_the_review_line(self):
        review = f"https://apps.apple.com/app/id{self.USAGENOW}?action=write-review"
        text = telegram_post.compose_text(self.item(self.USAGENOW, "ko"))
        self.assertIn(review, text)
        self.assertIn("📝 이미 이 앱을 사용 중이신가요? App Store에서 평가하거나 리뷰를 작성할 수 있습니다\n" + review, text)
        self.assertTrue(text.endswith(common.footer_for("ko")))
        first = next(part for part in text.split() if part.startswith("https://"))
        self.assertIn("ct=soc_tg_guide", first)  # the download CTA stays first and attributed
        self.assertNotIn("ct=", review)
        self.assertIn("write-review", telegram_post.compose_text(self.item(self.USAGENOW, "en-US")))
        for app, lang in ((self.USAGENOW, "ja"), (self.USAGENOW, "en-GB"), (self.MOCHI, "ko"),
                          ("6798814385", "zh-Hans")):
            with self.subTest(app=app, lang=lang):
                self.assertNotIn("write-review", telegram_post.compose_text(self.item(app, lang)))
        self.assertNotIn("write-review", telegram_post.compose_text(self.item(self.USAGENOW, "ko"), review=False))
        # The public-history reader still sees one App per post (both links name the same App ID).
        urls = [part for part in text.split() if part.startswith("https://apps.apple.com")]
        self.assertEqual({self.USAGENOW}, telegram_post._app_ids(urls))

    def test_posts_sent_before_the_review_line_count_as_used(self):
        target = self.item(self.USAGENOW, "ko")
        pool = [target]

        def candidates(pool_arg, channel, now):
            return pool_arg if channel == "telegram:asia" else [{"app": "7000000009"}]

        def ledger(digest):
            receipts = {} if digest is None else {"LumiApps2026/1": {
                "app_store_id": self.USAGENOW, "payload_digest": digest,
                "timestamp": "2026-10-10T01:00:00+00:00"}}
            return {"receipts": receipts, "intents": {}}

        with mock.patch.object(telegram_post, "channel_candidates", side_effect=candidates):
            self.assertIs(target, telegram_post.choose_unpublished(pool, ledger(None), self.NOW))
            for old in (telegram_post.compose_text(target, review=False),
                        telegram_post.compose_text(target, android=False, review=False),
                        telegram_post.compose_text(target)):
                with self.subTest(old=old[-80:]):
                    self.assertIsNone(
                        telegram_post.choose_unpublished(pool, ledger(telegram_post._digest(old)), self.NOW)
                    )


class TelegramCampaignAndPaidLocaleTest(unittest.TestCase):
    """Telegram text posts: per-app campaign token, posts sent with soc_tg_guide stay used, and the
    locale rotation leans on the paying markets without dropping the others."""

    NOW = dt.datetime(2026, 10, 16, 1, 5, tzinfo=dt.timezone.utc)

    def item(self, app, lang, key="mochi"):
        return {"app": app, "app_key": key, "lang": lang, "text": f"Quality copy {lang}",
                "url": f"https://apps.apple.com/app/id{app}", "source": "publisher_intent_catalog"}

    def test_token_names_the_app_and_can_name_the_locale(self):
        self.assertEqual("soc_tg_mochi", telegram_post.telegram_campaign(self.item("1", "zh-Hant")))
        self.assertEqual("soc_tg_mochi_zhhant", telegram_post.telegram_campaign(self.item("1", "zh-Hant"), True))
        self.assertEqual("soc_tg_guide", telegram_post.telegram_campaign({"app": "1", "lang": "en"}))
        longest = telegram_post.telegram_campaign(self.item("1", "zh-Hans", "claudeusagemini"), True)
        self.assertEqual("soc_tg_claudeusagemini_zhhans", longest)
        for key in ("claudeusagemini", "lumibopomofopro", "a" * 40):
            for with_locale in (False, True):
                token = telegram_post.telegram_campaign(self.item("1", "pt-BR", key), with_locale)
                self.assertRegex(token, r"^[a-z0-9_]{1,30}$")
                self.assertTrue(common.APP_STORE_CAMPAIGN_RE.fullmatch(token))
        text = telegram_post.compose_text(self.item("6785004775", "en-US"))
        first = next(part for part in text.split() if part.startswith("https://"))
        self.assertEqual(["soc_tg_mochi"], urllib.parse.parse_qs(urllib.parse.urlsplit(first).query)["ct"])

    def test_posts_sent_with_the_shared_token_count_as_used(self):
        target = self.item("6785004775", "ko")

        def candidates(pool_arg, channel, now):
            return pool_arg if channel == "telegram:asia" else [{"app": "7000000009"}]

        def ledger(digest):
            return {"receipts": {"LumiApps2026/1": {
                "app_store_id": "6785004775", "payload_digest": digest,
                "timestamp": "2026-10-10T01:00:00+00:00"}}, "intents": {}}

        with mock.patch.object(telegram_post, "channel_candidates", side_effect=candidates):
            self.assertIs(target, telegram_post.choose_unpublished([target], ledger("x"), self.NOW))
            for ct in ("soc_tg_guide", "soc_tg_mochi", "soc_tg_mochi_ko"):
                for android in (True, False):
                    old = telegram_post.compose_text(target, android=android, ct=ct)
                    with self.subTest(ct=ct, android=android):
                        self.assertIsNone(telegram_post.choose_unpublished(
                            [target], ledger(telegram_post._digest(old)), self.NOW))

    def test_paid_locales_lead_three_days_of_four_and_every_locale_stays(self):
        days = [dt.date(2026, 10, 18) + dt.timedelta(days=i) for i in range(24)]
        for zone, locales in telegram_post.TZ_LANGS.items():
            picks = [telegram_post.paid_locale_of_day(zone, d) for d in days]
            self.assertEqual(6, picks.count(None), zone)  # one long-tail day in four
            self.assertTrue(set(filter(None, picks)) <= set(locales), zone)
        asia = [telegram_post.paid_locale_of_day("asia", d) for d in days]
        self.assertGreater(asia.count("zh-Hant"), asia.count("ja"))
        self.assertGreater(asia.count("ja"), asia.count("ko"))
        self.assertGreater(asia.count("ko"), 0)
        americas = [telegram_post.paid_locale_of_day("americas", d) for d in days]
        self.assertGreater(americas.count("en-US"), americas.count("pt-BR"))
        eligible = [self.item("1", lang) for lang in ("ms", "ko", "mr-IN", "zh-Hant", "ja")] + \
                   [self.item("2", lang, "cyca") for lang in ("vi", "ja")]
        paid_day = next(d for d in days if telegram_post.paid_locale_of_day("asia", d) == "ja")
        ordered = telegram_post.paid_market_first(eligible, "asia", paid_day)
        self.assertEqual(sorted(map(id, eligible)), sorted(map(id, ordered)))  # nothing dropped
        self.assertEqual(["ja", "zh-Hant", "ko", "ms", "mr-IN"], [i["lang"] for i in ordered[:5]])
        self.assertEqual(["1"] * 5 + ["2"] * 2, [i["app"] for i in ordered])  # app rotation kept
        long_tail = next(d for d in days if telegram_post.paid_locale_of_day("asia", d) is None)
        self.assertEqual(eligible, telegram_post.paid_market_first(eligible, "asia", long_tail))

    def test_choose_unpublished_posts_the_paid_locale_of_the_day(self):
        pool = [self.item("6785004775", lang) for lang in ("mr-IN", "ms", "ko", "zh-Hant")]

        def candidates(pool_arg, channel, now):
            return pool_arg if channel == "telegram:asia" else [{"app": "7000000009"}]

        empty = {"receipts": {}, "intents": {}}
        for offset in range(8):
            now = self.NOW + dt.timedelta(days=offset)
            want = telegram_post.paid_locale_of_day("asia", now.date())
            with mock.patch.object(telegram_post, "channel_candidates", side_effect=candidates):
                picked = telegram_post.choose_unpublished(pool, empty, now)
            with self.subTest(day=now.date()):
                if want is None:
                    self.assertEqual("mr-IN", picked["lang"])  # long-tail day: the plain rotation
                elif want == "ja":
                    self.assertEqual("zh-Hant", picked["lang"])  # no ja copy: next paid locale
                else:
                    self.assertEqual(want, picked["lang"])


if __name__ == "__main__":
    unittest.main()
