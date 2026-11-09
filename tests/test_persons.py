from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


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


def test_update_person_and_social_profiles():
    # 1. Register a person
    payload = {
        "name": "Target Account Test",
        "profession": "Finance Director",
        "biography": "Initial bio."
    }
    create_res = client.post("/api/v1/persons", json=payload)
    assert create_res.status_code == 201
    person_id = create_res.json()["id"]

    # 2. Update their biography and connect LinkedIn + Instagram URLs
    update_payload = {
        "profession": "Managing Director at Global Wealth Inc",
        "biography": "Updated comprehensive background dossier for the account.",
        "linkedin_url": "https://www.linkedin.com/in/test-finance-leader/",
        "instagram_url": "https://www.instagram.com/test_finance_official/"
    }
    put_res = client.put(f"/api/v1/persons/{person_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()

    assert updated_data["profession"] == "Managing Director at Global Wealth Inc"
    assert updated_data["biography"] == "Updated comprehensive background dossier for the account."
    assert len(updated_data["social_profiles"]) == 2

    # Check platforms
    platforms = {p["platform"]: p["profile_url"] for p in updated_data["social_profiles"]}
    assert "linkedin" in platforms
    assert "instagram" in platforms
    assert "test-finance-leader" in platforms["linkedin"]
    assert "test_finance_official" in platforms["instagram"]

    # 3. Clean up
    del_res = client.delete(f"/api/v1/persons/{person_id}")
    assert del_res.status_code == 204
