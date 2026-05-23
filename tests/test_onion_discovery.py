# =============================================================================
# Tests: Onion Discovery Engine
# =============================================================================
# Testet alle Komponenten der Onion Discovery Engine (ADR-007).
#
# Ausführung:
#   python3 -m pytest tests/test_onion_discovery.py -v
# =============================================================================

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Seed Queue ───────────────────────────────────────────────────────────────


def test_seed_queue_add():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        result = sq.add_seed("http://testforum.onion", source="manual")
        assert result is True
        assert sq.total_count == 1
        assert sq.pending_count == 1


def test_seed_queue_no_duplicates():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://test.onion")
        result = sq.add_seed("http://test.onion")
        assert result is False  # Duplikat
        assert sq.total_count == 1


def test_seed_queue_get_next():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://low.onion", priority=1)
        sq.add_seed("http://high.onion", priority=10)

        # Sollte höchste Priorität zuerst holen
        seed = sq.get_next()
        assert seed is not None
        assert "high" in seed.url
        assert seed.status == "fetching"


def test_seed_queue_mark_completed():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://test.onion")
        sq.mark_completed("http://test.onion", "approved")
        assert sq.pending_count == 0


def test_seed_queue_persistence():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        seed_file = f"{tmpdir}/seeds.json"

        # Erste Instanz
        sq1 = SeedQueue(seed_file=seed_file)
        sq1.add_seed("http://persist.onion")

        # Zweite Instanz (lässt aus Datei)
        sq2 = SeedQueue(seed_file=seed_file)
        assert sq2.total_count == 1
        assert sq2.pending_count == 1


def test_seed_queue_get_stats():
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://a.onion")
        sq.add_seed("http://b.onion")
        sq.add_seed("http://c.onion")
        sq.mark_completed("http://a.onion", "approved")

        stats = sq.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 2
        assert stats.get("approved") == 1


# ─── Policy Gateway ───────────────────────────────────────────────────────────


def test_policy_allowlist():
    from onion_discovery.policy_gateway import PolicyGateway

    gateway = PolicyGateway(allowlist=["good.onion"])
    assert gateway.is_allowed("http://good.onion").allowed is True
    assert gateway.is_allowed("http://bad.onion").allowed is False


def test_policy_blocklist():
    from onion_discovery.policy_gateway import PolicyGateway

    gateway = PolicyGateway(blocklist=["evil.onion"])
    assert gateway.is_allowed("http://evil.onion").allowed is False
    assert gateway.is_allowed("http://good.onion").allowed is True


def test_policy_opt_out():
    from onion_discovery.policy_gateway import PolicyGateway

    gateway = PolicyGateway(opt_out=["dnt.onion"])
    assert gateway.is_allowed("http://dnt.onion").allowed is False


def test_policy_rate_limit():
    from onion_discovery.policy_gateway import PolicyGateway

    gateway = PolicyGateway(
        max_requests_per_host=2,
        global_delay=0.0,
    )
    # Erste zwei Requests sollten erlaubt sein
    assert gateway.is_allowed("http://test.onion/page1").allowed is True
    assert gateway.is_allowed("http://test.onion/page2").allowed is True
    # Dritter sollte wegen Host-Limit abgewiesen werden
    decision = gateway.is_allowed("http://test.onion/page3")
    assert decision.allowed is False
    assert decision.block_type == "rate_limit"


def test_policy_is_onion():
    from onion_discovery.policy_gateway import PolicyGateway

    gateway = PolicyGateway()
    assert gateway.is_onion_url("http://abc.onion") is True
    assert gateway.is_onion_url("http://example.com") is False


# ─── Link Extractor ───────────────────────────────────────────────────────────


def test_link_extractor_html():
    from onion_discovery.link_extractor import LinkExtractor

    html = """
    <html><body>
    <a href="http://forum1.onion">Forum 1</a>
    <a href="http://forum2.onion">Forum 2</a>
    <a href="http://example.com">Normal</a>
    </body></html>
    """

    extractor = LinkExtractor()
    links = extractor.extract("http://source.onion", html)

    onion_links = [link for link in links if ".onion" in link["url"]]
    assert len(onion_links) == 2
    assert onion_links[0]["anchor_text"] == "Forum 1"


def test_link_extractor_raw_text():
    from onion_discovery.link_extractor import LinkExtractor

    # v3 Onion-Adressen haben 56 Zeichen (Base32)
    v3_onion = "http://secretforumabc123456789abcdefghijklmnopqrstuvwxyz234567.onion"
    html = f"Check out {v3_onion} for details"
    extractor = LinkExtractor()
    links = extractor.extract("http://source.onion", html)
    onion_links = [link for link in links if ".onion" in link["url"]]
    assert len(onion_links) >= 1, f"Sollte Onion-Link finden, aber: {links}"


def test_link_extractor_no_duplicates():
    from onion_discovery.link_extractor import LinkExtractor

    html = """
    <a href="http://same.onion">Link 1</a>
    <a href="http://same.onion">Link 2</a>
    """
    extractor = LinkExtractor()
    links = extractor.extract("http://source.onion", html)
    same = [link for link in links if "same.onion" in link["url"]]
    assert len(same) == 1  # Dedupliziert


def test_link_extractor_relative():
    from onion_discovery.link_extractor import LinkExtractor

    html = '<a href="/page">Relative</a>'
    extractor = LinkExtractor()
    links = extractor.extract("http://forum.onion", html)
    # Relative Links ohne .onion sollten ignoriert werden
    onion_links = [link for link in links if ".onion" in link["url"]]
    assert len(onion_links) == 0


def test_is_onion():
    from onion_discovery.link_extractor import LinkExtractor

    assert LinkExtractor.is_onion("http://abc.onion") is True
    assert LinkExtractor.is_onion("http://abc.com") is False


# ─── Classifier ───────────────────────────────────────────────────────────────


def test_classifier_topic_detection():
    from onion_discovery.classifier import Classifier

    c = Classifier()
    result = c.classify(
        title="Linux Security Forum",
        content="Discussion about linux security, encryption and privacy tools.",
    )
    assert result.topic in ("technology", "forum")
    assert result.confidence >= 0.3


def test_classifier_high_risk():
    from onion_discovery.classifier import Classifier

    c = Classifier()
    result = c.classify(
        title="Marketplace",
        content="Buy drugs, weapons and counterfeit money. Best prices.",
    )
    assert result.risk_level in ("high", "critical")
    assert result.requires_human_review is True


def test_classifier_unknown_topic():
    from onion_discovery.classifier import Classifier

    c = Classifier()
    result = c.classify(title="", content="")
    assert result.topic == "unknown"
    assert result.requires_human_review is True


def test_classifier_low_risk():
    from onion_discovery.classifier import Classifier

    c = Classifier()
    result = c.classify(
        title="Technology Wiki", content="Python programming guide and tutorials."
    )
    # Default-Risiko ist "medium" für unbekannte/low-confidence Inhalte
    assert result.risk_level in ("low", "medium")
    # Technologie-Wiki sollte ohne Human Review indexierbar sein
    assert result.indexable is True


# ─── Human Review Queue ───────────────────────────────────────────────────────


def test_review_queue_add():
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        result = rq.add("id1", "http://test.onion", "Test", risk_level="high")
        assert result is True
        assert rq.pending_count == 1


def test_review_queue_approve():
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        rq.add("id1", "http://test.onion")
        assert rq.approve("id1", reviewer="tester") is True
        assert rq.pending_count == 0


def test_review_queue_reject():
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        rq.add("id1", "http://test.onion")
        assert rq.reject("id1", reviewer="tester", reason="Not relevant") is True
        assert rq.pending_count == 0


def test_review_queue_priority():
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        rq.add("low1", "http://low.onion", risk_level="low")
        rq.add("high1", "http://high.onion", risk_level="critical")

        next_item = rq.get_next_pending()
        assert next_item is not None
        assert "high" in next_item.url  # Höchstes Risiko zuerst


# ─── Discovery Pipeline ───────────────────────────────────────────────────────


@patch("onion_discovery.engine.DiscoveryPipeline.enabled")
def test_pipeline_disabled(mock_enabled):
    from onion_discovery.engine import DiscoveryPipeline

    mock_enabled.return_value = False
    pipeline = DiscoveryPipeline()
    stats = pipeline.run_once()
    assert stats["status"] == "disabled"


@patch("onion_discovery.engine.requests.Session.get")
@patch("onion_discovery.engine.DiscoveryPipeline.enabled")
def test_pipeline_full_run(mock_enabled, mock_get):
    from onion_discovery.engine import DiscoveryPipeline

    mock_enabled.return_value = True

    # Mock Fetch
    mock_response = MagicMock()
    mock_response.text = """
    <html><head><title>Test Forum</title></head>
    <body>
    <a href="http://other.onion">Other</a>
    <p>Discussion about privacy and security.</p>
    </body></html>
    """
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = DiscoveryPipeline(max_pages_per_run=1)
        pipeline.seed_queue.seed_file = f"{tmpdir}/seeds.json"
        pipeline.review_queue.queue_file = f"{tmpdir}/reviews.json"

        pipeline.add_seed("http://forum.onion")
        stats = pipeline.run_once()

        assert stats["seeds_processed"] >= 1
