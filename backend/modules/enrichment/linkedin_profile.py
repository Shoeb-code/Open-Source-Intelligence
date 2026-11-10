import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.models import Person, SocialProfile
from backend.modules.enrichment.schemas import (
    StructuredLinkedInProfile,
    ExperienceItem,
    EducationItem,
    ProjectItem,
    ActivityItem,
)
from backend.utils.logger import logger
from backend.utils.url_validator import canonicalize_url

_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ALEXANDRIA_SCRAPE_URL ="https://api.firecrawl.dev/v2/scrape"


class LinkedInEnrichmentError(Exception):
    """Domain error raised when LinkedIn enrichment validation or upstream fetch fails."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _redact_api_key(text: str) -> str:
    if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY in text:
        return text.replace(settings.FIRECRAWL_API_KEY, "[REDACTED]")
    return text


def _format_enrichlayer_date(date_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(date_obj, dict):
        return None
    year = date_obj.get("year")
    month = date_obj.get("month")
    if not year:
        return None
    if isinstance(month, int) and 1 <= month <= 12:
        return f"{_MONTH_NAMES[month]} {year}"
    return str(year)


def _clean_summary_text(raw_summary: Optional[str]) -> Optional[str]:
    if not raw_summary or not isinstance(raw_summary, str):
        return None
    # Preserve paragraph breaks from HTML <br> before stripping residual markup
    normalized = re.sub(r"<br\s*/?>", "\n", raw_summary, flags=re.IGNORECASE)
    text = BeautifulSoup(normalized, "html.parser").get_text()
    # Collapse excessive blank lines while retaining readable paragraphs
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for i, line in enumerate(lines) if line or (i > 0 and lines[i - 1]))
    return cleaned.strip() or None


def _unwrap_alexandria_record(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts the inner EnrichLayer profile object from either a Firecrawl v2 envelope or direct dict."""
    if not isinstance(raw_payload, dict):
        raise LinkedInEnrichmentError("Invalid JSON response structure from enrichment provider.", status_code=502)

    if "data" in raw_payload and isinstance(raw_payload["data"], dict) and "alexandria" in raw_payload["data"]:
        alex_list = raw_payload["data"].get("alexandria") or []
        if not alex_list:
            raise LinkedInEnrichmentError("Alexandria returned an empty provider result list.", status_code=502)
        first = alex_list[0]
        if isinstance(first, dict) and first.get("error"):
            err = first["error"]
            raise LinkedInEnrichmentError(
                f"Alexandria provider error ({err.get('code', 'unknown')}): {err.get('message', 'Request failed')}",
                status_code=int(err.get("status") or 502),
            )
        inner = first.get("data") if isinstance(first, dict) else None
        if not isinstance(inner, dict) or not inner:
            raise LinkedInEnrichmentError("EnrichLayer returned no profile record for this URL.", status_code=404)
        return inner

    # Direct EnrichLayer record dict
    if any(k in raw_payload for k in ("public_identifier", "full_name", "experiences", "education")):
        return raw_payload

    raise LinkedInEnrichmentError("Unrecognized profile payload shape from EnrichLayer.", status_code=502)


def _extract_credits_cost(raw_payload: Dict[str, Any]) -> int:
    if not isinstance(raw_payload, dict):
        return 0
    data_block = raw_payload.get("data")
    if isinstance(data_block, dict):
        if isinstance(data_block.get("creditsCost"), int):
            return data_block["creditsCost"]
        alex = data_block.get("alexandria") or []
        if alex and isinstance(alex[0], dict) and isinstance(alex[0].get("creditsCost"), int):
            return alex[0]["creditsCost"]
    return 0


class LinkedInProfileEnrichmentService:
    """Fetches, validates, and normalizes structured LinkedIn profiles via Firecrawl Alexandria (EnrichLayer)."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 45.0):
        self.api_key = api_key if api_key is not None else settings.FIRECRAWL_API_KEY
        self.timeout = timeout

    @staticmethod
    def validate_linkedin_profile_url(url: str) -> str:
        """Validates and canonicalizes a LinkedIn /in/<username> profile URL."""
        if not url or not isinstance(url, str):
            raise LinkedInEnrichmentError("A valid LinkedIn profile URL is required.", status_code=400)

        canon = canonicalize_url(url.strip())
        parsed = urlparse(canon)
        netloc = parsed.netloc.lower().split(":")[0]

        if not (netloc == "linkedin.com" or netloc.endswith(".linkedin.com")):
            raise LinkedInEnrichmentError(f"Invalid LinkedIn domain: {netloc}", status_code=400)

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2 or parts[0].lower() != "in":
            raise LinkedInEnrichmentError(
                "URL must point to a personal LinkedIn /in/<username> profile.",
                status_code=400,
            )

        identifier = parts[1]
        if identifier.lower() in ("dir", "pub", "jobs", "company", "posts", "pulse", "feed", "checkpoint", "login"):
            raise LinkedInEnrichmentError("Invalid LinkedIn personal profile identifier.", status_code=400)

        return f"https://www.linkedin.com/in/{identifier}"

    @staticmethod
    def resolve_verified_linkedin_profile(
        db: Session,
        person: Person,
        override_url: Optional[str] = None,
    ) -> SocialProfile:
        """Ensures the target has a LinkedIn /in/ profile that has passed identity verification."""
        li_profiles = [
            p for p in (person.social_profiles or [])
            if p.platform == "linkedin" and "/in/" in (p.profile_url or "").lower()
        ]

        if override_url:
            clean_override = LinkedInProfileEnrichmentService.validate_linkedin_profile_url(override_url)
            override_slug = clean_override.rstrip("/").split("/")[-1].lower()
            for prof in li_profiles:
                existing_slug = (prof.username or prof.profile_url.rstrip("/").split("/")[-1]).lower()
                if existing_slug == override_slug:
                    if prof.verification_status != "VERIFIED":
                        raise LinkedInEnrichmentError(
                            "This LinkedIn profile URL has not passed identity verification yet.",
                            status_code=403,
                        )
                    return prof
            raise LinkedInEnrichmentError(
                "Provided LinkedIn profile URL is not verified for this target. Verify it first via discovery or profile update.",
                status_code=403,
            )

        verified = [p for p in li_profiles if p.verification_status == "VERIFIED"]
        if verified:
            # Validate canonical /in/ structure cleanly
            LinkedInProfileEnrichmentService.validate_linkedin_profile_url(verified[0].profile_url)
            return verified[0]

        if li_profiles:
            raise LinkedInEnrichmentError(
                "Target's LinkedIn profile URL is pending or unverified. Run Auto-Discovery to verify identity before enriching.",
                status_code=403,
            )

        raise LinkedInEnrichmentError(
            "No verified LinkedIn (/in/) profile URL found for this target. Run Auto-Discovery first.",
            status_code=400,
        )

    def fetch_alexandria_profile(
        self,
        profile_url: str,
        http_client: Optional[httpx.Client] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """Calls Firecrawl Alexandria (EnrichLayer people/profile) without logging credentials."""
        clean_url = self.validate_linkedin_profile_url(profile_url)

        if not self.api_key:
            raise LinkedInEnrichmentError(
                "FIRECRAWL_API_KEY is not configured in environment variables.",
                status_code=503,
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "alexandria": {
                "provider": "enrichlayer",
                "capability": "people/profile",
                "options": {
                    "profile_url": clean_url,
                },
            }
        }

        try:
            if http_client is not None:
                resp = http_client.post(ALEXANDRIA_SCRAPE_URL, headers=headers, json=payload, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(ALEXANDRIA_SCRAPE_URL, headers=headers, json=payload)

            if resp.status_code == 401 or resp.status_code == 403:
                raise LinkedInEnrichmentError("Firecrawl API authentication failed.", status_code=502)
            if resp.status_code == 402:
                raise LinkedInEnrichmentError("Insufficient Firecrawl credits to run enrichment.", status_code=402)
            if resp.status_code != 200:
                raise LinkedInEnrichmentError(
                    f"Firecrawl Alexandria API returned HTTP {resp.status_code}.",
                    status_code=502,
                )

            raw_json = resp.json()
            record = _unwrap_alexandria_record(raw_json)
            credits_cost = _extract_credits_cost(raw_json)
            return record, credits_cost

        except LinkedInEnrichmentError:
            raise
        except httpx.TimeoutException:
            logger.warning(f"Timeout calling Firecrawl Alexandria for LinkedIn profile: {clean_url}")
            raise LinkedInEnrichmentError("Timed out waiting for Firecrawl Alexandria response.", status_code=504)
        except httpx.HTTPError as e:
            safe_err = _redact_api_key(str(e))
            logger.warning(f"HTTP error calling Firecrawl Alexandria ({type(e).__name__}): {safe_err}")
            raise LinkedInEnrichmentError(f"Network error contacting Firecrawl Alexandria: {type(e).__name__}", status_code=502)
        except ValueError:
            logger.warning(f"Invalid JSON payload returned by Firecrawl Alexandria for: {clean_url}")
            raise LinkedInEnrichmentError("Invalid JSON response received from Firecrawl Alexandria.", status_code=502)

    @staticmethod
    def normalize_record(record: Dict[str, Any]) -> StructuredLinkedInProfile:
        """Normalizes raw EnrichLayer JSON fields into clean validated Pydantic structures."""
        raw_exps = record.get("experiences") if isinstance(record.get("experiences"), list) else []
        experiences: List[ExperienceItem] = []
        for exp in raw_exps:
            if not isinstance(exp, dict):
                continue
            desc = exp.get("description")
            if isinstance(desc, str) and desc.strip() in ("", "."):
                desc = None
            experiences.append(ExperienceItem(
                company=exp.get("company"),
                title=exp.get("title"),
                location=exp.get("location"),
                start_date=_format_enrichlayer_date(exp.get("starts_at")),
                end_date=_format_enrichlayer_date(exp.get("ends_at")) or "Present",
                is_current=exp.get("ends_at") is None,
                description=desc,
                company_linkedin_profile_url=exp.get("company_linkedin_profile_url"),
                logo_url=exp.get("logo_url"),
            ))

        raw_edus = record.get("education") if isinstance(record.get("education"), list) else []
        education: List[EducationItem] = []
        for edu in raw_edus:
            if not isinstance(edu, dict):
                continue
            education.append(EducationItem(
                school=edu.get("school"),
                degree_name=edu.get("degree_name"),
                field_of_study=edu.get("field_of_study"),
                start_date=_format_enrichlayer_date(edu.get("starts_at")),
                end_date=_format_enrichlayer_date(edu.get("ends_at")),
                description=edu.get("description"),
                school_linkedin_profile_url=edu.get("school_linkedin_profile_url"),
            ))

        raw_projs = record.get("accomplishment_projects") if isinstance(record.get("accomplishment_projects"), list) else []
        projects: List[ProjectItem] = []
        for proj in raw_projs:
            if not isinstance(proj, dict):
                continue
            projects.append(ProjectItem(
                title=proj.get("title"),
                description=proj.get("description"),
                url=proj.get("url"),
                start_date=_format_enrichlayer_date(proj.get("starts_at")),
                end_date=_format_enrichlayer_date(proj.get("ends_at")),
            ))

        raw_acts = record.get("activities") if isinstance(record.get("activities"), list) else []
        activities: List[ActivityItem] = []
        for act in raw_acts[:20]:
            if not isinstance(act, dict):
                continue
            activities.append(ActivityItem(
                title=act.get("title"),
                link=act.get("link"),
                activity_status=act.get("activity_status"),
            ))

        raw_skills = record.get("skills") if isinstance(record.get("skills"), list) else []
        skills = [str(s).strip() for s in raw_skills if s and str(s).strip()]

        raw_certs = record.get("certifications") if isinstance(record.get("certifications"), list) else []
        certifications = [c for c in raw_certs if isinstance(c, dict)]

        location = record.get("location_str")
        if not location:
            parts = [record.get("city"), record.get("state"), record.get("country_full_name")]
            location = ", ".join(p for p in parts if p) or None

        return StructuredLinkedInProfile(
            headline=record.get("headline") or record.get("occupation"),
            occupation=record.get("occupation"),
            location=location,
            profile_pic_url=record.get("profile_pic_url"),
            follower_count=record.get("follower_count") if isinstance(record.get("follower_count"), int) else None,
            connections=record.get("connections") if isinstance(record.get("connections"), int) else None,
            summary=_clean_summary_text(record.get("summary")),
            experiences=experiences,
            education=education,
            projects=projects,
            activities=activities,
            skills=skills,
            certifications=certifications,
        )

    @staticmethod
    def apply_profile_to_person(
        db: Session,
        person: Person,
        structured: StructuredLinkedInProfile,
        status: str = "SUCCESS",
        enriched_at: Optional[datetime] = None,
    ) -> Person:
        """Persists enriched profile fields onto Person without overwriting existing biography."""
        person.headline = structured.headline
        person.occupation = structured.occupation
        person.location = structured.location
        person.profile_pic_url = structured.profile_pic_url
        person.follower_count = structured.follower_count
        person.connections = structured.connections
        person.summary = structured.summary
        person.experiences = [e.model_dump() for e in structured.experiences]
        person.education = [e.model_dump() for e in structured.education]
        person.projects = [p.model_dump() for p in structured.projects]
        person.activities = [a.model_dump() for a in structured.activities]
        person.skills = structured.skills
        person.certifications = structured.certifications
        person.profile_enriched_at = enriched_at or _utc_now()
        person.enrichment_status = status

        db.commit()
        db.refresh(person)
        return person

    @staticmethod
    def build_structured_from_person(person: Person) -> StructuredLinkedInProfile:
        return StructuredLinkedInProfile(
            headline=person.headline,
            occupation=person.occupation,
            location=person.location,
            profile_pic_url=person.profile_pic_url,
            follower_count=person.follower_count,
            connections=person.connections,
            summary=person.summary,
            experiences=[ExperienceItem(**e) for e in (person.experiences or []) if isinstance(e, dict)],
            education=[EducationItem(**e) for e in (person.education or []) if isinstance(e, dict)],
            projects=[ProjectItem(**p) for p in (person.projects or []) if isinstance(p, dict)],
            activities=[ActivityItem(**a) for a in (person.activities or []) if isinstance(a, dict)],
            skills=list(person.skills or []),
            certifications=list(person.certifications or []),
        )

    def enrich_target(
        self,
        db: Session,
        person: Person,
        force: bool = False,
        override_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> Dict[str, Any]:
        """Enriches a verified target person with LinkedIn EnrichLayer data, avoiding duplicate API calls."""
        verified_profile = self.resolve_verified_linkedin_profile(db, person, override_url=override_url)

        # Prevent unnecessary duplicate paid calls when already enriched unless explicitly requested
        if not force and person.enrichment_status == "SUCCESS" and person.profile_enriched_at is not None:
            return {
                "success": True,
                "enrichment_status": "ALREADY_ENRICHED",
                "credits_cost": 0,
                "message": "Profile is already enriched. Pass force=true to refresh from Firecrawl Alexandria.",
                "profile_enriched_at": person.profile_enriched_at,
                "structured_profile": self.build_structured_from_person(person),
                "target_id": person.id,
            }

        try:
            record, credits_cost = self.fetch_alexandria_profile(
                verified_profile.profile_url,
                http_client=http_client,
            )
            structured = self.normalize_record(record)
            updated_person = self.apply_profile_to_person(db, person, structured, status="SUCCESS")
            logger.info(
                f"Enriched LinkedIn profile for {person.name} ({person.id}) via Alexandria EnrichLayer (credits={credits_cost})"
            )
            return {
                "success": True,
                "enrichment_status": "SUCCESS",
                "credits_cost": credits_cost,
                "message": "LinkedIn profile enriched successfully.",
                "profile_enriched_at": updated_person.profile_enriched_at,
                "structured_profile": structured,
                "target_id": updated_person.id,
            }
        except LinkedInEnrichmentError:
            if not person.profile_enriched_at:
                person.enrichment_status = "FAILED"
                db.commit()
            raise

    @classmethod
    def import_from_json_file(
        cls,
        db: Session,
        file_path: Path,
        person_id: Optional[str] = None,
    ) -> Optional[Person]:
        """Safely imports an existing EnrichLayer JSON response file into the matching Person without calling the API."""
        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"Enrichment JSON cache file not found: {path}")
            return None

        try:
            raw_json = json.loads(path.read_text(encoding="utf-8"))
            record = _unwrap_alexandria_record(raw_json)
        except Exception as e:
            logger.error(f"Failed to parse cached enrichment JSON {path}: {e}")
            return None

        # Resolve target dynamically from DB using person_id, public_identifier, or full_name
        person: Optional[Person] = None
        if person_id:
            person = db.query(Person).filter(Person.id == person_id).first()

        pub_id = (record.get("public_identifier") or "").strip().lower()
        if not person and pub_id:
            social = db.query(SocialProfile).filter(
                SocialProfile.platform == "linkedin",
                (SocialProfile.username.ilike(pub_id)) | (SocialProfile.profile_url.ilike(f"%/in/{pub_id}%")),
            ).first()
            if social:
                person = db.query(Person).filter(Person.id == social.person_id).first()

        full_name = (record.get("full_name") or "").strip()
        if not person and full_name:
            matches = db.query(Person).filter(Person.name.ilike(full_name)).all()
            if len(matches) == 1:
                person = matches[0]

        if not person:
            logger.warning(f"No matching target person found in DB for enrichment cache file {path.name}")
            return None

        # Respect existing verification status or attach verified SocialProfile if discovered identifier matches
        if pub_id:
            existing_li = db.query(SocialProfile).filter(
                SocialProfile.person_id == person.id,
                SocialProfile.platform == "linkedin",
            ).first()
            if not existing_li:
                db.add(SocialProfile(
                    person_id=person.id,
                    platform="linkedin",
                    username=pub_id,
                    profile_url=f"https://www.linkedin.com/in/{pub_id}",
                    verification_status="VERIFIED",
                ))
                db.flush()

        structured = cls.normalize_record(record)
        meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
        enriched_dt = _utc_now()
        if meta.get("last_updated"):
            try:
                enriched_dt = datetime.fromisoformat(str(meta["last_updated"]).replace("Z", "+00:00"))
            except ValueError:
                pass

        updated = cls.apply_profile_to_person(db, person, structured, status="SUCCESS", enriched_at=enriched_dt)
        logger.info(f"Imported cached EnrichLayer profile from {path.name} into target {updated.name} ({updated.id})")
        return updated


def main():
    import argparse
    from backend.database.connection import SessionLocal, init_db

    parser = argparse.ArgumentParser(description="Import cached EnrichLayer JSON files into the database.")
    parser.add_argument("--file", required=True, help="Path to cached EnrichLayer response JSON file.")
    parser.add_argument("--person-id", required=False, default=None, help="Optional explicit Person ID.")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        person = LinkedInProfileEnrichmentService.import_from_json_file(
            db,
            Path(args.file),
            person_id=args.person_id,
        )
        if person:
            print(f"Imported LinkedIn profile for {person.name} ({person.id}) with {len(person.experiences or [])} experiences and {len(person.education or [])} education items.")
        else:
            print("No matching target person found or invalid JSON file.")
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
