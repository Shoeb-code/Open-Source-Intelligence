from app.modules.persons.schemas import IdentityContext
from app.modules.extraction.metadata_extractor import ExtractedPayload
from app.modules.identity.verifier import IdentityVerifier


def test_identity_verifier_verified_match():
    context = IdentityContext(
        person_id="p-1",
        name="Rahul Sharma",
        profession="VP Engineering at TechFlow",
        organizations=["TechFlow"],
        known_usernames=["rahul_techflow"],
        profile_urls={}
    )
    payload = ExtractedPayload(
        title="Rahul Sharma, VP Engineering at TechFlow on Scaling Cloud Systems",
        source_url="https://youtube.com/watch?v=abc12345678",
        canonical_url="https://youtube.com/watch?v=abc12345678",
        source_type="YOUTUBE",
        publisher="Tech Talks Daily",
        description="Rahul Sharma discusses distributed architecture at TechFlow.",
        extracted_content="In this episode, Rahul Sharma from TechFlow explains modern backend engineering.",
        content_hash="hash123",
        extraction_status="SUCCESS"
    )

    status, score, signals = IdentityVerifier.verify(context, payload)
    assert status == "VERIFIED"
    assert score >= 0.80
    assert "exact_name_in_corpus" in signals["matched_signals"]
    assert "organization:TechFlow" in signals["matched_signals"]


def test_identity_verifier_unrelated_person_rejected():
    context = IdentityContext(
        person_id="p-1",
        name="Rahul Sharma",
        profession="VP Engineering at TechFlow",
        organizations=["TechFlow"],
        known_usernames=["rahul_techflow"],
        profile_urls={}
    )
    # Different individual with entirely different name
    payload = ExtractedPayload(
        title="John Smith on Machine Learning in Healthcare",
        source_url="https://news.com/article/john-smith",
        canonical_url="https://news.com/article/john-smith",
        source_type="NEWS",
        publisher="Global News",
        description="John Smith leads healthcare AI.",
        extracted_content="John Smith discussed patient outcome prediction.",
        content_hash="hash999",
        extraction_status="SUCCESS"
    )

    status, score, signals = IdentityVerifier.verify(context, payload)
    assert status == "REJECTED"
    assert score < 0.35

