from backend.modules.persons.schemas import IdentityContext
from backend.modules.discovery.query_builder import QueryBuilder


def test_query_builder():
    context = IdentityContext(
        person_id="p-123",
        name="Alexander Hamilton",
        profession="Financial Architect at Treasury Corp",
        organizations=["Treasury Corp"],
        known_usernames=["ahamilton"],
        profile_urls={"linkedin": "https://linkedin.com/in/ahamilton"}
    )
    queries = QueryBuilder.build_queries(context)
    assert "youtube" in queries
    assert "news" in queries
    assert "podcasts" in queries
    assert "events" in queries
    assert "linkedin" in queries
    assert "instagram" in queries

    # Confirm name is included in all queries
    for q_list in queries.values():
        for q in q_list:
            assert "Alexander Hamilton" in q

    # Confirm organization is leveraged in contextual queries
    assert any("Treasury Corp" in q for q in queries["youtube"])
    assert any("Treasury Corp" in q for q in queries["linkedin"])
    assert any("Treasury Corp" in q for q in queries["instagram"])


def test_collectors_item_detection_and_username_extraction():
    from backend.modules.collectors.instagram import InstagramCollector
    from backend.modules.collectors.linkedin import LinkedInCollector

    # Instagram checks
    assert InstagramCollector._detect_item_type("https://instagram.com/reel/C8XYZ123/") == "INSTAGRAM_REEL"
    assert InstagramCollector._detect_item_type("https://instagram.com/p/C3ABC456/") == "INSTAGRAM_POST"
    assert InstagramCollector._detect_item_type("https://instagram.com/madhulunawat/") == "INSTAGRAM_PROFILE"
    assert InstagramCollector._extract_username("https://instagram.com/madhulunawat/") == "madhulunawat"
    assert InstagramCollector._clean_title("Madhu Lunawat (@madhulunawat) • Instagram photos and videos", "https://instagram.com/madhulunawat") == "Madhu Lunawat (@madhulunawat)"

    # LinkedIn checks
    assert LinkedInCollector._detect_item_type("https://linkedin.com/in/madhu-lunawat-1a3b719") == "LINKEDIN_PROFILE"
    assert LinkedInCollector._detect_item_type("https://linkedin.com/pulse/future-wealth-madhu-lunawat") == "ARTICLE"
    assert LinkedInCollector._detect_item_type("https://linkedin.com/posts/madhulunawat-talk") == "LINKEDIN_POST"
    assert LinkedInCollector._extract_username("https://linkedin.com/in/madhu-lunawat-1a3b719") == "madhu-lunawat-1a3b719"
    assert LinkedInCollector._clean_title("Madhu Lunawat - Founder - The Wealth Company | LinkedIn", "https://linkedin.com/in/madhu-lunawat-1a3b719") == "Madhu Lunawat - Founder - The Wealth Company"

