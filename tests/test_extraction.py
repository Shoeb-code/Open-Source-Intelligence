import logging
import threading
import time
from typing import Any, Callable, Dict, List
import httpx

from backend.config import settings
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.extraction.article_extractor import ArticleExtractor
from backend.modules.extraction.metadata_extractor import MetadataExtractor
from backend.modules.extraction.transcript_extractor import TranscriptExtractor
from backend.modules.identity.verifier import IdentityVerifier
from backend.modules.persons.schemas import IdentityContext
from backend.utils.url_validator import canonicalize_url


class _MockResponse:
    def __init__(self, status_code: int, text: str = "", json_data: Any = None, headers: Dict[str, str] = None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self.headers = headers or {}

    def json(self):
        return self._json_data


def _install_mock_httpx(
    monkeypatch,
    post_handler: Callable[[str, Dict[str, Any], Dict[str, Any]], Any],
    get_handler: Callable[[str], Any] = None,
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
            calls.append({"method": "GET", "url": url, "headers": headers or {}})
            if get_handler is None:
                raise AssertionError(f"Direct HTTPX GET must NOT be called for target URL: {url}")
            res = get_handler(url)
            if isinstance(res, Exception):
                raise res
            return res

        def post(self, url, headers=None, json=None, **kwargs):
            calls.append({"method": "POST", "url": url, "headers": headers or {}, "json": json or {}})
            res = post_handler(url, json or {}, headers or {})
            if isinstance(res, Exception):
                raise res
            return res

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    return calls


VALID_ARTICLE_MARKDOWN = (
    "# How Modern AI Systems Scale\n\n"
    "Enterprise software engineering teams are rapidly adopting resilient extraction pipelines "
    "to parse industry commentary, interviews, and long-form engineering blogs across distributed cloud deployments.\n\n"
    "In an extensive technical briefing, senior architects explained how structured Firecrawl rendering, "
    "concurrency bounds, and metadata validation preserve accuracy even on JS-heavy publications."
)


def test_firecrawl_v2_request_metadata_and_no_direct_httpx_get(monkeypatch, caplog):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "FIRECRAWL_SCRAPE_URL", "https://api.firecrawl.dev/v2/scrape")
    monkeypatch.setattr(settings, "FIRECRAWL_ONLY_MAIN_CONTENT", True)
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 200)

    calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={
                "success": True,
                "data": {
                    "markdown": VALID_ARTICLE_MARKDOWN,
                    "metadata": {
                        "title": "How Modern AI Systems Scale",
                        "ogSiteName": "Tech Herald",
                        "sourceURL": "https://example.org/articles/ai-systems",
                        "statusCode": 200,
                    },
                },
            },
        ),
    )

    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, title, publisher, method = ArticleExtractor.extract_article_with_method(
            "https://example.org/articles/ai-systems"
        )

    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert title == "How Modern AI Systems Scale"
    assert publisher == "Tech Herald"
    assert content is not None and "resilient extraction pipelines" in content
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == "https://api.firecrawl.dev/v2/scrape"
    assert calls[0]["headers"]["Authorization"] == "Bearer fc-test-secret-key"
    assert calls[0]["headers"]["Content-Type"] == "application/json"
    assert calls[0]["json"] == {
        "url": "https://example.org/articles/ai-systems",
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    details = ArticleExtractor.get_last_extraction_details()
    assert details is not None
    assert details["method"] == "firecrawl"
    assert details["target_status_code"] == 200
    assert details["api_status_code"] == 200
    assert "fc-test-secret-key" not in caplog.text
    assert "[PROVIDER] Firecrawl v2" in caplog.text


def test_firecrawl_handles_missing_metadata(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 150)

    _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={"success": True, "data": {"markdown": VALID_ARTICLE_MARKDOWN}},
        ),
    )

    content, status, title, publisher, method = ArticleExtractor.extract_article_with_method(
        "https://example.org/articles/no-meta"
    )
    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert title is None
    assert publisher is None
    assert content is not None and "How Modern AI Systems Scale" in content


def test_firecrawl_429_retries_respecting_retry_after(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    sleep_calls = []
    monkeypatch.setattr("backend.modules.extraction.article_extractor.time.sleep", lambda s: sleep_calls.append(s))

    attempts = {"count": 0}

    def _handler(url, payload, headers):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _MockResponse(429, headers={"Retry-After": "1.2"})
        return _MockResponse(200, json_data={"success": True, "data": {"markdown": VALID_ARTICLE_MARKDOWN}})

    _install_mock_httpx(monkeypatch, post_handler=_handler)

    content, status, _, _, method = ArticleExtractor.extract_article_with_method("https://example.org/rate-limited")
    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert attempts["count"] == 2
    assert sleep_calls == [1.2]
    assert content is not None


def test_firecrawl_502_503_bounded_retries(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    sleep_calls = []
    monkeypatch.setattr("backend.modules.extraction.article_extractor.time.sleep", lambda s: sleep_calls.append(s))

    codes = [502, 503, 200]

    def _handler(url, payload, headers):
        code = codes.pop(0)
        if code != 200:
            return _MockResponse(code)
        return _MockResponse(200, json_data={"success": True, "data": {"markdown": VALID_ARTICLE_MARKDOWN}})

    calls = _install_mock_httpx(monkeypatch, post_handler=_handler)
    content, status, _, _, method = ArticleExtractor.extract_article_with_method("https://example.org/transient-gateway")

    assert status == "SUCCESS"
    assert method == "firecrawl"
    assert len(calls) == 3
    assert len(sleep_calls) == 2
    assert content is not None


def test_firecrawl_402_fails_immediately_without_retry_and_redacts_key(monkeypatch, caplog):
    secret = "fc-ultra-secret-never-log"
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", secret)
    monkeypatch.setattr("backend.modules.extraction.article_extractor.time.sleep", lambda s: AssertionError("Must not sleep on 402"))

    calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(402, text="Payment Required"),
    )

    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, _, _, method = ArticleExtractor.extract_article_with_method("https://example.org/article")

    assert content is None
    assert status == "FAILED"
    assert method == "failed"
    assert len(calls) == 1
    assert secret not in caplog.text
    assert "402" in caplog.text


def test_firecrawl_timeout_and_missing_key_fallback_safely(monkeypatch, caplog):
    secret = "fc-secret-timeout-key"
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", secret)
    monkeypatch.setattr("backend.modules.extraction.article_extractor.time.sleep", lambda s: None)

    calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: httpx.TimeoutException(f"Timeout using {secret}"),
    )
    with caplog.at_level(logging.INFO, logger="appearance_intelligence"):
        content, status, _, _, method = ArticleExtractor.extract_article_with_method("https://example.org/slow")
    assert content is None
    assert status == "FAILED"
    assert method == "failed"
    assert len(calls) == 2
    assert secret not in caplog.text

    # Missing API key makes zero requests and falls back to metadata snippet if present
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", None)
    no_key_calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: AssertionError("Firecrawl must not be called when API key is missing"),
    )
    item = DiscoveredItem(
        title="Fallback News Piece",
        url="https://example.org/missing-key",
        description="Fallback snippet from search index metadata.",
        source_type="NEWS",
    )
    payload = MetadataExtractor.extract(item)
    assert payload.extraction_status == "METADATA_FALLBACK"
    assert payload.extraction_method == "metadata_fallback"
    assert payload.extracted_content == "Fallback snippet from search index metadata."
    assert no_key_calls == []


def test_firecrawl_cloudflare_captcha_login_and_short_content_rejected(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 200)

    # 1. Cloudflare / CAPTCHA markdown returned with HTTP 200
    _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={
                "success": True,
                "data": {
                    "markdown": "Checking your browser before accessing this publication. Please verify you are human (challenges.cloudflare.com).",
                    "metadata": {"title": "Just a moment...", "statusCode": 403},
                },
            },
        ),
    )
    content, status, title, _, method = ArticleExtractor.extract_article_with_method("https://example.org/cf-wall")
    assert content is None
    assert status == "RESTRICTED"
    assert title is None
    assert method == "failed"

    # 2. Login wall markdown
    _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={
                "success": True,
                "data": {
                    "markdown": "Please sign in to view the full story. Create a free account to continue reading our member portal.",
                    "metadata": {"title": "Sign In - Portal", "statusCode": 200},
                },
            },
        ),
    )
    content_login, status_login, title_login, _, _ = ArticleExtractor.extract_article_with_method("https://example.org/login-wall")
    assert content_login is None
    assert status_login == "RESTRICTED"
    assert title_login is None

    # 3. Insufficient short stub falls back to search metadata when available
    _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={"success": True, "data": {"markdown": "Short stub.", "metadata": {"statusCode": 200}}},
        ),
    )
    item = DiscoveredItem(
        title="Short Page",
        url="https://example.org/stub",
        description="Indexed search summary for short stub page.",
        source_type="WEBPAGE",
    )
    payload = MetadataExtractor.extract(item)
    assert payload.extraction_status == "METADATA_FALLBACK"
    assert payload.extraction_method == "metadata_fallback"
    assert payload.extracted_content == "Indexed search summary for short stub page."


def test_binary_urls_skipped_before_firecrawl(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: AssertionError(f"Firecrawl must not be called for binary URL {url}"),
    )

    for url in (
        "https://example.org/assets/photo.JPG?width=800",
        "https://example.org/docs/report.pdf?download=1",
        "https://example.org/media/audio.mp3",
        "https://example.org/archive.zip",
    ):
        content, status, _, _, method = ArticleExtractor.extract_article_with_method(url)
        assert content is None
        assert status == "FAILED"
        assert method == "failed"

    assert calls == []


def test_shared_firecrawl_concurrency_semaphore(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "FIRECRAWL_MAX_CONCURRENCY", 2)

    active = 0
    max_observed = 0
    lock = threading.Lock()

    def _post(url, payload, headers):
        nonlocal active, max_observed
        with lock:
            active += 1
            max_observed = max(max_observed, active)
        time.sleep(0.06)
        with lock:
            active -= 1
        return _MockResponse(200, json_data={"success": True, "data": {"markdown": VALID_ARTICLE_MARKDOWN}})

    _install_mock_httpx(monkeypatch, post_handler=_post)

    sem1 = ArticleExtractor._get_firecrawl_semaphore()
    sem2 = ArticleExtractor._get_firecrawl_semaphore()
    assert sem1 is sem2

    urls = [f"https://site-{i}.example.org/article" for i in range(6)]
    results = []
    threads = [threading.Thread(target=lambda u=u: results.append(ArticleExtractor.extract_article_text(u))) for u in urls]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 6
    assert all(st == "SUCCESS" for _, st in results)
    assert max_observed <= 2


def test_all_web_sources_route_through_firecrawl_without_httpx_get(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "ARTICLE_MIN_CONTENT_LENGTH", 150)

    calls = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={
                "success": True,
                "data": {
                    "markdown": VALID_ARTICLE_MARKDOWN,
                    "metadata": {"title": f"Title for {payload['url']}", "ogSiteName": "Media Hub", "statusCode": 200},
                },
            },
        ),
    )

    for src_type in ("NEWS", "BLOG", "WEBPAGE", "PODCAST", "EVENT"):
        item = DiscoveredItem(
            title=f"{src_type} Appearance",
            url=f"https://example.org/{src_type.lower()}/appearance",
            source_type=src_type,
        )
        payload = MetadataExtractor.extract(item)
        assert payload.extraction_status == "SUCCESS"
        assert payload.extraction_method == "firecrawl"
        assert payload.publisher == "Media Hub"

    assert len(calls) == 5
    assert all(c["method"] == "POST" and c["url"] == "https://api.firecrawl.dev/v2/scrape" for c in calls)


def test_linkedin_firecrawl_first_exa_fallback_and_metadata_fallback(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")
    monkeypatch.setattr(settings, "EXA_API_KEY", "exa-test-key")

    # 1. LinkedIn post succeeds directly via Firecrawl (even short authentic LinkedIn post)
    calls1 = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(
            200,
            json_data={
                "success": True,
                "data": {
                    "markdown": "Auto Expo 2025 AI mobility launch milestone with CarDekho Group.",
                    "metadata": {"title": "Auto Expo 2025 Launch | Amit Jain | LinkedIn", "statusCode": 200},
                },
            },
        ),
    )
    li_post = DiscoveredItem(
        title="",
        url="https://linkedin.com/posts/cardekhoamitjain_autoexpo-activity-123",
        source_type="LINKEDIN",
    )
    p1 = MetadataExtractor.extract(li_post)
    assert p1.extraction_status == "SUCCESS"
    assert p1.extraction_method == "firecrawl"
    assert p1.publisher == "LinkedIn"
    assert p1.title == "Auto Expo 2025 Launch | Amit Jain"
    assert p1.extraction_details is not None
    assert p1.extraction_details["method"] == "firecrawl"
    assert calls1[0]["json"]["url"] == "https://www.linkedin.com/posts/cardekhoamitjain_autoexpo-activity-123"
    assert len(calls1) == 1

    # 2. LinkedIn profile falls back to Exa /contents when Firecrawl returns auth wall
    calls2 = _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: (
            _MockResponse(
                200,
                json_data={
                    "success": True,
                    "data": {"markdown": "Sign in or join LinkedIn to view this profile.", "metadata": {"title": "Sign In"}},
                },
            )
            if "firecrawl.dev" in url
            else _MockResponse(
                200,
                json_data={
                    "results": [
                        {
                            "title": "Amit Jain - Co-Founder & CEO",
                            "text": "Co-Founder & CEO at CarDekho Group. IIT Delhi alumnus building AI mobility.",
                        }
                    ]
                },
            )
        ),
    )
    li_profile = DiscoveredItem(
        title="Amit Jain Profile",
        url="https://www.linkedin.com/in/cardekhoamitjain",
        source_type="LINKEDIN",
    )
    p2 = MetadataExtractor.extract(li_profile)
    assert p2.extraction_status == "SUCCESS"
    assert p2.extraction_method == "exa_contents"
    assert "CarDekho Group" in (p2.extracted_content or "")
    assert [c["url"] for c in calls2] == [
        "https://api.firecrawl.dev/v2/scrape",
        "https://api.exa.ai/contents",
    ]
    # Verify existing identity scoring continues recognizing extracted LinkedIn profile
    ctx = IdentityContext(
        person_id="p-amit",
        name="Amit Jain",
        profession="CEO",
        organizations=["CarDekho Group"],
        known_usernames=["cardekhoamitjain"],
        profile_urls={"linkedin": canonicalize_url("https://www.linkedin.com/in/cardekhoamitjain")},
    )
    id_status, score, _ = IdentityVerifier.verify(ctx, p2)
    assert id_status == "VERIFIED" and score >= 0.6

    # 3. Both Firecrawl & Exa fail -> metadata fallback when description exists
    _install_mock_httpx(
        monkeypatch,
        post_handler=lambda url, payload, headers: _MockResponse(403, text="Forbidden"),
    )
    li_fallback = DiscoveredItem(
        title="LinkedIn Keynote Post",
        url="https://www.linkedin.com/posts/cardekhoamitjain_fallback-456",
        description="Search snippet summary for keynote post.",
        source_type="LINKEDIN",
    )
    p3 = MetadataExtractor.extract(li_fallback)
    assert p3.extraction_status == "METADATA_FALLBACK"
    assert p3.extraction_method == "metadata_fallback"
    assert p3.extracted_content == "Search snippet summary for keynote post."


def test_youtube_urls_continue_using_transcript_workflow(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-secret-key")

    monkeypatch.setattr(
        TranscriptExtractor,
        "extract_transcript",
        staticmethod(lambda url, allow_whisper=True: ("Full YouTube interview transcript text here.", "SUCCESS")),
    )
    monkeypatch.setattr(
        ArticleExtractor,
        "extract_article",
        classmethod(lambda cls, url: AssertionError("Firecrawl ArticleExtractor must not be called for YouTube URLs")),
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
