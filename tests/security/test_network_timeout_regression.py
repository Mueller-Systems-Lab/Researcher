"""Security regression tests for network timeout handling.

All tests are local/mocked/static. No external network calls are made.
"""

import ast
import concurrent.futures
from pathlib import Path
from unittest.mock import patch

from scrapers.http_session import TimeoutConfig, create_session
from search.composite import CompositeRetriever

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_HTTP_PATHS = (
    "config",
    "crawlers",
    "darknet_search",
    "search",
    "dashboard",
    "vectordb",
    "mcp_tools",
    "onion_discovery",
    "scripts",
    "scrapers",
    "searcher_pipeline",
    "research_planner",
)


class _FakeFuture:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def result(self):
        if self._exc is not None:
            raise self._exc
        return self._result


class _FakeExecutor:
    def __init__(self, *args, **kwargs):
        self.futures = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, func, max_results):
        if func.__name__ == "_search_searxng":
            future = _FakeFuture(exc=concurrent.futures.TimeoutError())
        else:
            future = _FakeFuture(
                result=[
                    {
                        "url": "darknet://forum/thread/1",
                        "title": "partial",
                        "score": 1,
                    }
                ]
            )
        self.futures.append(future)
        return future


def test_composite_retriever_handles_backend_timeout_with_partial_results():
    """A backend TimeoutError must not discard already available results."""
    retriever = CompositeRetriever("timeout regression")

    def fake_as_completed(future_map):
        return list(future_map)

    with (
        patch("concurrent.futures.ThreadPoolExecutor", _FakeExecutor),
        patch("concurrent.futures.as_completed", fake_as_completed),
    ):
        results = retriever.search(max_results=5)

    assert results == [
        {"url": "darknet://forum/thread/1", "title": "partial", "score": 1}
    ]


def test_http_session_sets_default_and_custom_timeout_configuration():
    """Created sessions expose explicit connect/read timeout configuration."""
    default_session = create_session()
    custom_session = create_session(timeout=TimeoutConfig(connect=2.5, read=7.5))

    assert default_session.timeout == (10.0, 30.0)
    assert custom_session.timeout == (2.5, 7.5)


def _has_timeout_keyword(call: ast.Call) -> bool:
    return any(keyword.arg == "timeout" for keyword in call.keywords)


def _is_requests_call(call: ast.Call) -> bool:
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr in {"get", "post", "put", "delete", "head", "request"}
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "requests"
    )


def _is_urlopen_call(call: ast.Call) -> bool:
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "urlopen"
        and isinstance(call.func.value, ast.Attribute)
        and call.func.value.attr == "request"
        and isinstance(call.func.value.value, ast.Name)
        and call.func.value.value.id == "urllib"
    )


def _is_session_http_call(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute):
        return False
    if call.func.attr not in {"get", "post", "put", "delete", "head", "request"}:
        return False
    value = call.func.value
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id == "create_session"
    if isinstance(value, ast.Name):
        return value.id in {"session", "_session"}
    if isinstance(value, ast.Attribute):
        return value.attr in {"session", "_session"}
    return False


def test_project_external_http_calls_use_explicit_timeout():
    """Project-owned external HTTP calls must pass an explicit timeout argument."""
    violations = []
    files = []
    for rel_path in PROJECT_HTTP_PATHS:
        root = REPO_ROOT / rel_path
        if root.exists():
            files.extend(root.rglob("*.py"))

    for path in sorted(files):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (
                _is_requests_call(node)
                or _is_urlopen_call(node)
                or _is_session_http_call(node)
            ):
                continue
            if not _has_timeout_keyword(node):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert not violations, "HTTP calls without explicit timeout: " + ", ".join(
        violations
    )
