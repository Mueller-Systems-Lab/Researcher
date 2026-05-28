# =============================================================================
# Darknet-Crawler — Forum-Crawler über Tor SOCKS5
# =============================================================================
# Extrahiert Posts aus einem Darknet-Forum, bereinigt HTML und speichert
# strukturierte Daten für die Weitergabe an den Whoosh-Index (T-006).
#
# Nutzung:
#   from crawlers.darknet_crawler import DarknetCrawler
#   crawler = DarknetCrawler()
#   posts = crawler.crawl(max_pages=5)
#
# Sicherheitshinweise:
#   - Läuft ausschließlich über Tor SOCKS5-Proxy (kein Clearnet-Traffic)
#   - Nur passives HTML-Parsing (BeautifulSoup) — kein JavaScript
#   - Crawl-Pausen zwischen Requests (default 5s)
#   - Wegwerf-Account für Login verwenden
#   - Vor Nutzung rechtliche Prüfung erforderlich!
# =============================================================================

import logging
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from crawlers.config import config
from scrapers.http_session import create_session

logger = logging.getLogger(__name__)


@dataclass
class ForumPost:
    """Ein einzelner Forum-Post."""

    url: str
    author: str
    timestamp: str
    content: str
    title: str = ""
    forum_id: str = ""


class DarknetCrawler:
    """Crawler für Darknet-Foren über Tor SOCKS5.

    Verwendet eine `requests.Session` mit Tor-SOCKS5-Proxy.
    Alle HTTP-Anfragen laufen über Tor — keine direkten Verbindungen.
    """

    def __init__(self, config_override: dict | None = None):
        # Tiefe Kopie der globalen Config pro Instanz (T-024)
        import copy

        self.config = copy.deepcopy(config)
        if config_override:
            for key, value in config_override.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

        self.session = self._create_session()
        self.logged_in = False

    def _create_session(self) -> requests.Session:
        """Erstellt eine requests.Session mit Tor-SOCKS5-Proxy (via http_session)."""
        return create_session(proxy=self.config.proxy_url)

    def _extract_csrf_token(self, html: str) -> str | None:
        """Extrahiert CSRF-Token aus einem Login-Formular."""
        soup = BeautifulSoup(html, "lxml")
        for inp in soup.find_all("input"):
            name = inp.get("name", "")
            if "csrf" in name.lower() or "token" in name.lower():
                return inp.get("value")
        return None

    def login(self) -> bool:
        """Meldet sich im Forum an.

        Geht davon aus, dass das Forum ein CSRF-geschütztes Login-Formular hat.
        Die Login-URL und Credentials werden aus der Konfiguration gelesen.

        Returns:
            True bei erfolgreichem Login, False bei Fehler.
        """
        if not self.config.is_configured:
            logger.error(
                "Crawler nicht konfiguriert: FORUM_BASE_URL und LOGIN_URL "
                "müssen gesetzt sein"
            )
            return False

        if not self.config.username or not self.config.password:
            logger.error(
                "Login-Daten nicht konfiguriert: FORUM_USERNAME und "
                "FORUM_PASSWORD müssen gesetzt sein"
            )
            return False

        try:
            # Login-Seite laden, um CSRF-Token zu extrahieren
            logger.info(f"Lade Login-Seite: {self.config.login_url}")
            r = self.session.get(self.config.login_url, timeout=30)
            r.raise_for_status()

            csrf_token = self._extract_csrf_token(r.text)
            if csrf_token:
                logger.debug(f"CSRF-Token gefunden: {csrf_token[:20]}...")

            # Login-Daten
            login_data = {
                "username": self.config.username,
                "password": self.config.password,
            }
            if csrf_token:
                login_data["csrf_token"] = csrf_token

            # Login ausführen
            logger.info("Führe Login aus...")
            r = self.session.post(
                self.config.login_url,
                data=login_data,
                timeout=30,
            )
            r.raise_for_status()

            # Prüfen, ob Login erfolgreich war
            # (z. B. durch Prüfen auf Logout-Link oder fehlendes Login-Formular)
            self.logged_in = "login" not in r.url.lower()
            if self.logged_in:
                logger.info("Login erfolgreich")
            else:
                logger.warning("Login möglicherweise fehlgeschlagen")
            return self.logged_in

        except requests.RequestException as e:
            logger.error(f"Login-Fehler: {e}")
            return False

    def crawl_thread_page(self, url: str, page: int = 1) -> list[ForumPost]:
        """Crawlt eine einzelne Thread-Seite.

        Args:
            url: Basis-URL des Threads.
            page: Seitennummer (wird an URL angehängt).

        Returns:
            Liste von ForumPost-Dataclasses.
        """
        page_url = f"{url}?page={page}" if page > 1 else url
        posts = []

        try:
            # Crawl-Pause vor dem Request
            if page > 1:
                time.sleep(self.config.crawl_delay)

            logger.debug(f"Crawle Seite: {page_url}")
            r = self.session.get(page_url, timeout=60)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "lxml")
            post_elements = soup.select(
                "div.post, article.post, div.forum_post, div.message"
            )

            for element in post_elements[: self.config.max_posts_per_page]:
                try:
                    post = ForumPost(
                        url=page_url,
                        author=self._extract_text(
                            element, "span.author, .username, .post_author"
                        ),
                        timestamp=self._extract_attribute(
                            element,
                            "span.time, .date, time",
                            "datetime",
                        )
                        or self._extract_text(element, "span.time, .date, time"),
                        content=self._extract_text(
                            element, "div.content, .post_content, .message"
                        ),
                        title=self._extract_text(
                            element,
                            "h2.post_title, .post_title, .thread_title",
                        ),
                    )
                    if post.content:
                        posts.append(post)
                except Exception as e:
                    logger.warning(f"Fehler beim Parsen eines Posts: {e}")
                    continue

            logger.debug(f"  → {len(posts)} Posts von Seite {page} extrahiert")

        except requests.RequestException as e:
            logger.error(f"Fehler beim Crawlen von {page_url}: {e}")

        return posts

    def crawl(self, max_pages: int | None = None) -> list[ForumPost]:
        """Crawlt mehrere Seiten eines Threads.

        Args:
            max_pages: Maximale Anzahl Seiten (default: aus Konfiguration).

        Returns:
            Liste aller gefundenen ForumPosts.
        """
        if max_pages is None:
            max_pages = self.config.max_pages

        if not self.logged_in:
            logger.info("Nicht eingeloggt — versuche Login...")
            if not self.login():
                logger.error("Login fehlgeschlagen — Crawling abgebrochen")
                return []

        if not self.config.forum_base_url:
            logger.error("FORUM_BASE_URL nicht konfiguriert — Crawling abgebrochen")
            return []

        all_posts = []
        logger.info(
            f"Starte Crawling: {self.config.forum_base_url} ({max_pages} Seiten)"
        )

        for page in range(1, max_pages + 1):
            posts = self.crawl_thread_page(self.config.forum_base_url, page)
            all_posts.extend(posts)
            logger.info(
                f"Seite {page}/{max_pages}: {len(posts)} Posts "
                f"(gesamt: {len(all_posts)})"
            )

            # Pause zwischen Seiten (ausser nach der letzten)
            if page < max_pages:
                time.sleep(self.config.crawl_delay)

        logger.info(f"Crawling abgeschlossen: {len(all_posts)} Posts extrahiert")
        return all_posts

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: str) -> str:
        """Extrahiert Text aus einem Element per CSS-Selektor."""
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_attribute(
        soup: BeautifulSoup, selector: str, attribute: str
    ) -> str | None:
        """Extrahiert ein Attribut aus einem Element per CSS-Selektor."""
        element = soup.select_one(selector)
        if element:
            return element.get(attribute)
        return None
