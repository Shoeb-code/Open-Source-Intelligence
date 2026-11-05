from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal, init_db
from backend.database.models import Person, Appearance, Source, AppearanceAnalysis, ResearchJob
from backend.workers.tasks import execute_research_pipeline

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_end_to_end_pipeline_and_report():
    # 1. Register Person
    person_res = client.post("/api/v1/persons", json={
        "name": "Sarah Connor",
        "profession": "Lead Systems Engineer at CyberTech",
        "biography": "Distributed systems engineer and keynote speaker.",
        "linkedin_url": "https://linkedin.com/in/sarah-connor",
        "youtube_url": "https://youtube.com/@sarahconnor_dev"
    })
    assert person_res.status_code == 201
    person_data = person_res.json()
    person_id = person_data["id"]

    # 2. Pre-populate an appearance and source to verify reporting APIs
    db = SessionLocal()
    app_entry = Appearance(
        person_id=person_id,
        appearance_type="INTERVIEW",
        title="Sarah Connor on Distributed Systems at CyberTech",
        description="Interview covering edge resilience and consensus protocols.",
        publisher="Cloud Engineering Podcast",
        published_at=datetime.now(timezone.utc),
        identity_status="VERIFIED",
        confidence_score=0.95
    )
    db.add(app_entry)
    db.flush()

    src_entry = Source(
        appearance_id=app_entry.id,
        source_url="https://youtube.com/watch?v=mock1234567",
        canonical_url="https://youtube.com/watch?v=mock1234567",
        source_type="YOUTUBE",
        extracted_content="Sarah Connor discussed resilient node consensus at CyberTech.",
        extraction_status="SUCCESS"
    )
    db.add(src_entry)

    analysis_entry = AppearanceAnalysis(
        appearance_id=app_entry.id,
        summary="Sarah Connor describes building resilient consensus networks.",
        topics=["Consensus Protocols", "Distributed Systems", "Edge Computing"],
        key_points=["Resilience under partition", "Node synchronization"],
        person_role="GUEST",
        evidence=["Sarah Connor said: Consensus is non-negotiable."],
        model_name="gpt-4o-mini"
    )
    db.add(analysis_entry)
    db.commit()
    app_entry_id = app_entry.id
    db.close()

    # 3. Retrieve appearances
    appearances_res = client.get(f"/api/v1/persons/{person_id}/appearances")
    assert appearances_res.status_code == 200
    appearances = appearances_res.json()
    assert len(appearances) == 1
    assert appearances[0]["title"] == "Sarah Connor on Distributed Systems at CyberTech"
    assert appearances[0]["identity_status"] == "VERIFIED"
    assert appearances[0]["analysis"]["person_role"] == "GUEST"

    # 4. Retrieve timeline
    timeline_res = client.get(f"/api/v1/persons/{person_id}/timeline")
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert len(timeline) == 1
    assert timeline[0]["appearance_id"] == app_entry_id

    # 5. Retrieve sources
    sources_res = client.get(f"/api/v1/persons/{person_id}/sources")
    assert sources_res.status_code == 200
    sources = sources_res.json()
    assert len(sources) == 1
    assert sources[0]["source_type"] == "YOUTUBE"

    # 6. Retrieve Consolidated Final Report
    report_res = client.get(f"/api/v1/persons/{person_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert "Sarah Connor" in report["executive_summary"]
    assert report["statistics"]["verified_appearances"] == 1
    assert len(report["recurring_topics"]) > 0
    assert len(report["important_statements"]) > 0



def test_direct_url_analysis_endpoint():
    # 1. Register Person
    p_res = client.post("/api/v1/persons", json={
        "name": "Alan Turing",
        "profession": "Mathematician & Computer Scientist",
        "biography": "Pioneer of theoretical computer science and artificial intelligence."
    })
    assert p_res.status_code == 201
    person_id = p_res.json()["id"]

    # 2. Upload / Analyze direct URL
    upload_res = client.post(f"/api/v1/persons/{person_id}/analyze-url", json={
        "url": "https://example.com/interviews/alan-turing-legacy",
        "source_type": "NEWS",
        "title": "Alan Turing on Computational Intelligence"
    })
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["title"] == "Alan Turing on Computational Intelligence"
    assert data["person_id"] == person_id
    assert len(data["sources"]) == 1
    assert data["analysis"] is not None
