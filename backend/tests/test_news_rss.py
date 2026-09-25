from datetime import datetime, timezone

from app.providers.news_rss import parse_feed
from app.services.news_classifier import classify, tag_currencies

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Fed holds rates, signals inflation remains elevated</title>
  <link>https://example.com/fed-holds</link>
  <description>The Federal Reserve kept rates unchanged and warned inflation risks remain to the upside.</description>
  <pubDate>Mon, 01 Sep 2026 14:30:00 GMT</pubDate>
</item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
  <title>ECB signals further easing as growth slows</title>
  <link href="https://example.com/ecb-easing"/>
  <summary>Policymakers hinted at more cuts.</summary>
  <updated>2026-09-01T10:00:00Z</updated>
</entry>
</feed>"""


def test_parses_rss_2_0():
    items = parse_feed(RSS_SAMPLE, source="Test Feed", currency="USD")
    assert len(items) == 1
    assert items[0].headline == "Fed holds rates, signals inflation remains elevated"
    assert items[0].source_url == "https://example.com/fed-holds"
    assert items[0].published_at.tzinfo is not None


def test_parses_atom():
    items = parse_feed(ATOM_SAMPLE, source="Test Feed", currency="EUR")
    assert len(items) == 1
    assert items[0].source_url == "https://example.com/ecb-easing"


def test_malformed_xml_returns_empty_not_raises():
    assert parse_feed("<not valid xml", source="x", currency=None) == []


def test_classify_hawkish_headline():
    info = classify("Fed hikes rates, inflation remains elevated")
    assert info["tone"] > 0
    assert info["category"] in ("central_bank", "inflation")
    assert info["impact"] in ("high", "medium")


def test_classify_dovish_headline():
    info = classify("Central bank cuts rates as recession fears grow")
    assert info["tone"] < 0


def test_tag_currencies_multi():
    tags = tag_currencies("ECB and Bank of England both signal caution amid euro area slowdown")
    assert "EUR" in tags and "GBP" in tags
