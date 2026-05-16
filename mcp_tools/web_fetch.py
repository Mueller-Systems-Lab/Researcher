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
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from mcp_tools.base import MCPToolBase, MCPToolResult
from onion_discovery.policy_gateway import PolicyGateway

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
                    "description": "HTML bereinigen, nur Text extrahieren (default: true)",
                    "default": True,
                },
            },
            "required": ["url"],
        }

    def __init__(self, policy_gateway: Optional[PolicyGateway] = None):
        self.policy = policy_gateway or PolicyGateway()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                    "Gecko/20100101 Firefox/128.0"
                ),
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        self._session.timeout = 30

    def _validate_url_target(self, url: str) -> Optional[str]:
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
        except Exception as e:
            logger.warning(f"SSRF-Validierungsfehler für {url}: {e}")
            return None  # Im Zweifel erlauben (kein blockierendes Verhalten)

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
            response = self._session.get(url, timeout=30)
            response.raise_for_status()
            content = response.text

            result = {
                "url": url,
                "status": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "content_length": len(content),
            }

            if extract_text:
                soup = BeautifulSoup(content, "lxml")
                # Titel extrahieren
                title = soup.title.get_text(strip=True) if soup.title else ""
                # Text aus relevanten Tags
                text_parts = []
                for tag in soup.find_all(
                    [
                        "p",
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "li",
                        "article",
                        "section",
                        "blockquote",
                    ]
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
                    "Onion-Seite geladen — "
                    "dies ist möglicherweise gegen die Richtlinien"
                )

            return MCPToolResult(True, data=result).to_dict()

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
        except requests.RequestException as e:
            return MCPToolResult(False, error=f"HTTP-Fehler: {e}").to_dict()
        except Exception as e:
            logger.exception(f"Unerwarteter Fehler bei web-fetch: {e}")
            return MCPToolResult(False, error=f"Interner Fehler: {e}").to_dict()
