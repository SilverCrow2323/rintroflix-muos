import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from rintroflix.epg import EPG, _parse_xmltv_time
from rintroflix.m3u import Channel


class XmltvParserTests(unittest.TestCase):
    def test_timezone_offset_is_converted_to_utc(self):
        actual = _parse_xmltv_time("20261125110000 +0100")
        expected = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc).timestamp()
        self.assertEqual(actual, expected)

    def test_negative_offset_is_converted_to_utc(self):
        actual = _parse_xmltv_time("20261125110000 -0530")
        expected = datetime(2026, 11, 25, 16, 30, tzinfo=timezone.utc).timestamp()
        self.assertEqual(actual, expected)

    def test_rejects_malformed_or_out_of_range_offsets(self):
        for value in (
            "20261125110000 UTC",
            "20261125110000 +1460",
            "20261125110000 +1401",
            "20261125110000 +0160",
            "20261125110000 +0100 extra",
            "20261125110000junk",
        ):
            with self.subTest(value=value):
                self.assertIsNone(_parse_xmltv_time(value))

    def test_rejects_invalid_calendar_values(self):
        self.assertIsNone(_parse_xmltv_time("20260230120000"))
        self.assertIsNone(_parse_xmltv_time("20261125256000"))

    def test_namespaced_xmltv_channel_and_programme_are_indexed(self):
        payload = b"""<?xml version="1.0"?>
        <tv xmlns="urn:example:xmltv">
          <channel id="rai-uno">
            <display-name>Rai 1</display-name>
          </channel>
          <programme channel="rai-uno" start="20261125110000 +0100" stop="20261125113000 +0100">
            <title>Telegiornale</title>
            <desc>Edizione delle undici</desc>
          </programme>
        </tv>"""
        epg = EPG()
        epg._parse(payload)
        channel = Channel("Rai 1", "https://example.invalid/live", tvg_id="rai-uno")
        items = epg.programmes_for(channel)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Telegiornale")
        self.assertEqual(items[0].desc, "Edizione delle undici")
        self.assertEqual(items[0].stop - items[0].start, 1800)

    def test_invalid_stop_does_not_create_a_fallback_programme(self):
        payload = b"""<tv><channel id="x"><display-name>X</display-name></channel>
        <programme channel="x" start="20261125110000" stop="20261125100000">
          <title>Invalid</title>
        </programme></tv>"""
        epg = EPG()
        epg._parse(payload)
        self.assertEqual(epg.by_key, {})

    def test_missing_stop_uses_documented_half_hour_fallback(self):
        payload = b"""<tv><channel id="x"><display-name>X</display-name></channel>
        <programme channel="x" start="20261125110000"><title>Short</title></programme></tv>"""
        epg = EPG()
        epg._parse(payload)
        self.assertEqual(epg.by_key["x"][0].stop - epg.by_key["x"][0].start, 1800)

    def test_malformed_source_does_not_partially_mutate_existing_index(self):
        epg = EPG()
        epg._parse(b"""<tv><channel id="stable"><display-name>Stable</display-name></channel>
        <programme channel="stable" start="20261125110000"><title>Keep</title></programme></tv>""")
        before = {key: list(value) for key, value in epg.by_key.items()}
        broken = b"""<tv><channel id="partial"><display-name>Partial</display-name></channel>
        <programme channel="partial" start="20261125110000"><title>Do not keep</title></programme><broken>"""
        with self.assertRaises(ET.ParseError):
            epg._parse(broken)
        self.assertEqual(epg.by_key, before)
        self.assertNotIn("partial", epg.by_key)


if __name__ == "__main__":
    unittest.main()
