"""
California Resource Provider.

Discovers educational resources that support California
Content Standards and Frameworks.

DISCOVERY STRATEGY:
==================
1. Official resources from CDE:
   - CDE Instructional Materials page
   - California Curriculum Frameworks

2. Commonly used resources from major districts:
   - Los Angeles USD
   - San Diego USD

3. Metadata enrichment via Google Books (ISBNs, covers only)
"""

import logging

from core.services.resources import (
    BaseResourceProvider,
    DiscoveryResult,
    ResourceData,
    ResourceProviderError,
    register_resource_provider,
)
from core.services.resources.discovery import (
    get_curated_resources,
    normalize_subject,
    discover_from_authority_website,
    discover_from_district_website,
    enrich_resources_batch,
    AUTHORITY_RESOURCE_PAGES,
    DISTRICT_CURRICULUM_PAGES,
)

logger = logging.getLogger(__name__)


@register_resource_provider("STATE_CA")
class CaliforniaResourceProvider(BaseResourceProvider):
    """
    Resource provider for California standards.

    SEARCH STRATEGY:
    ================
    1. CDE Instructional Materials
       - URL: https://www.cde.ca.gov/ci/rl/im/
       - State-adopted instructional materials by subject
       - K-8 and 9-12 adoption lists

    2. California Curriculum Frameworks
       - URL: https://www.cde.ca.gov/ci/
       - Comprehensive frameworks with resource recommendations

    3. California Digital Library
       - URL: https://www.cde.ca.gov/ci/cr/cf/
       - Free digital resources for California educators

    IMPLEMENTATION:
    ==============
    - Returns curated official CDE resources
    - Searches Google Books for California-aligned textbooks
    """

    SEARCH_STRATEGY = """
    1. Check CDE Adopted Instructional Materials list
    2. Review California Curriculum Frameworks
    3. Search California Digital Library
    4. Check major district curriculum pages
    """

    SOURCE_URLS = [
        "https://www.cde.ca.gov/ci/rl/im/",
        "https://www.cde.ca.gov/ci/",
        "https://www.cde.ca.gov/ci/cr/cf/",
        "https://www.lausd.org/",
        "https://www.sandiegounified.org/",
    ]

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_CA"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for California standards.

        Uses tiered discovery:
        1. Official: CDE authority pages (curated + AI discovery)
        2. Commonly Used: Major district curriculum pages
        3. Metadata enrichment via Google Books (ISBNs, covers)
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated official resources (fast, no API calls)
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Add California-specific official resources
        ca_resources = [
            ResourceData(
                title="CDE Adopted Instructional Materials",
                source_url="https://www.cde.ca.gov/ci/rl/im/",
                media_type="guide",
                platform="cde",
                publisher="California Department of Education",
                description="State-adopted instructional materials for California schools",
                recommendation_tier="official",
                endorsement_notes="Official CDE adopted materials",
                recommending_organization="California Department of Education",
            ),
            ResourceData(
                title="California Curriculum Frameworks",
                source_url="https://www.cde.ca.gov/ci/",
                media_type="curriculum",
                platform="cde",
                publisher="California Department of Education",
                description="Official California curriculum frameworks by subject",
                recommendation_tier="official",
                endorsement_notes="Official CDE frameworks",
                recommending_organization="California Department of Education",
            ),
            ResourceData(
                title="CDE Digital Library",
                source_url="https://www.cde.ca.gov/ci/cr/cf/",
                media_type="curriculum",
                platform="cde",
                publisher="California Department of Education",
                description="Free digital resources for California educators",
                recommendation_tier="official",
                endorsement_notes="Official CDE free resources",
                recommending_organization="California Department of Education",
            ),
        ]
        resources.extend(ca_resources)

        # 3. Discover official resources from CDE authority pages
        authority_info = AUTHORITY_RESOURCE_PAGES.get(self.program_code)
        if authority_info:
            for page_url in authority_info.get("official_pages", []):
                try:
                    official = discover_from_authority_website(
                        authority_url=page_url,
                        authority_name=authority_info["name"],
                        subject=subject,
                        grade_level=grade_level,
                    )
                    # Deduplicate by title
                    existing_titles = {r.title.lower() for r in resources}
                    for r in official:
                        if r.title.lower() not in existing_titles:
                            resources.append(r)
                            existing_titles.add(r.title.lower())

                    if official:
                        discovery_notes.append(
                            f"Found {len(official)} resources from {page_url}."
                        )
                except Exception as e:
                    logger.warning(f"Authority discovery failed for {page_url}: {e}")
                    discovery_notes.append(f"Authority discovery failed: {e}")

        # 4. Discover commonly used resources from major district websites
        districts = DISTRICT_CURRICULUM_PAGES.get(self.program_code, [])
        for district in districts:
            try:
                district_resources = discover_from_district_website(
                    district_url=district["url"],
                    district_name=district["name"],
                    subject=subject,
                    grade_level=grade_level,
                )
                # Deduplicate by title
                existing_titles = {r.title.lower() for r in resources}
                for r in district_resources:
                    if r.title.lower() not in existing_titles:
                        resources.append(r)
                        existing_titles.add(r.title.lower())

                if district_resources:
                    discovery_notes.append(
                        f"Found {len(district_resources)} resources from {district['name']}."
                    )
                sources_checked.append(district["url"])
            except Exception as e:
                logger.warning(f"District discovery failed for {district['name']}: {e}")
                discovery_notes.append(f"District discovery failed: {e}")

        # 5. Enrich resources with Google Books metadata (ISBNs, covers)
        if resources:
            try:
                enrich_resources_batch(resources)
                discovery_notes.append("Enriched metadata via Google Books.")
            except Exception as e:
                logger.warning(f"Metadata enrichment failed: {e}")

        return DiscoveryResult(
            authority_code=self.authority_code,
            program_code=self.program_code,
            subject=subject,
            grade_level=grade_level,
            resources=resources,
            sources_checked=sources_checked,
            discovery_notes=" ".join(discovery_notes) or "Discovery completed.",
        )

    def list_available_subjects(self) -> list[str]:
        return [
            "English Language Arts",
            "Mathematics",
            "Science (NGSS)",
            "History-Social Science",
            "Health Education",
            "Physical Education",
            "Visual and Performing Arts",
            "World Languages",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return [
            "Kindergarten",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
            "Grade 5",
            "Grade 6",
            "Grade 7",
            "Grade 8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
        ]
