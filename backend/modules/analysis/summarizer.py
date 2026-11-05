import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from backend.config import settings
from backend.modules.persons.schemas import IdentityContext
from backend.modules.extraction.metadata_extractor import ExtractedPayload
from backend.utils.logger import logger
from backend.utils.text_cleaner import truncate_text


class AIAnalysisResult:
    def __init__(
        self,
        summary: str,
        topics: List[str],
        key_points: List[str],
        person_role: str,
        evidence: List[str],
        model_name: str
    ):
        self.summary = summary
        self.topics = topics
        self.key_points = key_points
        self.person_role = person_role
        self.evidence = evidence
        self.model_name = model_name


class AppearanceSummarizer:
    """Analyzes extracted appearance transcripts and articles using LLMs or robust fallback."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.OPENAI_MODEL

    def _fallback_analysis(self, context: IdentityContext, payload: ExtractedPayload) -> AIAnalysisResult:
        """Deterministic extractive summary when LLM API key is not present."""
        content = payload.extracted_content or payload.description or payload.title
        sentences = [s.strip() for s in content.replace("\n", ". ").split(". ") if len(s.strip()) > 25]

        summary = ". ".join(sentences[:3]) + "." if sentences else f"Public appearance titled '{payload.title}'."
        key_points = sentences[1:5] if len(sentences) >= 5 else [payload.title]
        
        # Simple topic extraction
        words = [w.strip(".,;:?!").capitalize() for w in payload.title.split() if len(w) > 4]
        topics = list(dict.fromkeys(words))[:4] or ["Public Appearance"]

        role = "GUEST" if "interview" in payload.title.lower() or "podcast" in payload.title.lower() else "SPEAKER"

        return AIAnalysisResult(
            summary=summary,
            topics=topics,
            key_points=key_points,
            person_role=role,
            evidence=[payload.title],
            model_name="extractive-fallback-v1"
        )

    def analyze(self, context: IdentityContext, payload: ExtractedPayload) -> AIAnalysisResult:
        if not self.client:
            return self._fallback_analysis(context, payload)

        content_excerpt = truncate_text(payload.extracted_content or payload.description or "", max_chars=4000)

        prompt = f"""
You are an OSINT Intelligence Analyst analyzing a public appearance of an individual.

Target Identity:
Name: {context.name}
Profession: {context.profession or 'Unknown'}
Known Organizations: {', '.join(context.organizations) or 'None specified'}

Appearance Metadata:
Title: {payload.title}
Publisher/Channel: {payload.publisher or 'Unknown'}
Source Type: {payload.source_type}

Content / Transcript Excerpt:
{content_excerpt}

Instructions:
1. Provide a concise, objective summary (2-3 sentences).
2. Identify the target person's role (e.g. KEYNOTE_SPEAKER, GUEST, INTERVIEWEE, HOST, PANEL_MEMBER, MENTIONED).
3. Extract 3 to 6 major discussion topics.
4. Extract 3 to 5 key points or takeaways attributed to or discussing the target.
5. Extract 1 to 3 direct quotes or factual supporting statements from the text as evidence.

Return ONLY a valid JSON object matching this schema:
{{
  "summary": "string",
  "person_role": "string",
  "topics": ["string"],
  "key_points": ["string"],
  "evidence": ["string"]
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional intelligence analyst. Output strict JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            raw_json = response.choices[0].message.content
            parsed = json.loads(raw_json)

            return AIAnalysisResult(
                summary=parsed.get("summary", ""),
                topics=parsed.get("topics", []),
                key_points=parsed.get("key_points", []),
                person_role=parsed.get("person_role", "PARTICIPANT"),
                evidence=parsed.get("evidence", []),
                model_name=self.model
            )
        except Exception as e:
            logger.error(f"LLM analysis failed for '{payload.title}': {e}. Using fallback.")
            return self._fallback_analysis(context, payload)

