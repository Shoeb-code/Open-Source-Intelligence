import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.database.models import Appearance, AppearanceAnalysis, SocialProfile, Source
from backend.main import app
from backend.modules.intelligence.prompts import PROMPT_VERSION
from backend.modules.intelligence.summarizer import InsightsSummarizer
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def _seed_rich_person():
    res = client.post(
        "/api/v1/persons",
        json={
            "name": "Aditi Sharma",
            "profession": "Founder & CEO at FinBridge AI",
            "biography": "Fintech entrepreneur building SME credit automation.",
            "linkedin_url": "https://www.linkedin.com/in/aditi-sharma-finbridge",
        },
    )
    assert res.status_code == 201
    person_id = res.json()["id"]

    db = TestingSessionLocal()
    try:
        from backend.database.models import Person

        person = db.query(Person).filter(Person.id == person_id).first()
        person.headline = "Founder & CEO at FinBridge AI | Building automated SME underwriting"
        person.occupation = "CEO at FinBridge AI"
        person.location = "Mumbai, India"
        person.follower_count = 8500
        person.connections = 500
        person.summary = "Built FinBridge AI after 8 years leading credit analytics."
        person.experiences = [
            {
                "company": "FinBridge AI",
                "title": "Founder & CEO",
                "start_date": "Jan 2022",
                "end_date": "Present",
                "is_current": True,
                "description": "Automated SME credit scoring platform",
            }
        ]
        person.education = [
            {"school": "IIT Bombay", "degree_name": "B.Tech", "field_of_study": "Computer Science"}
        ]
        person.projects = [
            {"title": "InstantGST Score", "description": "Real-time GST underwriting engine"}
        ]
        person.skills = ["Machine Learning", "Credit Underwriting", "Fintech"]
        person.enrichment_status = "SUCCESS"

        sp = db.query(SocialProfile).filter(SocialProfile.person_id == person_id).first()
        sp.verification_status = "VERIFIED"

        # Verified Podcast appearance
        app1 = Appearance(
            person_id=person_id,
            appearance_type="PODCAST",
            title="Aditi Sharma on Scaling SME Underwriting with AI",
            description="Podcast discussing MSME credit underwriting challenges.",
            publisher="Fintech Insider India",
            published_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            identity_status="VERIFIED",
            confidence_score=0.92,
        )
        db.add(app1)
        db.flush()
        db.add(
            Source(
                appearance_id=app1.id,
                source_url="https://youtube.com/watch?v=fintech1234",
                canonical_url="https://youtube.com/watch?v=fintech1234",
                source_type="YOUTUBE",
                extracted_content="Aditi Sharma explained how GST APIs reduce SME loan turnaround from 14 days to 2 hours.",
                extraction_status="SUCCESS",
            )
        )
        db.add(
            AppearanceAnalysis(
                appearance_id=app1.id,
                summary="Discusses AI-driven SME underwriting and GST data pipelines.",
                topics=["SME Lending", "Artificial Intelligence", "GST APIs"],
                key_points=["Cut underwriting time from 14 days to 2 hours", "Expanding MSME lending across Tier 2 India"],
                person_role="GUEST",
                evidence=["GST APIs cut loan turnaround times."],
                model_name="llama-3.3-70b-versatile",
            )
        )

        # Rejected appearance from another person MUST be excluded
        app_rej = Appearance(
            person_id=person_id,
            appearance_type="INTERVIEW",
            title="Unrelated Speaker Interview",
            publisher="Random Blog",
            identity_status="REJECTED",
            confidence_score=0.1,
        )
        db.add(app_rej)
        db.flush()
        db.add(
            Source(
                appearance_id=app_rej.id,
                source_url="https://example.com/unrelated-speaker",
                canonical_url="https://example.com/unrelated-speaker",
                source_type="WEBPAGE",
                extracted_content="Should never be analyzed or cited.",
                extraction_status="SUCCESS",
            )
        )

        db.commit()
    finally:
        db.close()

    return person_id


def test_generate_and_retrieve_insights_with_llm_citation_grounding(monkeypatch):
    person_id = _seed_rich_person()

    fake_llm_json = {
        "executive_overview": "Aditi Sharma leads FinBridge AI and speaks publicly on AI underwriting.",
        "professional_insights": {
            "summary": "Founder with CS background leading FinBridge AI.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "CEO at FinBridge AI",
                    "detail": "Founded FinBridge AI in Jan 2022 following an IIT Bombay CS degree.",
                    "sub_category": "Current Role",
                    "claim_type": "VERIFIED_FACT",
                    "confidence": "HIGH",
                    "source_ids": ["S1"],
                }
            ],
        },
        "interest_insights": {
            "summary": "Passionate about fintech credit infrastructure.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "MSME Credit & AI Automation",
                    "detail": "Frequently discusses SME Lending and GST data pipelines.",
                    "sub_category": "Technology Interests",
                    "claim_type": "VERIFIED_FACT",
                    "confidence": "HIGH",
                    "source_ids": ["S2"],
                }
            ],
        },
        "knowledge_and_expertise": {
            "summary": "Demonstrated expertise in ML credit scoring.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "GST Underwriting Systems",
                    "detail": "Demonstrated production knowledge lowering loan turnaround from 14 days to 2 hours.",
                    "sub_category": "Technical Expertise",
                    "claim_type": "VERIFIED_FACT",
                    "confidence": "HIGH",
                    "source_ids": ["S2"],
                }
            ],
        },
        "company_insights": {
            "summary": "FinBridge AI offers InstantGST Score.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "InstantGST Score Product",
                    "detail": "Automated SME credit scoring product using real-time GST data.",
                    "sub_category": "Products and Services",
                    "claim_type": "VERIFIED_FACT",
                    "confidence": "HIGH",
                    "source_ids": ["S1", "S2"],
                }
            ],
        },
        "recent_activities": {
            "summary": "Featured on Fintech Insider India podcast.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "Fintech Insider India Appearance",
                    "detail": "Guest podcast covering MSME lending innovation.",
                    "sub_category": "Podcast",
                    "claim_type": "VERIFIED_FACT",
                    "confidence": "HIGH",
                    "source_ids": ["S2"],
                }
            ],
        },
        "business_insights": {
            "summary": "Targeting Tier 2 Indian MSME expansion.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "Tier-2 Credit Distribution Opportunity",
                    "detail": "Likely needs enriched B2B entity verification and GST merchant lead lists.",
                    "sub_category": "Potential Opportunities",
                    "claim_type": "AI_HYPOTHESIS",
                    "confidence": "MEDIUM",
                    "source_ids": ["S2"],
                }
            ],
        },
        "key_takeaways": {
            "summary": "High-fit AI fintech prospect for automated data enrichment.",
            "insufficient_evidence": False,
            "items": [
                {
                    "title": "Data API Partnership Pitch",
                    "detail": "Leadzen.ai can propose real-time SME director & company risk feeds.",
                    "sub_category": "Project Idea",
                    "claim_type": "AI_HYPOTHESIS",
                    "confidence": "MEDIUM",
                    "source_ids": ["S1", "S2"],
                }
            ],
        },
    }

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_llm_json)))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    def fake_init(self):
        self.client = mock_client
        self.model = "mock-groq-70b"

    monkeypatch.setattr(InsightsSummarizer, "__init__", fake_init)

    # Initial GET should have empty history
    get_empty = client.get(f"/api/v1/persons/{person_id}/insights")
    assert get_empty.status_code == 200
    assert get_empty.json()["latest_report"] is None
    assert get_empty.json()["history"] == []

    # Generate insights #1
    gen_res = client.post(
        f"/api/v1/persons/{person_id}/generate-insights",
        json={"focus_notes": "Evaluate B2B fintech data partnership"},
    )
    assert gen_res.status_code == 201
    created = gen_res.json()
    assert created["model_name"] == "mock-groq-70b"
    assert created["prompt_version"] == PROMPT_VERSION
    assert created["source_count"] == 2  # LinkedIn profile + 1 verified podcast (REJECTED excluded!)
    assert created["generation_time_seconds"] >= 0.0

    rep = created["report"]
    # Verify rejected item URL never slipped into prompt or citations
    prompt_called = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "unrelated-speaker" not in prompt_called

    # Verify hydration of real DB URLs and publication dates
    s2_cits = rep["interest_insights"]["items"][0]["supporting_sources"]
    assert len(s2_cits) == 1
    assert s2_cits[0]["url"] == "https://youtube.com/watch?v=fintech1234"
    assert s2_cits[0]["published_at"] == "2026-09-15"

    # Verify fact vs hypothesis distinction
    assert rep["professional_insights"]["items"][0]["claim_type"] == "VERIFIED_FACT"
    assert rep["business_insights"]["items"][0]["claim_type"] == "AI_HYPOTHESIS"

    # Generate insights #2 and confirm report history tracks both
    gen_res2 = client.post(f"/api/v1/persons/{person_id}/generate-insights", json={})
    assert gen_res2.status_code == 201
    second_id = gen_res2.json()["id"]

    hist_res = client.get(f"/api/v1/persons/{person_id}/insights")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["latest_report"]["id"] == second_id
    assert len(hist_data["history"]) == 2


def test_deterministic_fallback_and_insufficient_evidence(monkeypatch):
    # Case A: Rich person with LLM disabled (extractive-fallback-v1)
    rich_id = _seed_rich_person()

    def no_llm_init(self):
        self.client = None
        self.model = "extractive-fallback-v1"

    monkeypatch.setattr(InsightsSummarizer, "__init__", no_llm_init)

    res_rich = client.post(f"/api/v1/persons/{rich_id}/generate-insights", json={})
    assert res_rich.status_code == 201
    body = res_rich.json()
    assert body["model_name"] == "extractive-fallback-v1"
    rep = body["report"]
    assert len(rep["professional_insights"]["items"]) >= 2
    assert len(rep["interest_insights"]["items"]) >= 1
    assert len(rep["company_insights"]["items"]) >= 1
    assert len(rep["recent_activities"]["items"]) >= 1
    assert len(rep["business_insights"]["items"]) >= 1
    assert len(rep["key_takeaways"]["items"]) >= 1

    # Case B: Sparse person with zero appearances and no enrichment
    sparse_res = client.post(
        "/api/v1/persons",
        json={"name": "Sparse Subject", "profession": "Consultant"},
    )
    assert sparse_res.status_code == 201
    sparse_id = sparse_res.json()["id"]

    res_sparse = client.post(f"/api/v1/persons/{sparse_id}/generate-insights", json={})
    assert res_sparse.status_code == 201
    s_rep = res_sparse.json()["report"]
    assert s_rep["interest_insights"]["insufficient_evidence"] is True
    assert s_rep["company_insights"]["insufficient_evidence"] is True
    assert s_rep["recent_activities"]["insufficient_evidence"] is True
    assert s_rep["key_takeaways"]["insufficient_evidence"] is True
    assert s_rep["company_insights"]["insufficient_evidence_note"] is not None


def test_insights_404_on_missing_person():
    assert client.get("/api/v1/persons/does-not-exist/insights").status_code == 404
    assert client.post("/api/v1/persons/does-not-exist/generate-insights", json={}).status_code == 404

