from urllib.parse import urlparse
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.database.models import Person, SocialProfile
from backend.modules.persons.schemas import PersonCreate, PersonUpdate, IdentityContext
from backend.utils.url_validator import canonicalize_url, detect_platform
from backend.utils.logger import logger


def _extract_username_from_url(url: str, platform: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return None
        parts = path.split("/")
        if platform == "linkedin" and "in" in parts:
            idx = parts.index("in")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        elif platform == "youtube" and parts[0].startswith("@"):
            return parts[0].lstrip("@")
        elif platform == "instagram":
            return parts[0]
        return parts[-1]
    except Exception:
        return None


def create_person(db: Session, payload: PersonCreate) -> Person:
    """Creates a new person and associates provided social profiles."""
    person = Person(
        name=payload.name.strip(),
        profession=payload.profession.strip() if payload.profession else None,
        biography=payload.biography.strip() if payload.biography else None
    )
    db.add(person)
    db.flush()

    # Collect profiles
    profiles_to_create = []
    
    if payload.linkedin_url:
        clean_url = canonicalize_url(payload.linkedin_url)
        profiles_to_create.append(SocialProfile(
            person_id=person.id,
            platform="linkedin",
            username=_extract_username_from_url(clean_url, "linkedin"),
            profile_url=clean_url
        ))
        
    if payload.instagram_url:
        clean_url = canonicalize_url(payload.instagram_url)
        profiles_to_create.append(SocialProfile(
            person_id=person.id,
            platform="instagram",
            username=_extract_username_from_url(clean_url, "instagram"),
            profile_url=clean_url
        ))
        
    if payload.youtube_url:
        clean_url = canonicalize_url(payload.youtube_url)
        profiles_to_create.append(SocialProfile(
            person_id=person.id,
            platform="youtube",
            username=_extract_username_from_url(clean_url, "youtube"),
            profile_url=clean_url
        ))

    if payload.additional_profiles:
        for p in payload.additional_profiles:
            clean_url = canonicalize_url(p.profile_url)
            platform = p.platform or detect_platform(clean_url)
            username = p.username or _extract_username_from_url(clean_url, platform)
            profiles_to_create.append(SocialProfile(
                person_id=person.id,
                platform=platform,
                username=username,
                profile_url=clean_url
            ))

    for prof in profiles_to_create:
        db.add(prof)

    db.commit()
    db.refresh(person)
    logger.info(f"Registered new person: {person.name} ({person.id}) with {len(profiles_to_create)} profile(s)")
    return person


def get_person_by_id(db: Session, person_id: str) -> Optional[Person]:
    return db.query(Person).filter(Person.id == person_id).first()


def list_persons(db: Session, skip: int = 0, limit: int = 20) -> List[Person]:
    return db.query(Person).offset(skip).limit(limit).all()


def build_identity_context(db: Session, person_id: str) -> Optional[IdentityContext]:
    """Generates structured IdentityContext for discovery and verification."""
    person = get_person_by_id(db, person_id)
    if not person:
        return None

    usernames = []
    profile_urls = {}
    for prof in person.social_profiles:
        if prof.username and prof.username not in usernames:
            usernames.append(prof.username)
        profile_urls[prof.platform] = prof.profile_url

    # Infer organizations from profession and biography
    organizations = []
    if person.profession:
        prof = person.profession.strip()
        matched_delimiter = False
        for delim in [" at ", " @ ", " of ", ", ", " - ", " | "]:
            if delim in prof.lower():
                idx = prof.lower().find(delim)
                org = prof[idx + len(delim):].strip()
                if org and org not in organizations:
                    organizations.append(org)
                matched_delimiter = True
                break

        # If no delimiter was used, check if the string directly names a company/firm
        if not matched_delimiter:
            company_indicators = [
                "company", "amc", "group", "ltd", "limited", "inc", "corp",
                "fund", "funds", "capital", "wealth", "ventures", "pvt",
                "technologies", "tech", "partners", "bank", "financial", "firm"
            ]
            if any(term in prof.lower() for term in company_indicators) and prof not in organizations:
                organizations.append(prof)

    # Check biography for prominent organizations
    if person.biography:
        bio = person.biography
        for delim in [" of ", " at ", " @ ", " co-founder of ", " founder of "]:
            if delim in bio.lower():
                idx = bio.lower().find(delim)
                snippet = bio[idx + len(delim):].split(".")[0].split(",")[0].strip()
                if 3 < len(snippet) < 60 and snippet not in organizations:
                    organizations.append(snippet)

    return IdentityContext(
        person_id=person.id,
        name=person.name,
        profession=person.profession,
        organizations=organizations,
        known_usernames=usernames,
        profile_urls=profile_urls
    )


def update_person(db: Session, person_id: str, payload: PersonUpdate) -> Optional[Person]:
    """Updates an existing person's details and social profile URLs."""
    person = get_person_by_id(db, person_id)
    if not person:
        return None

    if payload.name is not None and payload.name.strip():
        person.name = payload.name.strip()
    if payload.profession is not None:
        person.profession = payload.profession.strip() if payload.profession else None
    if payload.biography is not None:
        person.biography = payload.biography.strip() if payload.biography else None

    def _upsert_platform_profile(platform: str, url_val: Optional[str]):
        if url_val is None:
            return
        url_clean = canonicalize_url(url_val.strip()) if url_val.strip() else ""
        existing = db.query(SocialProfile).filter(
            SocialProfile.person_id == person.id,
            SocialProfile.platform == platform
        ).first()

        if url_clean:
            username = _extract_username_from_url(url_clean, platform)
            if existing:
                existing.profile_url = url_clean
                existing.username = username
                existing.verification_status = "VERIFIED"
            else:
                db.add(SocialProfile(
                    person_id=person.id,
                    platform=platform,
                    username=username,
                    profile_url=url_clean,
                    verification_status="VERIFIED"
                ))
        elif existing and not url_val.strip():
            db.delete(existing)

    _upsert_platform_profile("linkedin", payload.linkedin_url)
    _upsert_platform_profile("instagram", payload.instagram_url)
    _upsert_platform_profile("youtube", payload.youtube_url)

    if payload.additional_profiles is not None:
        for p in payload.additional_profiles:
            clean_url = canonicalize_url(p.profile_url)
            platform = p.platform or detect_platform(clean_url)
            _upsert_platform_profile(platform, clean_url)

    db.commit()
    db.refresh(person)
    logger.info(f"Updated person details for {person.name} ({person.id})")
    return person


def delete_person(db: Session, person_id: str) -> bool:
    person = get_person_by_id(db, person_id)
    if not person:
        return False
    db.delete(person)
    db.commit()
    logger.info(f"Deleted person: {person_id}")
    return True
