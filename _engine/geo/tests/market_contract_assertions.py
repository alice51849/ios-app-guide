import re


def assert_blocked_record(test, record, url_fields=("canonical_app_store_url", "app_store_url")):
    for field in url_fields:
        test.assertIn(field, record)
        test.assertIsNone(record[field], field)
    state = record["market_availability"]
    test.assertEqual(state["state"], "MARKET_UNAVAILABLE_OR_UNVERIFIED")
    test.assertEqual(state["reason"], "MARKET_NOT_IN_APPLE_MEDIA_SERVICES")
    test.assertEqual(state["value"], "N/A")
    test.assertIs(state["content_retained"], True)
    test.assertIs(state["publishable"], False)
    test.assertIs(state["facts_allowed"], False)
    test.assertEqual(state["outbox_count"], 0)
    evidence = state["evidence"]
    test.assertEqual(evidence["source_url"], "https://support.apple.com/en-us/118205")
    test.assertEqual(evidence["country"], "BD")
    test.assertEqual(evidence["observed_at"], "2026-09-12")
    test.assertEqual(evidence["apple_media_services_markets"], 174)
    test.assertIs(evidence["country_listed"], False)
    test.assertEqual(evidence["lookup_app_results"], 0)
    test.assertEqual(evidence["lookup_control_results"], 0)


def assert_blocked_page(test, source):
    test.assertNotIn("apps.apple.com", source.lower())
    test.assertNotIn("itunes.apple.com", source.lower())
    test.assertNotRegex(source, r'app-store-(?:qr|facts)')
    test.assertNotIn('name="apple-itunes-app"', source)
    notes = re.findall(r'<p\b[^>]*class="market-availability"[^>]*>.*?</p>', source, re.S)
    test.assertEqual(len(notes), 1)
    test.assertIn('data-market-state="MARKET_UNAVAILABLE_OR_UNVERIFIED"', notes[0])
    test.assertIn('data-market-reason="MARKET_NOT_IN_APPLE_MEDIA_SERVICES"', notes[0])
    test.assertIn('data-market-evidence="https://support.apple.com/en-us/118205"', notes[0])
    test.assertIn("Apple App Store এখনো বাংলাদেশে চালু হয়নি", notes[0])
    test.assertIn("সরাসরি ডাউনলোড লিঙ্ক দেওয়া সম্ভব নয়।", notes[0])
    test.assertNotRegex(source, r'href=["\'](?:None|null|)["\']')
