from backend.modules.extraction.metadata_extractor import ExtractedPayload
from backend.modules.deduplication.deduplicator import Deduplicator


def test_deduplicator_consolidates_duplicates():
    item1 = ExtractedPayload(
        title="Rahul Sharma Keynote at CloudConf 2026",
        source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        canonical_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="YOUTUBE",
        publisher="CloudConf",
        content_hash="content_hash_1",
        extraction_status="SUCCESS"
    )
    # Same video embedded on another website with tracking parameters
    item2 = ExtractedPayload(
        title="Rahul Sharma Keynote at CloudConf 2026",
        source_url="https://youtu.be/dQw4w9WgXcQ?utm_source=twitter",
        canonical_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        source_type="YOUTUBE",
        publisher="CloudConf",
        content_hash="content_hash_1",
        extraction_status="SUCCESS"
    )
    # Distinct video appearance
    item3 = ExtractedPayload(
        title="Podcast #42 with Rahul Sharma",
        source_url="https://youtube.com/watch?v=ZZZ99988811",
        canonical_url="https://youtube.com/watch?v=ZZZ99988811",
        source_type="YOUTUBE",
        publisher="DevRadio",
        content_hash="content_hash_2",
        extraction_status="SUCCESS"
    )

    groups = Deduplicator.deduplicate([item1, item2, item3])
    # item1 and item2 must merge into 1 group
    assert len(groups) == 2
    merged_group = [g for g in groups if len(g.associated_sources) > 1][0]
    assert len(merged_group.associated_sources) == 2

