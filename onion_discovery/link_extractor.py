# =============================================================================
# Onion Discovery — Link Extractor
# =============================================================================
# Extrahiert .onion-Links aus HTML-Inhalten.
# Dedupliziert anhand der URL und erzeugt synthetische URIs.
# Berücksichtigt relative und absolute Pfade.
#
# Nutzung:
#   extractor = LinkExtractor()
#   links = extractor.extract("http://forum.onion", html_content)
# =============================================================================

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Regex für .onion-Links (v2 und v3)
ONION_URL_PATTERN = re.compile(
    r"(https?://[a-z2-7]{16,56}\.onion(?::\d{1,5})?(?:/[^\s\"'<>()]*)?)",
    re.IGNORECASE,
)

# Onion-Links in Text-Inhalten (ohne HTML-Tags)
ONION_RAW_PATTERN = re.compile(
    r"([a-z2-7]{16,56}\.onion(?::\d{1,5})?(?:/[^\s\"'<>()\[\]]*)?)",
    re.IGNORECASE,
)


class LinkExtractor:
    """Extrahiert und dedupliziert .onion-Links aus HTML/Text."""

    def __init__(
        self,
        include_same_domain: bool = False,
        max_links_per_page: int = 50,
    ):
        self.include_same_domain = include_same_domain
        self.max_links_per_page = max_links_per_page

    def extract(self, base_url: str, html: str) -> list[dict]:
        """Extrahiert .onion-Links aus HTML.

        Args:
            base_url: Die URL der aktuellen Seite (für relative Pfade).
            html: Der HTML-Inhalt.

        Returns:
            Liste von Dicts mit Keys: url, source_url, anchor_text.
        """
        links = []
        seen = set()
        base_host = urlparse(base_url).hostname or ""

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            logger.warning("BeautifulSoup konnte HTML nicht parsen", exc_info=True)
            soup = None

        # 1. Links aus <a href="...">-Tags
        if soup:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href", "").strip()
                if not href:
                    continue
                absolute_url = urljoin(base_url, href)
                onion_urls = self._find_onion_urls(absolute_url)

                for onion_url in onion_urls:
                    onion_url = self._normalize(onion_url)
                    if onion_url not in seen:
                        # Prüfen ob selbe Domain
                        onion_host = urlparse(onion_url).hostname or ""
                        if not self.include_same_domain and onion_host == base_host:
                            continue
                        seen.add(onion_url)
                        links.append(
                            {
                                "url": onion_url,
                                "source_url": base_url,
                                "anchor_text": a_tag.get_text(strip=True)[:200],
                                "extracted_from": "a_href",
                            }
                        )

        # 2. Direkte .onion-URLs im Rohtext (falls BeautifulSoup fehlschlug)
        for match in ONION_URL_PATTERN.finditer(html):
            url = self._normalize(match.group(1))
            if url not in seen:
                seen.add(url)
                links.append(
                    {
                        "url": url,
                        "source_url": base_url,
                        "anchor_text": "",
                        "extracted_from": "raw_text",
                    }
                )

        # 3. .onion-Hostnamen ohne Protokoll (z.B. "forumabc123.onion")
        for match in ONION_RAW_PATTERN.finditer(html):
            raw = match.group(1)
            url = self._normalize(f"http://{raw}")
            if url not in seen:
                seen.add(url)
                links.append(
                    {
                        "url": url,
                        "source_url": base_url,
                        "anchor_text": "",
                        "extracted_from": "raw_hostname",
                    }
                )

        # Begrenzen
        links = links[: self.max_links_per_page]

        logger.debug(f"{len(links)} Onion-Links aus {base_url} extrahiert")
        return links

    @staticmethod
    def _normalize(url: str) -> str:
        """Normalisiert eine URL: lowercase, Pfad bereinigen."""
        url = url.lower().rstrip("/")
        # Entferne Fragment
        if "#" in url:
            url = url[: url.index("#")]
        return url

    @staticmethod
    def _find_onion_urls(url: str) -> list[str]:
        """Findet .onion-URLs in einem String."""
        return (
            ONION_URL_PATTERN.findall(url) or [url] if ".onion" in url.lower() else []
        )

    @staticmethod
    def is_onion(url: str) -> bool:
        return ".onion" in url.lower()
