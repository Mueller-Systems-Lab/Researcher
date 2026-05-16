# =============================================================================
# Tests: Darknet-Crawler (T-025 Coverage)
# =============================================================================
import sys, os
from unittest.mock import patch, MagicMock

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
def test_crawler_login_not_configured(mock_get):
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    result = crawler.login()
    assert result is False


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
