import logging
from typing import Any, Callable, Dict, List
import httpx

from backend.config import settings
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.extraction.article_extractor import ArticleExtractor
from backend.modules.extraction.metadata_extractor import MetadataExtractor
from backend.modules.extraction.transcript_extractor import TranscriptExtractor


class _MockResponse:
    def __init__(self, status_code: int, text: str = "", json_data: Any = None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data

    def json(self):
        return self._json_data


def _install_mock_httpx(
    monkeypatch,
    get_handler: Callable[[str], Any],
    post_handler: Callable[[str, Dict[str, Any]], Any] = None,
    recorded_calls: List[Dict[str, Any]] = None,
):
    calls = recorded_calls if recorded_calls is not None else []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None, **kwargs):
            calls.append({"method": "GET", "url": url})
            res = get_handler(url)
            if isinstance(res, Exception):
                raise res
            return res

        def post(self, url, headers=None, json=None, **kwargs):
            calls.append({"method": "POST", "url": url, "json": json})
            if post_handler is None:
                raise AssertionError(f"Unexpected Firecrawl POST to {url}")
            res = post_handler(url, json or {})
            if isinstance(res, Exception):
                raise res
            return res

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    return calls


VALID_ARTICLE_HTML = """
<html>
  <head>
    <title>How Modern AI Systems Scale - Tech Herald</title>
    <meta property="og:title" content="How Modern AI Systems Scale" />
    <meta property="og:site_name" content="Tech Herald" />
  </head>
  <body>
    <nav><a href="/">Home</a> <a href="/news">News</a> <a href="/login">Sign in</a></nav>
    <div id="cookie-banner">We use cookies to improve your experience. Accept all cookies.</div>
    <article>
      <h1>How Modern AI Systems Scale</h1>
      <p>Enterprise software engineering teams are rapidly adopting resilient local extraction pipelines before relying on costly third-party APIs.</p>
      <p>In an extensive industry interview, senior architects explained how structured caching and HTML quality validation dramatically lower infrastructure bills while preserving accuracy and latency SLAs.</p>
    </article>
    <footer>Copyright 2026 Tech Herald</footer>
  </body>
</html>
"""


def test_httpx_valid_article_skips_firecrawl(monkeypatch, caplog):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 200)

    calls = _install_mock_httpx(
        monkeypatch,
        get_handler=lambda url: _MockResponse(200, text=VALID_ARTICLE_HTML),
        post_handler=lambda url, payload: AssertionError("Firecrawl should NOT be called when HTTPX succeeds"),
    )

    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, title, publisher, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/articles/ai-systems"
        )

    assert status == "SUCCESS"
    assert method == "httpx"
    assert title == "How Modern AI Systems Scale"
    assert publisher == "Tech Herald"
    assert content is not None and "resilient local extraction pipelines" in content
    assert "We use cookies" not in content
    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert "method=httpx" in caplog.text


def test_httpx_403_triggers_firecrawl_fallback(monkeypatch, caplog):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")

    calls = _install_mock_httpx(
        monkeypatch,
        get_handler=lambda url: _MockResponse(403, text="Forbidden"),
        post_handler=lambda url, payload: _MockResponse(
            200,
            json_data={"data": {"markdown": "Rescued full article text extracted cleanly by Firecrawl fallback service."}},
        ),
    )

    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, _, _, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/protected/article"
        )

    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert "Rescued full article text" in content
    assert [c["method"] for c in calls] == ["GET", "POST"]
    assert calls[1]["url"] == "https://api.firecrawl.dev/v0/scrape"
    assert "method=firecrawl" in caplog.text


def test_httpx_200_empty_or_cookie_nav_boilerplate_triggers_firecrawl(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 200)

    for html_body in (
        "<html><body></body></html>",
        "<html><body><p>Short stub.</p></body></html>",
        (
            "<html><body>"
            "<nav><a href='/a'>Home Menu</a> <a href='/b'>Pricing</a> <a href='/c'>Login</a></nav>"
            "<p>We use cookies to improve browsing. Accept all cookies or manage cookie preferences.</p>"
            "</body></html>"
        ),
    ):
        calls = _install_mock_httpx(
            monkeypatch,
            get_handler=lambda url, body=html_body: _MockResponse(200, text=body),
            post_handler=lambda url, payload: _MockResponse(
                200,
                json_data={"data": {"markdown": "Complete article body retrieved after insufficient HTTPX content."}},
            ),
        )
        content, status, _, _, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/empty-or-banner"
        )
        assert status == "SUCCESS"
        assert method == "firecrawl"
        assert "Complete article body" in content
        assert [c["method"] for c in calls] == ["GET", "POST"]


def test_httpx_captcha_and_login_pages_trigger_firecrawl(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 150)

    captcha_html = """
    <html>
      <head><title>Just a moment...</title></head>
      <body>
        <form id="challenge-form">
          <p>Checking your browser before accessing this publication. Please verify you are human and complete the CAPTCHA to continue reading this article.</p>
          <div class="g-recaptcha"></div>
        </form>
      </body>
    </html>
    """
    login_html = """
    <html>
      <head><title>Sign In - Member Portal</title></head>
      <body>
        <main>
          <form>
            <p>Please sign in to view the full story and executive commentary for this member-only publication.</p>
            <p>Create a free account to continue reading our latest investigative interviews and deep-dive reports.</p>
            <input type="password" name="password" />
          </form>
        </main>
      </body>
    </html>
    """

    for gate_html in (captcha_html, login_html):
        calls = _install_mock_httpx(
            monkeypatch,
            get_handler=lambda url, body=gate_html: _MockResponse(200, text=body),
            post_handler=lambda url, payload: _MockResponse(
                200,
                json_data={"data": {"content": "Authenticated Firecrawl content bypassing gate wall cleanly."}},
            ),
        )
        content, status, _, _, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/gated"
        )
        assert status == "SUCCESS"
        assert method == "firecrawl"
        assert "Authenticated Firecrawl content" in content
        assert [c["method"] for c in calls] == ["GET", "POST"]


def test_httpx_timeout_triggers_firecrawl_fallback(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")

    def _timeout(url):
        raise httpx.TimeoutException("Timed out reading URL")

    calls = _install_mock_httpx(
        monkeypatch,
        get_handler=_timeout,
        post_handler=lambda url, payload: _MockResponse(
            200,
            json_data={"data": {"markdown": "Recovered content from Firecrawl after HTTPX timeout."}},
        ),
    )

    content, status, _, _, method = ArticleExtractor.extract_article_with_method(
        "https://example.org/slow-site"
    )
    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert "Recovered content" in content
    assert [c["method"] for c in calls] == ["GET", "POST"]


def test_firecrawl_fallback_failure_preserves_error_handling_and_redacts_key(monkeypatch, caplog):
    secret = "fc-ultra-secret-never-log"
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", secret)

    _install_mock_httpx(
        monkeypatch,
        get_handler=lambda url: _MockResponse(403, text="Forbidden"),
        post_handler=lambda url, payload: httpx.ConnectError(f"Connection failed with key {secret}"),
    )

    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, title, publisher, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/hard-blocked"
        )

    assert content is None
    assert status == "RESTRICTED"
    assert title is None
    assert publisher is None
    assert method == "failed"
    assert secret not in caplog.text
    assert "method=failure" in caplog.text

    # Also verify metadata fallback continues working when MetadataExtractor wraps failed extraction
    item = DiscoveredItem(
        title="Blocked News Piece",
        url="https://example.org/hard-blocked",
        description="Fallback snippet from search index metadata.",
        source_type="NEWS",
    )
    payload = MetadataExtractor.extract(item)
    assert payload.extraction_status == "METADATA_FALLBACK"
    assert payload.extraction_method == "metadata_fallback"
    assert payload.extracted_content == "Fallback snippet from search index metadata."


def test_youtube_urls_continue_using_transcript_workflow(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")

    monkeypatch.setattr(
        TranscriptExtractor,
        "extract_transcript",
        staticmethod(lambda url: ("Full YouTube interview transcript text here.", "SUCCESS")),
    )
    monkeypatch.setattr(
        ArticleExtractor,
        "extract_article",
        classmethod(lambda cls, url: AssertionError("ArticleExtractor must not be called for YouTube URLs")),
    )

    item = DiscoveredItem(
        title="Founder Keynote Interview",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="YOUTUBE",
    )
    payload = MetadataExtractor.extract(item)

    assert payload.extraction_status == "SUCCESS"
    assert payload.extraction_method == "youtube_transcript"
    assert payload.extracted_content == "Full YouTube interview transcript text here."

