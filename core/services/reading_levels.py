"""
Reading Level Analysis and Conversion Utility

Supports multiple reading level systems:
- Lexile (MetaMetrics)
- ATOS / Accelerated Reader (Renaissance Learning)
- Flesch-Kincaid Grade Level
- Guided Reading (Fountas & Pinnell)
- DRA (Developmental Reading Assessment)

Conversion formulas derived from published correlation studies.
"""

import re
from dataclasses import dataclass
from typing import Optional
from html.parser import HTMLParser

try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False


# =============================================================================
# CONVERSION TABLES
# =============================================================================

# Grade to Lexile mapping (mid-year typical ranges)
# Source: Lexile Grade Level Charts (MetaMetrics)
GRADE_TO_LEXILE = {
    "K": (0, 300),
    "1": (200, 400),
    "2": (300, 500),
    "3": (500, 700),
    "4": (650, 850),
    "5": (750, 950),
    "6": (850, 1050),
    "7": (950, 1100),
    "8": (1000, 1150),
    "9": (1050, 1200),
    "10": (1100, 1250),
    "11": (1150, 1300),
    "12": (1200, 1400),
}

# ATOS to Lexile approximate conversion
# Source: Regression analysis of published AR/Lexile correlations
# Formula: Lexile ≈ (ATOS - 0.5) * 150 + 100
ATOS_TO_LEXILE_COEFFICIENTS = (150, -25)  # slope, intercept adjustment

# Guided Reading levels (Fountas & Pinnell) to Grade mapping
GUIDED_READING_TO_GRADE = {
    "A": 0.0, "B": 0.2, "C": 0.4, "D": 0.6,
    "E": 0.8, "F": 1.0, "G": 1.2, "H": 1.4,
    "I": 1.6, "J": 1.8, "K": 2.0, "L": 2.3,
    "M": 2.6, "N": 3.0, "O": 3.3, "P": 3.6,
    "Q": 4.0, "R": 4.3, "S": 4.6, "T": 5.0,
    "U": 5.3, "V": 5.6, "W": 6.0, "X": 6.5,
    "Y": 7.0, "Z": 8.0, "Z+": 9.0,
}

# Grade to Guided Reading (approximate)
GRADE_TO_GUIDED_READING = {
    0: "A-D", 0.5: "D-F", 1: "E-J", 1.5: "H-L",
    2: "J-M", 2.5: "L-O", 3: "M-P", 3.5: "O-R",
    4: "P-S", 4.5: "R-T", 5: "S-V", 5.5: "U-W",
    6: "V-X", 7: "W-Y", 8: "X-Z", 9: "Z", 10: "Z+",
}

# AR Points estimation (based on word count)
# Standard formula: Points ≈ Word Count / 10,000 (rounded)
# With minimum of 0.5 for any substantial text
AR_POINTS_WORDS_PER_POINT = 10000


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ReadingLevelMetrics:
    """Comprehensive reading level analysis results."""
    # Raw metrics
    word_count: int
    sentence_count: int
    syllable_count: int
    avg_sentence_length: float
    avg_syllables_per_word: float
    difficult_word_count: int
    difficult_word_pct: float

    # Computed grade levels
    flesch_kincaid_grade: float
    atos_level: float  # AR Book Level (same as FK grade, essentially)
    grade_level: float  # Averaged estimate

    # Lexile
    lexile_estimate: int
    lexile_range: tuple  # (low, high)
    lexile_label: str

    # Other systems
    guided_reading: str
    dra_level: Optional[int]

    # AR-specific
    ar_points: float
    ar_interest_level: str  # LG, MG, MG+, UG

    # Raw scores for reference
    flesch_reading_ease: float
    dale_chall_score: float
    smog_index: float
    coleman_liau_index: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "syllable_count": self.syllable_count,
            "avg_sentence_length": self.avg_sentence_length,
            "avg_syllables_per_word": self.avg_syllables_per_word,
            "difficult_word_count": self.difficult_word_count,
            "difficult_word_pct": self.difficult_word_pct,
            "flesch_kincaid_grade": self.flesch_kincaid_grade,
            "atos_level": self.atos_level,
            "grade_level": self.grade_level,
            "lexile_estimate": self.lexile_estimate,
            "lexile_range": list(self.lexile_range),
            "lexile_label": self.lexile_label,
            "guided_reading": self.guided_reading,
            "dra_level": self.dra_level,
            "ar_points": self.ar_points,
            "ar_interest_level": self.ar_interest_level,
            "flesch_reading_ease": self.flesch_reading_ease,
            "dale_chall_score": self.dale_chall_score,
            "smog_index": self.smog_index,
            "coleman_liau_index": self.coleman_liau_index,
        }

    @property
    def ar_level_display(self) -> str:
        """Format ATOS level for display (e.g., '4.5')."""
        return f"{self.atos_level:.1f}"

    @property
    def lexile_display(self) -> str:
        """Format Lexile for display (e.g., '720L')."""
        return f"{self.lexile_estimate}L"

    @property
    def grade_display(self) -> str:
        """Format grade level for display."""
        grade = int(self.grade_level)
        month = int((self.grade_level - grade) * 10)
        if grade == 0:
            return "K" if month < 5 else "K-1"
        return f"Grade {grade}"


# =============================================================================
# TEXT UTILITIES
# =============================================================================

class HTMLStripper(HTMLParser):
    """Strip HTML tags from text."""
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return ' '.join(self.text_parts)


def strip_html(html_text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not html_text:
        return ""

    # Quick check if there's any HTML
    if '<' not in html_text:
        return html_text

    stripper = HTMLStripper()
    try:
        stripper.feed(html_text)
        text = stripper.get_text()
    except Exception:
        # Fallback regex if parser fails
        text = re.sub(r'<[^>]+>', ' ', html_text)

    # Decode common entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# =============================================================================
# CONVERSION FUNCTIONS
# =============================================================================

def lexile_to_grade(lexile: int) -> float:
    """Convert Lexile to approximate grade level."""
    # Inverse of grade-to-Lexile formula
    # Lexile ≈ 200 + (grade * 100)
    # grade ≈ (Lexile - 200) / 100
    if lexile < 0:
        return 0.0
    grade = (lexile - 200) / 100
    return max(0.0, min(12.9, grade))


def grade_to_lexile(grade: float) -> int:
    """Convert grade level to approximate Lexile."""
    # Lexile ≈ 200 + (grade * 100)
    lexile = 200 + (grade * 100)
    return max(0, min(1700, int(lexile)))


def atos_to_lexile(atos: float) -> int:
    """Convert ATOS/AR level to approximate Lexile."""
    # ATOS is essentially the same as Flesch-Kincaid grade level
    # Lexile ≈ 200 + (ATOS * 100)
    return grade_to_lexile(atos)


def lexile_to_atos(lexile: int) -> float:
    """Convert Lexile to approximate ATOS/AR level."""
    return lexile_to_grade(lexile)


def grade_to_guided_reading(grade: float) -> str:
    """Convert grade level to Guided Reading level range."""
    # Find closest grade key
    grade_keys = sorted(GRADE_TO_GUIDED_READING.keys())
    closest = min(grade_keys, key=lambda k: abs(k - grade))
    return GRADE_TO_GUIDED_READING[closest]


def guided_reading_to_grade(gr_level: str) -> float:
    """Convert Guided Reading level to grade equivalent."""
    level = gr_level.upper().strip()
    if level in GUIDED_READING_TO_GRADE:
        return GUIDED_READING_TO_GRADE[level]
    # Handle ranges like "M-P"
    if "-" in level:
        first = level.split("-")[0]
        if first in GUIDED_READING_TO_GRADE:
            return GUIDED_READING_TO_GRADE[first]
    return 3.0  # Default to 3rd grade


def grade_to_dra(grade: float) -> int:
    """Convert grade level to DRA level."""
    # DRA levels roughly follow: grade * 10 for early grades
    if grade < 1:
        return int(grade * 10) + 1  # A=1, 2, 3, 4
    elif grade < 3:
        return int(10 + (grade - 1) * 10)  # 10-30
    else:
        return int(30 + (grade - 3) * 4)  # 34, 38, 40, 44, 50, etc.


def estimate_ar_points(word_count: int) -> float:
    """
    Estimate AR quiz points based on word count.

    AR points are generally: word_count / 10,000 (rounded)
    with a minimum of 0.5 for any substantial text.
    """
    if word_count < 500:
        return 0.5
    points = word_count / AR_POINTS_WORDS_PER_POINT
    # Round to nearest 0.5
    return max(0.5, round(points * 2) / 2)


def get_ar_interest_level(grade: float, content_maturity: str = "general") -> str:
    """
    Determine AR Interest Level based on grade and content.

    Interest Levels:
    - LG: Lower Grades (K-3)
    - MG: Middle Grades (4-8)
    - MG+: Middle Grades Plus (6+, more mature themes)
    - UG: Upper Grades (9-12)
    """
    if grade < 3.5:
        return "LG"
    elif grade < 6:
        return "MG"
    elif grade < 9:
        return "MG+" if content_maturity == "mature" else "MG"
    else:
        return "UG"


def get_lexile_label(lexile: int) -> str:
    """Get a descriptive label for a Lexile score."""
    if lexile < 200:
        return "Beginning Reader (BR)"
    elif lexile < 400:
        return "Grade K-1"
    elif lexile < 600:
        return "Grade 2-3"
    elif lexile < 800:
        return "Grade 4-5"
    elif lexile < 1000:
        return "Grade 6-8"
    elif lexile < 1200:
        return "Grade 9-10"
    elif lexile < 1400:
        return "Grade 11-12"
    else:
        return "College Level"


def get_lexile_range_for_grade(grade: float) -> tuple:
    """Get the typical Lexile range for a grade level."""
    grade_str = str(int(min(12, max(0, grade))))
    if grade_str == "0":
        grade_str = "K"
    if grade_str in GRADE_TO_LEXILE:
        return GRADE_TO_LEXILE[grade_str]
    # Interpolate for grades not in table
    low = 200 + int(grade * 100) - 50
    high = 200 + int(grade * 100) + 100
    return (max(0, low), min(1700, high))


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_reading_level(text: str) -> Optional[ReadingLevelMetrics]:
    """
    Perform comprehensive reading level analysis on text.

    Args:
        text: Plain text or HTML content to analyze

    Returns:
        ReadingLevelMetrics object with all computed levels, or None if text is too short
    """
    if not TEXTSTAT_AVAILABLE:
        raise ImportError("textstat library required for reading level analysis. Install with: pip install textstat")

    # Clean text
    plain_text = strip_html(text) if '<' in text else text

    if not plain_text or len(plain_text.split()) < 30:
        return None

    # Get basic counts
    word_count = textstat.lexicon_count(plain_text, removepunct=True)
    sentence_count = textstat.sentence_count(plain_text)
    syllable_count = textstat.syllable_count(plain_text)

    if sentence_count == 0 or word_count == 0:
        return None

    # Derived metrics
    avg_sentence_length = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count

    # Difficult words
    difficult_word_count = textstat.difficult_words(plain_text)
    difficult_word_pct = (difficult_word_count / word_count * 100) if word_count > 0 else 0

    # Get readability scores
    flesch_kincaid_grade = textstat.flesch_kincaid_grade(plain_text)
    flesch_reading_ease = textstat.flesch_reading_ease(plain_text)
    dale_chall_score = textstat.dale_chall_readability_score(plain_text)
    smog_index = textstat.smog_index(plain_text)
    coleman_liau_index = textstat.coleman_liau_index(plain_text)

    # Average multiple grade estimates for robustness
    grade_estimates = [
        flesch_kincaid_grade,
        dale_chall_score,
        smog_index,
        coleman_liau_index,
    ]
    valid_grades = [g for g in grade_estimates if g is not None and 0 <= g <= 18]
    avg_grade = sum(valid_grades) / len(valid_grades) if valid_grades else flesch_kincaid_grade or 5.0

    # Clamp to reasonable range
    avg_grade = max(0.0, min(12.9, avg_grade))

    # ATOS is essentially the same as Flesch-Kincaid
    atos_level = round(flesch_kincaid_grade, 1) if flesch_kincaid_grade else avg_grade

    # Lexile estimation
    base_lexile = grade_to_lexile(avg_grade)
    # Adjust based on text complexity factors
    sentence_adjustment = (avg_sentence_length - 15) * 3
    difficulty_adjustment = (difficult_word_pct - 10) * 5
    lexile_estimate = int(base_lexile + sentence_adjustment + difficulty_adjustment)
    lexile_estimate = max(0, min(1700, lexile_estimate))

    # Get range and label
    lexile_range = get_lexile_range_for_grade(avg_grade)
    lexile_label = get_lexile_label(lexile_estimate)

    # Guided Reading
    guided_reading = grade_to_guided_reading(avg_grade)

    # DRA
    dra_level = grade_to_dra(avg_grade)

    # AR Points
    ar_points = estimate_ar_points(word_count)

    # AR Interest Level
    ar_interest_level = get_ar_interest_level(avg_grade)

    return ReadingLevelMetrics(
        word_count=word_count,
        sentence_count=sentence_count,
        syllable_count=syllable_count,
        avg_sentence_length=round(avg_sentence_length, 1),
        avg_syllables_per_word=round(avg_syllables_per_word, 2),
        difficult_word_count=difficult_word_count,
        difficult_word_pct=round(difficult_word_pct, 1),
        flesch_kincaid_grade=round(flesch_kincaid_grade, 1) if flesch_kincaid_grade else 0.0,
        atos_level=round(atos_level, 1),
        grade_level=round(avg_grade, 1),
        lexile_estimate=lexile_estimate,
        lexile_range=lexile_range,
        lexile_label=lexile_label,
        guided_reading=guided_reading,
        dra_level=dra_level,
        ar_points=ar_points,
        ar_interest_level=ar_interest_level,
        flesch_reading_ease=round(flesch_reading_ease, 1) if flesch_reading_ease else 0.0,
        dale_chall_score=round(dale_chall_score, 1) if dale_chall_score else 0.0,
        smog_index=round(smog_index, 1) if smog_index else 0.0,
        coleman_liau_index=round(coleman_liau_index, 1) if coleman_liau_index else 0.0,
    )


def format_reading_level_display(metrics: ReadingLevelMetrics, format: str = "full") -> str:
    """
    Format reading level metrics for display.

    Args:
        metrics: ReadingLevelMetrics object
        format: "full", "compact", "ar", "lexile"

    Returns:
        Formatted string
    """
    if format == "ar":
        return f"AR {metrics.ar_level_display} ({metrics.ar_interest_level})"
    elif format == "lexile":
        return metrics.lexile_display
    elif format == "compact":
        return f"{metrics.lexile_display} / AR {metrics.ar_level_display}"
    else:  # full
        return (
            f"{metrics.lexile_display} | "
            f"AR {metrics.ar_level_display} | "
            f"GR {metrics.guided_reading} | "
            f"{metrics.grade_display}"
        )
