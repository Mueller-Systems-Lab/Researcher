# =============================================================================
# Tests: Scraper-Resilience (SSL-Fallback, 505-Retry, JS-Detection)
# =============================================================================

from unittest import mock

import pytest
import requests

from scrapers.http_session import (
    DEFAULT_TIMEOUT,
    RETRY_CONFIG,
    RETRY_STATUS_CODES,
    USER_AGENT,
    USER_AGENT_FALLBACK,
    create_session,
    detect_js_only,
    is_505_http_version_error,
    refetch_with_fallback_ua,
    ssl_fallback_fetch,
)

# ── Session-Factory Tests ──────────────────────────────────────────────────────


class TestCreateSession:
    """Tests für zentrale Session-Factory."""

    def test_default_session_has_user_agent(self):
        session = create_session()
        assert session.headers["User-Agent"] == USER_AGENT

    def test_default_session_has_accept_header(self):
        session = create_session()
        assert "Accept" in session.headers
        assert "text/html" in session.headers["Accept"]

    def test_default_session_has_timeout(self):
        session = create_session()
        t = DEFAULT_TIMEOUT.to_tuple()
        assert session.timeout == t

    def test_default_session_has_retry_adapter(self):
        session = create_session()
        adapters = session.adapters
        https_adapter = adapters.get("https://")
        assert https_adapter is not None
        assert https_adapter.max_retries.total == RETRY_CONFIG.total

    def test_default_session_retry_status_codes(self):
        session = create_session()
        adapter = session.adapters["https://"]
        retry = adapter.max_retries
        assert 502 in retry.status_forcelist
        assert 503 in retry.status_forcelist
        assert 504 in retry.status_forcelist
        assert 505 in retry.status_forcelist

    def test_default_session_backoff_factor(self):
        session = create_session()
        adapter = session.adapters["https://"]
        retry = adapter.max_retries
        assert retry.backoff_factor == RETRY_CONFIG.backoff_factor

    def test_custom_user_agent(self):
        custom_ua = "Researcher/2.0 TestBot"
        session = create_session(user_agent=custom_ua)
        assert session.headers["User-Agent"] == custom_ua

    def test_custom_timeout(self):
        from scrapers.http_session import TimeoutConfig

        t = TimeoutConfig(connect=5.0, read=15.0)
        session = create_session(timeout=t)
        assert session.timeout == (5.0, 15.0)

    def test_proxy_configuration(self):
        proxy = "socks5h://127.0.0.1:9050"
        session = create_session(proxy=proxy)
        assert session.proxies["http"] == proxy
        assert session.proxies["https"] == proxy

    def test_retry_only_get_and_head(self):
        session = create_session()
        adapter = session.adapters["https://"]
        retry = adapter.max_retries
        assert "GET" in retry.allowed_methods
        assert "HEAD" in retry.allowed_methods
        assert "POST" not in retry.allowed_methods

    def test_retry_config_defaults(self):
        assert RETRY_CONFIG.total == 3
        assert RETRY_CONFIG.backoff_factor == 0.5
        assert 505 in RETRY_CONFIG.status_forcelist


# ── JavaScript-Detection Tests ─────────────────────────────────────────────────


class TestDetectJsOnly:
    """Tests für JS-Detection."""

    def test_empty_html_not_js(self):
        result = detect_js_only("")
        assert result["js_required"] is False
        assert result["confidence"] == "high"

    def test_none_html_not_js(self):
        result = detect_js_only(None)  # type: ignore[arg-type]
        assert result["js_required"] is False

    def test_normal_html_not_js(self):
        html = "<html><body><p>Normal content</p></body></html>"
        result = detect_js_only(html)
        assert result["js_required"] is False

    def test_javascript_required_text(self):
        html = (
            "<html><body><p>JavaScript is required to view this page.</p></body></html>"
        )
        result = detect_js_only(html)
        assert result["js_required"] is True
        assert "javascript is required" in result["reason"].lower()

    def test_noscript_tag(self):
        html = "<html><body><noscript>Please enable JavaScript</noscript></body></html>"
        result = detect_js_only(html)
        assert result["js_required"] is True

    def test_cloudflare_challenge(self):
        html = (
            "<html><body>"
            "<p>Checking your browser before accessing the site.</p>"
            "<p>DDoS protection by Cloudflare</p>"
            "</body></html>"
        )
        result = detect_js_only(html)
        assert result["js_required"] is True
        assert result["confidence"] == "high"

    def test_cloudflare_challenge_body_heuristic(self):
        html = (
            "<html><head></head>"
            "<body>"
            "<h1>Just a moment...</h1>"
            "<p>We are checking your browser. This should take a few seconds.</p>"
            "<script>var jschl=document.getElementById('challenge-form');</script>"
            '<div class="cf-browser-verification">'
            "<p>Please wait while we verify your connection.</p>"
            "</div>"
            "</body></html>"
        )
        result = detect_js_only(html)
        assert result["js_required"] is True
        assert result["confidence"] == "high"

    def test_enable_javascript_text(self):
        html = (
            "<html><body>You need to enable JavaScript to run this app.</body></html>"
        )
        result = detect_js_only(html)
        assert result["js_required"] is True

    def test_captcha_detection(self):
        html = "<html><body><p>Please complete the CAPTCHA</p></body></html>"
        result = detect_js_only(html)
        assert result["js_required"] is True
        assert result["confidence"] == "high"

    def test_ddos_protection_detection(self):
        html = "<html><body>DDoS protection</body></html>"
        result = detect_js_only(html)
        assert result["js_required"] is True
        assert result["confidence"] == "high"

    def test_case_insensitive(self):
        html = "<HTML><BODY><P>JavaScript is REQUIRED</P></BODY></HTML>"
        result = detect_js_only(html)
        assert result["js_required"] is True

    def test_please_enable_js(self):
        html = "<html><body>Please enable JS to continue</body></html>"
        result = detect_js_only(html)
        assert result["js_required"] is True


# ── 505-Handling Tests ─────────────────────────────────────────────────────────


class Test505Handling:
    """Tests für HTTP 505 Version Not Supported."""

    def test_is_505_true(self):
        resp = mock.Mock(spec=requests.Response)
        resp.status_code = 505
        assert is_505_http_version_error(resp) is True

    def test_is_505_false_200(self):
        resp = mock.Mock(spec=requests.Response)
        resp.status_code = 200
        assert is_505_http_version_error(resp) is False

    def test_is_505_false_404(self):
        resp = mock.Mock(spec=requests.Response)
        resp.status_code = 404
        assert is_505_http_version_error(resp) is False

    def test_is_505_false_502(self):
        resp = mock.Mock(spec=requests.Response)
        resp.status_code = 502
        assert is_505_http_version_error(resp) is False

    def test_refetch_switches_user_agent(self):
        session = create_session()
        original_ua = session.headers["User-Agent"]

        with mock.patch.object(session, "get") as mock_get:
            mock_resp = mock.Mock(spec=requests.Response)
            mock_get.return_value = mock_resp

            refetch_with_fallback_ua(session, "http://example.com")

        # UA should be restored after call
        assert session.headers["User-Agent"] == original_ua

    def test_refetch_uses_fallback_ua(self):
        session = create_session()

        captured_ua = []

        def capture_get(url, **kwargs):
            captured_ua.append(session.headers.get("User-Agent", ""))
            resp = mock.Mock(spec=requests.Response)
            return resp

        with mock.patch.object(session, "get", side_effect=capture_get):
            refetch_with_fallback_ua(session, "http://example.com")

        assert len(captured_ua) == 1
        assert captured_ua[0] == USER_AGENT_FALLBACK

    def test_refetch_restores_ua_on_error(self):
        session = create_session()
        original_ua = session.headers["User-Agent"]

        with mock.patch.object(session, "get", side_effect=requests.ConnectionError):
            result = refetch_with_fallback_ua(session, "http://example.com")

        assert result is None
        assert session.headers["User-Agent"] == original_ua


# ── SSL-Fallback Tests ─────────────────────────────────────────────────────────


class TestSslFallback:
    """Tests für SSL-Fallback-Mechanismus."""

    def test_ssl_fallback_disables_verify(self):
        session = create_session()
        session.verify = True

        with mock.patch.object(session, "get") as mock_get:
            mock_resp = mock.Mock(spec=requests.Response)
            mock_get.return_value = mock_resp

            ssl_fallback_fetch(session, "https://example.com")

        # Verify should be restored
        assert session.verify is True

    def test_ssl_fallback_restores_verify_on_error(self):
        session = create_session()
        session.verify = True

        with mock.patch.object(session, "get", side_effect=requests.ConnectionError):
            with pytest.raises(requests.ConnectionError):
                ssl_fallback_fetch(session, "https://example.com")

        # Verify should be restored even on error
        assert session.verify is True

    def test_ssl_fallback_temporarily_sets_verify_false(self):
        session = create_session()
        session.verify = True

        captured_verify = []

        def capture_get(url, **kwargs):
            captured_verify.append(session.verify)
            resp = mock.Mock(spec=requests.Response)
            return resp

        with mock.patch.object(session, "get", side_effect=capture_get):
            ssl_fallback_fetch(session, "https://bad-ssl.example.com")

        assert len(captured_verify) == 1
        assert captured_verify[0] is False


# ── Retry-Status-Codes Tests ───────────────────────────────────────────────────


class TestRetryStatusCodes:
    """Tests für Retry-Status-Code-Konfiguration."""

    def test_505_in_retry_status_codes(self):
        assert 505 in RETRY_STATUS_CODES

    def test_all_server_errors_in_retry(self):
        """502, 503, 504, 505 sollten alle einen Retry auslösen."""
        expected = {502, 503, 504, 505}
        assert RETRY_STATUS_CODES == expected

    def test_404_not_in_retry(self):
        assert 404 not in RETRY_STATUS_CODES

    def test_200_not_in_retry(self):
        assert 200 not in RETRY_STATUS_CODES

    def test_retry_config_status_forcelist_matches(self):
        """Die RetryConfig.status_forcelist sollte mit RETRY_STATUS_CODES übereinstimmen."""
        assert RETRY_CONFIG.status_forcelist == RETRY_STATUS_CODES


# ── Integration: WebFetchTool Resilience ───────────────────────────────────────


class TestWebFetchToolResilience:
    """Integrationstests für WebFetchTool mit Resilience-Features."""

    def test_web_fetch_imports_resilience(self):
        """Stellt sicher, dass web_fetch.py die Resilience-Module importiert."""
        from mcp_tools.web_fetch import WebFetchTool

        tool = WebFetchTool()
        assert tool._session is not None
        assert tool._session.headers["User-Agent"] == USER_AGENT

    def test_web_fetch_session_has_retry(self):
        """WebFetchTool sollte eine Session mit Retry-Adapter verwenden."""
        from mcp_tools.web_fetch import WebFetchTool

        tool = WebFetchTool()
        adapter = tool._session.adapters.get("https://")
        assert adapter is not None
        assert adapter.max_retries.total == 3

    def test_no_verify_false_literal_in_web_fetch(self):
        """Security: web_fetch.py darf kein verify=False als String-Literal enthalten."""
        with open("mcp_tools/web_fetch.py") as f:
            content = f.read()
        assert "verify=False" not in content, (
            "verify=False darf nicht als Literal im Projektcode vorkommen "
            "(Security Regression Test). Nutze ssl_fallback_fetch() stattdessen."
        )

    def test_no_verify_false_literal_in_http_session(self):
        """Security: http_session.py darf kein verify=False als String-Literal."""
        with open("scrapers/http_session.py") as f:
            content = f.read()
        assert "verify=False" not in content, (
            "verify=False darf nicht als Literal in http_session.py vorkommen."
        )
