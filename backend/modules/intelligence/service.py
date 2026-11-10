import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, selectinload

from backend.database.models import Appearance, Person, PersonInsightsReport
from backend.modules.intelligence.schemas import (
    GenerateInsightsRequest,
    InsightsHistoryResponse,
    InsightsReportPayload,
    InsightsReportResponse,
    SourceCitation,
)
from backend.modules.intelligence.summarizer import EvidenceBundle, InsightsSummarizer
from backend.utils.logger import logger
from backend.utils.text_cleaner import truncate_text


def _fmt_iso_date(dt: Any) -> Optional[str]:
    if not dt:
        return None
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(dt)[:10]


def collect_person_evidence(db: Session, person: Person) -> EvidenceBundle:
    """Aggregates all already-stored DB evidence for a person without triggering external APIs or paid scrapers."""
    citation_map: Dict[str, SourceCitation] = {}
    catalog_lines: List[str] = []
    cit_counter = 1

    experiences = list(person.experiences or [])
    education = list(person.education or [])
    projects = list(person.projects or [])
    skills = list(person.skills or [])
    certifications = list(person.certifications or [])

    li_profile = next(
        (sp for sp in (person.social_profiles or []) if sp.platform == "linkedin"),
        None,
    )
    has_li_enrichment = bool(
        person.headline
        or person.summary
        or experiences
        or education
        or projects
        or skills
        or certifications
    )

    # 1. LinkedIn Profile & Enrichment Digest
    digest_parts: List[str] = [
        f"Name: {person.name}",
        f"Registered Profession: {person.profession or 'Unknown'}",
    ]
    if person.biography:
        digest_parts.append(f"Account Biography: {truncate_text(person.biography, 400)}")
    if person.headline:
        digest_parts.append(f"LinkedIn Headline: {person.headline}")
    if person.occupation:
        digest_parts.append(f"Current Occupation: {person.occupation}")
    if person.location:
        digest_parts.append(f"Location: {person.location}")
    if person.follower_count is not None:
        digest_parts.append(f"LinkedIn Followers: {person.follower_count}")
    if person.summary:
        digest_parts.append(f"LinkedIn Summary: {truncate_text(person.summary, 700)}")

    if person.social_profiles:
        social_str = ", ".join(
            f"{sp.platform}: {sp.profile_url} ({sp.verification_status})"
            for sp in person.social_profiles
        )
        digest_parts.append(f"Social Profiles: {social_str}")

    if experiences:
        exp_lines = [
            f"- {e.get('title', 'Role')} at {e.get('company', 'Company')} ({e.get('start_date') or '?'} to {e.get('end_date') or 'Present'})"
            + (f" — {truncate_text(e['description'], 120)}" if e.get("description") else "")
            for e in experiences[:8]
        ]
        digest_parts.append("Work Experience History:\n" + "\n".join(exp_lines))

    if education:
        edu_lines = [
            "- " + " | ".join(filter(None, [e.get("school"), e.get("degree_name"), e.get("field_of_study")]))
            for e in education[:6]
        ]
        digest_parts.append("Education:\n" + "\n".join(edu_lines))

    if projects:
        proj_lines = [
            f"- {p.get('title', 'Project')}: {truncate_text(p.get('description') or '', 180)}"
            for p in projects[:6]
        ]
        digest_parts.append("Projects & Initiatives:\n" + "\n".join(proj_lines))

    if skills:
        digest_parts.append("Skills: " + ", ".join(skills[:20]))
    if certifications:
        cert_lines = [c.get("name") or c.get("title") or "Certification" for c in certifications[:10] if isinstance(c, dict)]
        if cert_lines:
            digest_parts.append("Certifications: " + ", ".join(cert_lines))

    # Assign S1 to LinkedIn Profile / Enrichment record if present
    if li_profile or has_li_enrichment:
        cid = f"S{cit_counter}"
        cit_counter += 1
        citation_map[cid] = SourceCitation(
            title=f"LinkedIn Profile - {person.name}",
            url=li_profile.profile_url if li_profile else None,
            source_type="LINKEDIN_PROFILE",
            published_at=_fmt_iso_date(person.profile_enriched_at),
        )
        catalog_lines.append(
            f"[{cid}] LINKEDIN_PROFILE | Date: {_fmt_iso_date(person.profile_enriched_at) or 'N/A'} | "
            f"URL: {li_profile.profile_url if li_profile else 'N/A'} | Enriched LinkedIn profile data included in dossier above."
        )

    # 2. Stored Verified/Likely Appearances across LinkedIn Posts, YouTube, Podcasts, News, Web
    appearances: List[Appearance] = (
        db.query(Appearance)
        .options(selectinload(Appearance.sources), selectinload(Appearance.analysis))
        .filter(
            Appearance.person_id == person.id,
            Appearance.identity_status != "REJECTED",
        )
        .order_by(Appearance.published_at.desc(), Appearance.confidence_score.desc(), Appearance.created_at.desc())
        .all()
    )

    coverage: Dict[str, int] = {
        "linkedin_profile_enriched": 1 if has_li_enrichment else 0,
        "linkedin_posts": 0,
        "youtube_and_podcasts": 0,
        "articles_and_news": 0,
        "other_sources": 0,
        "total_sources_analyzed": 1 if (li_profile or has_li_enrichment) else 0,
    }

    appearances_meta: List[Dict[str, Any]] = []
    max_catalog_chars = 9500
    running_catalog_chars = sum(len(x) for x in catalog_lines)

    for app in appearances:
        primary_src = app.sources[0] if app.sources else None
        src_url = primary_src.source_url if primary_src else None
        src_type = (primary_src.source_type if primary_src else app.appearance_type or "WEBPAGE").upper()
        pub_date = _fmt_iso_date(app.published_at or app.created_at)

        app_type_upper = (app.appearance_type or "").upper()
        if "LINKEDIN" in app_type_upper or "LINKEDIN" in src_type or (src_url and "linkedin.com" in src_url.lower()):
            coverage["linkedin_posts"] += 1
        elif app_type_upper in ("PODCAST", "INTERVIEW", "CONFERENCE", "WEBINAR") or src_type == "YOUTUBE":
            coverage["youtube_and_podcasts"] += 1
        elif app_type_upper in ("NEWS_ARTICLE", "ARTICLE", "BLOG") or src_type in ("NEWS", "ARTICLE", "WEBPAGE"):
            coverage["articles_and_news"] += 1
        else:
            coverage["other_sources"] += 1
        coverage["total_sources_analyzed"] += 1

        cid = f"S{cit_counter}"
        cit_counter += 1
        citation_map[cid] = SourceCitation(
            title=app.title,
            url=src_url,
            source_type=app.appearance_type or src_type,
            published_at=pub_date,
        )

        analysis_summary = app.analysis.summary if app.analysis else None
        analysis_topics = list(app.analysis.topics or []) if app.analysis else []
        analysis_kp = list(app.analysis.key_points or []) if app.analysis else []
        raw_excerpt = ""
        if primary_src and primary_src.extracted_content:
            raw_excerpt = truncate_text(primary_src.extracted_content, 220)
        elif app.description:
            raw_excerpt = truncate_text(app.description, 200)

        appearances_meta.append({
            "citation_id": cid,
            "title": app.title,
            "appearance_type": app.appearance_type,
            "publisher": app.publisher,
            "published_at": pub_date,
            "identity_status": app.identity_status,
            "summary": analysis_summary,
            "description": app.description,
            "topics": analysis_topics,
            "key_points": analysis_kp,
            "url": src_url,
        })

        if running_catalog_chars < max_catalog_chars:
            kp_str = " | ".join(truncate_text(k, 140) for k in analysis_kp[:2]) if analysis_kp else ""
            topics_str = ", ".join(analysis_topics[:4]) if analysis_topics else ""
            entry = (
                f"[{cid}] {app.appearance_type} ({app.identity_status}) | Date: {pub_date or 'Unknown'} | "
                f"Publisher: {app.publisher or 'Unknown'} | Title: {truncate_text(app.title, 120)} | URL: {src_url or 'N/A'}\n"
                f"    Summary: {truncate_text(analysis_summary or raw_excerpt or 'N/A', 220)}"
                + (f"\n    Topics: {topics_str}" if topics_str else "")
                + (f"\n    Key Points: {kp_str}" if kp_str else "")
            )
            if running_catalog_chars + len(entry) <= max_catalog_chars or len(catalog_lines) < 5:
                catalog_lines.append(entry)
                running_catalog_chars += len(entry)

    return EvidenceBundle(
        person_name=person.name,
        profession=person.profession,
        biography=person.biography,
        headline=person.headline,
        occupation=person.occupation,
        location=person.location,
        experiences=experiences,
        education=education,
        projects=projects,
        skills=skills,
        certifications=certifications,
        person_summary=person.summary,
        appearances_meta=appearances_meta,
        citation_map=citation_map,
        person_digest="\n".join(digest_parts),
        evidence_catalog="\n".join(catalog_lines) if catalog_lines else "No external evidence collected yet.",
        data_coverage=coverage,
    )


def _to_response(row: PersonInsightsReport) -> InsightsReportResponse:
    return InsightsReportResponse(
        id=row.id,
        person_id=row.person_id,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        generation_time_seconds=row.generation_time_seconds,
        source_count=row.source_count,
        generated_at=row.created_at,
        report=InsightsReportPayload.model_validate(row.report_data),
    )


def generate_and_save_insights(
    db: Session,
    person: Person,
    request: Optional[GenerateInsightsRequest] = None,
) -> InsightsReportResponse:
    """Synthesizes collected evidence for a person, persists the report snapshot, and returns it."""
    t0 = time.perf_counter()
    bundle = collect_person_evidence(db, person)
    summarizer = InsightsSummarizer()
    payload, model_name, prompt_version = summarizer.generate(
        bundle,
        focus_notes=request.focus_notes if request else None,
    )
    elapsed = round(time.perf_counter() - t0, 3)

    report_row = PersonInsightsReport(
        person_id=person.id,
        model_name=model_name,
        prompt_version=prompt_version,
        generation_time_seconds=elapsed,
        source_count=bundle.data_coverage.get("total_sources_analyzed", 0),
        report_data=payload.model_dump(),
    )
    db.add(report_row)
    db.commit()
    db.refresh(report_row)
    logger.info(
        f"Generated AI insights report {report_row.id} for {person.name} ({person.id}) "
        f"using {model_name} [{prompt_version}] in {elapsed}s ({report_row.source_count} sources)"
    )
    return _to_response(report_row)


def get_insights_history(db: Session, person_id: str) -> InsightsHistoryResponse:
    """Returns latest persisted AI insights report and full historical snapshots for a person."""
    rows = (
        db.query(PersonInsightsReport)
        .filter(PersonInsightsReport.person_id == person_id)
        .order_by(PersonInsightsReport.created_at.desc())
        .all()
    )
    history = [_to_response(r) for r in rows]
    return InsightsHistoryResponse(
        person_id=person_id,
        latest_report=history[0] if history else None,
        history=history,
    )
