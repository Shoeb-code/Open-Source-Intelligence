from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.modules.persons.schemas import PersonCreate, PersonResponse, IdentityContext
from app.modules.persons import service

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def register_person(payload: PersonCreate, db: Session = Depends(get_db)):
    """Registers a person and initializes their public identity reference."""
    return service.create_person(db, payload)


@router.get("", response_model=List[PersonResponse])
def get_all_persons(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Lists registered persons."""
    return service.list_persons(db, skip=skip, limit=limit)


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: str, db: Session = Depends(get_db)):
    """Retrieves identity details for a given person ID."""
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get("/{person_id}/context", response_model=IdentityContext)
def get_person_identity_context(person_id: str, db: Session = Depends(get_db)):
    """Generates the structured identity context used by discovery and verification engines."""
    context = service.build_identity_context(db, person_id)
    if not context:
        raise HTTPException(status_code=404, detail="Person not found")
    return context

