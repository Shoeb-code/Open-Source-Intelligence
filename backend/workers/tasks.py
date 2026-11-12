from collections import defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, as_completed, wait
import statistics
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import (
    ResearchJob, Appearance, Source, AppearanceAnalysis, CollectionLog, SocialProfile
)
from backend.modules.persons.schemas import IdentityContext
from backend.modules.persons.service import build_identity_context
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.service import DiscoveryService
from backend.modules.extraction.article_extractor import ArticleExtractor
from backend.modules.extraction.metadata_extractor import ExtractedPayload, MetadataExtractor
from backend.modules.identity.verifier import IdentityVerifier
from backend.modules.deduplication.deduplicator import DeduplicationGroup, Deduplicator
from backend.modules.analysis.classifier import AppearanceClassifier
from backend.modules.analysis.summarizer import AIAnalysisResult, AppearanceSummarizer
from backend.workers.celery_app import celery_app
from backend.utils.logger import logger
from backend.utils.text_cleaner import compute_content_hash
from backend.utils.url_validator import canonicalize_url, dedup_url_key, extract_youtube_video_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _filter_new_candidates(
    db: Session,
    person_id: str,
    discovered_items: List[DiscoveredItem],
) -> Tuple[List[DiscoveredItem], int, set]:
    """
    Pre-deduplicates discovered URLs by canonical URL and YouTube video ID and skips
    URLs already stored for this target person before making outbound extraction calls.
    """
    existing_canonical_urls = {
        row[0]
        for row in db.query(Source.canonical_url)
        .join(Appearance, Source.appearance_id == Appearance.id)
        .filter(
            Appearance.person_id == person_id,
            Source.canonical_url.isnot(None),
        )
        .all()
    }
    existing_yt_ids = {extract_youtube_video_id(u) for u in existing_canonical_urls if u}
    existing_yt_ids.discard(None)
    existing_dedup_keys = {dedup_url_key(u) for u in existing_canonical_urls if u}

    seen_urls = set()
    seen_yt_ids = set()
    seen_dedup_keys = set()
    filtered: List[DiscoveredItem] = []
    skipped = 0

    for item in discovered_items:
        canon = canonicalize_url(item.url)
        yt_id = extract_youtube_video_id(canon)
        dkey = dedup_url_key(canon)

        if canon in existing_canonical_urls or canon in seen_urls or dkey in existing_dedup_keys or dkey in seen_dedup_keys:
            skipped += 1
            continue
        if yt_id and (yt_id in existing_yt_ids or yt_id in seen_yt_ids):
            skipped += 1
            continue

        seen_urls.add(canon)
        seen_dedup_keys.add(dkey)
        if yt_id:
            seen_yt_ids.add(yt_id)
        filtered.append(item)

    return filtered, skipped, existing_canonical_urls


def _extract_items_concurrently(
    items: List[DiscoveredItem],
    job: Optional[ResearchJob] = None,
    db: Optional[Session] = None,
) -> List[ExtractedPayload]:
    """
    Extracts URL payloads in parallel using a domain-aware non-blocking scheduler.
    Prevents head-of-line stalling when one host (e.g. youtube.com or linkedin.com) has many queued URLs.
    """
    if not items:
        return []

    total = len(items)
    workers = max(1, min(total, settings.EXTRACTION_MAX_WORKERS))
    max_per_host = max(1, settings.PER_DOMAIN_MAX_CONCURRENCY)
    allow_whisper = settings.ENABLE_BULK_YOUTUBE_WHISPER

    domain_queues: Dict[str, deque] = defaultdict(deque)
    for idx, item in enumerate(items):
        host = (urlparse(item.url).netloc or "default").lower()
        domain_queues[host].append((idx, item))

    active_per_host: Dict[str, int] = defaultdict(int)
    in_flight: Dict[Future, Tuple[int, str]] = {}
    ordered_results: Dict[int, Optional[ExtractedPayload]] = {}
    completed = 0
    progress_step = 2

    def _extract_one(item: DiscoveredItem) -> Optional[ExtractedPayload]:
        try:
            return MetadataExtractor.extract(item, allow_youtube_whisper=allow_whisper)
        except Exception as e:
            logger.warning(f"Failed extraction for {item.url}: {e}")
            return None

    def _pop_next_eligible() -> Optional[Tuple[int, str, DiscoveredItem]]:
        # Pick the eligible host with the largest remaining backlog so busy hosts start immediately
        # while free worker slots never block waiting on saturated hosts.
        best_host: Optional[str] = None
        best_len = 0
        for host, q in domain_queues.items():
            if q and active_per_host[host] < max_per_host and len(q) > best_len:
                best_host = host
                best_len = len(q)
        if best_host is None:
            return None
        idx, item = domain_queues[best_host].popleft()
        return idx, best_host, item

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while in_flight or any(domain_queues.values()):
            while len(in_flight) < workers:
                next_task = _pop_next_eligible()
                if next_task is None:
                    break
                idx, host, item = next_task
                active_per_host[host] += 1
                fut = executor.submit(_extract_one, item)
                in_flight[fut] = (idx, host)

            if not in_flight:
                break

            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                idx, host = in_flight.pop(fut)
                active_per_host[host] -= 1
                ordered_results[idx] = fut.result()
                completed += 1

            if job is not None and db is not None and (completed % progress_step == 0 or completed == total):
                job.progress = 35 + int(25 * completed / total)
                db.commit()

    return [ordered_results[i] for i in range(total) if ordered_results.get(i) is not None]


def _analyze_groups_concurrently(
    verified_groups: List[Tuple[DeduplicationGroup, str, float, str]],
    context: IdentityContext,
    summarizer: AppearanceSummarizer,
) -> List[Optional[AIAnalysisResult]]:
    """Runs Stage-1 AI summarization concurrently across accepted appearance groups."""
    if not verified_groups:
        return []

    workers = max(1, min(len(verified_groups), settings.ANALYSIS_MAX_WORKERS))

    def _analyze_one(idx: int, entry: Tuple[DeduplicationGroup, str, float, str]) -> Tuple[int, Optional[AIAnalysisResult]]:
        group, identity_status, _, _ = entry
        if identity_status not in ("VERIFIED", "LIKELY_MATCH", "NEEDS_REVIEW"):
            return idx, None
        return idx, summarizer.analyze(context, group.primary_item)

    results: List[Optional[AIAnalysisResult]] = [None] * len(verified_groups)
    if workers == 1:
        for idx, entry in enumerate(verified_groups):
            _, results[idx] = _analyze_one(idx, entry)
        return results

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_analyze_one, idx, entry) for idx, entry in enumerate(verified_groups)]
        for fut in as_completed(futures):
            idx, res = fut.result()
            results[idx] = res

    return results


def _refresh_failed_linkedin_sources(
    db: Session,
    person_id: str,
    context: IdentityContext,
    summarizer: AppearanceSummarizer,
) -> int:
    """
    Retries previously failed/restricted empty LinkedIn sources in-place so existing records
    populate post/profile content without duplicating appearances.
    """
    stale_rows = (
        db.query(Source, Appearance)
        .join(Appearance, Source.appearance_id == Appearance.id)
        .filter(
            Appearance.person_id == person_id,
            Source.extraction_status.in_(("FAILED", "RESTRICTED")),
            or_(Source.extracted_content.is_(None), Source.extracted_content == ""),
            Source.canonical_url.ilike("%linkedin.com%"),
        )
        .all()
    )
    if not stale_rows:
        return 0

    work_items = [
        (
            idx,
            src.canonical_url or src.source_url,
            app.title,
            app.publisher or "LinkedIn",
            app.published_at,
            src.source_type or "LINKEDIN",
            app.identity_status,
            app.analysis is None,
        )
        for idx, (src, app) in enumerate(stale_rows)
        if (src.canonical_url or src.source_url)
    ]
    if not work_items:
        return 0

    def _retry_one(entry):
        idx, target_url, title, pub, pub_at, src_type, identity_status, needs_analysis = entry
        try:
            text, status, page_title, page_pub = ArticleExtractor.extract_article(target_url)
            analysis_res = None
            if text and status == "SUCCESS" and needs_analysis and identity_status in ("VERIFIED", "LIKELY_MATCH", "NEEDS_REVIEW"):
                payload = ExtractedPayload(
                    title=page_title or title or "LinkedIn Post",
                    source_url=target_url,
                    canonical_url=canonicalize_url(target_url),
                    source_type=src_type,
                    publisher=page_pub or pub or "LinkedIn",
                    published_at=pub_at,
                    description=None,
                    extracted_content=text,
                    content_hash=compute_content_hash(text),
                    extraction_status=status,
                )
                analysis_res = summarizer.analyze(context, payload)
            return idx, text, status, page_title, page_pub, analysis_res
        except Exception as e:
            logger.warning(f"Failed refreshing LinkedIn source {target_url}: {e}")
            return idx, None, None, None, None, None

    workers = max(1, min(len(work_items), 4))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        retry_results = list(executor.map(_retry_one, work_items))

    refreshed = 0
    for idx, text, status, page_title, page_pub, analysis_res in retry_results:
        if not text or status != "SUCCESS":
            continue
        src, app = stale_rows[idx]
        src.extracted_content = text
        src.extraction_status = "SUCCESS"
        src.content_hash = compute_content_hash(text)
        if page_title and (not app.title or app.title == "LinkedIn Publication"):
            app.title = page_title
        if not app.publisher:
            app.publisher = page_pub or "LinkedIn"
        if not app.description:
            app.description = text[:500]
        if analysis_res is not None and app.analysis is None:
            db.add(AppearanceAnalysis(
                appearance_id=app.id,
                summary=analysis_res.summary,
                topics=analysis_res.topics,
                key_points=analysis_res.key_points,
                person_role=analysis_res.person_role,
                evidence=analysis_res.evidence,
                model_name=analysis_res.model_name,
            ))
        refreshed += 1

    if refreshed:
        db.commit()
    return refreshed


@celery_app.task(name="execute_research_pipeline")
def execute_research_pipeline(job_id: str):
    """
    Executes the end-to-end OSINT research workflow:
    Concurrent Discovery -> Pre-Dedup Filter -> Concurrent Extraction ->
    Deduplication -> Verification -> Concurrent Analysis -> DB Storage
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

        # --- STEP 1: CONCURRENT DISCOVERY ---
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
        job.progress = 30
        db.commit()

        if not discovered_items:
            logger.warning(f"No candidates found for {context.name}")
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = utc_now()
            db.commit()
            return

        # --- STEP 1.5: PRE-DEDUP & EXISTING DB FILTER ---
        summarizer = AppearanceSummarizer()
        refreshed_linkedin_count = _refresh_failed_linkedin_sources(db, job.person_id, context, summarizer)
        items_to_extract, skipped_duplicates, existing_urls = _filter_new_candidates(
            db, job.person_id, discovered_items
        )
        job.progress = 35
        db.commit()

        if not items_to_extract:
            total_time = round(time.time() - start_time, 2)
            db.add(CollectionLog(
                job_id=job.id,
                source="ContentExtractionEngine",
                status="SUCCESS",
                execution_time=0.0,
                error_message=(
                    f"Skipped extraction: all {skipped_duplicates} discovered URL(s) already stored or duplicated."
                    + (f" Refreshed {refreshed_linkedin_count} LinkedIn source(s)." if refreshed_linkedin_count else "")
                )
            ))
            db.add(CollectionLog(
                job_id=job.id,
                source="PipelineCoordinator",
                status="SUCCESS",
                execution_time=total_time,
                error_message=(
                    f"Pipeline complete. Stored 0 new appearances (all candidates already present"
                    + (f"; refreshed {refreshed_linkedin_count} LinkedIn source(s)" if refreshed_linkedin_count else "")
                    + ")."
                )
            ))
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = utc_now()
            db.commit()
            logger.info(f"Research job {job_id} finished cleanly in {total_time}s (all URLs already cached)")
            return

        # --- STEP 2: CONCURRENT EXTRACTION ---
        extract_start = time.time()
        extracted_payloads = _extract_items_concurrently(items_to_extract, job=job, db=db)

        extract_time = round(time.time() - extract_start, 2)
        method_counts: Dict[str, int] = {}
        durations_ms: List[float] = []
        total_retries = 0
        total_sem_wait_ms = 0.0
        status_counts: Dict[str, int] = {}
        for payload in extracted_payloads:
            m = payload.extraction_method or "unknown"
            method_counts[m] = method_counts.get(m, 0) + 1
            det = payload.extraction_details or {}
            if isinstance(det.get("duration_ms"), (int, float)) and det["duration_ms"] > 0:
                durations_ms.append(float(det["duration_ms"]))
            if isinstance(det.get("semaphore_wait_ms"), (int, float)):
                total_sem_wait_ms += float(det["semaphore_wait_ms"])
            if isinstance(det.get("retry_count"), int):
                total_retries += det["retry_count"]
            api_code = det.get("api_status_code")
            if isinstance(api_code, int) and api_code != 200:
                key = f"fc_{api_code}"
                status_counts[key] = status_counts.get(key, 0) + 1
            elif isinstance(det.get("failure_reason"), str) and "Timeout" in det["failure_reason"]:
                status_counts["fc_timeout"] = status_counts.get("fc_timeout", 0) + 1

        methods_summary = ", ".join(f"{k}={v}" for k, v in sorted(method_counts.items()))
        perf_parts = []
        if durations_ms:
            perf_parts.append(
                f"avg_ms={round(statistics.mean(durations_ms), 1)}, "
                f"p50_ms={round(statistics.median(durations_ms), 1)}, "
                f"max_ms={round(max(durations_ms), 1)}, "
                f"sem_wait_ms={round(total_sem_wait_ms, 1)}, retries={total_retries}"
            )
        if status_counts:
            perf_parts.append(", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
        perf_suffix = f" [{' | '.join(perf_parts)}]" if perf_parts else ""

        db.add(CollectionLog(
            job_id=job.id,
            source="ContentExtractionEngine",
            status="SUCCESS",
            execution_time=extract_time,
            error_message=(
                f"Extracted {len(extracted_payloads)}/{len(items_to_extract)} items "
                f"(pre-skipped {skipped_duplicates} duplicates/existing)"
                + (f" ({methods_summary})" if methods_summary else "")
                + perf_suffix
            )
        ))
        job.progress = 65
        db.commit()

        # --- STEP 3: DEDUPLICATION & VERIFICATION ---
        dedup_groups = Deduplicator.deduplicate(extracted_payloads)
        verified_groups: List[Tuple[DeduplicationGroup, str, float, str]] = []

        for group in dedup_groups:
            primary = group.primary_item
            identity_status, confidence_score, _ = IdentityVerifier.verify(context, primary)

            if identity_status == "REJECTED":
                logger.info(f"Skipping rejected appearance for {context.name}: '{primary.title}' (score={confidence_score})")
                continue

            if primary.canonical_url in existing_urls:
                continue

            appearance_type = AppearanceClassifier.classify(primary)
            verified_groups.append((group, identity_status, confidence_score, appearance_type))

        job.progress = 75
        db.commit()

        # --- STEP 4: CONCURRENT STAGE-1 AI ANALYSIS ---
        analysis_results = _analyze_groups_concurrently(verified_groups, context, summarizer)
        job.progress = 90
        db.commit()

        # --- STEP 5: PERSISTENCE ON MAIN SESSION ---
        saved_appearances_count = 0
        for (group, identity_status, confidence_score, appearance_type), analysis_res in zip(verified_groups, analysis_results):
            primary = group.primary_item

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

            for src_item in group.associated_sources:
                db.add(Source(
                    appearance_id=appearance.id,
                    source_url=src_item.source_url,
                    canonical_url=src_item.canonical_url,
                    source_type=src_item.source_type,
                    extracted_content=src_item.extracted_content,
                    content_hash=src_item.content_hash,
                    extraction_status=src_item.extraction_status
                ))

            if analysis_res is not None:
                db.add(AppearanceAnalysis(
                    appearance_id=appearance.id,
                    summary=analysis_res.summary,
                    topics=analysis_res.topics,
                    key_points=analysis_res.key_points,
                    person_role=analysis_res.person_role,
                    evidence=analysis_res.evidence,
                    model_name=analysis_res.model_name
                ))

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
                        db.flush()
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
                        db.flush()

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
