from app.modules.persons.schemas import IdentityContext
from app.modules.discovery.query_builder import QueryBuilder


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

    # Confirm name is included in all queries
    for q_list in queries.values():
        for q in q_list:
            assert "Alexander Hamilton" in q

    # Confirm organization is leveraged in contextual queries
    assert any("Treasury Corp" in q for q in queries["youtube"])

