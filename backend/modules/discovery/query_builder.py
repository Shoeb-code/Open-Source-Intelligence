from typing import List, Dict
from backend.modules.persons.schemas import IdentityContext


class QueryBuilder:
    """Builds targeted search queries for public appearance discovery."""

    @staticmethod
    def build_queries(context: IdentityContext) -> Dict[str, List[str]]:
        name = context.name
        profession = context.profession
        orgs = context.organizations

        queries: Dict[str, List[str]] = {
            "youtube": [
                f'"{name}" podcast',
                f'"{name}" interview',
                f'"{name}" conference talk',
                f'"{name}" keynote',
            ],
            "news": [
                f'"{name}" news interview',
                f'"{name}" press article',
                f'"{name}" media coverage',
            ],
            "podcasts": [
                f'"{name}" guest podcast episode',
                f'"{name}" podcast host interview',
            ],
            "events": [
                f'"{name}" conference speaker',
                f'"{name}" webinar presentation',
                f'"{name}" panel discussion',
            ],
            "linkedin": [
                f'"{name}" linkedin',
                f'"{name}" linkedin post',
                f'"{name}" linkedin pulse article',
                f'"{name}" linkedin thought leadership',
            ],
            "instagram": [
                f'"{name}" instagram',
                f'"{name}" instagram reel',
                f'"{name}" instagram post',
            ],
        }

        # Context-enriched queries if profession or organization exists
        if profession:
            queries["youtube"].append(f'"{name}" {profession} interview')
            queries["news"].append(f'"{name}" {profession}')
            queries["linkedin"].append(f'"{name}" {profession} linkedin')
            queries["instagram"].append(f'"{name}" {profession} instagram')

        if orgs:
            primary_org = orgs[0]
            queries["youtube"].append(f'"{name}" "{primary_org}"')
            queries["news"].append(f'"{name}" "{primary_org}"')
            queries["events"].append(f'"{name}" "{primary_org}" speaker')
            queries["linkedin"].append(f'"{name}" "{primary_org}" linkedin')
            queries["instagram"].append(f'"{name}" "{primary_org}" instagram')

        return queries

