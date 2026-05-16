# =============================================================================
# Tests: MCP Tools (T-016)
# =============================================================================
# Testet alle 5 MCP-Tools.
#
# Ausführung:
#   python3 -m pytest tests/test_mcp_tools.py -v
# =============================================================================

import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Registry ─────────────────────────────────────────────────────────────────


def test_registry_init():
    from mcp_tools.registry import init_tools, list_tools, get_tool, get_all_manifests

    init_tools()
    tools = list_tools()
    assert len(tools) == 5
    assert "web-fetch" in tools
    assert "evidence-store" in tools
    assert "claim-validator" in tools
    assert "audit-log" in tools
    assert "human-review-request" in tools

    manifests = get_all_manifests()
    assert len(manifests) == 5

    tool = get_tool("web-fetch")
    assert tool is not None

    missing = get_tool("nonexistent")
    assert missing is None


def test_registry_run_tool():
    from mcp_tools.registry import init_tools, run_tool, list_tools

    init_tools()
    result = run_tool("nonexistent", {})
    assert result["success"] is False

    # evidence-store ohne action
    result = run_tool("evidence-store", {})
    assert result["success"] is False
    assert "action" in result.get("error", "")


# ─── WebFetch ─────────────────────────────────────────────────────────────────


@patch("mcp_tools.web_fetch.requests.Session.get")
def test_web_fetch_success(mock_get):
    from mcp_tools.web_fetch import WebFetchTool

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = """
    <html><head><title>Test Page</title></head>
    <body><p>Hello World</p><h1>Research Content</h1></body></html>
    """
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    tool = WebFetchTool()
    result = tool.run({"url": "http://example.com"})

    assert result["success"] is True
    assert "text" in result["data"]
    assert (
        "Research Content" in result["data"]["text"]
        or "Hello World" in result["data"]["text"]
    )


def test_web_fetch_no_url():
    from mcp_tools.web_fetch import WebFetchTool

    tool = WebFetchTool()
    result = tool.run({})
    assert result["success"] is False
    assert "url" in result.get("error", "")


def test_web_fetch_onion_blocked():
    from mcp_tools.web_fetch import WebFetchTool

    tool = WebFetchTool()
    result = tool.run({"url": "http://darkforum.onion"})
    assert result["success"] is False
    assert "Onion" in result.get("error", "")


@patch("mcp_tools.web_fetch.requests.Session.get")
def test_web_fetch_connection_error(mock_get):
    from mcp_tools.web_fetch import WebFetchTool

    from requests.exceptions import ConnectionError

    mock_get.side_effect = ConnectionError("DNS failed")

    tool = WebFetchTool()
    result = tool.run({"url": "http://example.com"})
    assert result["success"] is False


# ─── EvidenceStore ────────────────────────────────────────────────────────────


def test_evidence_store_no_action():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({})
    assert result["success"] is False


def test_evidence_store_store_no_claim():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({"action": "store"})
    assert result["success"] is False
    assert "claim" in result.get("error", "")


def test_evidence_store_store_no_embedding():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({"action": "store", "claim": "Test claim"})
    assert result["success"] is False
    assert "embedding" in result.get("error", "")


def test_evidence_store_search_no_embedding():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({"action": "search"})
    assert result["success"] is False


def test_evidence_store_stats():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({"action": "stats"})
    assert result["success"] is True
    assert "total_evidence" in result["data"]


def test_evidence_store_unknown_action():
    from mcp_tools.evidence_store import EvidenceStore

    tool = EvidenceStore()
    result = tool.run({"action": "invalid"})
    assert result["success"] is False


# ─── ClaimValidator ───────────────────────────────────────────────────────────


def test_claim_validator_no_claim():
    from mcp_tools.claim_validator import ClaimValidator

    tool = ClaimValidator()
    result = tool.run({})
    assert result["success"] is False


@patch("mcp_tools.claim_validator.ClaimValidator.run")
def test_claim_validator_confidence(mock_run):
    """Testet die Confidence-Berechnungslogik isoliert."""
    from mcp_tools.claim_validator import ClaimValidator

    validator = ClaimValidator()
    # _assess testen
    assert validator._assess(0.8) == "gut belegt"
    assert validator._assess(0.5) == "teilweise belegt"
    assert validator._assess(0.2) == "schwach belegt"
    assert validator._assess(0.0) == "nicht belegt"


# ─── AuditLog ─────────────────────────────────────────────────────────────────


def test_audit_log_no_action():
    from mcp_tools.audit_log import AuditLog

    tool = AuditLog()
    result = tool.run({})
    assert result["success"] is False


def test_audit_log_write_no_event():
    from mcp_tools.audit_log import AuditLog

    tool = AuditLog()
    result = tool.run({"action": "write"})
    assert result["success"] is False


def test_audit_log_write_and_read():
    from mcp_tools.audit_log import AuditLog
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = f"{tmpdir}/audit.jsonl"
        tool = AuditLog(log_file=log_file)

        # Schreiben
        result = tool.run(
            {
                "action": "write",
                "event": "test_event",
                "actor": "pytest",
                "details": {"key": "value"},
            }
        )
        assert result["success"] is True

        # Lesen
        result = tool.run({"action": "read", "limit": 10})
        assert result["success"] is True
        assert result["data"]["count"] >= 1
        assert result["data"]["entries"][0]["event"] == "test_event"


def test_audit_log_stats():
    from mcp_tools.audit_log import AuditLog
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = f"{tmpdir}/audit.jsonl"
        tool = AuditLog(log_file=log_file)
        tool.run(
            {
                "action": "write",
                "event": "event1",
            }
        )
        tool.run(
            {
                "action": "write",
                "event": "event2",
            }
        )

        result = tool.run({"action": "stats"})
        assert result["success"] is True
        assert result["data"]["total_entries"] == 2


def test_audit_log_empty_read():
    from mcp_tools.audit_log import AuditLog
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tool = AuditLog(log_file=f"{tmpdir}/empty.jsonl")
        result = tool.run({"action": "read"})
        assert result["success"] is True
        assert result["data"]["count"] == 0


# ─── HumanReview ──────────────────────────────────────────────────────────────


def test_human_review_no_action():
    from mcp_tools.human_review import HumanReviewTool

    tool = HumanReviewTool()
    result = tool.run({})
    assert result["success"] is False


def test_human_review_request_no_url():
    from mcp_tools.human_review import HumanReviewTool

    tool = HumanReviewTool()
    result = tool.run({"action": "request"})
    assert result["success"] is False


def test_human_review_request_and_approve():
    from mcp_tools.human_review import HumanReviewTool
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_file = os.environ.get("ONION_REVIEW_FILE")
        os.environ["ONION_REVIEW_FILE"] = f"{tmpdir}/reviews.json"
        try:
            tool = HumanReviewTool()
            tool.review_queue.queue_file = f"{tmpdir}/reviews.json"

            # Request
            result = tool.run(
                {
                    "action": "request",
                    "url": "http://test.onion/page",
                    "title": "Test Page",
                    "risk_level": "high",
                    "reason": "High risk content",
                }
            )
            assert result["success"] is True
            item_id = result["data"]["item_id"]

            # List Pending
            result = tool.run({"action": "list_pending"})
            assert result["success"] is True
            assert result["data"]["pending"] >= 1

            # Approve
            result = tool.run(
                {
                    "action": "approve",
                    "item_id": item_id,
                    "reviewer": "pytest",
                }
            )
            assert result["success"] is True

            # Stats
            result = tool.run({"action": "stats"})
            assert result["success"] is True
        finally:
            if old_file is not None:
                os.environ["ONION_REVIEW_FILE"] = old_file
            else:
                del os.environ["ONION_REVIEW_FILE"]


def test_human_review_request_and_reject():
    from mcp_tools.human_review import HumanReviewTool
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_file = os.environ.get("ONION_REVIEW_FILE")
        os.environ["ONION_REVIEW_FILE"] = f"{tmpdir}/reviews.json"
        try:
            tool = HumanReviewTool()
            tool.review_queue.queue_file = f"{tmpdir}/reviews.json"

            result = tool.run(
                {
                    "action": "request",
                    "url": "http://bad.onion",
                    "risk_level": "critical",
                }
            )
            assert result["success"] is True
            item_id = result["data"]["item_id"]

            result = tool.run(
                {
                    "action": "reject",
                    "item_id": item_id,
                    "reason": "Not relevant",
                }
            )
            assert result["success"] is True
        finally:
            if old_file is not None:
                os.environ["ONION_REVIEW_FILE"] = old_file
            else:
                del os.environ["ONION_REVIEW_FILE"]


def test_human_review_approve_not_found():
    from mcp_tools.human_review import HumanReviewTool

    tool = HumanReviewTool()
    result = tool.run(
        {
            "action": "approve",
            "item_id": "nonexistent",
        }
    )
    assert result["success"] is False


def test_human_review_reject_no_id():
    from mcp_tools.human_review import HumanReviewTool

    tool = HumanReviewTool()
    result = tool.run({"action": "reject"})
    assert result["success"] is False

# ─── SSRF-Schutz (T-019) ──────────────────────────────────────────────────────

from unittest.mock import patch, MagicMock


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_localhost(mock_getaddrinfo):
    """SSRF: localhost wird blockiert."""
    from mcp_tools.web_fetch import WebFetchTool

    # Simuliere 127.0.0.1 als Auflösung
    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("127.0.0.1", 80))
    ]

    tool = WebFetchTool()
    result = tool.run({"url": "http://localhost:11434/api/tags"})
    assert result["success"] is False
    assert "SSRF" in result["error"] or "blockiert" in result["error"]


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_rfc1918(mock_getaddrinfo):
    """SSRF: RFC1918 (192.168.x.x) wird blockiert."""
    from mcp_tools.web_fetch import WebFetchTool

    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("192.168.1.1", 80))
    ]

    tool = WebFetchTool()
    result = tool.run({"url": "http://192.168.1.1/admin"})
    assert result["success"] is False
    assert "SSRF" in result["error"] or "blockiert" in result["error"]


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_10_range(mock_getaddrinfo):
    """SSRF: 10.x.x.x wird blockiert."""
    from mcp_tools.web_fetch import WebFetchTool

    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("10.0.0.5", 8000))
    ]

    tool = WebFetchTool()
    result = tool.run({"url": "http://10.0.0.5:8000"})
    assert result["success"] is False


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_public_ip_allowed(mock_getaddrinfo):
    """SSRF: Öffentliche IP wird erlaubt."""
    from mcp_tools.web_fetch import WebFetchTool
    from requests.exceptions import ConnectionError

    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("93.184.216.34", 80))
    ]

    tool = WebFetchTool()
    # Public IP geht durch SSRF-Prüfung, schlägt dann aber beim Fetch feil
    with patch.object(tool._session, 'get') as mock_get:
        mock_get.side_effect = ConnectionError("Expected test error")
        result = tool.run({"url": "http://example.com"})
        # Sollte NICHT "SSRF" im Fehler haben
        assert "SSRF" not in result.get("error", "")


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_link_local(mock_getaddrinfo):
    """SSRF: Link-Local (169.254.x.x) wird blockiert."""
    from mcp_tools.web_fetch import WebFetchTool

    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("169.254.1.1", 80))
    ]

    tool = WebFetchTool()
    result = tool.run({"url": "http://169.254.1.1"})
    assert result["success"] is False


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_ipv6_localhost(mock_getaddrinfo):
    """SSRF: IPv6 localhost (::1) wird blockiert."""
    from mcp_tools.web_fetch import WebFetchTool

    mock_getaddrinfo.return_value = [
        (0, 0, 0, "", ("::1", 80))
    ]

    tool = WebFetchTool()
    result = tool.run({"url": "http://[::1]:11434"})
    assert result["success"] is False


@patch("mcp_tools.web_fetch.socket.getaddrinfo")
def test_web_fetch_ssrf_resolution_failure(mock_getaddrinfo):
    """SSRF: Nicht auflösbarer Hostname gibt Fehler."""
    from mcp_tools.web_fetch import WebFetchTool

    import socket
    mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")

    tool = WebFetchTool()
    result = tool.run({"url": "http://nonexistent-domain-xyz-123.com"})
    assert result["success"] is False
    assert "nicht auflösbar" in result["error"]
