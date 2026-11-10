import secrets
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models import Person
from backend.modules.enrichment.linkedin_profile import (
    LinkedInEnrichmentError,
    LinkedInProfileEnrichmentService,
)
from backend.modules.enrichment.schemas import (
    LinkedInEnrichRequest,
    LinkedInEnrichResponse,
    LinkedInImportRequest,
)
from backend.modules.persons.service import get_person_by_id

linkedin_router = APIRouter(prefix="/linkedin", tags=["LinkedIn Enrichment"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _check_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Enforces Bearer/API-Key auth whenever API_AUTH_TOKEN is configured."""
    expected = settings.API_AUTH_TOKEN
    if not expected:
        return

    token: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required.",
        )
    if not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials.",
        )


def verify_target_enrichment_access(
    target_id: str,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    x_authorized_targets: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Person:
    """Authenticates the caller (if token configured) and confirms access to the target person."""
    _check_api_token(authorization=authorization, x_api_key=x_api_key)

    if x_authorized_targets is not None:
        allowed = {t.strip() for t in x_authorized_targets.split(",") if t.strip()}
        if target_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to enrich this target.",
            )

    person = get_person_by_id(db, target_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target person not found")

    return person


@linkedin_router.post("/enrich/{target_id}", response_model=LinkedInEnrichResponse)
def enrich_linkedin_profile(
    target_id: str,
    payload: LinkedInEnrichRequest = Body(default_factory=LinkedInEnrichRequest),
    person: Person = Depends(verify_target_enrichment_access),
    db: Session = Depends(get_db),
):
    """Triggers Firecrawl Alexandria (EnrichLayer) enrichment for a target's verified LinkedIn profile."""
    service = LinkedInProfileEnrichmentService()
    try:
        result = service.enrich_target(
            db=db,
            person=person,
            force=payload.force,
            override_url=payload.profile_url,
        )
        return LinkedInEnrichResponse(**result)
    except LinkedInEnrichmentError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@linkedin_router.post("/import-cache", response_model=LinkedInEnrichResponse)
def import_cached_linkedin_profile(
    payload: LinkedInImportRequest = Body(default_factory=LinkedInImportRequest),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Safely imports an existing *_enrichlayer_response.json file from project root without spending credits."""
    _check_api_token(authorization=authorization, x_api_key=x_api_key)

    rel = (payload.file_path or "").strip()
    if rel:
        candidate = (PROJECT_ROOT / rel).resolve()
        if not candidate.is_relative_to(PROJECT_ROOT):
            raise HTTPException(status_code=400, detail="Invalid cache file path outside project directory.")
        candidates = [candidate]
    else:
        candidates = sorted(PROJECT_ROOT.glob("*enrichlayer_response.json"))

    imported_person: Optional[Person] = None
    for path in candidates:
        if not path.is_file():
            continue
        imported_person = LinkedInProfileEnrichmentService.import_from_json_file(
            db=db,
            file_path=path,
            person_id=payload.target_id,
        )
        if imported_person:
            break

    if not imported_person:
        raise HTTPException(
            status_code=404,
            detail="No matching cached enrichment JSON file or matching target person found.",
        )

    structured = LinkedInProfileEnrichmentService.build_structured_from_person(imported_person)
    return LinkedInEnrichResponse(
        success=True,
        enrichment_status=imported_person.enrichment_status or "SUCCESS",
        credits_cost=0,
        message="Imported LinkedIn profile data from cached JSON response without spending credits.",
        profile_enriched_at=imported_person.profile_enriched_at,
        structured_profile=structured,
        target_id=imported_person.id,
    )

