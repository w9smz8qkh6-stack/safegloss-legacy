"""
Texas Resource Provider.

Discovers educational resources that support Texas TEKS
(Texas Essential Knowledge and Skills) learning objectives.

DISCOVERY STRATEGY:
==================
1. Official resources from TEA (Texas Education Agency):
   - TEA Instructional Materials page
   - Texas Resource Review

2. Commonly used resources from major districts:
   - Houston ISD curriculum
   - Dallas ISD curriculum
   - Austin ISD curriculum

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
    grade_matches,
    discover_from_authority_website,
    discover_from_district_website,
    enrich_resources_batch,
    AUTHORITY_RESOURCE_PAGES,
    DISTRICT_CURRICULUM_PAGES,
)

logger = logging.getLogger(__name__)


@register_resource_provider("STATE_TX")
class TexasResourceProvider(BaseResourceProvider):
    """
    Resource provider for Texas TEKS standards.

    SEARCH STRATEGY:
    ================
    1. TEA Adopted Instructional Materials List
       - URL: https://tea.texas.gov/academics/instructional-materials
       - Contains state-adopted textbooks by subject and grade
       - Updated annually after SBOE adoption cycles

    2. Texas Resource Review (TRR)
       - URL: https://texasresourcereview.org/
       - Reviews of instructional materials aligned to TEKS
       - Contains alignment ratings and teacher reviews

    3. Major District Curriculum Pages
       - Houston ISD: https://www.houstonisd.org/curriculum
       - Dallas ISD: https://www.dallasisd.org/curriculum
       - Austin ISD: https://www.austinisd.org/academics
       - These often list supplemental resources beyond state adoptions

    4. Publisher TEKS Alignment Documents
       - Pearson Texas Portal
       - McGraw-Hill Texas Resources
       - HMH (Houghton Mifflin Harcourt) Texas

    IMPLEMENTATION:
    ==============
    - Returns curated official TEA resources
    - Searches Google Books for TEKS-aligned textbooks
    - Future: Web scraping of TEA materials list
    """

    SEARCH_STRATEGY = """
    1. Check TEA Adopted Instructional Materials list
    2. Query Texas Resource Review for aligned materials
    3. Search major district curriculum pages (Houston, Dallas, Austin ISDs)
    4. Check publisher TEKS alignment documents
    """

    SOURCE_URLS = [
        "https://tea.texas.gov/academics/instructional-materials",
        "https://texasresourcereview.org/",
        "https://www.houstonisd.org/curriculum",
        "https://www.dallasisd.org/curriculum",
        "https://www.austinisd.org/academics",
    ]

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_TX"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Texas TEKS.

        Uses tiered discovery:
        1. Official: TEA authority pages (curated + AI discovery)
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

        # 2. Discover official resources from TEA authority pages
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

        # 3. Discover commonly used resources from major district websites
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

        # 4. Enrich resources with Google Books metadata (ISBNs, covers)
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
            "English Language Arts and Reading",
            "Mathematics",
            "Science",
            "Social Studies",
            "Technology Applications",
            "Health Education",
            "Physical Education",
            "Fine Arts",
            "Languages Other Than English",
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
            "Grades 6-8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
            "Grades 9-12",
        ]
