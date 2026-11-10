import json
from pathlib import Path
from unittest.mock import MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database.models import SocialProfile
from backend.main import app
from backend.modules.enrichment.linkedin_profile import (
    LinkedInEnrichmentError,
    LinkedInProfileEnrichmentService,
)
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def _create_verified_target(
    name: str = "Jane Doe",
    linkedin_url: str = "https://www.linkedin.com/in/janedoe",
    biography: str = "Original curated executive bio.",
    verification_status: str = "VERIFIED",
):
    res = client.post(
        "/api/v1/persons",
        json={
            "name": name,
            "profession": "Founder & CIO",
            "biography": biography,
            "linkedin_url": linkedin_url,
        },
    )
    assert res.status_code == 201
    person_id = res.json()["id"]

    if verification_status != "PENDING":
        db = TestingSessionLocal()
        try:
            sp = db.query(SocialProfile).filter(
                SocialProfile.person_id == person_id,
                SocialProfile.platform == "linkedin",
            ).first()
            if sp:
                sp.verification_status = verification_status
                db.commit()
        finally:
            db.close()

    return person_id


def _load_sample_payload() -> dict:
    sample_path = Path(__file__).resolve().parents[1] / "madhu_enrichlayer_response.json"
    if sample_path.is_file():
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        # Clone and sanitize identifier for isolated synthetic target test
        return data
    return {
        "success": True,
        "data": {
            "alexandria": [
                {
                    "provider": "enrichlayer",
                    "capability": "people/profile",
                    "creditsCost": 10,
                    "data": {
                        "public_identifier": "janedoe",
                        "full_name": "Jane Doe",
                        "headline": "Founder at Example Ventures",
                        "occupation": "Board Member",
                        "location_str": "New York, United States",
                        "follower_count": 2500,
                        "connections": 500,
                        "summary": "Building financial platforms.<br><br>Focused on inclusion.",
                        "experiences": [
                            {
                                "company": "Example Ventures",
                                "title": "Founder",
                                "location": "New York",
                                "starts_at": {"day": 1, "month": 5, "year": 2021},
                                "ends_at": None,
                                "description": "Leading operations",
                            }
                        ],
                        "education": [
                            {
                                "school": "MIT",
                                "degree_name": "B.S.",
                                "field_of_study": "Computer Science",
                                "starts_at": None,
                                "ends_at": None,
                            }
                        ],
                        "accomplishment_projects": [
                            {"title": "Open Finance", "description": "Public analytics tool", "url": None}
                        ],
                        "activities": [],
                        "skills": [],
                        "certifications": [],
                    },
                }
            ],
            "creditsCost": 10,
        },
    }


def test_validate_linkedin_profile_url_rules():
    assert (
        LinkedInProfileEnrichmentService.validate_linkedin_profile_url(
            "https://in.linkedin.com/in/madhu-lunawat-1a3b719/?originalSubdomain=in"
        )
        == "https://www.linkedin.com/in/madhu-lunawat-1a3b719"
    )

    for bad_url in [
        "https://www.linkedin.com/posts/someone_post-123",
        "https://www.linkedin.com/company/the-wealth-company",
        "https://www.linkedin.com/pulse/some-article",
        "https://example.com/in/janedoe",
        "not-a-url",
    ]:
        with pytest.raises(LinkedInEnrichmentError):
            LinkedInProfileEnrichmentService.validate_linkedin_profile_url(bad_url)


def test_enrich_endpoint_persistence_dedup_and_force_refresh(monkeypatch):
    person_id = _create_verified_target(
        name="Elena Vance",
        linkedin_url="https://www.linkedin.com/in/elena-vance",
        biography="Custom analyst-written bio that must never be overwritten.",
        verification_status="VERIFIED",
    )

    sample = _load_sample_payload()
    call_counter = {"count": 0}

    def fake_fetch(self, profile_url, http_client=None):
        call_counter["count"] += 1
        assert profile_url == "https://www.linkedin.com/in/elena-vance"
        inner = sample["data"]["alexandria"][0]["data"]
        record = json.loads(json.dumps(inner))
        record["public_identifier"] = "elena-vance"
        record["full_name"] = "Elena Vance"
        return record, 10

    monkeypatch.setattr(LinkedInProfileEnrichmentService, "fetch_alexandria_profile", fake_fetch)

    # 1. Initial enrichment succeeds and stores structured fields without touching biography
    res = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["enrichment_status"] == "SUCCESS"
    assert body["credits_cost"] == 10
    assert body["profile_enriched_at"] is not None
    assert len(body["structured_profile"]["experiences"]) >= 1
    assert len(body["structured_profile"]["education"]) >= 1
    assert call_counter["count"] == 1

    # Verify DB persistence via Person API
    person_res = client.get(f"/api/v1/persons/{person_id}")
    assert person_res.status_code == 200
    p_data = person_res.json()
    assert p_data["biography"] == "Custom analyst-written bio that must never be overwritten."
    assert p_data["headline"] is not None
    assert p_data["summary"] is not None
    assert "<br>" not in p_data["summary"]
    assert p_data["enrichment_status"] == "SUCCESS"
    assert len(p_data["experiences"]) >= 1
    assert len(p_data["education"]) >= 1

    # 2. Repeated click (force=False) skips external API call cleanly
    res_dup = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={"force": False})
    assert res_dup.status_code == 200
    dup_body = res_dup.json()
    assert dup_body["enrichment_status"] == "ALREADY_ENRICHED"
    assert dup_body["credits_cost"] == 0
    assert call_counter["count"] == 1

    # 3. Explicit re-enrichment (force=True) invokes API again
    res_force = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={"force": True})
    assert res_force.status_code == 200
    assert res_force.json()["enrichment_status"] == "SUCCESS"
    assert res_force.json()["credits_cost"] == 10
    assert call_counter["count"] == 2


def test_handles_empty_optional_fields_gracefully():
    record = {
        "public_identifier": "minimal-user",
        "full_name": "Minimal User",
        "headline": None,
        "occupation": None,
        "location_str": None,
        "summary": None,
        "experiences": None,
        "education": [],
        "accomplishment_projects": [],
        "activities": None,
        "skills": [],
        "certifications": None,
    }
    structured = LinkedInProfileEnrichmentService.normalize_record(record)
    assert structured.experiences == []
    assert structured.education == []
    assert structured.projects == []
    assert structured.skills == []
    assert structured.certifications == []
    assert structured.summary is None


def test_blocks_unverified_profile_and_enforces_auth_token(monkeypatch):
    # Pending profile must be blocked until verified
    pending_id = _create_verified_target(
        name="Pending Target",
        linkedin_url="https://www.linkedin.com/in/pending-target",
        verification_status="PENDING",
    )
    res_pending = client.post(f"/api/v1/linkedin/enrich/{pending_id}", json={})
    assert res_pending.status_code == 403

    # Verify auth token enforcement when API_AUTH_TOKEN is configured
    verified_id = _create_verified_target(
        name="Auth Target",
        linkedin_url="https://www.linkedin.com/in/auth-target",
        verification_status="VERIFIED",
    )
    monkeypatch.setattr(settings, "API_AUTH_TOKEN", "super-secret-token")

    res_no_auth = client.post(f"/api/v1/linkedin/enrich/{verified_id}", json={})
    assert res_no_auth.status_code == 401

    res_bad_auth = client.post(
        f"/api/v1/linkedin/enrich/{verified_id}",
        headers={"Authorization": "Bearer wrong-token"},
        json={},
    )
    assert res_bad_auth.status_code == 403

    # Also block unauthorized target scope header
    res_bad_scope = client.post(
        f"/api/v1/linkedin/enrich/{verified_id}",
        headers={
            "Authorization": "Bearer super-secret-token",
            "X-Authorized-Targets": "other-target-id",
        },
        json={},
    )
    assert res_bad_scope.status_code == 403


def test_import_cached_json_file_without_api_call(tmp_path):
    target_id = _create_verified_target(
        name="Cached Import Subject",
        linkedin_url="https://www.linkedin.com/in/cached-subject-123",
        biography="Preserved original biography.",
        verification_status="VERIFIED",
    )

    cache_file = tmp_path / "cached_enrichlayer_response.json"
    cache_file.write_text(
        json.dumps(
            {
                "public_identifier": "cached-subject-123",
                "full_name": "Cached Import Subject",
                "headline": "Chief Architect",
                "location_str": "Bengaluru, India",
                "follower_count": 4200,
                "connections": 500,
                "summary": "Architecting distributed systems.",
                "experiences": [
                    {
                        "company": "CoreTech",
                        "title": "Chief Architect",
                        "starts_at": {"day": 1, "month": 1, "year": 2020},
                        "ends_at": None,
                    }
                ],
                "education": [{"school": "IISc", "degree_name": "M.Tech"}],
                "accomplishment_projects": [],
                "skills": ["Distributed Systems"],
                "certifications": [],
            }
        ),
        encoding="utf-8",
    )

    db = TestingSessionLocal()
    try:
        updated = LinkedInProfileEnrichmentService.import_from_json_file(db, cache_file)
        assert updated is not None
        assert updated.id == target_id
        assert updated.biography == "Preserved original biography."
        assert updated.headline == "Chief Architect"
        assert len(updated.experiences) == 1
        assert updated.experiences[0]["is_current"] is True
        assert updated.education[0]["school"] == "IISc"
        assert updated.skills == ["Distributed Systems"]
    finally:
        db.close()


def test_error_handling_never_exposes_api_key(monkeypatch):
    secret = "fc-secret-key-should-not-leak-999"
    service = LinkedInProfileEnrichmentService(api_key=secret, timeout=2.0)

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.TimeoutException(f"Timeout contacting {secret}")

    with pytest.raises(LinkedInEnrichmentError) as exc_info:
        service.fetch_alexandria_profile(
            "https://www.linkedin.com/in/janedoe",
            http_client=mock_client,
        )
    assert exc_info.value.status_code == 504
    assert secret not in exc_info.value.message

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_client_401 = MagicMock(spec=httpx.Client)
    mock_client_401.post.return_value = mock_resp

    with pytest.raises(LinkedInEnrichmentError) as exc_401:
        service.fetch_alexandria_profile(
            "https://www.linkedin.com/in/janedoe",
            http_client=mock_client_401,
        )
    assert exc_401.value.status_code == 502
    assert secret not in exc_401.value.message


def test_import_cache_endpoint_path_traversal_and_http_call(monkeypatch):
    # Path traversal must be rejected
    res_bad = client.post("/api/v1/linkedin/import-cache", json={"file_path": "../../etc/passwd"})
    assert res_bad.status_code == 400

    # Mock fetch on full HTTP roundtrip (verifying request payload sent to Firecrawl v2)
    person_id = _create_verified_target(
        name="HTTP Integration Subject",
        linkedin_url="https://www.linkedin.com/in/http-subject",
        verification_status="VERIFIED",
    )

    captured = {}

    class MockTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "alexandria": [
                            {
                                "provider": "enrichlayer",
                                "capability": "people/profile",
                                "creditsCost": 10,
                                "data": {
                                    "public_identifier": "http-subject",
                                    "full_name": "HTTP Integration Subject",
                                    "headline": "VP Engineering",
                                    "experiences": [],
                                    "education": [],
                                    "skills": ["Python", "FastAPI"],
                                },
                            }
                        ],
                        "creditsCost": 10,
                    },
                },
            )

    orig_init = LinkedInProfileEnrichmentService.__init__

    def fake_init(self, api_key=None, timeout=45.0):
        orig_init(self, api_key="fc-test-token", timeout=timeout)

    monkeypatch.setattr(LinkedInProfileEnrichmentService, "__init__", fake_init)
    orig_client = httpx.Client

    def patched_client(*args, **kwargs):
        kwargs["transport"] = MockTransport()
        return orig_client(*args, **kwargs)

    monkeypatch.setattr("backend.modules.enrichment.linkedin_profile.httpx.Client", patched_client)

    res = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={})
    assert res.status_code == 200
    assert captured["url"] == "https://api.firecrawl.dev/v2/scrape"
    assert captured["headers"]["authorization"] == "Bearer fc-test-token"
    assert captured["body"] == {
        "alexandria": {
            "provider": "enrichlayer",
            "capability": "people/profile",
            "options": {"profile_url": "https://www.linkedin.com/in/http-subject"},
        }
    }
    data = res.json()
    assert data["structured_profile"]["headline"] == "VP Engineering"
    assert data["structured_profile"]["skills"] == ["Python", "FastAPI"]


def test_api_errors_do_not_overwrite_previously_stored_profile(monkeypatch):
    person_id = _create_verified_target(
        name="Resilient Target",
        linkedin_url="https://www.linkedin.com/in/resilient-target",
        biography="Preserved biography.",
        verification_status="VERIFIED",
    )

    sample = _load_sample_payload()
    inner = json.loads(json.dumps(sample["data"]["alexandria"][0]["data"]))
    inner["public_identifier"] = "resilient-target"
    inner["full_name"] = "Resilient Target"

    # 1. Initial enrichment succeeds
    monkeypatch.setattr(
        LinkedInProfileEnrichmentService,
        "fetch_alexandria_profile",
        lambda self, profile_url, http_client=None: (inner, 10),
    )
    res_ok = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={})
    assert res_ok.status_code == 200
    original_person = client.get(f"/api/v1/persons/{person_id}").json()
    assert len(original_person["experiences"]) == 10
    assert len(original_person["education"]) == 3
    assert original_person["headline"] is not None
    assert original_person["enrichment_status"] == "SUCCESS"

    # 2. Simulate upstream failures (timeout, HTTP 502, empty 404) on force=True refresh
    for err_status, err_msg in [
        (504, "Timed out waiting for Firecrawl Alexandria response."),
        (502, "Firecrawl Alexandria API returned HTTP 500."),
        (402, "Insufficient Firecrawl credits to run enrichment."),
        (404, "EnrichLayer returned no profile record for this URL."),
    ]:
        def _raise_err(self, profile_url, http_client=None, s=err_status, m=err_msg):
            raise LinkedInEnrichmentError(m, status_code=s)

        monkeypatch.setattr(LinkedInProfileEnrichmentService, "fetch_alexandria_profile", _raise_err)
        res_fail = client.post(f"/api/v1/linkedin/enrich/{person_id}", json={"force": True})
        assert res_fail.status_code == err_status

        # Previously stored profile data MUST remain completely intact
        after_fail = client.get(f"/api/v1/persons/{person_id}").json()
        assert after_fail["headline"] == original_person["headline"]
        assert after_fail["summary"] == original_person["summary"]
        assert after_fail["experiences"] == original_person["experiences"]
        assert after_fail["education"] == original_person["education"]
        assert after_fail["projects"] == original_person["projects"]
        assert after_fail["enrichment_status"] == "SUCCESS"
        assert after_fail["profile_enriched_at"] == original_person["profile_enriched_at"]


