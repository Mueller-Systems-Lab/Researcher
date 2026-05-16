# =============================================================================
# Tests: Darknet-Crawler (T-025 Coverage)
# =============================================================================
import sys, os
from unittest.mock import patch, MagicMock, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
    import os

    os.environ["FORUM_BASE_URL"] = "http://forum.onion"
    os.environ["LOGIN_URL"] = "http://forum.onion/login"
    try:
        from crawlers.config import CrawlerConfig

        cfg = CrawlerConfig()
        assert cfg.is_configured is True
    finally:
        del os.environ["FORUM_BASE_URL"]
        del os.environ["LOGIN_URL"]


def test_forum_post_dataclass():
    from crawlers.darknet_crawler import ForumPost

    post = ForumPost(url="http://t.onion", author="a", timestamp="now", content="c")
    assert post.url == "http://t.onion"
    assert post.title == ""
    assert post.forum_id == ""


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_no_credentials(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler
    import os

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = ""
    crawler.config.password = ""
    result = crawler.login()
    assert result is False


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_text_from_html(mock_get):
    """_extract_text und _extract_attribute Hilfsmethoden."""
    from crawlers.darknet_crawler import DarknetCrawler
    from bs4 import BeautifulSoup

    crawler = DarknetCrawler()
    html = '<div class="content">Hello <b>World</b></div>'
    soup = BeautifulSoup(html, "lxml")

    text = crawler._extract_text(soup, "div.content")
    assert "Hello" in text and "World" in text


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_attribute(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler
    from bs4 import BeautifulSoup

    crawler = DarknetCrawler()
    html = '<time datetime="2026-05-16">May 16</time>'
    soup = BeautifulSoup(html, "lxml")

    dt = crawler._extract_attribute(soup, "time", "datetime")
    assert dt == "2026-05-16"


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_extract_not_found(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler
    from bs4 import BeautifulSoup

    crawler = DarknetCrawler()
    soup = BeautifulSoup("<p>No data</p>", "lxml")

    assert crawler._extract_text(soup, "div.nonexistent") == ""
    assert crawler._extract_attribute(soup, "span", "data-x") is None


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_thread_page(mock_get):
    """crawl_thread_page parses HTML korrekt."""
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
    """crawl_thread_page bei HTTP-Fehler."""
    from crawlers.darknet_crawler import DarknetCrawler

    from requests.exceptions import HTTPError

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("404")
    mock_get.return_value = mock_response

    crawler = DarknetCrawler()
    crawler.logged_in = True
    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")
    assert posts == []


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_no_url(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    result = crawler.crawl(max_pages=1)
    assert result == []


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_session_created(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    assert crawler.session is not None
    assert "socks5h://" in crawler.session.proxies.get("http", "")


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


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_no_credentials(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler
    import os

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = ""
    crawler.config.password = ""
    result = crawler.login()
    assert result is False
