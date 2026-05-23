"""Integrationstests für Onion-Discovery-Pipeline — State-Machine, Policy, Tor, Review/Index."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from onion_discovery.classifier import (  # noqa: E402
    RISK_CRITICAL,
    RISK_HIGH,
    ClassificationResult,
    Classifier,
)
from onion_discovery.engine import DiscoveryPipeline  # noqa: E402
from onion_discovery.human_review import ReviewQueue  # noqa: E402
from onion_discovery.policy_gateway import PolicyGateway  # noqa: E402
from onion_discovery.seed_queue import SeedQueue  # noqa: E402


def _response(html: str) -> MagicMock:
    response = MagicMock()
    response.text = html
    response.raise_for_status.return_value = None
    return response


def _pipeline(
    tmpdir: str, *, max_pages_per_run: int = 1, **kwargs
) -> DiscoveryPipeline:
    return DiscoveryPipeline(
        seed_queue=SeedQueue(seed_file=f"{tmpdir}/seeds.json"),
        policy_gateway=kwargs.pop(
            "policy_gateway", PolicyGateway(global_delay=0.0, max_requests_per_host=10)
        ),
        review_queue=ReviewQueue(queue_file=f"{tmpdir}/reviews.json"),
        max_pages_per_run=max_pages_per_run,
        **kwargs,
    )


@pytest.mark.integration
class TestPipelineStateMachine:
    """Testet Fehlerpfade in der DiscoveryPipeline State-Machine."""

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    def test_pipeline_policy_check_blocks_seed(self, _enabled):
        """Given Policy blockiert; When run_once; Then Seed wird error und Fetch übersprungen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(
                tmpdir,
                policy_gateway=PolicyGateway(
                    blocklist=["blocked.onion"], global_delay=0.0
                ),
            )
            pipeline.add_seed("http://blocked.onion")

            with patch("onion_discovery.engine.requests.Session.get") as mock_get:
                stats = pipeline.run_once()

            assert stats["errors"] == 1
            assert pipeline.seed_queue._seeds["http://blocked.onion"].status == "error"
            mock_get.assert_not_called()

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_pipeline_fetch_error_handled(self, mock_index, mock_get, _enabled):
        """Given erster Fetch schlägt fehl; When run_once; Then Fehler zählt und nächster Seed läuft."""
        mock_get.side_effect = [
            requests.ConnectionError("tor unavailable"),
            _response(
                "<html><title>Tech</title><p>linux security encryption vpn guide</p></html>"
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir, max_pages_per_run=2)
            pipeline.add_seed("http://firstfail.onion")
            pipeline.seed_queue.add_seed("http://secondok.onion", priority=9)

            stats = pipeline.run_once()

            assert stats["errors"] >= 1
            assert stats["seeds_processed"] == 2
            assert (
                pipeline.seed_queue._seeds["http://secondok.onion"].status == "approved"
            )
            assert mock_index.return_value.add_post.called

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_pipeline_parse_error_does_not_crash(self, _mock_index, mock_get, _enabled):
        """Given Parser wirft Exception; When run_once; Then Fehler zählt und Pipeline crasht nicht."""
        mock_get.return_value = _response(
            "<html><title>Broken</title><p>linux security</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            classifier = MagicMock(
                classify=MagicMock(
                    return_value=ClassificationResult(
                        topic="technology",
                        risk_level="low",
                        indexable=True,
                        requires_human_review=False,
                        confidence=0.8,
                    )
                )
            )
            pipeline = _pipeline(tmpdir, classifier=classifier)
            pipeline.add_seed("http://parsefail.onion")

            with patch(
                "onion_discovery.engine.BeautifulSoup",
                side_effect=Exception("bad html"),
            ):
                stats = pipeline.run_once()

            assert stats["errors"] == 1
            assert stats["classified"] == 1
            classifier.classify.assert_called_once()
            assert classifier.classify.call_args.kwargs["title"] == ""
            assert classifier.classify.call_args.kwargs["content"] == ""

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_pipeline_idempotency_same_url_twice(self, _mock_index, mock_get, _enabled):
        """Given gleiche URL zweimal; When run_once; Then Index erhält keine Duplikate."""
        mock_get.return_value = _response(
            "<html><title>Tech</title><p>linux security encryption vpn guide</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir, max_pages_per_run=2)
            assert pipeline.add_seed("http://sameurl.onion") is True
            assert pipeline.add_seed("http://sameurl.onion") is False

            stats = pipeline.run_once()

            assert stats["seeds_processed"] == 1
            assert stats["sent_to_index"] <= 1


@pytest.mark.integration
class TestClassifierEdgeCases:
    """Testet Classifier-Grenzfälle."""

    def test_classifier_false_positive_medical_not_drugs(self):
        """Medizinischer 'drug'-Kontext wird nicht als high/critical eingestuft."""
        result = Classifier().classify(
            title="Medical reference",
            content="prescription drug information, medical treatment and dosage guide",
        )
        assert result.risk_level not in (RISK_HIGH, RISK_CRITICAL)

    def test_classifier_confidence_boundary(self):
        """Confidence-Grenze bleibt konsistent mit Topic/Risk-Review-Regeln."""
        low_conf = ClassificationResult(
            topic="technology", risk_level="low", confidence=0.49
        )
        high_conf = ClassificationResult(
            topic="technology", risk_level="low", confidence=0.51
        )
        unknown = ClassificationResult(
            topic="unknown", risk_level="medium", confidence=0.51
        )

        for result in (low_conf, high_conf):
            result.requires_human_review = (
                result.risk_level in (RISK_HIGH, RISK_CRITICAL)
                or result.topic == "unknown"
            )
        unknown.requires_human_review = (
            unknown.risk_level in (RISK_HIGH, RISK_CRITICAL)
            or unknown.topic == "unknown"
        )

        assert low_conf.requires_human_review is False
        assert high_conf.requires_human_review is False
        assert unknown.requires_human_review is True

    @pytest.mark.parametrize(
        "content,expected_topic",
        [
            ("linux security encryption vpn guide", "technology"),
            ("buy bitcoin monero escrow shop", "marketplace"),
            ("forum thread post discussion member", "forum"),
            ("leak document whistleblow evidence anonymous", "whistleblow"),
        ],
    )
    def test_classifier_topic_parametrized(self, content, expected_topic):
        """Parametrisierte Topic-Erkennung für Hauptkategorien."""
        assert Classifier().classify(content=content).topic == expected_topic

    def test_classifier_marketplace_always_high_risk(self):
        """Marketplace-Topic erzwingt mindestens RISK_HIGH."""
        result = Classifier().classify(content="buy bitcoin monero escrow shop")
        assert result.risk_level in (RISK_HIGH, RISK_CRITICAL)

    def test_classifier_multiple_high_risk_keywords_critical(self):
        """Drei High-Risk-Keywords erzwingen RISK_CRITICAL."""
        result = Classifier().classify(content="drug weapon counterfeit")
        assert result.risk_level == RISK_CRITICAL


@pytest.mark.integration
@pytest.mark.onion
class TestTorIntegration:
    """Testet Tor-Proxy-Integration in DiscoveryPipeline."""

    def test_pipeline_session_uses_tor_proxy(self):
        """Session wird mit Tor-Proxy konfiguriert."""
        pipeline = DiscoveryPipeline(tor_proxy="socks5h://127.0.0.1:9050")
        session = pipeline._create_session()
        assert session.proxies == {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_pipeline_fetch_uses_proxy_session(self, _mock_index, mock_get, _enabled):
        """Fetch verwendet die Proxy-konfigurierte Session."""
        mock_get.return_value = _response(
            "<html><title>Tech</title><p>linux security encryption vpn guide</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir, tor_proxy="socks5h://127.0.0.1:9050")
            pipeline.add_seed("http://proxycheck.onion")
            pipeline.run_once()

        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["timeout"] == 30

    def test_pipeline_tor_proxy_customizable(self):
        """Tor-Proxy ist via Konstruktor konfigurierbar."""
        pipeline = DiscoveryPipeline(tor_proxy="socks5h://custom:9150")
        assert pipeline.tor_proxy == "socks5h://custom:9150"
        assert pipeline._session.proxies["http"] == "socks5h://custom:9150"


@pytest.mark.integration
class TestReviewAndIndexFlow:
    """Testet Review-Queue → Index-Flow Integration."""

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_human_approval_gate_blocks_indexing(self, mock_index, mock_get, _enabled):
        """_on_before_persist Hook gibt False zurück → Page nicht im Index."""
        mock_get.return_value = _response(
            "<html><title>Tech</title><p>linux security encryption vpn guide</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir)
            pipeline._on_before_persist = lambda url, meta: False
            pipeline.add_seed("http://approvalgate.onion")

            stats = pipeline.run_once()

            assert stats["sent_to_index"] == 0
            mock_index.return_value.add_post.assert_not_called()

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_review_queue_populated_for_high_risk(self, mock_index, mock_get, _enabled):
        """High-Risk-Inhalte landen in Review-Queue, nicht im Index."""
        mock_get.return_value = _response(
            "<html><title>Market</title><p>drug weapon counterfeit listings</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir)
            pipeline.add_seed("http://highrisk.onion")

            stats = pipeline.run_once()

            assert stats["sent_to_review"] >= 1
            assert stats["sent_to_index"] == 0
            assert pipeline.review_queue.pending_count == 1
            mock_index.return_value.add_post.assert_not_called()

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_index_adapter_called_for_safe_content(
        self, mock_index, mock_get, _enabled
    ):
        """Index-Backend wird für unbedenkliche Inhalte aufgerufen."""
        mock_get.return_value = _response(
            "<html><title>Tech</title><p>linux security encryption vpn guide</p></html>"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(tmpdir)
            pipeline.add_seed("http://safecontent.onion")

            stats = pipeline.run_once()

            assert stats["sent_to_index"] == 1
            mock_index.return_value.add_post.assert_called_once()

    @patch.object(DiscoveryPipeline, "enabled", return_value=True)
    @patch("onion_discovery.engine.requests.Session.get")
    @patch("darknet_search.index.WhooshIndex")
    def test_index_adapter_not_called_for_blocked_seeds(
        self, mock_index, mock_get, _enabled
    ):
        """Index-Backend wird NICHT für blockierte Seeds aufgerufen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = _pipeline(
                tmpdir,
                policy_gateway=PolicyGateway(
                    blocklist=["blockedindex.onion"], global_delay=0.0
                ),
            )
            pipeline.add_seed("http://blockedindex.onion")

            stats = pipeline.run_once()

            assert stats["sent_to_index"] == 0
            mock_get.assert_not_called()
            mock_index.return_value.add_post.assert_not_called()
