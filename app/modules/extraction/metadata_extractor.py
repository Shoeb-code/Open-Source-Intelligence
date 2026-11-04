from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from app.modules.collectors.youtube import DiscoveredItem
from app.modules.extraction.transcript_extractor import TranscriptExtractor
from app.modules.extraction.article_extractor import ArticleExtractor
from app.utils.text_cleaner import compute_content_hash, clean_text
from app.utils.url_validator import canonicalize_url


class ExtractedPayload(BaseModel):
    title: str
    source_url: str
    canonical_url: str
    source_type: str
    publisher: Optional[str] = None
    published_at: Optional[datetime] = None
    description: Optional[str] = None
    extracted_content: Optional[str] = None
    content_hash: Optional[str] = None
    extraction_status: str  # SUCCESS, TRANSCRIPT_UNAVAILABLE, RESTRICTED, FAILED


class MetadataExtractor:
    """Dispatches content extraction based on source type and creates structured payload."""

    @staticmethod
    def extract(item: DiscoveredItem) -> ExtractedPayload:
        canonical_url = canonicalize_url(item.url)
        content: Optional[str] = None
        status = "PENDING"

        if item.source_type == "YOUTUBE":
            content, status = TranscriptExtractor.extract_transcript(canonical_url)
            # If transcript unavailable, use description as baseline content
            if not content and item.description:
                content = clean_text(item.description)

        elif item.source_type in ("NEWS", "PODCAST", "EVENT", "WEBPAGE"):
            content, status = ArticleExtractor.extract_article_text(canonical_url)
            if not content and item.description:
                content = clean_text(item.description)

        content_hash = compute_content_hash(content or item.title)

        return ExtractedPayload(
            title=item.title,
            source_url=item.url,
            canonical_url=canonical_url,
            source_type=item.source_type,
            publisher=item.publisher,
            published_at=item.published_at,
            description=item.description,
            extracted_content=content,
            content_hash=content_hash,
            extraction_status=status
        )

