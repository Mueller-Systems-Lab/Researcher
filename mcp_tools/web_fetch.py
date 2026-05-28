# =============================================================================
# MCP Tool: web-fetch
# =============================================================================
# Holt Webseiten-Inhalte über SearXNG oder direkten HTTP-Fetch.
# Respektiert Blocklist, Opt-out und Rate-Limits aus PolicyGateway.
# KEINE Live-Tor-Abfragen (ADR-006).
#
# Nutzung:
#   tool = WebFetchTool()
#   result = tool.run({"url": "http://example.com", "max_chars": 5000})
# =============================================================================

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from mcp_tools.base import MCPToolBase, MCPToolResult
from onion_discovery.policy_gateway import PolicyGateway
from scrapers.http_session import (
    create_session,
    detect_js_only,
    is_505_http_version_error,
    refetch_with_fallback_ua,
    ssl_fallback_fetch,
)

# Private und interne IP-Bereiche (SSRF-Schutz)
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # localhost
    ipaddress.ip_network("10.0.0.0/8"),  # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1"),  # localhost IPv6
    ipaddress.ip_network("fc00::/7"),  # unique local IPv6
    ipaddress.ip_network("fe80::/10"),  # link-local IPv6
]

logger = logging.getLogger(__name__)


class WebFetchTool(MCPToolBase):
    """MCP-Tool zum Fetchen von Webseiten-Inhalten."""

    @property
    def name(self) -> str:
        return "web-fetch"

    @property
    def description(self) -> str:
        return (
            "Holt Webseiten-Inhalte über HTTP. "
            "Respektiert Blocklist/Opt-out. "
            "Keine .onion-Adressen (nur Clearnet)."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Die URL der abzurufenden Webseite",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximale Zeichenanzahl (default: 5000)",
                    "default": 5000,
                },
                "extract_text": {
                    "type": "boolean",
                    "description": (
                        "HTML bereinigen, nur Text extrahieren (default: true)"
                    ),
                    "default": True,
                },
            },
            "required": ["url"],
        }

    def __init__(self, policy_gateway: PolicyGateway | None = None):
        self.policy = policy_gateway or PolicyGateway()
        self._session = create_session()

    def _validate_url_target(self, url: str) -> str | None:
        """Validiert die Ziel-IP einer URL (SSRF-Schutz).

        Löst den Hostnamen auf und prüft, ob die IP in einem privaten
        oder internen Netzwerk liegt.

        Returns:
            None wenn OK, Fehlerstring wenn blockiert.
        """
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if not host:
                return "Ungültige URL: kein Hostname"

            # Nur http/https erlauben (kein file://, ftp://, gopher://, etc.)
            if parsed.scheme not in ("http", "https"):
                return f"SSRF blockiert: Schema '{parsed.scheme}' nicht erlaubt"

            # Hostname auflösen
            addrinfo = socket.getaddrinfo(
                host, 80, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
            for family, _, _, _, sockaddr in addrinfo:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                except ValueError:
                    continue

                # Gegen private Netze prüfen
                for network in _PRIVATE_NETWORKS:
                    if ip in network:
                        return (
                            f"SSRF blockiert: {host} ({ip_str}) "
                            f"ist in privatem Netz {network}"
                        )

                # Zusätzlich: Prüfen ob die IP überhaupt routing-fähig ist
                if ip.is_loopback or ip.is_private or ip.is_link_local:
                    return (
                        f"SSRF blockiert: {host} ({ip_str}) "
                        f"ist eine private/lokale Adresse"
                    )
            return None

        except socket.gaierror as e:
            return f"Hostname nicht auflösbar: {host} ({e})"
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.warning(f"SSRF-Validierung: ungültige Adresse für {url}: {e}")
            return f"SSRF-Validierung: ungültige Adresse: {e}"
        except OSError as e:
            logger.warning(
                f"SSRF-Validierungs-Netzwerkfehler für {url}: {e}", exc_info=True
            )
            return f"SSRF-Validierungs-Netzwerkfehler: {e}"

    def _fetch_with_resilience(self, url: str) -> requests.Response:
        """Führt einen HTTP-GET mit Resilience-Strategie durch.

        Versucht zuerst den normalen Request. Bei 505-Fehlern wird
        automatisch ein Fallback-User-Agent verwendet.

        Args:
            url: Ziel-URL.

        Returns:
            requests.Response.

        Raises:
            requests.RequestException: Bei nicht-behebbaren Fehlern.
        """
        response = self._session.get(url, timeout=30, allow_redirects=True)

        # 505-Spezialbehandlung: HTTP Version Not Supported
        if is_505_http_version_error(response):
            logger.warning("505-Fehler bei %s — versuche Fallback-UA", url)
            fallback_response = refetch_with_fallback_ua(
                self._session,
                url,
                timeout=30,
                allow_redirects=True,
            )
            if fallback_response is not None:
                response = fallback_response

        response.raise_for_status()
        return response

    def _handle_http_error(self, error: requests.HTTPError, url: str) -> dict:
        """Behandelt HTTP-Fehler mit differenzierter Fehlermeldung.

        Args:
            error: Die HTTPError-Exception.
            url: Die angefragte URL.

        Returns:
            MCPToolResult als dict.
        """
        response = error.response
        status_code = response.status_code if response is not None else 0

        status_messages = {
            400: "Bad Request — ungültige Anfrage",
            401: "Unauthorized — Zugriff verweigert",
            403: "Forbidden — Zugriff verboten",
            404: "Not Found — Seite nicht gefunden",
            405: "Method Not Allowed",
            408: "Request Timeout",
            429: "Too Many Requests — Rate-Limit erreicht",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
            505: "HTTP Version Not Supported",
        }

        message = status_messages.get(status_code, f"HTTP {status_code}")
        return MCPToolResult(
            False,
            error=f"HTTP-Fehler {status_code}: {message} — {url}",
        ).to_dict()

    def _validate_redirect_chain(self, response, original_url: str) -> str | None:
        """Validiert SSRF-Schutz für alle Redirects und das finale Ziel.

        Args:
            response: requests.Response nach dem Fetch.
            original_url: Die ursprünglich angeforderte URL.

        Returns:
            Fehlerstring wenn eine Redirect-URL oder das finale Ziel
            blockiert wird, sonst None.
        """
        for redirect_resp in response.history:
            ssrf_error = self._validate_url_target(redirect_resp.url)
            if ssrf_error:
                return f"SSRF blockiert nach Redirect: {ssrf_error}"

        # Auch das finale Ziel validieren, wenn es vom Original abweicht
        final_url = response.url
        if final_url != original_url and isinstance(final_url, str):
            ssrf_error = self._validate_url_target(final_url)
            if ssrf_error:
                return f"SSRF blockiert: Final-URL {final_url} ist nicht erlaubt"

        return None

    def _check_js_only(self, response, url: str) -> dict | None:
        """Prüft, ob die Seite JavaScript benötigt.

        Returns:
            MCPToolResult als dict wenn JS benötigt wird (high confidence),
            None wenn die Seite ohne JS nutzbar ist.
        """
        js_check = detect_js_only(response.text)
        if js_check["js_required"]:
            confidence = js_check.get("confidence", "medium")
            reason = js_check.get("reason", "unbekannt")
            if confidence == "high":
                return MCPToolResult(
                    False,
                    data={
                        "url": url,
                        "status": response.status_code,
                        "js_required": True,
                        "js_reason": reason,
                    },
                    error=f"Seite benötigt JavaScript: {reason}",
                ).to_dict()
            logger.warning(
                "JS-Verdacht bei %s (confidence=%s): %s",
                url,
                confidence,
                reason,
            )
        return None

    def _build_result(
        self,
        url: str,
        response,
        max_chars: int,
        extract_text: bool,
    ) -> dict:
        """Baut das erfolgreiche Fetch-Result aus der Response.

        Args:
            url: Ursprüngliche URL.
            response: requests.Response.
            max_chars: Maximale Zeichenanzahl.
            extract_text: Ob Text extrahiert werden soll.

        Returns:
            MCPToolResult als dict.
        """
        content = response.text

        result = {
            "url": url,
            "status": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "content_length": len(content),
        }

        if extract_text:
            soup = BeautifulSoup(content, "lxml")
            title = soup.title.get_text(strip=True) if soup.title else ""
            text_parts = []
            for tag in soup.find_all(
                ["p", "h1", "h2", "h3", "h4", "li", "article", "section", "blockquote"]
            ):
                text = tag.get_text(strip=True)
                if text:
                    text_parts.append(text)
            text_content = "\n\n".join(text_parts)

            result["title"] = title
            result["text"] = text_content[:max_chars]
            if len(text_content) > max_chars:
                result["truncated"] = True
        else:
            result["html"] = content[:max_chars]

        if self.policy.is_onion_url(url):
            result["warning"] = (
                "Onion-Seite geladen — dies ist möglicherweise gegen die Richtlinien"
            )

        return MCPToolResult(True, data=result).to_dict()

    def run(self, params: dict) -> dict:
        url = params.get("url", "")
        max_chars = params.get("max_chars", 5000)
        extract_text = params.get("extract_text", True)

        if not url:
            return MCPToolResult(
                False, error="url-Parameter ist erforderlich"
            ).to_dict()

        # .onion nicht erlaubt (Clearnet-Only)
        if ".onion" in url.lower():
            return MCPToolResult(
                False,
                error="Onion-Adressen sind nicht erlaubt. "
                "Nutze das Onion-Discovery-System.",
            ).to_dict()

        # Policy-Prüfung
        decision = self.policy.is_allowed(url)
        if not decision.allowed:
            return MCPToolResult(
                False,
                error=f"URL blockiert: {decision.reason}",
            ).to_dict()

        # SSRF-Prüfung: Ziel-IP auflösen und gegen private Netze prüfen
        ssrf_error = self._validate_url_target(url)
        if ssrf_error:
            return MCPToolResult(False, error=ssrf_error).to_dict()

        try:
            response = self._fetch_with_resilience(url)

            # SSRF-Redirect-Revalidation
            ssrf_error = self._validate_redirect_chain(response, url)
            if ssrf_error:
                return MCPToolResult(False, error=ssrf_error).to_dict()

            # JavaScript-Only-Detection
            js_block = self._check_js_only(response, url)
            if js_block:
                return js_block

            return self._build_result(url, response, max_chars, extract_text)

        except requests.exceptions.SSLError as e:
            logger.warning("SSL-Fehler bei %s: %s — versuche Fallback", url, e)
            try:
                response = ssl_fallback_fetch(
                    self._session,
                    url,
                    timeout=30,
                    allow_redirects=True,
                )
                response.raise_for_status()
                logger.info("SSL-Fallback erfolgreich für %s", url)

                ssrf_error = self._validate_redirect_chain(response, url)
                if ssrf_error:
                    return MCPToolResult(False, error=ssrf_error).to_dict()

                return self._build_result(url, response, max_chars, extract_text)
            except requests.RequestException as fallback_error:
                return MCPToolResult(
                    False,
                    error=f"SSL-Fehler (auch mit Fallback): {fallback_error}",
                ).to_dict()
        except requests.exceptions.ConnectionError:
            return MCPToolResult(
                False,
                error=f"Verbindungsfehler: {url} nicht erreichbar",
            ).to_dict()
        except requests.exceptions.Timeout:
            return MCPToolResult(
                False,
                error=f"Timeout: {url} nach 30s nicht erreichbar",
            ).to_dict()
        except requests.HTTPError as e:
            return self._handle_http_error(e, url)
        except requests.RequestException as e:
            return MCPToolResult(False, error=f"HTTP-Fehler: {e}").to_dict()
        except Exception as e:
            logger.exception(f"Unerwarteter Fehler bei web-fetch: {e}")
            return MCPToolResult(False, error=f"Interner Fehler: {e}").to_dict()
