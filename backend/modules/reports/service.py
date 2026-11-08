from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import Person, ResearchJob, Appearance, Source, AppearanceAnalysis
from backend.modules.analysis.report_generator import ReportGenerator
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.extraction.metadata_extractor import MetadataExtractor
from backend.modules.identity.verifier import IdentityVerifier
from backend.modules.analysis.classifier import AppearanceClassifier
from backend.modules.analysis.summarizer import AppearanceSummarizer
from backend.modules.persons.service import build_identity_context
from backend.utils.url_validator import canonicalize_url, detect_platform, extract_youtube_video_id
from backend.utils.logger import logger


def create_research_job(db: Session, person_id: str) -> ResearchJob:
    job = ResearchJob(person_id=person_id, status="PENDING", progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_research_job(db: Session, job_id: str) -> Optional[ResearchJob]:
    return db.query(ResearchJob).filter(ResearchJob.id == job_id).first()


def get_appearances_by_person(
    db: Session, person_id: str, identity_status: Optional[str] = None
) -> List[Appearance]:
    query = db.query(Appearance).filter(Appearance.person_id == person_id)
    if identity_status:
        query = query.filter(Appearance.identity_status == identity_status)
    return query.order_by(Appearance.published_at.desc(), Appearance.created_at.desc()).all()


def get_sources_by_person(db: Session, person_id: str) -> List[Source]:
    return (
        db.query(Source)
        .join(Appearance, Source.appearance_id == Appearance.id)
        .filter(Appearance.person_id == person_id)
        .all()
    )


def delete_appearance(db: Session, appearance_id: str) -> bool:
    appearance = db.query(Appearance).filter(Appearance.id == appearance_id).first()
    if not appearance:
        return False
    db.delete(appearance)
    db.commit()
    logger.info(f"Deleted appearance: {appearance_id}")
    return True


def generate_report_for_person(db: Session, person_id: str) -> Optional[Dict[str, Any]]:
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return None
    appearances = (
        db.query(Appearance)
        .filter(Appearance.person_id == person_id)
        .all()
    )
    return ReportGenerator.generate_report(person, appearances)


def analyze_and_store_url(
    db: Session,
    person_id: str,
    url: str,
    source_type: Optional[str] = None,
    title: Optional[str] = None
) -> Optional[Appearance]:
    """Ingests, extracts, verifies, analyzes, and persists a direct URL appearance for a target individual."""
    context = build_identity_context(db, person_id)
    if not context:
        return None

    clean_url = canonicalize_url(url)
    
    # Auto-detect source type if not provided
    if not source_type:
        detected = detect_platform(clean_url)
        if detected == "youtube":
            source_type = "YOUTUBE"
        elif "podcast" in clean_url.lower():
            source_type = "PODCAST"
        elif "news" in clean_url.lower():
            source_type = "NEWS"
        else:
            source_type = "WEBPAGE"

    # Initial candidate item
    item = DiscoveredItem(
        title=title or "Uploaded Media Appearance",
        url=clean_url,
        source_type=source_type
    )

    # 1. Content Extraction
    payload = MetadataExtractor.extract(item)
    if title and payload.title == "Uploaded Media Appearance":
        payload.title = title

    # 2. Identity Verification
    identity_status, confidence_score, signals = IdentityVerifier.verify(context, payload)

    # 3. Categorization
    appearance_type = AppearanceClassifier.classify(payload)

    # 4. Create Appearance
    appearance = Appearance(
        person_id=person_id,
        appearance_type=appearance_type,
        title=payload.title,
        description=payload.description,
        publisher=payload.publisher,
        published_at=payload.published_at,
        identity_status=identity_status,
        confidence_score=confidence_score
    )
    db.add(appearance)
    db.flush()

    # 5. Create Source
    source = Source(
        appearance_id=appearance.id,
        source_url=clean_url,
        canonical_url=payload.canonical_url,
        source_type=payload.source_type,
        extracted_content=payload.extracted_content,
        content_hash=payload.content_hash,
        extraction_status=payload.extraction_status
    )
    db.add(source)

    # 6. AI Analysis
    summarizer = AppearanceSummarizer()
    analysis_res = summarizer.analyze(context, payload)
    analysis_entry = AppearanceAnalysis(
        appearance_id=appearance.id,
        summary=analysis_res.summary,
        topics=analysis_res.topics,
        key_points=analysis_res.key_points,
        person_role=analysis_res.person_role,
        evidence=analysis_res.evidence,
        model_name=analysis_res.model_name
    )
    db.add(analysis_entry)

    db.commit()
    db.refresh(appearance)
    logger.info(f"Direct URL ingested and analyzed for person {person_id}: {clean_url}")
    return appearance
