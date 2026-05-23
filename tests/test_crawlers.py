# =============================================================================
# Tests: Darknet-Crawler (T-025 Coverage)
# =============================================================================
import os
import sys
from unittest.mock import MagicMock, patch

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
    from requests.exceptions import HTTPError

    from crawlers.darknet_crawler import DarknetCrawler

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


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_success(mock_get, mock_post):
    """Login mit gültigen Credentials setzt logged_in auf True."""
    from crawlers.darknet_crawler import DarknetCrawler

    login_page = MagicMock()
    login_page.text = '<input name="csrf_token" value="abc123">'
    login_page.raise_for_status.return_value = None
    mock_get.return_value = login_page

    login_response = MagicMock()
    login_response.url = "http://forum.onion/"
    login_response.raise_for_status.return_value = None
    mock_post.return_value = login_response

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "pass"

    result = crawler.login()

    assert result is True
    assert crawler.logged_in is True


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_http_error(mock_get):
    """Login mit HTTP-Fehler gibt False zurück und crasht nicht."""
    from requests.exceptions import ConnectionError

    from crawlers.darknet_crawler import DarknetCrawler

    mock_get.side_effect = ConnectionError("Tor nicht erreichbar")
    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "pass"

    result = crawler.login()

    assert result is False
    assert crawler.logged_in is False


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_wrong_password(mock_get, mock_post):
    """Login mit falschem Passwort bleibt ausgeloggt, wenn URL login enthält."""
    from crawlers.darknet_crawler import DarknetCrawler

    login_page = MagicMock()
    login_page.text = '<input name="csrf_token" value="abc123">'
    login_page.raise_for_status.return_value = None
    mock_get.return_value = login_page

    login_response = MagicMock()
    login_response.url = "http://forum.onion/login?failed=1"
    login_response.raise_for_status.return_value = None
    mock_post.return_value = login_response

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "wrong"

    result = crawler.login()

    assert result is False
    assert crawler.logged_in is False


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_login_no_csrf_still_works(mock_get, mock_post):
    """Login ohne CSRF-Token versucht POST ohne csrf_token-Feld."""
    from crawlers.darknet_crawler import DarknetCrawler

    login_page = MagicMock()
    login_page.text = '<form><input name="username" value=""></form>'
    login_page.raise_for_status.return_value = None
    mock_get.return_value = login_page

    login_response = MagicMock()
    login_response.url = "http://forum.onion/"
    login_response.raise_for_status.return_value = None
    mock_post.return_value = login_response

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "pass"

    result = crawler.login()

    assert result is True
    mock_post.assert_called_once()
    assert "csrf_token" not in mock_post.call_args.kwargs["data"]


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_auto_login(mock_get, mock_post):
    """crawl() führt automatisch Login aus, wenn noch nicht eingeloggt."""
    from crawlers.darknet_crawler import DarknetCrawler

    login_page = MagicMock()
    login_page.text = '<input name="csrf_token" value="abc123">'
    login_page.raise_for_status.return_value = None
    thread_page = MagicMock()
    thread_page.text = """
    <html><body><div class="post">
        <span class="author">AutoUser</span>
        <time datetime="2026-05-20">20.05.2026</time>
        <div class="content">Automatisch gecrawlter Post</div>
    </div></body></html>
    """
    thread_page.raise_for_status.return_value = None
    mock_get.side_effect = [login_page, thread_page]

    login_response = MagicMock()
    login_response.url = "http://forum.onion/"
    login_response.raise_for_status.return_value = None
    mock_post.return_value = login_response

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion/thread/1"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "user"
    crawler.config.password = "pass"
    crawler.config.crawl_delay = 0

    posts = crawler.crawl(max_pages=1)

    assert len(posts) == 1
    assert posts[0].author == "AutoUser"
    assert crawler.logged_in is True


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_multi_page(mock_get):
    """crawl() mit max_pages=3 crawlt drei Seiten."""
    from crawlers.darknet_crawler import DarknetCrawler

    responses = []
    for page in range(1, 4):
        response = MagicMock()
        response.text = f"""
        <html><body><div class="post">
            <span class="author">User{page}</span>
            <span class="time">2026-05-{page:02d}</span>
            <div class="content">Post von Seite {page}</div>
        </div></body></html>
        """
        response.raise_for_status.return_value = None
        responses.append(response)
    mock_get.side_effect = responses

    crawler = DarknetCrawler()
    crawler.logged_in = True
    crawler.config.forum_base_url = "http://forum.onion/thread/1"
    crawler.config.crawl_delay = 0

    posts = crawler.crawl(max_pages=3)

    assert len(posts) == 3
    assert mock_get.call_count == 3
    assert posts[2].content == "Post von Seite 3"


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_thread_page_empty_html(mock_get):
    """crawl_thread_page mit HTML ohne Posts gibt eine leere Liste zurück."""
    from crawlers.darknet_crawler import DarknetCrawler

    response = MagicMock()
    response.text = "<html><body>No posts</body></html>"
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    crawler = DarknetCrawler()
    crawler.logged_in = True

    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")

    assert posts == []


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_thread_page_connection_error(mock_get):
    """crawl_thread_page gibt bei ConnectionError eine leere Liste zurück."""
    from requests.exceptions import ConnectionError

    from crawlers.darknet_crawler import DarknetCrawler

    mock_get.side_effect = ConnectionError("Verbindung fehlgeschlagen")

    crawler = DarknetCrawler()
    crawler.logged_in = True

    posts = crawler.crawl_thread_page("http://forum.onion/thread/1")

    assert posts == []


@patch("crawlers.darknet_crawler.requests.Session.post")
@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_credentials_not_in_logs(mock_get, mock_post, caplog):
    """Username und Passwort erscheinen nicht in Log-Ausgaben."""
    import logging

    from crawlers.darknet_crawler import DarknetCrawler

    login_page = MagicMock()
    login_page.text = '<input name="csrf_token" value="abc123">'
    login_page.raise_for_status.return_value = None
    mock_get.return_value = login_page

    login_response = MagicMock()
    login_response.url = "http://forum.onion/"
    login_response.raise_for_status.return_value = None
    mock_post.return_value = login_response

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = "http://forum.onion"
    crawler.config.login_url = "http://forum.onion/login"
    crawler.config.username = "secret-user"
    crawler.config.password = "super-secret-password"

    with caplog.at_level(logging.DEBUG, logger="crawlers.darknet_crawler"):
        assert crawler.login() is True

    assert "secret-user" not in caplog.text
    assert "super-secret-password" not in caplog.text


def test_crawler_config_override_respected():
    """config_override Parameter überschreibt Config-Werte."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler(config_override={"max_pages": 99})

    assert crawler.config.max_pages == 99


def test_crawler_session_socks5_proxy_configured():
    """Session hat SOCKS5-Proxy für HTTP und HTTPS gesetzt."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()

    assert "socks5h://" in crawler.session.proxies["http"]
    assert crawler.session.proxies["https"] == crawler.session.proxies["http"]


@patch("crawlers.darknet_crawler.requests.Session.get")
def test_crawler_crawl_no_forum_url(mock_get):
    """crawl() ohne FORUM_BASE_URL gibt eine leere Liste zurück."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    crawler.logged_in = True
    crawler.config.forum_base_url = ""

    result = crawler.crawl(max_pages=1)

    assert result == []
    mock_get.assert_not_called()


def test_crawler_login_not_configured():
    """login() ohne konfigurierte URLs gibt False zurück."""
    from crawlers.darknet_crawler import DarknetCrawler

    crawler = DarknetCrawler()
    crawler.config.forum_base_url = ""
    crawler.config.login_url = ""
    crawler.config.username = "user"
    crawler.config.password = "pass"

    result = crawler.login()

    assert result is False
