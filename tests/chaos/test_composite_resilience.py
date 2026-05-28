"""Chaos-Engineering-Tests für CompositeRetriever — Timeout-Kaskaden, Race Conditions, Edge Cases."""

import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from search.composite import CompositeRetriever


class _Future:
    """Kontrolliertes Future-Double für ThreadPoolExecutor-Tests."""

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def result(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.value


class _Executor:
    """Executor-Double, das Futures anhand des Backend-Methodennamens zurückgibt."""

    def __init__(self, *args, **kwargs):
        self.futures = {
            "_search_searxng": _Future(error=TimeoutError("SearXNG hängt")),
            "_search_darknet": _Future(
                [
                    {
                        "url": "darknet://fast/1",
                        "title": "Schnelles Darknet-Ergebnis",
                        "source": "Darknet Forum",
                        "score": 0.7,
                    }
                ]
            ),
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        return self.futures[fn.__name__]


@pytest.mark.chaos
class TestCompositeTimeoutCascade:
    """Timeout-Kaskaden: Langsame Backends blockieren nicht das Gesamtergebnis."""

    @pytest.mark.xfail(
        reason="CompositeRetriever behandelt Future-Timeouts derzeit nicht isoliert."
    )
    @patch("concurrent.futures.ThreadPoolExecutor", _Executor)
    def test_timeout_searxng_slow_darknet_fast(self):
        """SearXNG hängt, Darknet antwortet sofort → Ergebnis wird nicht blockiert."""
        r = CompositeRetriever("test")
        r.darknet_enabled = True

        results = r.search(max_results=10)

        assert results == [
            {
                "url": "darknet://fast/1",
                "title": "Schnelles Darknet-Ergebnis",
                "source": "Darknet Forum",
                "score": 0.7,
            }
        ]

    @pytest.mark.xfail(
        reason="CompositeRetriever fängt Future-TimeoutError derzeit nicht ab."
    )
    @patch("concurrent.futures.ThreadPoolExecutor")
    def test_timeout_both_slow_still_returns(self, mock_executor):
        """Beide Backends hängen → search() returned trotzdem eine leere Liste."""
        executor = mock_executor.return_value.__enter__.return_value
        executor.submit.side_effect = [
            _Future(error=TimeoutError("SearXNG hängt")),
            _Future(error=TimeoutError("Darknet hängt")),
        ]

        r = CompositeRetriever("test")
        r.darknet_enabled = True

        assert r.search(max_results=10) == []


@pytest.mark.chaos
class TestCompositePartialFailure:
    """Partielle Ausfälle: Ein Backend down, anderes liefert."""

    @patch("search.composite.DarknetRetriever")
    @patch("search.composite.create_session")
    def test_searxng_500_darknet_ok(self, mock_create, mock_darknet):
        """SearXNG 500er, Darknet gültig → Graceful Degradation."""
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_create.return_value = mock_session
        mock_darknet.return_value.search.return_value = [
            {"url": "darknet://ok/1", "title": "OK", "source": "Darknet Forum"}
        ]

        r = CompositeRetriever("test")
        r.darknet_enabled = True

        assert r.search(max_results=10) == [
            {"url": "darknet://ok/1", "title": "OK", "source": "Darknet Forum"}
        ]


@pytest.mark.chaos
class TestCompositeRaceConditions:
    """Race Conditions: Thread-Safety der Merge-Logik."""

    def test_concurrent_merge_no_duplicate_keys(self):
        """Beide Backends antworten gleichzeitig → keine Duplikate in Result-List."""
        barrier = threading.Barrier(2)

        def searx(_max_results):
            barrier.wait(timeout=1)
            return [
                {"url": "http://race.local/item", "source": "SearXNG", "score": 0.9}
            ]

        def darknet(_max_results):
            barrier.wait(timeout=1)
            return [
                {
                    "url": "http://race.local/item",
                    "source": "Darknet Forum",
                    "score": 0.5,
                }
            ]

        r = CompositeRetriever("race")
        with (
            patch.object(r, "_search_searxng", side_effect=searx),
            patch.object(r, "_search_darknet", side_effect=darknet),
        ):
            results = r.search(max_results=10)

        assert [item["url"] for item in results] == ["http://race.local/item"]


@pytest.mark.chaos
class TestCompositeEdgeCases:
    """Edge Cases: Leere Ergebnisse, Schema-Deduplizierung, Scoring."""

    @patch("search.composite.create_session")
    def test_both_empty_results_no_division_by_zero(self, mock_create):
        """Beide Services liefern [] → keine Division by Zero in Scoring."""
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"results": []}
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_create.return_value = mock_session

        r = CompositeRetriever("test")
        r.darknet_enabled = False

        results = r.search(max_results=10)

        assert results == []

    def test_deduplication_http_vs_https(self):
        """Gleiche URL mit http und https bleibt aktuell getrennt dokumentiert."""
        results = [
            {"url": "http://example.com", "title": "A"},
            {"url": "https://example.com", "title": "A"},
        ]

        deduped = CompositeRetriever._deduplicate(results)

        assert len(deduped) == 2
        assert {r["url"] for r in deduped} == {
            "http://example.com",
            "https://example.com",
        }
