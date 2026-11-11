import time
import threading
import httpx

from backend.config import settings
from backend.database.models import Appearance, Person, Source
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.service import DiscoveryService
from backend.modules.extraction.article_extractor import ArticleExtractor
from backend.modules.extraction.metadata_extractor import ExtractedPayload, MetadataExtractor
from backend.modules.extraction.transcript_extractor import TranscriptExtractor
from backend.modules.persons.schemas import IdentityContext
from backend.utils.http_pool import DomainConcurrencyLimiter
from backend.workers.tasks import _extract_items_concurrently, _filter_new_candidates
from tests.conftest import TestingSessionLocal


def test_filter_new_candidates_pre_dedups_and_skips_db_existing():
    db = TestingSessionLocal()
    try:
        p1 = Person(name="Test Person One", profession="Engineer")
        p2 = Person(name="Test Person Two", profession="Founder")
        db.add_all([p1, p2])
        db.flush()

        app1 = Appearance(
            person_id=p1.id,
            appearance_type="NEWS_ARTICLE",
            title="Existing Article",
            identity_status="VERIFIED",
            confidence_score=0.9,
        )
        db.add(app1)
        db.flush()

        db.add(
            Source(
                appearance_id=app1.id,
                source_url="https://example.org/news/already-saved",
                canonical_url="https://example.org/news/already-saved",
                source_type="NEWS",
                extraction_status="SUCCESS",
            )
        )
        db.add(
            Source(
                appearance_id=app1.id,
                source_url="https://www.youtube.com/watch?v=existing123",
                canonical_url="https://www.youtube.com/watch?v=existing123",
                source_type="YOUTUBE",
                extraction_status="SUCCESS",
            )
        )
        db.commit()

        candidates = [
            # Already in DB (even with utm param) -> skip
            DiscoveredItem(title="Already Saved", url="https://example.org/news/already-saved?utm_source=x", source_type="NEWS"),
            # Same YouTube video already in DB -> skip
            DiscoveredItem(title="Existing Video", url="https://youtu.be/existing123", source_type="YOUTUBE"),
            # New article duplicated across two collectors -> keep 1, skip 1
            DiscoveredItem(title="Brand New", url="https://example.org/news/brand-new", source_type="NEWS"),
            DiscoveredItem(title="Brand New Dup", url="https://example.org/news/brand-new?ref=feed", source_type="NEWS"),
            # New YouTube video across watch + short url -> keep 1, skip 1
            DiscoveredItem(title="New Video", url="https://www.youtube.com/watch?v=newvid01234", source_type="YOUTUBE"),
            DiscoveredItem(title="New Video Short", url="https://youtu.be/newvid01234", source_type="YOUTUBE"),
        ]

        filtered, skipped, existing_urls = _filter_new_candidates(db, p1.id, candidates)
        assert skipped == 4
        assert [c.title for c in filtered] == ["Brand New", "New Video"]
        assert "https://example.org/news/already-saved" in existing_urls

        # Different target person must NOT skip URLs belonging only to p1
        filtered_p2, skipped_p2, _ = _filter_new_candidates(db, p2.id, candidates[:2])
        assert skipped_p2 == 0
        assert len(filtered_p2) == 2
    finally:
        db.close()


def test_concurrent_extraction_preserves_order_and_respects_domain_limit(monkeypatch):
    monkeypatch.setattr(settings, "EXTRACTION_MAX_WORKERS", 6)
    monkeypatch.setattr(settings, "PER_DOMAIN_MAX_CONCURRENCY", 2)

    lock = threading.Lock()
    active_same_host = 0
    max_same_host_seen = 0

    def _fake_extract(item: DiscoveredItem, allow_youtube_whisper: bool = True):
        nonlocal active_same_host, max_same_host_seen
        with lock:
            if "samehost.example" in item.url:
                active_same_host += 1
                max_same_host_seen = max(max_same_host_seen, active_same_host)
        time.sleep(0.05)
        with lock:
            if "samehost.example" in item.url:
                active_same_host -= 1
        return ExtractedPayload(
            title=item.title,
            source_url=item.url,
            canonical_url=item.url,
            source_type=item.source_type,
            extracted_content=f"Extracted {item.title}",
            content_hash=item.title,
            extraction_status="SUCCESS",
            extraction_method="httpx",
        )

    monkeypatch.setattr(MetadataExtractor, "extract", staticmethod(_fake_extract))

    items = [
        DiscoveredItem(title=f"Item {i}", url=f"https://samehost.example/post/{i}", source_type="NEWS")
        for i in range(6)
    ]

    t0 = time.perf_counter()
    payloads = _extract_items_concurrently(items)
    elapsed = time.perf_counter() - t0

    assert [p.title for p in payloads] == [f"Item {i}" for i in range(6)]
    assert max_same_host_seen <= 2
    # 6 items at 0.05s each sequentially = 0.30s; with limit=2 on same host should finish around ~0.15s
    assert elapsed < 0.28


def test_404_skips_firecrawl_fallback(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc-test-key")
    post_called = False

    class _Fake404Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, **kwargs):
            class _Resp:
                status_code = 404
                text = "Not Found"

            return _Resp()

        def post(self, *args, **kwargs):
            nonlocal post_called
            post_called = True
            raise AssertionError("Firecrawl should NOT be called on HTTP 404")

    monkeypatch.setattr(httpx, "Client", _Fake404Client)

    content, status, _, _, method = ArticleExtractor.extract_article_with_method("https://example.org/missing-page")
    assert content is None
    assert status == "FAILED"
    assert method == "failed"
    assert post_called is False


def test_youtube_bulk_vs_direct_whisper_control(monkeypatch):
    recorded_flags = []

    def _fake_transcript(url: str, allow_whisper: bool = True):
        recorded_flags.append(allow_whisper)
        return "Sample video metadata text", "METADATA_FALLBACK"

    monkeypatch.setattr(TranscriptExtractor, "extract_transcript", classmethod(lambda cls, url, allow_whisper=True: _fake_transcript(url, allow_whisper)))

    yt_item = DiscoveredItem(
        title="Talk Video",
        url="https://www.youtube.com/watch?v=abcDEF12345",
        source_type="YOUTUBE",
    )

    MetadataExtractor.extract(yt_item, allow_youtube_whisper=False)
    MetadataExtractor.extract(yt_item, allow_youtube_whisper=True)

    assert recorded_flags == [False, True]


def test_concurrent_discovery_service_aggregates_all_collectors(monkeypatch):
    svc = DiscoveryService()

    def _delayed(label):
        def _fn(queries, max_per_query=3):
            time.sleep(0.05)
            return [DiscoveredItem(title=f"{label} Hit", url=f"https://example.org/{label.lower()}/1", source_type="NEWS")]
        return _fn

    for attr, name in [
        ("youtube_collector", "YouTube"),
        ("news_collector", "News"),
        ("podcast_collector", "Podcast"),
        ("webpage_collector", "Events"),
        ("linkedin_collector", "LinkedIn"),
        ("instagram_collector", "Instagram"),
    ]:
        monkeypatch.setattr(getattr(svc, attr), "discover", _delayed(name))

    ctx = IdentityContext(
        person_id="p-test",
        name="Ada Lovelace",
        profession="Computer Scientist",
        organizations=["Analytical Engine"],
        known_usernames=[],
        profile_urls={},
    )

    t0 = time.perf_counter()
    results = svc.run_discovery(ctx)
    elapsed = time.perf_counter() - t0

    assert len(results) == 6
    # 6 collectors * 0.05s sequentially = 0.30s; concurrent runs around ~0.05-0.12s
    assert elapsed < 0.22

