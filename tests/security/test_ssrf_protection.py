"""SSRF-Schutz-Regressionstests für mcp_tools/web_fetch.py — 8 Angriffsvektoren."""

import os
import socket
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from mcp_tools.web_fetch import _PRIVATE_NETWORKS, WebFetchTool


@pytest.mark.security
@pytest.mark.ssrf
class TestSSRFProtection:
    """Testet SSRF-Schutz in WebFetchTool._validate_url_target()"""

    def _tool(self):
        policy = MagicMock()
        policy.is_allowed.return_value = MagicMock(allowed=True, reason="Allowed")
        policy.is_onion_url.return_value = False
        return WebFetchTool(policy_gateway=policy)

    def test_ssrf_blocks_dns_rebinding(self):
        """Testet SSRF-Schutz gegen DNS-Rebinding (IP-Änderung zwischen Lookup und Request)."""
        tool = self._tool()

        # GIVEN: Domain die beim ersten Lookup eine öffentliche IP zurückgibt.
        public_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]
        private_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
        ]

        # WHEN: _validate_url_target wird mit öffentlicher IP aufgerufen.
        with patch("socket.getaddrinfo", return_value=public_addrinfo):
            first_validation = tool._validate_url_target("http://rebinding.example/")

        # THEN: Die öffentliche IP wird erlaubt.
        assert first_validation is None

        # WHEN: Ein zweiter Lookup im Redirect-/Revalidierungsfenster Loopback sieht.
        with patch("socket.getaddrinfo", return_value=private_addrinfo):
            second_validation = tool._validate_url_target("http://rebinding.example/")

        # THEN: Die neue interne IP wird blockiert.
        assert second_validation is not None
        assert "SSRF blockiert" in second_validation

    @pytest.mark.parametrize(
        "host",
        [
            "::1",
            "[::1]",
            "[::ffff:127.0.0.1]",
            "[fe80::1%lo0]",
        ],
    )
    def test_ssrf_blocks_ipv6_loopback(self, host):
        """Testet SSRF-Schutz gegen IPv6-komprimierte Loopback-Adressen."""
        tool = self._tool()
        url = f"http://{host}/"

        def fake_getaddrinfo(resolved_host, *_args, **_kwargs):
            ip_by_host = {
                "::1": "::1",
                "::ffff:127.0.0.1": "::ffff:127.0.0.1",
                "fe80::1%lo0": "fe80::1",
            }
            ip = ip_by_host.get(resolved_host, "::1")
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, 80, 0, 0))]

        # GIVEN: URL mit IPv6-Loopback-Host.
        # WHEN: _validate_url_target wird aufgerufen.
        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            error = tool._validate_url_target(url)

        # THEN: Fehlerstring wird zurückgegeben (nicht None).
        # Bare "::1" (ohne Klammern) liefert "kein Hostname" via urlparse — auch korrekt.
        assert error is not None
        assert any(kw in error for kw in ("SSRF", "fehlgeschlagen", "kein Hostname"))

    @pytest.mark.parametrize(
        "url,expected_blocked",
        [
            ("http://2130706433/", True),
            ("http://0x7f000001/", True),
            ("http://0177.0.0.1/", True),
            ("http://3232235777/", True),
        ],
    )
    def test_ssrf_blocks_ipv4_integer_representation(self, url, expected_blocked):
        """Testet SSRF-Schutz gegen IPv4-Integer-Repräsentation."""
        tool = self._tool()
        ip_by_host = {
            "2130706433": "127.0.0.1",
            "0x7f000001": "127.0.0.1",
            "0177.0.0.1": "127.0.0.1",
            "3232235777": "192.168.1.1",
        }

        def fake_getaddrinfo(resolved_host, *_args, **_kwargs):
            ip = ip_by_host[resolved_host]
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

        # GIVEN: URL mit Integer-Format-IP.
        # WHEN: _validate_url_target wird aufgerufen.
        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            error = tool._validate_url_target(url)

        # THEN: Blockierung erfolgt.
        assert (error is not None) is expected_blocked
        assert "SSRF blockiert" in error

    def test_ssrf_revalidates_redirects(self):
        """Testet SSRF-Schutz gegen Redirect-Ketten zu internen IPs."""
        tool = self._tool()
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "text/html"}
        response.text = "<html><title>ok</title><p>ok</p></html>"
        response.raise_for_status.return_value = None

        redirect_response = MagicMock()
        redirect_response.url = "http://192.168.1.1/admin"
        response.history = [redirect_response]

        def fake_getaddrinfo(resolved_host, *_args, **_kwargs):
            ip = "192.168.1.1" if resolved_host == "192.168.1.1" else "8.8.8.8"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

        # GIVEN: Externe URL redirectet zu 192.168.1.1.
        # WHEN: run() macht requests.get() mit allow_redirects=True.
        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            with patch.object(tool._session, "get", return_value=response) as mock_get:
                result = tool.run({"url": "http://example.com/", "max_chars": 100})

        # THEN: response.history enthält Redirect — validate erneut aufgerufen und blockiert.
        mock_get.assert_called_once_with(
            "http://example.com/", timeout=30, allow_redirects=True
        )
        assert result["success"] is False
        assert "SSRF blockiert nach Redirect" in result["error"]

    def test_ssrf_handles_idn_homograph(self):
        """Testet SSRF-Schutz gegen IDN-Homograph-Angriffe (kyrillisches 'а')."""
        tool = self._tool()
        url = "http://exаmple.com/"  # U+0430 statt ASCII-a
        public_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]

        # GIVEN: URL mit kyrillischem 'а' statt ASCII 'a'.
        # WHEN: _validate_url_target wird aufgerufen (Hostname-Auflösung).
        with patch("socket.getaddrinfo", return_value=public_addrinfo) as mock_dns:
            error = tool._validate_url_target(url)

        # THEN: Hostname wird kontrolliert aufgelöst und nicht als private IP blockiert.
        assert error is None
        mock_dns.assert_called_once_with(
            "exаmple.com", 80, socket.AF_UNSPEC, socket.SOCK_STREAM
        )

    @pytest.mark.parametrize(
        "encoded_path",
        [
            "%2e%2e%2f",
            "%252e%252e%252f",
            "..%2f",
        ],
    )
    def test_ssrf_handles_url_encoding_bypass(self, encoded_path):
        """Testet SSRF-Schutz gegen URL-Encoding-Bypass-Versuche."""
        tool = self._tool()
        url = f"http://example.com/{encoded_path}127.0.0.1"
        public_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]

        # GIVEN: URL mit Encoding-Sequenzen.
        # WHEN: _validate_url_target wird aufgerufen.
        with patch("socket.getaddrinfo", return_value=public_addrinfo) as mock_dns:
            error = tool._validate_url_target(url)

        # THEN: Hostname wird korrekt extrahiert (parsed.hostname von urlparse).
        assert error is None
        mock_dns.assert_called_once_with(
            "example.com", 80, socket.AF_UNSPEC, socket.SOCK_STREAM
        )

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1%00.example.com",
            # "http://127.0.0.1%00@evil.com" — urlparse interpretiert %00 als
            # Teil des Usernames (userinfo), nicht des Hostnames. Der Hostname
            # ist evil.com (öffentlich). Kein SSRF-Risiko in diesem Fall.
        ],
    )
    def test_ssrf_blocks_null_byte_injection(self, url):
        """Testet SSRF-Schutz gegen Null-Byte-Injection in Hostnamen."""
        tool = self._tool()

        def fake_getaddrinfo(resolved_host, *_args, **_kwargs):
            assert resolved_host != "127.0.0.1"
            if "%00" in resolved_host:
                raise socket.gaierror("encoded null byte in hostname")
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]

        # GIVEN: URL mit Null-Byte im Host-Teil.
        # WHEN: _validate_url_target extrahiert hostname via urlparse.
        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            error = tool._validate_url_target(url)

        # THEN: Hostname sollte nicht 127.0.0.1 sein; Null-Byte bleibt Teil des Strings.
        assert error is not None

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://localhost:6379/_INFO",
            "ftp://127.0.0.1/",
        ],
    )
    def test_ssrf_blocks_disallowed_schemas(self, url):
        """Testet SSRF-Schutz gegen nicht erlaubte URL-Schemas."""
        tool = self._tool()

        # GIVEN: URL mit nicht-http-Schema.
        # WHEN: _validate_url_target wird aufgerufen.
        error = tool._validate_url_target(url)

        # THEN: Blockierung wegen Schema oder fehlendem Host bei file://.
        assert error is not None
        assert "Schema" in error or "kein Hostname" in error

    def test_private_networks_list_is_complete(self):
        """Testet SSRF-Schutz gegen fehlende RFC1918- und lokale Netzdefinitionen."""
        import ipaddress

        required = [
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "169.254.0.0/16",
        ]
        for net in required:
            assert ipaddress.ip_network(net) in _PRIVATE_NETWORKS

    def test_ssrf_validate_allows_public_ip(self):
        """Testet SSRF-Schutz gegen False-Positives bei öffentlichen IPs."""
        tool = self._tool()
        public_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]

        # GIVEN: Öffentliche IP aus DNS-Auflösung.
        # WHEN: _validate_url_target wird aufgerufen.
        with patch("socket.getaddrinfo", return_value=public_addrinfo):
            error = tool._validate_url_target("http://example.com")

        # THEN: Öffentliche IP wird nicht blockiert.
        assert error is None
