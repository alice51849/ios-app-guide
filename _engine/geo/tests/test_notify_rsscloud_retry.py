import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notify_rsscloud


class RssCloudRetryTests(unittest.TestCase):
    transient = (
        "The ping was cancelled because there was an error reading the resource "
        "at URL https://example.com/rss.xml."
    )

    @staticmethod
    def response(success, message):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = json.dumps(
            {"success": success, "msg": message}
        ).encode()
        return response

    def test_resource_fetch_failure_retries_before_recording_receipt(self):
        receipts = []
        with (
            mock.patch.object(
                notify_rsscloud.urllib.request, "urlopen",
                side_effect=[
                    self.response(False, self.transient),
                    self.response(True, "accepted"),
                ],
            ) as request,
            mock.patch.object(notify_rsscloud.time, "sleep") as sleep,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                "accepted",
                notify_rsscloud.ping(
                    topic="https://example.com/rss.xml", attempts=3,
                    delay=2, receipt_sink=receipts.append,
                ),
            )
        self.assertEqual(2, request.call_count)
        sleep.assert_called_once_with(2)
        self.assertEqual(1, len(receipts))
        self.assertEqual(64, len(receipts[0]["response_sha256"]))
        self.assertEqual(
            request.call_args_list[0].args[0].full_url,
            request.call_args_list[1].args[0].full_url,
        )
        self.assertEqual(
            request.call_args_list[0].args[0].data,
            request.call_args_list[1].args[0].data,
        )

    def test_repeated_resource_failure_stays_failed_without_receipt(self):
        receipts = []
        with (
            mock.patch.object(
                notify_rsscloud.urllib.request, "urlopen",
                return_value=self.response(False, self.transient),
            ) as request,
            mock.patch.object(notify_rsscloud.time, "sleep") as sleep,
            redirect_stdout(io.StringIO()),
        ):
            with self.assertRaisesRegex(RuntimeError, "after 3 attempts.*error reading"):
                notify_rsscloud.ping(attempts=3, receipt_sink=receipts.append)
        self.assertEqual(3, request.call_count)
        self.assertEqual(2, sleep.call_count)
        self.assertEqual([], receipts)

    def test_permanent_service_rejection_does_not_retry(self):
        with (
            mock.patch.object(
                notify_rsscloud.urllib.request, "urlopen",
                return_value=self.response(False, "Invalid feed URL"),
            ) as request,
            mock.patch.object(notify_rsscloud.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "after 1 attempts.*Invalid feed URL"):
                notify_rsscloud.ping(attempts=3)
        request.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
