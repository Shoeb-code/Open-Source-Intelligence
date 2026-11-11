from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.extraction.transcript_extractor import TranscriptExtractor
from backend.modules.extraction.article_extractor import ArticleExtractor
from backend.utils.text_cleaner import compute_content_hash, clean_text
from backend.utils.url_validator import canonicalize_url


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
    extraction_method: Optional[str] = None  # httpx, firecrawl, youtube_transcript, metadata_fallback, failed


class MetadataExtractor:
    """Dispatches content extraction based on source type and creates structured payload."""

    @staticmethod
    def extract(item: DiscoveredItem, allow_youtube_whisper: bool = True) -> ExtractedPayload:
        canonical_url = canonicalize_url(item.url)
        content: Optional[str] = None
        status = "PENDING"
        extraction_method: Optional[str] = None
        title = item.title
        publisher = item.publisher

        source_type = (item.source_type or "WEBPAGE").upper()

        if source_type == "YOUTUBE":
            if allow_youtube_whisper:
                content, status = TranscriptExtractor.extract_transcript(canonical_url)
            else:
                try:
                    content, status = TranscriptExtractor.extract_transcript(canonical_url, allow_whisper=False)
                except TypeError:
                    content, status = TranscriptExtractor.extract_transcript(canonical_url)
            if status in ("SUCCESS", "AI_TRANSCRIBED"):
                extraction_method = "youtube_transcript"
            elif status == "METADATA_FALLBACK":
                extraction_method = "metadata_fallback"
            else:
                extraction_method = "failed"
            # If transcript unavailable, use description as baseline content
            if not content and item.description:
                content = clean_text(item.description)
                extraction_method = "metadata_fallback"

        elif source_type in ("NEWS", "PODCAST", "EVENT", "WEBPAGE", "BLOG", "ARTICLE", "LINKEDIN", "INSTAGRAM"):
            content, status, page_title, page_pub = ArticleExtractor.extract_article(canonical_url)
            extraction_method = ArticleExtractor.get_last_extraction_method() or (
                "httpx" if status == "SUCCESS" else "failed"
            )
            if not content and item.description:
                content = clean_text(item.description)
                if status in ("PENDING", "RESTRICTED", "FAILED"):
                    status = "METADATA_FALLBACK"
                    extraction_method = "metadata_fallback"
            if page_title and (not title or title == "Uploaded Media Appearance"):
                title = page_title
            if page_pub and not publisher:
                publisher = page_pub
            if not publisher:
                if source_type == "LINKEDIN" or "linkedin.com" in canonical_url:
                    publisher = "LinkedIn"
                elif source_type == "INSTAGRAM" or "instagram.com" in canonical_url:
                    publisher = "Instagram"

        content_hash = compute_content_hash(content or title or item.url)

        return ExtractedPayload(
            title=title or "Public Appearance",
            source_url=item.url,
            canonical_url=canonical_url,
            source_type=source_type,
            publisher=publisher,
            published_at=item.published_at,
            description=item.description,
            extracted_content=content,
            content_hash=content_hash,
            extraction_status=status,
            extraction_method=extraction_method,
        )

