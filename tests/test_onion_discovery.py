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


# ─── SeedQueue untested pure-logic paths ─────────────────────────────────


def test_seed_queue_add_seeds_batch():
    """add_seeds fügt mehrere Seeds im Batch hinzu."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        count = sq.add_seeds(
            ["http://a.onion", "http://b.onion", "http://c.onion"],
            source="file",
            priority=7,
        )
        assert count == 3
        assert sq.total_count == 3
        assert sq.pending_count == 3


def test_seed_queue_add_seeds_with_duplicates():
    """add_seeds ignoriert Duplikate im Batch."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://existing.onion")
        count = sq.add_seeds(
            [
                "http://existing.onion",
                "http://new.onion",
                "http://new.onion",
            ]
        )
        assert count == 1
        assert sq.total_count == 2


def test_seed_queue_add_seeds_empty_batch():
    """add_seeds mit leerer Liste gibt 0 zurück."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        assert sq.add_seeds([], source="file") == 0


def test_seed_queue_mark_error():
    """mark_error setzt status='error'."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://broken.onion")
        sq.mark_error("http://broken.onion", "Connection refused")
        assert sq.pending_count == 0
        assert sq.get_stats().get("error") == 1


def test_seed_queue_mark_error_nonexistent():
    """mark_error für nicht existierende URL ist No-Op."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.mark_error("http://nonexistent.onion", "oops")
        assert sq.total_count == 0


def test_seed_queue_get_next_empty():
    """get_next auf leerer Queue gibt None."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        assert sq.get_next() is None


def test_seed_queue_get_next_max_priority_filter():
    """get_next(max_priority=...) filtert nach Priorität."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://low.onion", priority=2)
        sq.add_seed("http://high.onion", priority=9)

        seed = sq.get_next(max_priority=5)
        assert seed is not None
        assert "low" in seed.url


def test_seed_queue_add_priority_clamping():
    """Priorität wird auf [1, 10] geclampt."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        sq.add_seed("http://below.onion", priority=-5)
        sq.add_seed("http://above.onion", priority=100)

        seed = sq.get_next()
        assert seed is not None
        assert "above" in seed.url  # priority 100→10 ist höher


def test_seed_queue_add_with_tags():
    """add_seed mit Tags speichert diese."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        seed_file = f"{tmpdir}/seeds.json"
        sq = SeedQueue(seed_file=seed_file)
        sq.add_seed("http://tagged.onion", tags=["forum", "high-value"])

        sq2 = SeedQueue(seed_file=seed_file)
        seed = list(sq2._seeds.values())[0]
        assert "forum" in seed.tags


def test_seed_queue_url_trailing_slash_dedup():
    """Trailing-Slash-Varianten werden als Duplikat erkannt."""
    from onion_discovery.seed_queue import SeedQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        sq = SeedQueue(seed_file=f"{tmpdir}/seeds.json")
        assert sq.add_seed("http://test.onion/") is True
        assert sq.add_seed("http://test.onion") is False
        assert sq.total_count == 1


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


# ─── Human Review Queue (additional pure-logic paths) ──────────────────────


def test_review_queue_add_duplicate():
    """add() returns False when item_id already exists."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        assert rq.add("id1", "http://test.onion") is True
        assert rq.add("id1", "http://test.onion") is False
        assert rq.pending_count == 1


def test_review_queue_get_next_pending_empty():
    """get_next_pending() returns None when queue is empty."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        assert rq.get_next_pending() is None


def test_review_queue_get_pending_items_order():
    """get_pending_items() returns oldest-first."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        rq.add("first", "http://first.onion")
        rq.add("second", "http://second.onion")

        items = rq.get_pending_items()
        assert len(items) == 2
        assert items[0].id == "first"
        assert items[1].id == "second"


def test_review_queue_get_pending_items_limit():
    """get_pending_items() respects limit."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        for i in range(10):
            rq.add(f"id{i}", f"http://url{i}.onion")

        items = rq.get_pending_items(limit=3)
        assert len(items) == 3


def test_review_queue_approve_nonexistent():
    """approve() returns False for nonexistent id."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        assert rq.approve("nonexistent", reviewer="tester") is False


def test_review_queue_reject_nonexistent():
    """reject() returns False for nonexistent id."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        assert rq.reject("nonexistent", reviewer="tester") is False


def test_review_queue_get_stats():
    """get_stats() returns correct counts."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        rq.add("a", "http://a.onion")
        rq.add("b", "http://b.onion")
        rq.add("c", "http://c.onion")

        rq.approve("a", reviewer="tester")
        rq.reject("b", reviewer="tester", reason="nope")

        stats = rq.get_stats()
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 1


def test_review_queue_pending_count_property():
    """pending_count returns correct count."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        assert rq.pending_count == 0

        rq.add("a", "http://a.onion")
        assert rq.pending_count == 1
        rq.approve("a", reviewer="tester")
        assert rq.pending_count == 0


def test_review_queue_content_truncation():
    """add() truncates content to 500 chars."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        long_content = "x" * 1000
        rq.add("id1", "http://test.onion", content=long_content)
        assert len(rq._items["id1"].content_preview) == 500


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

# ─── Discovery Pipeline — enabled() pure-logic ───────────────────────────


def test_pipeline_enabled_truthy():
    """enabled() returns True when ONION_DISCOVERY_ENABLED='true'."""
    from onion_discovery.engine import DiscoveryPipeline

    with patch.dict(os.environ, {"ONION_DISCOVERY_ENABLED": "true"}):
        p = DiscoveryPipeline()
        assert p.enabled() is True


def test_pipeline_enabled_truthy_one():
    """enabled() returns True for '1'."""
    from onion_discovery.engine import DiscoveryPipeline

    with patch.dict(os.environ, {"ONION_DISCOVERY_ENABLED": "1"}):
        p = DiscoveryPipeline()
        assert p.enabled() is True


def test_pipeline_enabled_case_insensitive():
    """enabled() is case-insensitive via .lower()."""
    from onion_discovery.engine import DiscoveryPipeline

    with patch.dict(os.environ, {"ONION_DISCOVERY_ENABLED": "TRUE"}):
        p = DiscoveryPipeline()
        assert p.enabled() is True


def test_pipeline_enabled_falsy():
    """enabled() returns False for 'false'."""
    from onion_discovery.engine import DiscoveryPipeline

    with patch.dict(os.environ, {"ONION_DISCOVERY_ENABLED": "false"}):
        p = DiscoveryPipeline()
        assert p.enabled() is False


def test_pipeline_enabled_unset_default():
    """enabled() returns False when env var absent."""
    from onion_discovery.engine import DiscoveryPipeline

    saved = os.environ.pop("ONION_DISCOVERY_ENABLED", None)
    try:
        p = DiscoveryPipeline()
        assert p.enabled() is False
    finally:
        if saved is not None:
            os.environ["ONION_DISCOVERY_ENABLED"] = saved


# ─── Human Review Queue — _load error handling ───────────────────────────


def test_review_queue_load_corrupted_json():
    """_load() handles JSONDecodeError — empty queue, no crash."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        queue_file = f"{tmpdir}/reviews.json"
        with open(queue_file, "w") as f:
            f.write("{this is not valid json [[[")

        rq = ReviewQueue(queue_file=queue_file)
        assert rq.pending_count == 0


def test_review_queue_load_os_error():
    """_load() handles OSError during open — empty queue."""
    from onion_discovery.human_review import ReviewQueue

    with patch("os.path.exists", return_value=True),          patch("builtins.open", side_effect=OSError("Permission denied")):
        rq = ReviewQueue(queue_file="/fake/reviews.json")
        assert rq.pending_count == 0


def test_review_queue_add_defaults_only():
    """add() with only item_id+url builds ReviewItem with correct defaults."""
    from onion_discovery.human_review import ReviewQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        rq = ReviewQueue(queue_file=f"{tmpdir}/reviews.json")
        result = rq.add("min_id", "http://minimal.onion")
        assert result is True

        item = rq._items["min_id"]
        assert item.title == ""
        assert item.content_preview == ""
        assert item.risk_level == "medium"
        assert item.status == "pending"
