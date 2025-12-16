"""
Common Core State Standards Provider.

Fetches Common Core State Standards (CCSS) for English Language Arts
and Mathematics.

This is a reference implementation demonstrating the provider pattern.
"""

from datetime import datetime
from typing import Optional

from ..providers import (
    BaseStandardsProvider,
    FetchResult,
    ObjectiveNodeData,
    ProviderError,
    register_provider,
)


# Sample CCSS ELA data for Grade 6 Reading Literature
SAMPLE_ELA_GRADE_6_RL = {
    "subject": "English Language Arts",
    "grade_level": "Grade 6",
    "version_label": "2010 Standards",
    "strands": [
        {
            "code": "CCSS.ELA-LITERACY.RL.6",
            "text": "Reading: Literature - Grade 6",
            "substrands": [
                {
                    "code": "Key Ideas and Details",
                    "objectives": [
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.1",
                            "text": "Cite textual evidence to support analysis of what the text says explicitly as well as inferences drawn from the text."
                        },
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.2",
                            "text": "Determine a theme or central idea of a text and how it is conveyed through particular details; provide a summary of the text distinct from personal opinions or judgments."
                        },
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.3",
                            "text": "Describe how a particular story's or drama's plot unfolds in a series of episodes as well as how the characters respond or change as the plot moves toward a resolution."
                        },
                    ]
                },
                {
                    "code": "Craft and Structure",
                    "objectives": [
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.4",
                            "text": "Determine the meaning of words and phrases as they are used in a text, including figurative and connotative meanings; analyze the impact of a specific word choice on meaning and tone."
                        },
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.5",
                            "text": "Analyze how a particular sentence, chapter, scene, or stanza fits into the overall structure of a text and contributes to the development of the theme, setting, or plot."
                        },
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.6",
                            "text": "Explain how an author develops the point of view of the narrator or speaker in a text."
                        },
                    ]
                },
                {
                    "code": "Integration of Knowledge and Ideas",
                    "objectives": [
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.7",
                            "text": "Compare and contrast the experience of reading a story, drama, or poem to listening to or viewing an audio, video, or live version of the text, including contrasting what they \"see\" and \"hear\" when reading the text to what they perceive when they listen or watch."
                        },
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.9",
                            "text": "Compare and contrast texts in different forms or genres (e.g., stories and poems; historical novels and fantasy stories) in terms of their approaches to similar themes and topics."
                        },
                    ]
                },
                {
                    "code": "Range of Reading and Level of Text Complexity",
                    "objectives": [
                        {
                            "code": "CCSS.ELA-LITERACY.RL.6.10",
                            "text": "By the end of the year, read and comprehend literature, including stories, dramas, and poems, in the grades 6-8 text complexity band proficiently, with scaffolding as needed at the high end of the range."
                        },
                    ]
                },
            ]
        },
    ]
}


@register_provider("CCSS_ELA")
class CommonCoreProvider(BaseStandardsProvider):
    """
    Provider for Common Core State Standards.

    Currently uses sample ELA data. In production, would fetch from:
    - corestandards.org
    - Official CCSS documents
    """

    @property
    def authority_code(self) -> str:
        return "CCSS"

    @property
    def program_code(self) -> str:
        return "CCSS_ELA"

    def fetch_objectives(
        self,
        subject: str,
        grade_level: str,
        version: Optional[str] = None,
    ) -> FetchResult:
        """
        Fetch CCSS objectives for a subject/grade combination.

        For demonstration, returns sample data for ELA Grade 6.
        """
        if "english" not in subject.lower() and "ela" not in subject.lower():
            raise ProviderError(
                f"Sample provider only supports English Language Arts. "
                f"Requested: {subject}",
                provider=self.program_code,
            )

        if "6" not in grade_level:
            raise ProviderError(
                f"Sample provider only supports Grade 6. "
                f"Requested: {grade_level}",
                provider=self.program_code,
            )

        # Build nodes from sample data
        nodes = []
        node_id = 0

        for strand in SAMPLE_ELA_GRADE_6_RL["strands"]:
            node_id += 1
            strand_id = str(node_id)

            # Add strand node
            nodes.append(ObjectiveNodeData(
                id=strand_id,
                parent_id=None,
                node_type="strand",
                code=strand["code"],
                text=strand["text"],
                sort_order=node_id,
            ))

            # Add substrand nodes
            for substrand in strand.get("substrands", []):
                node_id += 1
                substrand_id = str(node_id)

                nodes.append(ObjectiveNodeData(
                    id=substrand_id,
                    parent_id=strand_id,
                    node_type="substrand",
                    code="",  # Substrands don't have CCSS codes
                    text=substrand["code"],  # Use the label as text
                    sort_order=node_id,
                ))

                # Add objective nodes
                for obj in substrand.get("objectives", []):
                    node_id += 1
                    nodes.append(ObjectiveNodeData(
                        id=str(node_id),
                        parent_id=substrand_id,
                        node_type="objective",
                        code=obj["code"],
                        text=obj["text"],
                        sort_order=node_id,
                    ))

        # Build provenance
        provenance = {
            "source_publisher_name": "Common Core State Standards Initiative",
            "source_publisher_type": "nonprofit",
            "source_title": "Common Core State Standards for English Language Arts - Grade 6",
            "source_url": "https://www.corestandards.org/ELA-Literacy/RL/6/",
            "source_url_canonical": "https://www.corestandards.org/ELA-Literacy/",
            "source_accessed_at": datetime.utcnow().isoformat() + "Z",
            "source_content_type": "html",
            "source_version_label": "2010 Standards",
            "acquisition_method": "manual_curated",
            "acquisition_notes": (
                "Sample data for demonstration purposes. "
                "Production implementation would parse official CCSS documents."
            ),
            "evidence_sha256_raw": "",
            "evidence_sha256_canonical": "",
        }

        return FetchResult(
            authority_code=self.authority_code,
            program_code=self.program_code,
            subject=SAMPLE_ELA_GRADE_6_RL["subject"],
            grade_level=SAMPLE_ELA_GRADE_6_RL["grade_level"],
            version_label=SAMPLE_ELA_GRADE_6_RL["version_label"],
            provenance=provenance,
            nodes=nodes,
        )

    def list_available_subjects(self) -> list[str]:
        """Return available subjects (sample data only)."""
        return ["English Language Arts"]

    def list_available_grades(self, subject: Optional[str] = None) -> list[str]:
        """Return available grade levels (sample data only)."""
        return ["Grade 6"]
