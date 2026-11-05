from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import Person, ResearchJob, Appearance, Source
from backend.modules.analysis.report_generator import ReportGenerator


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

