from backend.modules.extraction.metadata_extractor import ExtractedPayload
from backend.modules.persons.schemas import IdentityContext
from backend.modules.analysis.classifier import AppearanceClassifier
from backend.modules.analysis.summarizer import AppearanceSummarizer


def test_appearance_classifier():
    p1 = ExtractedPayload(
        title="Episode 104: AI Systems with Dr. Smith",
        source_url="https://podcasts.apple.com/us/podcast/id123",
        canonical_url="https://podcasts.apple.com/us/podcast/id123",
        source_type="PODCAST",
        extraction_status="SUCCESS"
    )
    assert AppearanceClassifier.classify(p1) == "PODCAST"

    p2 = ExtractedPayload(
        title="Keynote: Scaling Systems at TechConf 2026",
        source_url="https://techconf.org/speakers/smith",
        canonical_url="https://techconf.org/speakers/smith",
        source_type="EVENT",
        extraction_status="SUCCESS"
    )
    assert AppearanceClassifier.classify(p2) == "CONFERENCE"

    p3 = ExtractedPayload(
        title="Madhu Lunawat on LinkedIn: Keynote at AIC",
        source_url="https://www.linkedin.com/posts/madhulunawat_keynote",
        canonical_url="https://www.linkedin.com/posts/madhulunawat_keynote",
        source_type="LINKEDIN",
        extraction_status="SUCCESS"
    )
    assert AppearanceClassifier.classify(p3) == "LINKEDIN_POST"

    p4 = ExtractedPayload(
        title="Ms. Madhu Lunawat - CEO of The Wealth Company - Instagram Reel",
        source_url="https://www.instagram.com/reel/DRebwp5DCr2/",
        canonical_url="https://www.instagram.com/reel/DRebwp5DCr2/",
        source_type="INSTAGRAM",
        extraction_status="SUCCESS"
    )
    assert AppearanceClassifier.classify(p4) == "INSTAGRAM_REEL"

    p5 = ExtractedPayload(
        title="Madhu Lunawat, Founder, MD & CEO - The Wealth Company",
        source_url="https://www.instagram.com/p/DSHW9Bgj5F7/",
        canonical_url="https://www.instagram.com/p/DSHW9Bgj5F7/",
        source_type="INSTAGRAM",
        extraction_status="SUCCESS"
    )
    assert AppearanceClassifier.classify(p5) == "INSTAGRAM_POST"


def test_appearance_summarizer_fallback_evidence():
    context = IdentityContext(
        person_id="p-1",
        name="Elena Rostova",
        profession="Quantum Computing Specialist",
        organizations=["QuantumLabs"],
        known_usernames=[],
        profile_urls={}
    )
    payload = ExtractedPayload(
        title="Elena Rostova on Fault-Tolerant Qubits",
        source_url="https://news.quantum.org/elena",
        canonical_url="https://news.quantum.org/elena",
        source_type="NEWS",
        publisher="Quantum News",
        extracted_content="Elena Rostova demonstrated scalable topological qubits at QuantumLabs. The discovery promises significant coherence enhancements.",
        extraction_status="SUCCESS"
    )

    summarizer = AppearanceSummarizer()
    res = summarizer.analyze(context, payload)
    assert res.summary is not None
    assert len(res.topics) > 0
    assert len(res.evidence) > 0

