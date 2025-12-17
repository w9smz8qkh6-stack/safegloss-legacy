"""
Unified AI Fetcher Service.

Single entry point for AI-powered data extraction using OpenRouter.
Consolidates all external API calls to OpenRouter for tab data fetching.
"""

import json
import logging
from typing import Optional

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from openai import OpenAI

logger = logging.getLogger(__name__)


# Default prompts for each tab type
# All prompts include {source_url} to encourage AI to use official documentation as reference
DEFAULT_TAB_PROMPTS = {
    "syllabus": """You are an expert at extracting syllabus information from official course documentation.
Extract syllabus information for {course_name} ({syllabus_code}).

Official course page: {source_url}
Use information from the official source above as your primary reference.

Return a JSON object with:
{{
    "aims": ["aim1", "aim2", ...],
    "assessment_objectives": ["ao1", "ao2", ...],
    "content_outline": [
        {{"topic": "Topic Name", "subtopics": ["subtopic1", "subtopic2"]}}
    ],
    "assessment_structure": {{
        "components": [{{"name": "Paper 1", "weight": "40%", "duration": "1h 30m", "description": "..."}}],
        "total_marks": 100
    }}
}}

Only include information you are confident about from official sources. Leave arrays empty if unknown.""",

    "ced": """You are an expert on College Board Advanced Placement (AP) courses.
Extract Course & Exam Description (CED) information for {course_name}.

Official course page: {source_url}
Use information from the official College Board source above as your primary reference.

Return a JSON object with:
{{
    "course_overview": "2-3 sentence description of the course",
    "big_ideas": [
        {{"name": "Big Idea 1", "abbreviation": "BI1", "description": "..."}}
    ],
    "units": [
        {{
            "number": 1,
            "title": "Unit Title",
            "weight": "10-15%",
            "topics": ["Topic 1", "Topic 2"],
            "key_concepts": ["concept1", "concept2"]
        }}
    ],
    "skills": [
        {{"name": "Skill Category", "skills": ["skill1", "skill2"]}}
    ],
    "exam_structure": {{
        "duration": "3 hours",
        "sections": [
            {{
                "name": "Section I: Multiple Choice",
                "questions": 50,
                "time": "1 hour 30 minutes",
                "weight": "50%"
            }},
            {{
                "name": "Section II: Free Response",
                "questions": 4,
                "time": "1 hour 30 minutes",
                "weight": "50%"
            }}
        ]
    }},
    "calculator_policy": "Description of calculator use if applicable",
    "formula_sheet": "Whether a formula sheet is provided"
}}

Only include information you are confident about for this specific AP course. Leave arrays empty if unknown.""",

    "objectives": """You are an expert instructional designer in the tradition of Walter Dick and James Carey.
Your task is to identify learning objectives for this course.

Course Title: {course_name}
Course Code: {syllabus_code}
Standards Authority: {authority}
Program: {program}
Official course page: {source_url}

APPROACH:
1. First, look for explicitly stated learning objectives, standards, or competencies in official documentation
2. If explicit objectives are not available, INFER them by analyzing:
   - Course assessments (exams, projects, papers) - what must students demonstrate?
   - Course content and topics - what knowledge and skills are being taught?
   - Prerequisites and outcomes - what should students be able to do after completing the course?

Use Bloom's Taxonomy action verbs (analyze, evaluate, create, apply, etc.) to write clear, measurable objectives.
Each objective should describe an observable behavior or demonstrable skill.

Return a JSON object with:
{{
    "objectives": [
        {{
            "code": "1",
            "text": "Objective text using action verb",
            "source": "explicit|inferred",
            "children": [
                {{"code": "1.1", "text": "Sub-objective", "source": "explicit|inferred", "children": []}}
            ]
        }}
    ],
    "methodology_note": "Brief note on whether objectives were extracted from documentation or inferred from assessments"
}}

Create a hierarchical structure with numbered codes (1, 1.1, 1.1.1, etc).
Be comprehensive - include all major learning outcomes a student should achieve.""",

    "official_resources": """You are an expert at finding official educational resources published by curriculum authorities.
Find OFFICIAL resources for {course_name} ({syllabus_code}) published by {authority}.

Official course page: {source_url}
Look for resources officially published or endorsed by the curriculum authority.

Return a JSON object with:
{{
    "textbooks": [
        {{
            "title": "Book Title",
            "authors": ["Author 1"],
            "publisher": "Publisher",
            "isbn": "ISBN-13",
            "url": "https://..."
        }}
    ],
    "guides": [
        {{"title": "Guide Name", "type": "teacher|student", "url": "..."}}
    ],
    "past_papers": [
        {{"title": "Paper Name", "year": "2023", "session": "May/June", "url": "..."}}
    ],
    "digital_resources": [
        {{"title": "Resource Name", "platform": "Platform", "url": "..."}}
    ]
}}

Only include resources officially published or endorsed by {authority}. Do not include third-party resources.""",

    "unofficial_resources": """You are an expert at finding high-quality third-party educational resources.
Find UNOFFICIAL (third-party) resources for {course_name} ({syllabus_code}).

Official course page for reference: {source_url}
Look for well-regarded third-party textbooks, study guides, and preparation materials.

Return a JSON object with:
{{
    "textbooks": [
        {{
            "title": "Book Title",
            "authors": ["Author 1"],
            "publisher": "Publisher",
            "isbn": "ISBN-13",
            "url": "https://..."
        }}
    ],
    "guides": [
        {{"title": "Guide Name", "type": "prep_book|study_guide|workbook", "url": "..."}}
    ],
    "video_courses": [
        {{"title": "Course Name", "platform": "YouTube|Udemy|Coursera|Khan Academy", "url": "..."}}
    ],
    "websites": [
        {{"title": "Resource Name", "description": "Brief description", "url": "..."}}
    ]
}}

Only include well-known, reputable third-party resources. Do not invent resources.""",

    "resources": """You are an expert at finding official and endorsed educational resources.
Find resources for {course_name} ({syllabus_code}).

Official course page: {source_url}
Use the official source as your primary reference for finding endorsed resources.

Return a JSON object with:
{{
    "textbooks": [
        {{
            "title": "Book Title",
            "authors": ["Author 1"],
            "publisher": "Publisher",
            "isbn": "ISBN-13",
            "is_official": true,
            "url": "https://..."
        }}
    ],
    "guides": [
        {{"title": "Guide Name", "type": "teacher|student", "url": "..."}}
    ],
    "past_papers": [
        {{"title": "Paper Name", "year": "2023", "session": "May/June", "url": "..."}}
    ],
    "digital_resources": [
        {{"title": "Resource Name", "platform": "Platform", "url": "..."}}
    ]
}}

Only include publicly accessible resources. Do not invent resources.""",

    "examinations": """You are an expert at extracting examination information from curricula.
Extract examination information for {course_name} ({syllabus_code}).

Official course page: {source_url}
Use the official examination specifications as your primary reference.

Return a JSON object with:
{{
    "exam_format": "Description of overall exam format",
    "papers": [
        {{
            "name": "Paper 1",
            "duration": "1h 30m",
            "marks": 80,
            "description": "Multiple choice questions covering...",
            "weighting": "40%"
        }}
    ],
    "grading": {{
        "scale": "A*-G or 1-5 etc",
        "thresholds": "Grade boundaries information"
    }},
    "specimen_papers": [
        {{"title": "Specimen Paper 1", "url": "..."}}
    ]
}}

Only include information from official examination documentation.""",

    "overview": """You are an expert at summarizing educational course information.
Provide an overview of {course_name} ({syllabus_code}).

Official course page: {source_url}
Use the official source as your primary reference for accurate course information.

Return a JSON object with:
{{
    "description": "Brief course description (2-3 sentences)",
    "key_features": ["feature1", "feature2"],
    "target_audience": "Description of who this course is for",
    "prerequisites": ["prerequisite1"],
    "duration": "Course duration if applicable",
    "assessment_overview": "Brief description of how students are assessed"
}}

Keep responses concise and factual based on official documentation.""",

    # =============================================================================
    # CAMBRIDGE-SPECIFIC PROMPTS
    # =============================================================================

    "scheme": """You are an expert on Cambridge Assessment International Education curriculum and Schemes of Work.
Create a Scheme of Work for this Cambridge course.

Course Title: {course_name}
Syllabus Code: {syllabus_code}
Program: {program}
Official syllabus page: {source_url}

SOURCES:
You may reference both official and unofficial schemes of work, but PREFER sources from:
1. Cambridge Assessment International Education (official schemes)
2. Endorsed publishers (Cambridge University Press, Hodder Education, Oxford)
3. Well-established educational resource providers
Only use community/teacher-created schemes if authoritative sources are unavailable.

A Scheme of Work is a plan that defines work to be done in the classroom, typically organized by:
- Teaching weeks/terms
- Topics and subtopics
- Learning objectives addressed
- Suggested activities and resources
- Assessment opportunities

Return a JSON object with:
{{
    "total_teaching_hours": "Recommended total guided learning hours",
    "terms": [
        {{
            "term": 1,
            "weeks": "1-12",
            "units": [
                {{
                    "unit_number": 1,
                    "title": "Unit Title",
                    "weeks": "1-3",
                    "hours": 9,
                    "topics": ["Topic 1", "Topic 2"],
                    "learning_objectives": ["LO codes addressed"],
                    "assessment_objectives": ["AO1", "AO2"],
                    "suggested_activities": ["Activity 1", "Activity 2"],
                    "resources": ["Textbook Ch 1", "Past paper questions"],
                    "assessment": "End of unit test / Essay / Practical"
                }}
            ]
        }}
    ],
    "revision_weeks": "Suggested weeks for revision before exams",
    "notes": "Any additional planning notes"
}}

Base this on the official Cambridge syllabus content. Be realistic about pacing.""",

    "cambridge_syllabus": """You are an expert on Cambridge Assessment International Education syllabuses.
Extract the COMPLETE syllabus information for this Cambridge course.

Course Title: {course_name}
Syllabus Code: {syllabus_code}
Program: {program}
Official syllabus page: {source_url}

REQUIREMENTS - EXTRACT EVERYTHING:
1. ALL syllabus aims (typically 5-10 aims)
2. ALL Assessment Objectives with their official descriptions and weightings
3. COMPLETE subject content - every section, every topic, every content point
4. FULL assessment structure with all papers and their details

Cambridge syllabuses are organized with numbered sections (e.g., Section 1, 2, 3...) containing numbered topics (e.g., 1.1, 1.2, 2.1...) and specific content points that candidates must know.

Return a JSON object with:
{{
    "syllabus_code": "{syllabus_code}",
    "aims": ["Full text of Aim 1", "Full text of Aim 2", ...],
    "assessment_objectives": [
        {{
            "code": "AO1",
            "name": "Knowledge with understanding",
            "description": "Full official Cambridge description of what this AO requires",
            "weighting": "40%"
        }},
        {{
            "code": "AO2",
            "name": "Application",
            "description": "Full official Cambridge description",
            "weighting": "30%"
        }},
        {{
            "code": "AO3",
            "name": "Analysis and evaluation",
            "description": "Full official Cambridge description",
            "weighting": "30%"
        }}
    ],
    "subject_content": [
        {{
            "section": "1",
            "title": "First Major Topic Area",
            "topics": [
                {{
                    "number": "1.1",
                    "title": "First Subtopic",
                    "content_points": [
                        "Specific content point a) that students must learn",
                        "Specific content point b) that students must learn",
                        "Specific content point c) that students must learn"
                    ]
                }},
                {{
                    "number": "1.2",
                    "title": "Second Subtopic",
                    "content_points": ["Content point a)", "Content point b)"]
                }}
            ]
        }},
        {{
            "section": "2",
            "title": "Second Major Topic Area",
            "topics": [...]
        }}
    ],
    "assessment_structure": {{
        "components": [
            {{
                "paper": "Paper 1",
                "name": "Theory Paper / Written Examination",
                "duration": "1h 30m",
                "marks": 80,
                "weighting": "50%",
                "format": "Detailed description of question types and structure",
                "ao_coverage": {{"AO1": "50%", "AO2": "30%", "AO3": "20%"}}
            }}
        ]
    }},
    "guided_learning_hours": "130-180 hours"
}}

IMPORTANT: Include ALL content from the syllabus. A typical Cambridge syllabus has 4-8 major sections with 3-6 topics each, and each topic has 2-10 content points. Be exhaustive.""",

    "cambridge_objectives": """You are an expert instructional designer specializing in Cambridge Assessment International Education curricula.
Your task is to create DETAILED learning objectives for EVERY topic in this Cambridge course syllabus.

Course Title: {course_name}
Syllabus Code: {syllabus_code}
Program: {program}
Official syllabus page: {source_url}

CAMBRIDGE ASSESSMENT FRAMEWORK:
Cambridge Assessment International Education uses Assessment Objectives (AOs) which define what candidates should be able to do:
- AO1: Knowledge with understanding (recall, select, use knowledge)
- AO2: Application (apply knowledge to familiar and unfamiliar contexts)
- AO3: Analysis and evaluation (analyze, evaluate, make reasoned judgments)
- AO4: (where applicable) Practical/experimental skills

CAMBRIDGE ACTION WORDS:
Use Cambridge's official command/action words when writing objectives:
- Knowledge level (AO1): define, describe, give, identify, label, list, name, state
- Comprehension level (AO1-AO2): compare, distinguish, explain, interpret, outline, summarize
- Application level (AO2): apply, calculate, demonstrate, determine, illustrate, show, use
- Analysis level (AO3): analyse, classify, deduce, derive, examine, relate
- Synthesis level (AO3): construct, design, develop, formulate, plan, propose
- Evaluation level (AO3): assess, comment, criticise, discuss, evaluate, justify, recommend

REQUIREMENTS - BE COMPREHENSIVE:
1. Extract the official Assessment Objectives (AOs) with their weightings from the syllabus
2. For EACH syllabus topic/section, create multiple specific learning objectives:
   - At least 3-5 objectives per major topic area
   - Cover all cognitive levels (knowledge, application, analysis)
   - Each objective must start with a Cambridge action word
3. Organize objectives hierarchically by syllabus section
4. Include sub-objectives for complex topics
5. Reference specific syllabus content points in each objective

Return a JSON object with:
{{
    "assessment_objectives": [
        {{
            "code": "AO1",
            "name": "Knowledge with understanding",
            "weighting": "40%",
            "description": "Official Cambridge description from syllabus"
        }}
    ],
    "objectives": [
        {{
            "code": "1",
            "text": "Section 1: [Topic Name] - Top-level topic objective",
            "ao_mapping": ["AO1"],
            "syllabus_reference": "Section 1",
            "source": "explicit",
            "children": [
                {{
                    "code": "1.1",
                    "text": "Define and describe [specific concept] as outlined in the syllabus",
                    "ao_mapping": ["AO1"],
                    "syllabus_reference": "1.1",
                    "source": "explicit",
                    "children": []
                }},
                {{
                    "code": "1.2",
                    "text": "Apply [concept] to solve problems in familiar contexts",
                    "ao_mapping": ["AO2"],
                    "syllabus_reference": "1.1",
                    "source": "inferred",
                    "children": []
                }},
                {{
                    "code": "1.3",
                    "text": "Analyse and evaluate [concept] in unfamiliar situations",
                    "ao_mapping": ["AO3"],
                    "syllabus_reference": "1.1",
                    "source": "inferred",
                    "children": []
                }}
            ]
        }}
    ],
    "methodology_note": "Objectives derived from Cambridge syllabus content. Each syllabus section mapped to multiple objectives across AO levels."
}}

IMPORTANT: Generate objectives for EVERY section of the syllabus. A typical Cambridge syllabus has 4-8 major sections, each needing 10-20 specific objectives. Aim for 50-100 total objectives for comprehensive coverage.""",

    "cambridge_resources": """You are an expert on Cambridge Assessment International Education educational resources.
Find all endorsed and recommended resources for this Cambridge course.

Course Title: {course_name}
Syllabus Code: {syllabus_code}
Program: {program}
Official course page: {source_url}

Find ALL resources associated with this course including:
- Student-facing materials (textbooks, workbooks, revision guides)
- Teacher-facing materials (teacher guides, lesson plans, schemes of work)
- Companion materials (digital resources, online platforms)
- Supplementary materials (past papers, mark schemes, examiner reports)
- Complementary materials (enrichment resources, extension activities)

Return a JSON object with:
{{
    "student_resources": [
        {{
            "title": "Full book title",
            "authors": ["Author Name"],
            "publisher": "Publisher Name",
            "isbn": "ISBN-13",
            "url": "Publisher or retailer URL",
            "cover_url": "URL to book cover image",
            "type": "textbook|workbook|revision_guide|coursebook",
            "description": "Brief description"
        }}
    ],
    "teacher_resources": [
        {{
            "title": "Teacher Guide title",
            "authors": ["Author Name"],
            "publisher": "Publisher Name",
            "isbn": "ISBN-13",
            "url": "URL",
            "cover_url": "URL to cover image",
            "type": "teacher_guide|lesson_plans|scheme_of_work",
            "description": "Brief description"
        }}
    ],
    "digital_resources": [
        {{
            "title": "Resource name",
            "platform": "Cambridge GO|Elevate|Other",
            "url": "URL",
            "type": "online_textbook|practice_questions|videos",
            "description": "Brief description"
        }}
    ],
    "exam_materials": [
        {{
            "title": "Past Paper / Mark Scheme",
            "year": "2023",
            "session": "May/June|Oct/Nov",
            "paper": "Paper 1",
            "type": "past_paper|mark_scheme|examiner_report",
            "url": "URL if available"
        }}
    ]
}}

Include cover_url for books when available (typically from publisher websites or Cambridge).
Only include real, published resources. Do not invent resources.""",

    "cambridge_unofficial_resources": """You are an expert on third-party educational resources for Cambridge Assessment International Education courses.
Find high-quality UNOFFICIAL (third-party) resources for this Cambridge course.

Course Title: {course_name}
Syllabus Code: {syllabus_code}
Program: {program}
Official course page for reference: {source_url}

Find well-regarded third-party resources NOT published by Cambridge, including:
- Third-party textbooks and study guides
- Revision guides from other publishers (CGP, Hodder, etc.)
- Online video courses and tutorials
- Educational websites and platforms
- Community resources and forums

Return a JSON object with:
{{
    "student_resources": [
        {{
            "title": "Full book title",
            "authors": ["Author Name"],
            "publisher": "Publisher Name",
            "isbn": "ISBN-13",
            "url": "Publisher or retailer URL",
            "cover_url": "URL to book cover image",
            "type": "textbook|revision_guide|workbook|study_guide",
            "description": "Brief description"
        }}
    ],
    "digital_resources": [
        {{
            "title": "Resource name",
            "platform": "YouTube|Khan Academy|Coursera|Website",
            "url": "URL",
            "type": "video_course|practice_site|tutorial",
            "description": "Brief description"
        }}
    ],
    "websites": [
        {{
            "title": "Website name",
            "url": "URL",
            "description": "What the site offers"
        }}
    ]
}}

Include cover_url for books when available.
Only include well-known, reputable third-party resources. Do not invent resources.""",

    # =============================================================================
    # COLLEGE BOARD AP-SPECIFIC PROMPTS
    # =============================================================================

    "collegeboard_objectives": """You are an expert on College Board Advanced Placement (AP) curriculum frameworks.
Extract the COMPLETE learning objectives and Big Ideas hierarchy from this AP course's Course and Exam Description (CED).

Course Title: {course_name}
Course Code: {syllabus_code}
Official CED page: {source_url}

AP COURSE FRAMEWORK STRUCTURE:
College Board AP courses are organized around a hierarchical framework:
1. BIG IDEAS (BI) - Overarching conceptual themes (typically 3-7 per course)
2. ENDURING UNDERSTANDINGS (EU) - Key takeaways within each Big Idea
3. LEARNING OBJECTIVES (LO) - Specific, measurable outcomes students must demonstrate
4. ESSENTIAL KNOWLEDGE (EK) - Facts, concepts, and processes students must know
5. SCIENCE PRACTICES / SKILLS - Cross-cutting abilities (varies by subject)

REQUIREMENTS - EXTRACT EVERYTHING FROM THE CED:
1. ALL Big Ideas with their full titles and descriptions
2. ALL Enduring Understandings nested under their Big Ideas
3. ALL Learning Objectives with their official codes (e.g., LO 1.1.A)
4. ALL Essential Knowledge statements with codes
5. Skills/Practices framework if applicable

Return a JSON object with:
{{
    "course_code": "{syllabus_code}",
    "skills_framework": [
        {{
            "skill_category": "Skill Category Name",
            "code": "1",
            "description": "What this skill category covers",
            "skills": [
                {{"code": "1.A", "name": "Skill name", "description": "Skill description"}}
            ]
        }}
    ],
    "big_ideas": [
        {{
            "code": "BIG IDEA 1",
            "abbreviation": "BI1",
            "title": "Full Big Idea Title",
            "description": "Complete description of what this Big Idea encompasses",
            "enduring_understandings": [
                {{
                    "code": "EU 1.1",
                    "statement": "Full enduring understanding statement",
                    "learning_objectives": [
                        {{
                            "code": "LO 1.1.A",
                            "statement": "Full learning objective statement",
                            "essential_knowledge": [
                                {{
                                    "code": "EK 1.1.A.1",
                                    "statement": "Essential knowledge statement"
                                }}
                            ]
                        }}
                    ]
                }}
            ]
        }}
    ],
    "objectives": [
        {{
            "code": "1",
            "text": "Big Idea 1: [Title]",
            "source": "explicit",
            "children": [
                {{
                    "code": "1.1",
                    "text": "EU 1.1: [Enduring Understanding]",
                    "source": "explicit",
                    "children": [
                        {{
                            "code": "1.1.1",
                            "text": "LO 1.1.A: [Learning Objective]",
                            "source": "explicit",
                            "children": []
                        }}
                    ]
                }}
            ]
        }}
    ],
    "methodology_note": "Objectives extracted directly from the AP Course and Exam Description (CED). Big Ideas, Enduring Understandings, Learning Objectives, and Essential Knowledge are official College Board designations."
}}

IMPORTANT:
- Extract ALL content from the CED - a typical AP course has 3-7 Big Ideas, each with multiple Enduring Understandings and Learning Objectives
- The "objectives" array provides a flattened hierarchical view for the tree renderer
- Keep the "big_ideas" array with the full nested structure for detailed display
- Include exact codes as they appear in the CED (e.g., "LO 2.3.B", "EK 4.1.A.2")
- Be exhaustive - capture every Learning Objective in the CED""",
}


def get_tab_config(document, tab_id: str):
    """
    Get tab configuration for a document, with fallback hierarchy:
    1. Program-specific config
    2. Authority-level config
    3. None (caller should use defaults)
    """
    from core.models import ProviderTabConfig

    program = document.authority_program
    authority = program.authority

    # Try program-specific first
    config = ProviderTabConfig.objects.filter(
        program=program,
        tab_id=tab_id,
        is_active=True,
    ).first()

    if config:
        return config

    # Fall back to authority-level
    config = ProviderTabConfig.objects.filter(
        authority=authority,
        program__isnull=True,
        tab_id=tab_id,
        is_active=True,
    ).first()

    return config


def get_all_tab_configs(document):
    """
    Get all tab configurations for a document, merging program and authority configs.
    Program configs override authority configs for the same tab_id.
    """
    from core.models import ProviderTabConfig

    program = document.authority_program
    authority = program.authority

    # Get authority-level configs
    authority_configs = {
        c.tab_id: c
        for c in ProviderTabConfig.objects.filter(
            authority=authority,
            program__isnull=True,
            is_active=True,
        )
    }

    # Get program-specific configs (override authority)
    program_configs = {
        c.tab_id: c
        for c in ProviderTabConfig.objects.filter(
            program=program,
            is_active=True,
        )
    }

    # Merge: program overrides authority
    merged = {**authority_configs, **program_configs}

    # Return sorted by sort_order
    return sorted(merged.values(), key=lambda c: (c.sort_order, c.tab_id))


class UnifiedAIFetcher:
    """
    Single entry point for AI-powered data extraction.

    Consolidates all external API calls to OpenRouter for consistent
    handling, caching, and provenance tracking.
    """

    def __init__(self, model: str = "openai/gpt-4o-mini"):
        """
        Initialize the fetcher.

        Args:
            model: OpenRouter model to use (default: gpt-4o-mini for speed/cost)
        """
        self.model = model
        self._client = None

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize OpenAI client for OpenRouter."""
        if self._client is None:
            api_key = getattr(settings, "OPENROUTER_API_KEY", None)
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not configured in settings")
            self._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        return self._client

    def fetch_tab_data(
        self,
        document,
        tab_config=None,
        tab_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict:
        """
        Fetch data for a tab using OpenRouter.

        Args:
            document: StandardsDocument instance
            tab_config: ProviderTabConfig instance (optional, will look up if not provided)
            tab_id: Tab ID to fetch (required if tab_config not provided)
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Dict with tab data

        Raises:
            ValueError: If neither tab_config nor tab_id provided
        """
        from core.models import TabDataCache

        if tab_config is None and tab_id is None:
            raise ValueError("Either tab_config or tab_id must be provided")

        if tab_config is None:
            tab_config = get_tab_config(document, tab_id)

        effective_tab_id = tab_config.tab_id if tab_config else tab_id

        # Check cache first (unless forcing refresh)
        if not force_refresh:
            cache = TabDataCache.objects.filter(
                document=document,
                tab_id=effective_tab_id,
            ).first()
            if cache and cache.is_fresh():
                logger.debug(f"Using cached data for {document.pk}/{effective_tab_id}")
                return cache.data

        # Build context from document
        context = self._build_document_context(document)

        # Get extraction prompt
        prompt = self._get_prompt(tab_config, effective_tab_id, context)

        # Call OpenRouter
        try:
            result, usage = self._call_openrouter(prompt)
        except Exception as e:
            logger.error(f"OpenRouter call failed for {document.pk}/{effective_tab_id}: {e}")
            # Update cache with error
            TabDataCache.objects.update_or_create(
                document=document,
                tab_id=effective_tab_id,
                defaults={
                    "data": {},
                    "fetch_status": "error",
                    "error_message": str(e),
                    "fetch_method_used": "ai_extract",
                    "ai_model_used": self.model,
                },
            )
            raise

        # Cache result
        TabDataCache.objects.update_or_create(
            document=document,
            tab_id=effective_tab_id,
            defaults={
                "data": result,
                "fetch_status": "success",
                "error_message": "",
                "fetch_method_used": "ai_extract",
                "ai_model_used": self.model,
                "tokens_used": usage.get("total_tokens") if usage else None,
            },
        )

        logger.info(f"Fetched fresh data for {document.pk}/{effective_tab_id}")
        return result

    def _build_document_context(self, document) -> dict:
        """Build context dict from document for prompt templating."""
        return {
            "course_name": document.source_title,
            "syllabus_code": document.syllabus_code or "",
            "source_url": document.source_url or "",
            "subject": document.subject,
            "grade_level": document.grade_level,
            "authority": document.authority_program.authority.name,
            "program": document.authority_program.name,
            "version": document.version_label or "",
        }

    def _get_prompt(self, tab_config, tab_id: str, context: dict) -> str:
        """Get the prompt template and fill in context."""
        if tab_config and tab_config.ai_extraction_prompt:
            # Check if it's a reference to a named prompt in DEFAULT_TAB_PROMPTS
            prompt_ref = tab_config.ai_extraction_prompt
            if prompt_ref in DEFAULT_TAB_PROMPTS:
                template = DEFAULT_TAB_PROMPTS[prompt_ref]
            else:
                # Treat as literal prompt template
                template = prompt_ref
        else:
            template = DEFAULT_TAB_PROMPTS.get(tab_id, DEFAULT_TAB_PROMPTS["overview"])

        # Fill in template variables
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            # Try partial formatting
            for key, value in context.items():
                template = template.replace(f"{{{key}}}", str(value))
            return template

    def _call_openrouter(self, prompt: str) -> tuple[dict, Optional[dict]]:
        """
        Make a single call to OpenRouter.

        Returns:
            Tuple of (parsed_result, usage_info)
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that returns only valid JSON as described in the prompt. Do not include any explanation or markdown formatting.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
            )

            content = completion.choices[0].message.content
            result = json.loads(content)

            # Extract usage info
            usage = None
            if completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

            return result, usage

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenRouter response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from AI: {e}")

    def fetch_multiple_tabs(
        self,
        document,
        tab_ids: list[str],
        force_refresh: bool = False,
    ) -> dict[str, dict]:
        """
        Fetch data for multiple tabs.

        Args:
            document: StandardsDocument instance
            tab_ids: List of tab IDs to fetch
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Dict mapping tab_id -> data
        """
        results = {}
        for tab_id in tab_ids:
            try:
                results[tab_id] = self.fetch_tab_data(
                    document,
                    tab_id=tab_id,
                    force_refresh=force_refresh,
                )
            except Exception as e:
                logger.error(f"Failed to fetch {tab_id} for {document.pk}: {e}")
                results[tab_id] = {"error": str(e)}
        return results
