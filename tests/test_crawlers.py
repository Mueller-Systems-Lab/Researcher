# =============================================================================
# Tests: Darknet-Crawler (Issue #43 — Coverage ≥ 80%)
# =============================================================================
# Mock-Strategie:
#   - unittest.mock.patch für requests.Session + Tor-SOCKS
#   - responses Library für realistische HTTP-Mocks
#   - monkeypatch für Umgebungsvariablen
# =============================================================================
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# Config Tests
# ============================================================================
def test_crawler_config_defaults():
    from crawlers.config import CrawlerConfig

    cfg = CrawlerConfig()
    assert cfg.tor_host == "127.0.0.1"
    assert cfg.tor_port == 9050
    assert cfg.proxy_url == "socks5h://127.0.0.1:9050"
    assert cfg.max_pages == 5
    assert cfg.crawl_delay == 5.0
    assert cfg.is_configured is False


def test_crawler_config_configured():
    os.environ["FORUM_BASE_URL"] = "http://forum.onion"
    os.environ["LOGIN_URL"] = "http://forum.onion/login"
    try:
        from crawlers.config import CrawlerConfig

        cfg = CrawlerConfig()
        assert cfg.is_configured is True
    finally:
        del os.environ["FORUM_BASE_URL"]
        del os.environ["LOGIN_URL"]


# ============================================================================
# Dataclass Tests
# ============================================================================
def test_forum_post_dataclass():
    from crawlers.darknet_crawler import ForumPost

    post = ForumPost(url="http://t.onion", author="a", timestamp="now", content="c")
    assert post.url == "http://t.onion"
    assert post.title == ""
    assert post.forum_id == ""


# ============================================================================
# Static Helper Tests
# ============================================================================
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_text_from_html(mock_get):
    from bs4 import BeautifulSoup

    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    html = '<div class="content">Hello <b>World</b></div>'
    soup = BeautifulSoup(html, "lxml")
    text = crawler._extract_text(soup, "div.content")
    assert "Hello" in text and "World" in text


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_attribute(mock_get):
    from bs4 import BeautifulSoup

    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    html = '<time datetime="2026-05-16">May 16</time>'
    soup = BeautifulSoup(html, "lxml")
    dt = crawler._extract_attribute(soup, "time", "datetime")
    assert dt == "2026-05-16"


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_not_found(mock_get):
    from bs4 import BeautifulSoup

    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    soup = BeautifulSoup("<p>No data</p>", "lxml")
    assert crawler._extract_text(soup, "div.nonexistent") == ""
    assert crawler._extract_attribute(soup, "span", "data-x") is None


# ============================================================================
# CSRF Token Tests
# ============================================================================
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_csrf(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    html = '<input name="csrf_token" value="abc123">'
    token = crawler._extract_csrf_token(html)
    assert token == "abc123"


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_csrf_none(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    html = '<input name="username" value="test">'
    token = crawler._extract_csrf_token(html)
    assert token is None


# ============================================================================
# Session / __init__ Tests
# ============================================================================
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_session_created(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    assert crawler.session is not None
    assert "socks5h://" in crawler.session.proxies.get("http", "")


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_init_with_config_override(mock_get):
    """__init__ mit config_override überschreibt Config-Werte."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler(
        config_override={
            "max_pages": 3,
            "crawl_delay": 2.0,
            "forum_base_url": "http://custom.onion",
            "login_url": "http://custom.onion/login",
        }
    )
    assert crawler.config.max_pages == 3
    assert crawler.config.crawl_delay == 2.0
    assert crawler.config.forum_base_url == "http://custom.onion"


# ============================================================================
# Login Tests
# ============================================================================
@pytest.fixture
def configured_crawler():
    """Crawler mit minimaler Konfiguration für Login-Tests."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "testuser"
    crawler.config.password = "testpass"
    return crawler


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_no_credentials(mock_get, configured_crawler):
    """Login schlägt fehl ohne Credentials."""
    configured_crawler.config.username = ""
    configured_crawler.config.password = ""
    result = configured_crawler.login()
    assert result is False


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_no_url(mock_get, configured_crawler):
    """Login schlägt fehl ohne Forum-URL."""
    configured_crawler.config.forum_base_url = ""
    configured_crawler.config.login_url = ""
    result = configured_crawler.login()
    assert result is False


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_success_with_csrf(mock_get, mock_post, configured_crawler):
    """Erfolgreicher Login mit CSRF-Token."""
    # Mock: Login-Seite mit CSRF-Token
    mock_login_page = MagicMock()
    mock_login_page.text = '<input name="csrf_token" value="token123">'
    mock_login_page.raise_for_status.return_value = None

    # Mock: Login-POST — URL enthält nicht "login" → logged_in wird True
    mock_post_response = MagicMock()
    mock_post_response.url = "http://forum.onion/index"
    mock_post_response.raise_for_status.return_value = None

    mock_get.return_value = mock_login_page
    mock_post.return_value = mock_post_response

    result = configured_crawler.login()
    assert result is True
    assert configured_crawler.logged_in is True


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_connection_error(mock_get, configured_crawler):
    """Login fängt ConnectionError und gibt False zurück."""
    from requests.exceptions import ConnectionError

    mock_get.side_effect = ConnectionError("Tor not reachable")
    result = configured_crawler.login()
    assert result is False


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_http_403(mock_get, configured_crawler):
    """Login bei HTTP 403 (Forbidden) gibt False zurück."""
    from requests.exceptions import HTTPError

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
    mock_get.return_value = mock_response

    result = configured_crawler.login()
    assert result is False


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_http_500(mock_get, configured_crawler):
    """Login bei HTTP 500 (Server Error) gibt False zurück."""
    from requests.exceptions import HTTPError

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
    mock_get.return_value = mock_response

    result = configured_crawler.login()
    assert result is False


# ============================================================================
# Crawl Thread Page Tests
# ============================================================================
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html><body>
    <div class="post">
        <span class="author">User1</span>
        <span class="time">2026-05-16</span>
        <div class="content">Test post content</div>
        <h2 class="post_title">Test Title</h2>
    </div>
    <div class="post">
        <span class="author">User2</span>
        <span class="time">2026-05-15</span>
        <div class="content">Another post</div>
    </div>
    </body></html>
    """
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    crawler = DarknetCrawler()
    crawler.logged_in = True
    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")

    assert len(posts) == 2
    assert posts[0].author == "User1"
    assert posts[0].content == "Test post content"
    assert posts[1].author == "User2"


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page_http_error(mock_get):
    from requests.exceptions import HTTPError

    from crawlers.darknet_crawler import DarknetCrawler

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("404")
    mock_get.return_value = mock_response

    crawler = DarknetCrawler()
    crawler.logged_in = True
    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")
    assert posts == []


@patch("crawlers.darknet_crawler.time.sleep")  # Mock sleep to avoid waiting
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page_unicode(mock_get, mock_sleep):
    """Crawl mit Unicode-/Sonderzeichen in Post-Inhalten."""
    from crawlers.darknet_crawler import DarknetCrawler

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html><body>
    <div class="post">
        <span class="author">Üser1</span>
        <span class="time">2026-05-16</span>
        <div class="content">ポスト内容 with émojis 🕵️‍♂️</div>
    </div>
    </body></html>
    """
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    crawler = DarknetCrawler()
    crawler.logged_in = True
    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")

    assert len(posts) == 1
    assert "Üser1" in posts[0].author
    assert "ポスト内容" in posts[0].content


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page_empty(mock_get):
    """Crawl einer leeren Seite (keine Posts)."""
    from crawlers.darknet_crawler import DarknetCrawler

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><p>No posts yet.</p></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    crawler = DarknetCrawler()
    crawler.logged_in = True
    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")
    assert posts == []


# ============================================================================
# Crawl (Multi-Page) Tests
# ============================================================================
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_no_url(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    result = crawler.crawl(max_pages=1)
    assert result == []


@patch("crawlers.darknet_crawler.time.sleep")
def test_crawler_crawl_multi_page(mock_sleep):
    """crawl() über mehrere Seiten — mocked crawl_thread_page."""
    from crawlers.darknet_crawler import DarknetCrawler, ForumPost

    crawler = DarknetCrawler()
    crawler.logged_in = True
    crawler.config.forum_base_url = "http://forum.onion/thread/1"
    crawler.config.max_pages = 3

    # Mock crawl_thread_page: gibt für jede Seite 1 Post zurück
    call_count = {"count": 0}

    def fake_crawl(url, page=1):
        call_count["count"] += 1
        return [
            ForumPost(
                url=url,
                author=f"User{page}",
                timestamp=f"day{page}",
                content=f"Post {page}",
            )
        ]

    with patch.object(crawler, "crawl_thread_page", side_effect=fake_crawl):
        posts = crawler.crawl()

    assert len(posts) == 3
    assert posts[0].author == "User1"
    assert posts[1].author == "User2"
    assert posts[2].author == "User3"
    assert call_count["count"] == 3


# ════════════════════════════════════════════════════════════════════════
# R3 Branch-Coverage — darknet_crawler.py (94% → 97%+)
# Missing lines: 134, 157, 191-193, 221-222
# ════════════════════════════════════════════════════════════════════════


def test_crawler_login_failure_logged_in_false():
    """login(): when URL still contains 'login' after POST → logged_in=False (Line 134)."""
    from unittest.mock import MagicMock

    from crawlers.darknet_crawler import DarknetCrawler

    config = MagicMock()
    config.forum_base_url = "http://forum.onion"
    config.forum_login_url = "http://forum.onion/login"
    config.forum_username = "testuser"
    config.forum_password = "testpass"

    crawler = DarknetCrawler(config)
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.url = "http://forum.onion/login?error=1"
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    crawler.session = mock_session

    result = crawler.login()
    assert result is False
    assert crawler.logged_in is False


def test_crawler_no_forum_base_url():
    """crawl(): empty forum_base_url → returns [] (Lines 221-222)."""
    from unittest.mock import MagicMock

    from crawlers.darknet_crawler import DarknetCrawler

    config = MagicMock()
    config.forum_base_url = ""

    crawler = DarknetCrawler(config)
    crawler.logged_in = True  # skip login check

    result = crawler.crawl()
    assert result == []


def test_crawler_post_parse_exception_continue():
    """crawl_thread_page: parse exception caught, continues to next post (Lines 191-193)."""
    from unittest.mock import MagicMock, patch

    from crawlers.darknet_crawler import DarknetCrawler

    config = MagicMock()
    config.forum_base_url = "http://forum.onion"
    config.crawl_delay = 0
    crawler = DarknetCrawler(config)

    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response
    crawler.session = mock_session

    # Mock BeautifulSoup to have elements that cause extraction errors
    with patch("crawlers.darknet_crawler.BeautifulSoup") as mock_bs:
        mock_soup = MagicMock()
        mock_element = MagicMock()
        # Two elements: first raises AttributeError, second returns nothing
        mock_soup.select.return_value = [mock_element]
        # Make text extraction raise an exception
        mock_element.get_text.side_effect = AttributeError("no text")
        mock_bs.return_value = mock_soup

        posts = crawler.crawl_thread_page("http://forum.onion/thread/1")
        # Should return empty or handle gracefully — exception caught
        assert isinstance(posts, list)


# ── Missing-Line Coverage: 134, 157, 191-193 ─────────────────────────────


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_failed_not_redirected(mock_get, mock_post):
    """Login returns response still on login page → logged_in=False (line 134)."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "pass"

    # Login page response
    login_page = MagicMock()
    login_page.text = '<input name="csrf_token" value="token123">'
    login_page.raise_for_status.return_value = None

    # Login POST response — URL still contains "login"
    login_response = MagicMock()
    login_response.url = "http://forum.onion/login?error=1"
    login_response.raise_for_status.return_value = None

    mock_get.return_value = login_page
    mock_post.return_value = login_response

    result = crawler.login()
    assert result is False
    assert crawler.logged_in is False


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page_pagination_delay(mock_get):
    """crawl_thread_page with page>1 triggers crawl_delay sleep (line 157)."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    crawler.config.crawl_delay = 0.001  # minimal delay for test

    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with patch("crawlers.darknet_crawler.time.sleep") as mock_sleep:
        posts = crawler.crawl_thread_page("http://forum.onion/thread/1", page=2)

    assert isinstance(posts, list)
    mock_sleep.assert_called_once_with(0.001)


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_post_parse_exception_with_mixed_elements(mock_get):
    """Post parsing exception with mixed elements → logged and continue (lines 191-193)."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    mock_response = MagicMock()
    mock_response.text = "<html><body></body></html>"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with patch("crawlers.darknet_crawler.BeautifulSoup") as mock_bs:
        mock_soup = MagicMock()
        # First element causes exception, second element works
        mock_element_bad = MagicMock()
        mock_element_good = MagicMock()
        mock_soup.select.return_value = [mock_element_bad, mock_element_good]
        mock_soup.select_one.return_value = MagicMock()

        # Bad element: all extractors raise
        mock_element_bad.select_one.side_effect = RuntimeError("parse error")
        # Good element: normal extraction
        mock_element_good.select_one.return_value = MagicMock()
        mock_element_good.select_one.return_value.get_text.return_value = (
            "Valid content"
        )

        mock_bs.return_value = mock_soup

        with patch.object(
            crawler, "_extract_text", side_effect=RuntimeError("parse error")
        ):
            posts = crawler.crawl_thread_page("http://forum.onion/thread/1")

    assert isinstance(posts, list)
