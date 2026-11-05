import re
from backend.modules.extraction.metadata_extractor import ExtractedPayload


class AppearanceClassifier:
    """Classifies public appearances into standardized categories."""

    @staticmethod
    def classify(payload: ExtractedPayload) -> str:
        text = f"{payload.title} {payload.description or ''} {payload.source_url}".lower()

        if "podcast" in text or "episode" in text:
            return "PODCAST"
        elif "interview" in text or "qa" in text or "q&a" in text:
            return "INTERVIEW"
        elif "keynote" in text or "conference" in text or "summit" in text or "talk" in text:
            return "CONFERENCE"
        elif "webinar" in text or "workshop" in text or "live stream" in text:
            return "WEBINAR"
        elif payload.source_type == "NEWS" or "news" in text or "press" in text:
            return "NEWS_ARTICLE"
        elif "blog" in text or "medium.com" in text or "substack.com" in text:
            return "BLOG"

        if payload.source_type == "YOUTUBE":
            return "INTERVIEW"

        return "OTHER"

