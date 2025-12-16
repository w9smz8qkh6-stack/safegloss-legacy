"""
Texas TEKS Standards Provider.

Fetches Texas Essential Knowledge and Skills (TEKS) from the
Texas Education Agency (TEA).

Uses comprehensive seed data from the official TEA standards,
with web discovery as an optional enrichment layer.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..providers import (
    BaseStandardsProvider,
    FetchResult,
    ObjectiveNodeData,
    register_provider,
)
from ..discovery import (
    discover_standards_from_url,
    convert_to_fetch_result,
    get_standards_url_for_program,
)

logger = logging.getLogger(__name__)


def load_teks_seed_data():
    """Load comprehensive TEKS data from seed file."""
    seed_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "seeds" / "texas_teks_comprehensive.json"

    if not seed_path.exists():
        logger.warning(f"TEKS seed file not found at {seed_path}")
        return None

    try:
        with open(seed_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load TEKS seed file: {e}")
        return None


# Load seed data once at module load
_SEED_DATA = None


def get_seed_data():
    """Get cached seed data, loading if needed."""
    global _SEED_DATA
    if _SEED_DATA is None:
        _SEED_DATA = load_teks_seed_data()
    return _SEED_DATA


@register_provider("STATE_TX")
class TexasTEKSProvider(BaseStandardsProvider):
    """
    Provider for Texas Essential Knowledge and Skills (TEKS).

    Uses comprehensive seed data from official TEA standards documents,
    covering ELA, Math, Science, and Technology Applications.
    """

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_TX"

    def _find_subject_data(self, subject: str, grade_level: str):
        """Find subject/grade data in seed file."""
        seed_data = get_seed_data()
        if not seed_data:
            return None

        # Normalize inputs
        subject_lower = subject.lower().strip()
        grade_lower = grade_level.lower().strip()

        # Find matching subject
        for subj_data in seed_data.get("subjects", []):
            subj_name = subj_data.get("name", "").lower()
            subj_code = subj_data.get("code", "").lower()

            if subject_lower in subj_name or subject_lower == subj_code or subj_name in subject_lower:
                # Find matching grade
                for grade_data in subj_data.get("grade_levels", []):
                    grade_name = grade_data.get("grade", "").lower()
                    grade_code = grade_data.get("code", "").lower()

                    if grade_lower in grade_name or grade_lower == grade_code or grade_name in grade_lower:
                        return {
                            "subject": subj_data,
                            "grade": grade_data,
                            "source": seed_data.get("source", {}),
                        }

        return None

    def fetch_objectives(
        self,
        subject: str,
        grade_level: str,
        version: Optional[str] = None,
    ) -> Optional[FetchResult]:
        """
        Fetch TEKS objectives for a subject/grade combination.

        Uses comprehensive seed data from official TEA standards.
        """
        logger.info(f"Fetching TEKS for {subject} {grade_level}")

        # 1. Try web discovery from official TEA pages (optional enhancement)
        standards_url = get_standards_url_for_program(
            self.program_code, subject, grade_level
        )

        if standards_url:
            logger.info(f"Attempting web discovery from {standards_url}")
            try:
                discovered = discover_standards_from_url(
                    url=standards_url,
                    authority_name="Texas Education Agency",
                    subject=subject,
                    grade_level=grade_level,
                    version_label=version or "Current",
                )

                if discovered.objectives:
                    logger.info(f"Web discovery found {len(discovered.objectives)} objectives")
                    result = convert_to_fetch_result(
                        discovered,
                        self.authority_code,
                        self.program_code,
                    )
                    result.provenance["source_publisher_name"] = "Texas Education Agency"
                    return result
                else:
                    logger.info(f"Web discovery returned no objectives, using seed data")
            except Exception as e:
                logger.info(f"Web discovery failed: {e}, using seed data")

        # 2. Use comprehensive seed data
        match = self._find_subject_data(subject, grade_level)

        if not match:
            logger.info(f"No seed data for {subject} {grade_level}")
            return None

        subj_data = match["subject"]
        grade_data = match["grade"]
        source = match["source"]

        # Build nodes from seed data
        nodes = []
        node_id = 0

        for strand in grade_data.get("strands", []):
            node_id += 1
            strand_id = f"s{node_id}"

            # Add strand node
            nodes.append(ObjectiveNodeData(
                id=strand_id,
                parent_id=None,
                node_type=strand.get("node_type", "strand"),
                code=strand.get("code", ""),
                text=strand.get("name", strand.get("text", "")),
                sort_order=node_id,
            ))

            # Add objective nodes (expectations)
            for exp in strand.get("expectations", []):
                node_id += 1
                nodes.append(ObjectiveNodeData(
                    id=f"o{node_id}",
                    parent_id=strand_id,
                    node_type=exp.get("node_type", "objective"),
                    code=exp.get("code", ""),
                    text=exp.get("text", ""),
                    sort_order=node_id,
                ))

        # Build provenance
        provenance = {
            "source_publisher_name": source.get("publisher", "Texas Education Agency"),
            "source_publisher_type": source.get("publisher_type", "government"),
            "source_title": f"{subj_data.get('name', subject)} TEKS, {grade_data.get('grade', grade_level)}",
            "source_url": source.get("url", "https://tea.texas.gov/academics/curriculum-standards/teks"),
            "source_url_canonical": "https://tea.texas.gov/academics/curriculum-standards/teks-review/texas-essential-knowledge-and-skills",
            "source_accessed_at": datetime.utcnow().isoformat() + "Z",
            "source_content_type": "json",
            "source_version_label": source.get("version", "Adopted 2017, Revised 2024"),
            "acquisition_method": source.get("acquisition_method", "manual_curated"),
            "acquisition_notes": "Comprehensive TEKS from official TEA standards",
            "evidence_sha256_raw": "",
            "evidence_sha256_canonical": "",
        }

        return FetchResult(
            authority_code=self.authority_code,
            program_code=self.program_code,
            subject=subj_data.get("name", subject),
            grade_level=grade_data.get("grade", grade_level),
            version_label=source.get("version", "2024"),
            provenance=provenance,
            nodes=nodes,
        )

    def list_available_subjects(self) -> list[str]:
        """Return available subjects from seed data."""
        seed_data = get_seed_data()
        if not seed_data:
            return ["English Language Arts and Reading", "Mathematics", "Science", "Technology Applications"]

        return [s.get("name", "") for s in seed_data.get("subjects", [])]

    def list_available_grades(self, subject: Optional[str] = None) -> list[str]:
        """Return available grade levels from seed data."""
        seed_data = get_seed_data()
        if not seed_data:
            return ["Grade 6", "Grade 7", "Grade 8"]

        grades = set()
        for subj in seed_data.get("subjects", []):
            # If subject specified, only get grades for that subject
            if subject:
                subj_name = subj.get("name", "").lower()
                if subject.lower() not in subj_name and subj_name not in subject.lower():
                    continue

            for grade in subj.get("grade_levels", []):
                grades.add(grade.get("grade", ""))

        # Sort grades properly
        grade_order = ["Kindergarten"] + [f"Grade {i}" for i in range(1, 13)] + ["Grades 6-8", "Grades 9-12"]
        return sorted(list(grades), key=lambda g: grade_order.index(g) if g in grade_order else 99)
