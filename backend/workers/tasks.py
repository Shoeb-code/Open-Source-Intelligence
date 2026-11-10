import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import (
    ResearchJob, Appearance, Source, AppearanceAnalysis, CollectionLog, SocialProfile
)
from backend.modules.persons.service import build_identity_context
from backend.modules.discovery.service import DiscoveryService
from backend.modules.extraction.metadata_extractor import MetadataExtractor
from backend.modules.identity.verifier import IdentityVerifier
from backend.modules.deduplication.deduplicator import Deduplicator
from backend.modules.analysis.classifier import AppearanceClassifier
from backend.modules.analysis.summarizer import AppearanceSummarizer
from backend.workers.celery_app import celery_app
from backend.utils.logger import logger


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@celery_app.task(name="execute_research_pipeline")
def execute_research_pipeline(job_id: str):
    """
    Executes the end-to-end OSINT research workflow:
    Discovery -> Extraction -> Verification -> Deduplication -> Classification -> AI Analysis -> DB Storage
    """
    db: Session = SessionLocal()
    start_time = time.time()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database.")
            return

        job.status = "RUNNING"
        job.started_at = utc_now()
        job.progress = 10
        db.commit()

        context = build_identity_context(db, job.person_id)
        if not context:
            raise ValueError(f"Identity context could not be built for Person {job.person_id}")

        # --- STEP 1: DISCOVERY ---
        discovery_start = time.time()
        discovery_service = DiscoveryService()
        discovered_items = discovery_service.run_discovery(context)
        discovery_time = round(time.time() - discovery_start, 2)

        db.add(CollectionLog(
            job_id=job.id,
            source="DiscoveryEngine",
            status="SUCCESS",
            execution_time=discovery_time,
            error_message=f"Discovered {len(discovered_items)} candidate URLs"
        ))
        job.progress = 35
        db.commit()

        if not discovered_items:
            logger.warning(f"No candidates found for {context.name}")
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = utc_now()
            db.commit()
            return

        # --- STEP 2: EXTRACTION ---
        extract_start = time.time()
        extracted_payloads = []
        for item in discovered_items:
            try:
                payload = MetadataExtractor.extract(item)
                extracted_payloads.append(payload)
            except Exception as e:
                logger.warning(f"Failed extraction for {item.url}: {e}")

        extract_time = round(time.time() - extract_start, 2)
        method_counts = {}
        for payload in extracted_payloads:
            m = payload.extraction_method or "unknown"
            method_counts[m] = method_counts.get(m, 0) + 1
        methods_summary = ", ".join(f"{k}={v}" for k, v in sorted(method_counts.items()))
        db.add(CollectionLog(
            job_id=job.id,
            source="ContentExtractionEngine",
            status="SUCCESS",
            execution_time=extract_time,
            error_message=(
                f"Extracted content/metadata from {len(extracted_payloads)} items"
                + (f" ({methods_summary})" if methods_summary else "")
            )
        ))
        job.progress = 55
        db.commit()

        # --- STEP 3: DEDUPLICATION ---
        dedup_groups = Deduplicator.deduplicate(extracted_payloads)
        job.progress = 70
        db.commit()

        # --- STEP 4: VERIFICATION & AI ANALYSIS ---
        summarizer = AppearanceSummarizer()
        saved_appearances_count = 0

        for group in dedup_groups:
            primary = group.primary_item

            # Verify identity
            identity_status, confidence_score, evidence_signals = IdentityVerifier.verify(context, primary)

            # DISCARD REJECTED / UNRELATED RESULTS:
            # If the candidate was rejected (belongs to a different person or unrelated event), DO NOT store it!
            if identity_status == "REJECTED":
                logger.info(f"Skipping rejected appearance for {context.name}: '{primary.title}' (score={confidence_score})")
                continue

            # Skip duplicates if an appearance with the same canonical URL already exists for this person
            existing_app = (
                db.query(Appearance)
                .join(Source)
                .filter(
                    Appearance.person_id == job.person_id,
                    Source.canonical_url == primary.canonical_url
                )
                .first()
            )
            if existing_app:
                continue

            # Classify appearance category
            appearance_type = AppearanceClassifier.classify(primary)

            # Create Appearance entity
            appearance = Appearance(
                person_id=job.person_id,
                appearance_type=appearance_type,
                title=primary.title,
                description=primary.description,
                publisher=primary.publisher,
                published_at=primary.published_at,
                identity_status=identity_status,
                confidence_score=confidence_score
            )
            db.add(appearance)
            db.flush()

            # Create Source entities for all merged items in this group
            for src_item in group.associated_sources:
                source = Source(
                    appearance_id=appearance.id,
                    source_url=src_item.source_url,
                    canonical_url=src_item.canonical_url,
                    source_type=src_item.source_type,
                    extracted_content=src_item.extracted_content,
                    content_hash=src_item.content_hash,
                    extraction_status=src_item.extraction_status
                )
                db.add(source)

            # Run AI Analysis for relevant (VERIFIED or LIKELY_MATCH or NEEDS_REVIEW) appearances
            if identity_status in ("VERIFIED", "LIKELY_MATCH", "NEEDS_REVIEW"):
                analysis_res = summarizer.analyze(context, primary)
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

            # Auto-link discovered social profile accounts if not already linked
            if identity_status in ("VERIFIED", "LIKELY_MATCH"):
                target_url = primary.canonical_url.lower()
                if "linkedin.com/in/" in target_url:
                    existing_li = db.query(SocialProfile).filter(
                        SocialProfile.person_id == job.person_id,
                        SocialProfile.platform == "linkedin"
                    ).first()
                    if not existing_li:
                        from backend.modules.persons.service import _extract_username_from_url
                        db.add(SocialProfile(
                            person_id=job.person_id,
                            platform="linkedin",
                            username=_extract_username_from_url(primary.canonical_url, "linkedin"),
                            profile_url=primary.canonical_url,
                            verification_status="VERIFIED"
                        ))
                    elif existing_li.verification_status != "VERIFIED":
                        existing_li.verification_status = "VERIFIED"
                elif "instagram.com/" in target_url and not any(p in target_url for p in ("/p/", "/reel/", "/tv/")):
                    existing_ig = db.query(SocialProfile).filter(
                        SocialProfile.person_id == job.person_id,
                        SocialProfile.platform == "instagram"
                    ).first()
                    if not existing_ig:
                        from backend.modules.persons.service import _extract_username_from_url
                        db.add(SocialProfile(
                            person_id=job.person_id,
                            platform="instagram",
                            username=_extract_username_from_url(primary.canonical_url, "instagram"),
                            profile_url=primary.canonical_url,
                            verification_status="VERIFIED"
                        ))

            saved_appearances_count += 1

        total_time = round(time.time() - start_time, 2)
        job.status = "COMPLETED"
        job.progress = 100
        job.completed_at = utc_now()

        db.add(CollectionLog(
            job_id=job.id,
            source="PipelineCoordinator",
            status="SUCCESS",
            execution_time=total_time,
            error_message=f"Pipeline complete. Stored {saved_appearances_count} consolidated appearances."
        ))

        db.commit()
        logger.info(f"Research job {job_id} successfully completed in {total_time}s")

    except Exception as e:
        logger.exception(f"Research job {job_id} failed: {e}")
        try:
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                job.completed_at = utc_now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

