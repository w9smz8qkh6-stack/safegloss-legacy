"""
Florida Resource Provider.

Discovers educational resources that support Florida B.E.S.T.
(Benchmarks for Excellent Student Thinking) standards.

DISCOVERY STRATEGY:
==================
1. Official resources from FLDOE:
   - FLDOE Instructional Materials page
   - CPALMS standards portal

2. Commonly used resources from major districts:
   - Miami-Dade County Public Schools
   - Broward County Public Schools

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


@register_resource_provider("STATE_FL")
class FloridaResourceProvider(BaseResourceProvider):
    """
    Resource provider for Florida B.E.S.T. standards.

    SEARCH STRATEGY:
    ================
    1. FLDOE Instructional Materials
       - URL: https://www.fldoe.org/academics/standards/instructional-materials/
       - State-adopted instructional materials list
       - Updated after adoption cycles

    2. CPALMS (Collaborate, Plan, Align, Learn, Motivate, Share)
       - URL: https://www.cpalms.org/
       - Florida's official standards and resources portal
       - Contains lesson plans, assessments, and resource links

    3. Florida Virtual School (FLVS)
       - URL: https://www.flvs.net/
       - Free online courses aligned to Florida standards

    IMPLEMENTATION:
    ==============
    - Returns curated official FLDOE resources
    - Searches Google Books for aligned textbooks
    """

    SEARCH_STRATEGY = """
    1. Check FLDOE Instructional Materials adoption list
    2. Search CPALMS for aligned resources
    3. Check FLVS course catalog
    4. Search major district curriculum pages
    """

    SOURCE_URLS = [
        "https://www.fldoe.org/academics/standards/instructional-materials/",
        "https://www.cpalms.org/",
        "https://www.flvs.net/",
        "https://www.dadeschools.net/",
        "https://www.browardschools.com/",
    ]

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_FL"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Florida B.E.S.T. standards.

        Uses tiered discovery:
        1. Official: FLDOE authority pages (curated + AI discovery)
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

        # 2. Add Florida-specific official resources
        florida_resources = [
            ResourceData(
                title="CPALMS - Florida's Standards Portal",
                source_url="https://www.cpalms.org/",
                media_type="curriculum",
                platform="cpalms",
                publisher="Florida Department of Education",
                description="Official Florida B.E.S.T. standards, lesson plans, and resources",
                recommendation_tier="official",
                endorsement_notes="Official FLDOE resource platform",
                recommending_organization="Florida Department of Education",
            ),
            ResourceData(
                title="Florida Virtual School (FLVS)",
                source_url="https://www.flvs.net/",
                media_type="course",
                platform="flvs",
                publisher="Florida Virtual School",
                description="Free online courses aligned to Florida standards",
                recommendation_tier="official",
                endorsement_notes="Florida's official virtual school",
                recommending_organization="Florida Department of Education",
            ),
        ]
        resources.extend(florida_resources)

        # 3. Discover official resources from FLDOE authority pages
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
            "Science",
            "Social Studies",
            "Health Education",
            "Physical Education",
            "Fine Arts",
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
