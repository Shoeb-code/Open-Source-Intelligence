from typing import List, Dict, Optional
from rapidfuzz import fuzz
from backend.modules.extraction.metadata_extractor import ExtractedPayload
from backend.utils.url_validator import extract_youtube_video_id, canonicalize_url


class DeduplicationGroup:
    def __init__(self, primary_item: ExtractedPayload):
        self.primary_item = primary_item
        self.associated_sources: List[ExtractedPayload] = [primary_item]

    def add_source(self, item: ExtractedPayload):
        self.associated_sources.append(item)


class Deduplicator:
    """Consolidates duplicate appearances across canonical URLs, video IDs, titles, and hashes."""

    @staticmethod
    def deduplicate(items: List[ExtractedPayload]) -> List[DeduplicationGroup]:
        groups: List[DeduplicationGroup] = []

        for item in items:
            matched_group: Optional[DeduplicationGroup] = None
            item_canon_url = canonicalize_url(item.canonical_url)
            item_yt_id = extract_youtube_video_id(item_canon_url)

            for group in groups:
                primary = group.primary_item
                primary_canon_url = canonicalize_url(primary.canonical_url)
                primary_yt_id = extract_youtube_video_id(primary_canon_url)

                # 1. Exact canonical URL match
                if item_canon_url == primary_canon_url:
                    matched_group = group
                    break

                # 2. YouTube Video ID match
                if item_yt_id and primary_yt_id and item_yt_id == primary_yt_id:
                    matched_group = group
                    break

                # 3. Content hash match
                if item.content_hash and primary.content_hash and item.content_hash == primary.content_hash:
                    matched_group = group
                    break

                # 4. Title fuzzy similarity (> 88%) + same publisher
                if primary.publisher and item.publisher and primary.publisher.lower() == item.publisher.lower():
                    title_ratio = fuzz.ratio(primary.title.lower(), item.title.lower())
                    if title_ratio > 88:
                        matched_group = group
                        break

            if matched_group:
                matched_group.add_source(item)
            else:
                groups.append(DeduplicationGroup(item))

        return groups

