import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
from openai import NotFoundError, OpenAI

from backend.config import settings
from backend.modules.intelligence.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_insights_prompt,
)
from backend.modules.intelligence.schemas import (
    InsightItem,
    InsightSection,
    InsightsReportPayload,
    SourceCitation,
)
from backend.utils.logger import logger
from backend.utils.text_cleaner import truncate_text


class EvidenceBundle:
    """In-memory synthesis container built strictly from existing DB records."""

    def __init__(
        self,
        person_name: str,
        profession: Optional[str],
        biography: Optional[str],
        headline: Optional[str],
        occupation: Optional[str],
        location: Optional[str],
        experiences: List[Dict[str, Any]],
        education: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        skills: List[str],
        certifications: List[Dict[str, Any]],
        person_summary: Optional[str],
        appearances_meta: List[Dict[str, Any]],
        citation_map: Dict[str, SourceCitation],
        person_digest: str,
        evidence_catalog: str,
        data_coverage: Dict[str, int],
    ):
        self.person_name = person_name
        self.profession = profession
        self.biography = biography
        self.headline = headline
        self.occupation = occupation
        self.location = location
        self.experiences = experiences
        self.education = education
        self.projects = projects
        self.skills = skills
        self.certifications = certifications
        self.person_summary = person_summary
        self.appearances_meta = appearances_meta
        self.citation_map = citation_map
        self.person_digest = person_digest
        self.evidence_catalog = evidence_catalog
        self.data_coverage = data_coverage


def _first_citation(citation_map: Dict[str, SourceCitation], preferred_types: Tuple[str, ...]) -> List[SourceCitation]:
    for cit in citation_map.values():
        if cit.source_type and cit.source_type.upper() in preferred_types:
            return [cit]
    if citation_map:
        return [next(iter(citation_map.values()))]
    return []


class InsightsSummarizer:
    """Generates consolidated 7-section executive insights using configured Groq/OpenAI LLM or deterministic fallback."""

    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        elif settings.OPENAI_API_KEY:
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            self.model = settings.OPENAI_MODEL
        else:
            self.client = None
            self.model = "extractive-fallback-v1"

    @staticmethod
    def _resolve_citations(
        raw_source_ids: Any,
        citation_map: Dict[str, SourceCitation],
    ) -> List[SourceCitation]:
        citations: List[SourceCitation] = []
        seen_keys = set()
        if not isinstance(raw_source_ids, list):
            return citations

        for ref in raw_source_ids:
            if not isinstance(ref, str):
                continue
            key = ref.strip().strip("[]").upper()
            cit = citation_map.get(key)
            if not cit:
                # Also match if model emitted an exact URL from our catalog
                for existing in citation_map.values():
                    if existing.url and existing.url == ref.strip():
                        cit = existing
                        break
            if cit:
                dedup_key = (cit.url or cit.title or "", cit.published_at or "")
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    citations.append(cit)
        return citations[:4]

    @classmethod
    def _hydrate_section(
        cls,
        raw_section: Any,
        citation_map: Dict[str, SourceCitation],
    ) -> InsightSection:
        if not isinstance(raw_section, dict):
            return InsightSection(
                insufficient_evidence=True,
                insufficient_evidence_note="Insufficient evidence returned for this section.",
                items=[],
            )

        raw_items = raw_section.get("items") if isinstance(raw_section.get("items"), list) else []
        hydrated_items: List[InsightItem] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            detail = str(item.get("detail") or "").strip()
            if not title or not detail:
                continue

            raw_claim = str(item.get("claim_type") or "VERIFIED_FACT").upper()
            claim_type = "AI_HYPOTHESIS" if "HYPOTHESIS" in raw_claim or "INTERPRET" in raw_claim else "VERIFIED_FACT"

            raw_conf = str(item.get("confidence") or "MEDIUM").upper()
            confidence = raw_conf if raw_conf in ("HIGH", "MEDIUM", "LOW") else "MEDIUM"

            sources = cls._resolve_citations(item.get("source_ids"), citation_map)
            hydrated_items.append(
                InsightItem(
                    title=title,
                    detail=detail,
                    sub_category=str(item.get("sub_category")).strip() if item.get("sub_category") else None,
                    claim_type=claim_type,
                    confidence=confidence,
                    supporting_sources=sources,
                )
            )

        insuff = bool(raw_section.get("insufficient_evidence", False)) or len(hydrated_items) == 0
        note = raw_section.get("insufficient_evidence_note")
        if insuff and not note:
            note = "Limited public evidence currently collected for this category."

        return InsightSection(
            summary=str(raw_section.get("summary")).strip() if raw_section.get("summary") else None,
            insufficient_evidence=insuff,
            insufficient_evidence_note=str(note).strip() if note else None,
            items=hydrated_items,
        )

    def _fallback_insights(self, bundle: EvidenceBundle) -> Tuple[InsightsReportPayload, str]:
        """Deterministic evidence-grounded 7-section builder when LLM API is unavailable or fails."""
        c_map = bundle.citation_map
        li_cit = _first_citation(c_map, ("LINKEDIN_PROFILE", "LINKEDIN"))

        # 1. Professional Insights (Roles, Experiences, Education)
        prof_items: List[InsightItem] = []
        if bundle.headline or bundle.occupation or bundle.profession:
            role_desc = " | ".join(filter(None, [bundle.headline, bundle.occupation or bundle.profession, bundle.location]))
            prof_items.append(
                InsightItem(
                    title="Current Role & Positioning",
                    detail=role_desc,
                    sub_category="Current Role",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )
        if bundle.experiences:
            exp_lines = [
                f"{e.get('title', 'Role')} at {e.get('company', 'Organization')} ({e.get('start_date') or '?'} - {e.get('end_date') or 'Present'})"
                for e in bundle.experiences[:5]
            ]
            prof_items.append(
                InsightItem(
                    title=f"Career Progression ({len(bundle.experiences)} recorded roles)",
                    detail="; ".join(exp_lines),
                    sub_category="Experience",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )
        if bundle.education:
            edu_lines = [
                " - ".join(filter(None, [e.get("school"), e.get("degree_name"), e.get("field_of_study")]))
                for e in bundle.education[:4]
            ]
            prof_items.append(
                InsightItem(
                    title="Academic & Professional Qualifications",
                    detail="; ".join(edu_lines),
                    sub_category="Background",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )

        prof_section = InsightSection(
            summary=f"Professional profile grounded across {len(bundle.experiences)} roles and {len(bundle.education)} credentials."
            if prof_items
            else None,
            insufficient_evidence=len(prof_items) == 0,
            insufficient_evidence_note="No structured employment, education, or headline data collected yet."
            if not prof_items
            else None,
            items=prof_items,
        )

        # 2. Interest Insights (Recurring topics & themes across appearances)
        topic_counts: Counter = Counter()
        topic_sources: Dict[str, List[SourceCitation]] = {}
        for app in bundle.appearances_meta:
            cit = c_map.get(app["citation_id"])
            for topic in app.get("topics") or []:
                t_clean = str(topic).strip()
                if len(t_clean) > 2:
                    topic_counts[t_clean] += 1
                    if cit and t_clean not in topic_sources:
                        topic_sources[t_clean] = [cit]

        interest_items: List[InsightItem] = []
        if topic_counts:
            top_topics = topic_counts.most_common(6)
            interest_items.append(
                InsightItem(
                    title="Frequently Discussed Themes",
                    detail="Top recurring topics across public posts and media: "
                    + ", ".join(f"{t} ({cnt})" for t, cnt in top_topics),
                    sub_category="Recurring Themes",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH" if len(bundle.appearances_meta) >= 3 else "MEDIUM",
                    supporting_sources=topic_sources.get(top_topics[0][0], _first_citation(c_map, ("LINKEDIN", "YOUTUBE"))),
                )
            )

        interest_section = InsightSection(
            summary="Themes derived from topic tags across verified public posts and media appearances."
            if interest_items
            else None,
            insufficient_evidence=len(interest_items) == 0,
            insufficient_evidence_note="Insufficient posts, videos, or articles collected to identify recurring interests."
            if not interest_items
            else None,
            items=interest_items,
        )

        # 3. Knowledge and Expertise
        know_items: List[InsightItem] = []
        if bundle.skills:
            know_items.append(
                InsightItem(
                    title="Listed Skills",
                    detail=", ".join(bundle.skills[:10]),
                    sub_category="Technical Expertise",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )
        speaking_apps = [
            a for a in bundle.appearances_meta
            if a.get("appearance_type") in ("INTERVIEW", "PODCAST", "CONFERENCE", "WEBINAR", "ARTICLE")
        ]
        if speaking_apps:
            top_talk = speaking_apps[0]
            know_items.append(
                InsightItem(
                    title=f"Demonstrated Domain Expertise via {len(speaking_apps)} Public Discussions",
                    detail=f"Public commentary and speaker sessions covering: {top_talk['title']}.",
                    sub_category="Industry Knowledge",
                    claim_type="VERIFIED_FACT",
                    confidence="MEDIUM",
                    supporting_sources=[c_map[top_talk["citation_id"]]] if top_talk["citation_id"] in c_map else [],
                )
            )

        know_section = InsightSection(
            summary="Subject-matter capabilities evidenced across panels, talks, and credentials."
            if know_items
            else None,
            insufficient_evidence=len(know_items) == 0,
            insufficient_evidence_note="Insufficient technical talks, skills, or specialist articles collected yet."
            if not know_items
            else None,
            items=know_items,
        )

        # 4. Company Insights
        comp_items: List[InsightItem] = []
        current_companies = [e for e in bundle.experiences if e.get("is_current")]
        if current_companies:
            comp_str = "; ".join(f"{e.get('company')} ({e.get('title')})" for e in current_companies[:4])
            comp_items.append(
                InsightItem(
                    title="Active Organizations & Leadership Scope",
                    detail=f"Currently associated with: {comp_str}.",
                    sub_category="Company Activities",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )
        if bundle.projects:
            proj_str = "; ".join(
                filter(None, [f"{p.get('title')}: {p.get('description') or ''}".strip(": ") for p in bundle.projects[:4]])
            )
            comp_items.append(
                InsightItem(
                    title="Publicly Announced Initiatives & Programs",
                    detail=proj_str,
                    sub_category="Publicly Announced Initiatives",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH",
                    supporting_sources=li_cit,
                )
            )

        comp_section = InsightSection(
            summary="Organization positioning and initiatives derived from verified profile records."
            if comp_items
            else None,
            insufficient_evidence=len(comp_items) == 0,
            insufficient_evidence_note="Insufficient organization, product, or business model details in collected data."
            if not comp_items
            else None,
            items=comp_items,
        )

        # 5. Recent Activities
        recent_items: List[InsightItem] = []
        for app in bundle.appearances_meta[:5]:
            cit = c_map.get(app["citation_id"])
            recent_items.append(
                InsightItem(
                    title=truncate_text(app["title"], max_chars=120),
                    detail=app.get("summary") or app.get("description") or f"{app.get('appearance_type')} published by {app.get('publisher') or 'External outlet'}.",
                    sub_category=app.get("appearance_type"),
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH" if app.get("identity_status") == "VERIFIED" else "MEDIUM",
                    supporting_sources=[cit] if cit else [],
                )
            )

        recent_section = InsightSection(
            summary=f"Top {len(recent_items)} most recent verified public activities." if recent_items else None,
            insufficient_evidence=len(recent_items) == 0,
            insufficient_evidence_note="No verified recent posts, interviews, podcasts, or articles discovered yet."
            if not recent_items
            else None,
            items=recent_items,
        )

        # 6. Business Insights
        biz_items: List[InsightItem] = []
        all_kp = []
        for app in bundle.appearances_meta[:6]:
            for kp in app.get("key_points") or []:
                all_kp.append((kp, app["citation_id"]))
        if all_kp:
            kp_text, kp_cid = all_kp[0]
            biz_items.append(
                InsightItem(
                    title="Observed Strategic Priority",
                    detail=truncate_text(kp_text, max_chars=280),
                    sub_category="Business Priorities",
                    claim_type="VERIFIED_FACT",
                    confidence="MEDIUM",
                    supporting_sources=[c_map[kp_cid]] if kp_cid in c_map else [],
                )
            )
            biz_items.append(
                InsightItem(
                    title="Recommended Investigation Lead",
                    detail=f"Explore commercial alignment and distribution workflows referenced across {bundle.person_name}'s public commentary.",
                    sub_category="Areas Worth Investigating",
                    claim_type="AI_HYPOTHESIS",
                    confidence="LOW",
                    supporting_sources=[c_map[kp_cid]] if kp_cid in c_map else [],
                )
            )

        biz_section = InsightSection(
            summary="Strategic themes and Leadzen.ai investigation leads derived from public statements."
            if biz_items
            else None,
            insufficient_evidence=len(biz_items) == 0,
            insufficient_evidence_note="Insufficient interview transcripts or press details to infer business priorities."
            if not biz_items
            else None,
            items=biz_items,
        )

        # 7. Key Takeaways
        takeaway_items: List[InsightItem] = []
        total_srcs = bundle.data_coverage.get("total_sources_analyzed", 0)
        if total_srcs > 0:
            takeaway_items.append(
                InsightItem(
                    title="Evidence Breadth Assessment",
                    detail=f"Synthesized {total_srcs} verified record(s) across LinkedIn, video, and web outlets for {bundle.person_name}.",
                    sub_category="Key Observation",
                    claim_type="VERIFIED_FACT",
                    confidence="HIGH" if total_srcs >= 5 else "MEDIUM",
                    supporting_sources=list(c_map.values())[:2],
                )
            )
            takeaway_items.append(
                InsightItem(
                    title="Outreach & Engagement Angle",
                    detail=f"Reference specific public initiatives and recurring discussion topics when tailoring Leadzen.ai engagement or project proposals.",
                    sub_category="Opportunity Hypothesis",
                    claim_type="AI_HYPOTHESIS",
                    confidence="MEDIUM",
                    supporting_sources=list(c_map.values())[:2],
                )
            )

        takeaway_section = InsightSection(
            summary="Actionable conclusions based on consolidated evidence." if takeaway_items else None,
            insufficient_evidence=len(takeaway_items) == 0,
            insufficient_evidence_note="Collect appearances or run LinkedIn enrichment first to generate actionable takeaways."
            if not takeaway_items
            else None,
            items=takeaway_items,
        )

        payload = InsightsReportPayload(
            executive_overview=(
                f"Consolidated intelligence digest for {bundle.person_name} "
                f"({bundle.headline or bundle.profession or 'Profile'}) across {total_srcs} stored evidence source(s)."
            ),
            data_coverage=bundle.data_coverage,
            professional_insights=prof_section,
            interest_insights=interest_section,
            knowledge_and_expertise=know_section,
            company_insights=comp_section,
            recent_activities=recent_section,
            business_insights=biz_section,
            key_takeaways=takeaway_section,
        )
        return payload, "extractive-fallback-v1"

    @staticmethod
    def _parse_json_content(raw_content: str) -> Dict[str, Any]:
        cleaned = (raw_content or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        return json.loads(cleaned or "{}")

    def _call_chat_completion(self, model_name: str, prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4096,
            )
            return response.choices[0].message.content or "{}"
        except Exception as exc:
            if "response_format" in str(exc).lower() or "json_object" in str(exc).lower():
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=4096,
                )
                return response.choices[0].message.content or "{}"
            raise

    def generate(
        self,
        bundle: EvidenceBundle,
        focus_notes: Optional[str] = None,
    ) -> Tuple[InsightsReportPayload, str, str]:
        """Generates structured 7-section insights, returning (payload, model_name, prompt_version)."""
        if not self.client or bundle.data_coverage.get("total_sources_analyzed", 0) == 0:
            payload, used_model = self._fallback_insights(bundle)
            return payload, used_model, PROMPT_VERSION

        prompt = build_insights_prompt(
            person_digest=bundle.person_digest,
            evidence_catalog=bundle.evidence_catalog,
            focus_notes=focus_notes,
        )

        candidate_models = [self.model]
        if settings.GROQ_API_KEY and self.client:
            for fallback_m in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"):
                if fallback_m not in candidate_models:
                    candidate_models.append(fallback_m)

        raw_content: Optional[str] = None
        used_model = self.model

        try:
            for idx, m_name in enumerate(candidate_models):
                try:
                    raw_content = self._call_chat_completion(m_name, prompt)
                    used_model = m_name
                    break
                except NotFoundError:
                    if idx == len(candidate_models) - 1:
                        raise
                    continue

            parsed = self._parse_json_content(raw_content or "{}")
            fallback_payload, _ = self._fallback_insights(bundle)

            def _resolve_section(key: str) -> InsightSection:
                if key in parsed and isinstance(parsed[key], dict):
                    return self._hydrate_section(parsed[key], bundle.citation_map)
                return getattr(fallback_payload, key)

            payload = InsightsReportPayload(
                executive_overview=str(parsed.get("executive_overview") or f"Intelligence summary for {bundle.person_name}.").strip(),
                data_coverage=bundle.data_coverage,
                professional_insights=_resolve_section("professional_insights"),
                interest_insights=_resolve_section("interest_insights"),
                knowledge_and_expertise=_resolve_section("knowledge_and_expertise"),
                company_insights=_resolve_section("company_insights"),
                recent_activities=_resolve_section("recent_activities"),
                business_insights=_resolve_section("business_insights"),
                key_takeaways=_resolve_section("key_takeaways"),
            )
            return payload, used_model, PROMPT_VERSION
        except Exception as e:
            logger.error(f"Insights LLM generation failed for {bundle.person_name} ({type(e).__name__}). Falling back cleanly.")
            payload, fallback_model = self._fallback_insights(bundle)
            return payload, fallback_model, PROMPT_VERSION
