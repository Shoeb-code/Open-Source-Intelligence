import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal, init_db
from app.database.models import Person

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_register_person_with_profiles():
    payload = {
        "name": "Jane Doe",
        "profession": "AI Research Scientist at DeepTech Labs",
        "biography": "Researcher focusing on multi-agent architectures and LLM reasoning.",
        "linkedin_url": "https://www.linkedin.com/in/janedoe/",
        "youtube_url": "https://www.youtube.com/@janedoe_ai",
        "instagram_url": "https://www.instagram.com/janedoe_official/"
    }
    response = client.post("/api/v1/persons", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["profession"] == "AI Research Scientist at DeepTech Labs"
    assert len(data["social_profiles"]) == 3

    person_id = data["id"]
    # Retrieve details
    get_res = client.get(f"/api/v1/persons/{person_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == person_id

    # Retrieve IdentityContext
    ctx_res = client.get(f"/api/v1/persons/{person_id}/context")
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()
    assert ctx_data["name"] == "Jane Doe"
    assert "DeepTech Labs" in ctx_data["organizations"]
    assert "janedoe" in ctx_data["known_usernames"] or "janedoe_ai" in ctx_data["known_usernames"]

