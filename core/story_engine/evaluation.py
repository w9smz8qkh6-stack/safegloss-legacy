"""
Story Engine Evaluation Harness

Batch-generates stories across bands/genres and reports distributions.
Used for quality assurance and regression testing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .profile_builder import WritingProfileBuilder
from .prompt_composer import PromptComposer, ComposedPrompt
from .validator import StoryValidator, ValidationResult
from .text_metrics import extract_metrics, TextMetrics


@dataclass
class EvaluationCase:
    """A single evaluation test case."""
    name: str
    age_band: str
    genre: str
    lexile_band: str
    theme: str
    word_count: int = 400
    style_profile: str | None = None
    ell_mode: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "age_band": self.age_band,
            "genre": self.genre,
            "lexile_band": self.lexile_band,
            "theme": self.theme,
            "word_count": self.word_count,
            "style_profile": self.style_profile,
            "ell_mode": self.ell_mode,
        }


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    case: EvaluationCase
    validation_result: ValidationResult | None = None
    prompt: ComposedPrompt | None = None
    story_text: str | None = None
    passed: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "case": self.case.to_dict(),
            "passed": self.passed,
            "validation_score": self.validation_result.score if self.validation_result else None,
            "issue_count": len(self.validation_result.issues) if self.validation_result else None,
            "error": self.error,
        }


@dataclass
class EvaluationReport:
    """Summary report of batch evaluation."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    results_by_band: dict = field(default_factory=dict)
    results_by_genre: dict = field(default_factory=dict)
    results_by_style: dict = field(default_factory=dict)
    results: list[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "error_cases": self.error_cases,
            "pass_rate": round(self.pass_rate, 3),
            "avg_score": round(self.avg_score, 3),
            "results_by_band": self.results_by_band,
            "results_by_genre": self.results_by_genre,
            "results_by_style": self.results_by_style,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 50,
            "EVALUATION REPORT",
            "=" * 50,
            f"Timestamp: {self.timestamp}",
            f"Total Cases: {self.total_cases}",
            f"Passed: {self.passed_cases} ({self.pass_rate:.1%})",
            f"Failed: {self.failed_cases}",
            f"Errors: {self.error_cases}",
            f"Average Score: {self.avg_score:.2f}",
            "",
            "Results by Lexile Band:",
        ]
        for band, stats in sorted(self.results_by_band.items()):
            lines.append(f"  {band}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1%})")

        lines.append("")
        lines.append("Results by Genre:")
        for genre, stats in sorted(self.results_by_genre.items()):
            lines.append(f"  {genre}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1%})")

        if self.results_by_style:
            lines.append("")
            lines.append("Results by Style:")
            for style, stats in sorted(self.results_by_style.items()):
                lines.append(f"  {style}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1%})")

        lines.append("=" * 50)
        return "\n".join(lines)


class EvaluationHarness:
    """
    Batch evaluation harness for story generation.

    Can run in two modes:
    1. Prompt-only mode: Tests profile building and prompt composition
    2. Full mode: Also tests generated stories (requires a generation callback)
    """

    # Default test matrix
    DEFAULT_AGE_BANDS = ["6-8", "8-10", "10-12", "12-14"]
    DEFAULT_LEXILE_BANDS = ["300-400L", "400-500L", "500-600L", "600-700L", "700-900L", "900-1100L"]
    DEFAULT_GENRES = ["realistic_fiction", "fantasy", "mystery", "informational_fiction"]
    DEFAULT_STYLES = [None, "minimalist", "cinematic", "humorous", "adventure"]
    DEFAULT_THEMES = {
        "realistic_fiction": "friendship and kindness",
        "fantasy": "magical adventure",
        "mystery": "solving a puzzle",
        "informational_fiction": "nature and animals",
    }

    def __init__(self):
        self.builder = WritingProfileBuilder()
        self.composer = PromptComposer()
        self.validator = StoryValidator()

    def generate_test_matrix(
        self,
        age_bands: list[str] | None = None,
        lexile_bands: list[str] | None = None,
        genres: list[str] | None = None,
        styles: list[str | None] | None = None,
        include_ell: bool = False,
    ) -> list[EvaluationCase]:
        """
        Generate a matrix of test cases.

        Args:
            age_bands: Age bands to test (default: all)
            lexile_bands: Lexile bands to test (default: all)
            genres: Genres to test (default: all)
            styles: Style profiles to test (default: common ones)
            include_ell: Whether to include ELL mode variations

        Returns:
            List of EvaluationCase objects
        """
        age_bands = age_bands or self.DEFAULT_AGE_BANDS
        lexile_bands = lexile_bands or self.DEFAULT_LEXILE_BANDS
        genres = genres or self.DEFAULT_GENRES
        styles = styles if styles is not None else [None]  # Default to no style

        cases = []
        case_num = 0

        for age in age_bands:
            # Find appropriate Lexile bands for this age
            appropriate_bands = self._filter_bands_for_age(age, lexile_bands)

            for band in appropriate_bands:
                for genre in genres:
                    for style in styles:
                        case_num += 1
                        theme = self.DEFAULT_THEMES.get(genre, "adventure")
                        cases.append(EvaluationCase(
                            name=f"case_{case_num:03d}_{age}_{band}_{genre}",
                            age_band=age,
                            genre=genre,
                            lexile_band=band,
                            theme=theme,
                            style_profile=style,
                        ))

                        if include_ell:
                            for ell_level in ["beginner", "intermediate"]:
                                case_num += 1
                                cases.append(EvaluationCase(
                                    name=f"case_{case_num:03d}_{age}_{band}_{genre}_ell_{ell_level}",
                                    age_band=age,
                                    genre=genre,
                                    lexile_band=band,
                                    theme=theme,
                                    style_profile=style,
                                    ell_mode=ell_level,
                                ))

        return cases

    def _filter_bands_for_age(self, age_band: str, lexile_bands: list[str]) -> list[str]:
        """Filter Lexile bands to those appropriate for an age band."""
        age_to_bands = {
            "6-8": ["300-400L", "400-500L"],
            "8-10": ["400-500L", "500-600L", "600-700L"],
            "10-12": ["600-700L", "700-900L"],
            "12-14": ["700-900L", "900-1100L"],
        }
        appropriate = set(age_to_bands.get(age_band, lexile_bands))
        return [b for b in lexile_bands if b in appropriate]

    def evaluate_prompt_only(self, cases: list[EvaluationCase]) -> EvaluationReport:
        """
        Evaluate prompt generation only (no actual story generation).

        Tests that profiles build correctly and prompts compose without errors.
        """
        report = EvaluationReport(total_cases=len(cases))
        scores = []

        for case in cases:
            result = EvaluationResult(case=case)
            try:
                # Build profile
                profile = self.builder.build(
                    age_band=case.age_band,
                    genre=case.genre,
                    lexile_band=case.lexile_band,
                    style_profile=case.style_profile,
                    ell_mode=case.ell_mode,
                    theme=case.theme,
                )

                # Compose prompt
                prompt = self.composer.compose(
                    profile=profile,
                    theme=case.theme,
                    word_count=case.word_count,
                )

                result.prompt = prompt
                result.passed = True
                report.passed_cases += 1
                scores.append(1.0)

            except Exception as e:
                result.error = str(e)
                result.passed = False
                report.error_cases += 1
                scores.append(0.0)

            report.results.append(result)
            self._update_distribution_stats(report, result)

        report.failed_cases = report.total_cases - report.passed_cases - report.error_cases
        report.pass_rate = report.passed_cases / report.total_cases if report.total_cases > 0 else 0
        report.avg_score = sum(scores) / len(scores) if scores else 0

        return report

    def evaluate_with_stories(
        self,
        cases: list[EvaluationCase],
        story_generator: Callable[[ComposedPrompt], str],
    ) -> EvaluationReport:
        """
        Full evaluation with story generation.

        Args:
            cases: Test cases to evaluate
            story_generator: Callback that takes a ComposedPrompt and returns generated text

        Returns:
            EvaluationReport with validation results
        """
        report = EvaluationReport(total_cases=len(cases))
        scores = []

        for case in cases:
            result = EvaluationResult(case=case)
            try:
                # Build profile
                profile = self.builder.build(
                    age_band=case.age_band,
                    genre=case.genre,
                    lexile_band=case.lexile_band,
                    style_profile=case.style_profile,
                    ell_mode=case.ell_mode,
                    theme=case.theme,
                )

                # Compose prompt
                prompt = self.composer.compose(
                    profile=profile,
                    theme=case.theme,
                    word_count=case.word_count,
                )
                result.prompt = prompt

                # Generate story
                story_text = story_generator(prompt)
                result.story_text = story_text

                # Validate
                validation = self.validator.validate(
                    text=story_text,
                    lexile_band=case.lexile_band,
                    target_word_count=case.word_count,
                )
                result.validation_result = validation
                result.passed = validation.valid
                scores.append(validation.score)

                if validation.valid:
                    report.passed_cases += 1
                else:
                    report.failed_cases += 1

            except Exception as e:
                result.error = str(e)
                result.passed = False
                report.error_cases += 1
                scores.append(0.0)

            report.results.append(result)
            self._update_distribution_stats(report, result)

        report.pass_rate = report.passed_cases / report.total_cases if report.total_cases > 0 else 0
        report.avg_score = sum(scores) / len(scores) if scores else 0

        return report

    def _update_distribution_stats(
        self,
        report: EvaluationReport,
        result: EvaluationResult,
    ) -> None:
        """Update distribution statistics in the report."""
        case = result.case

        # By Lexile band
        if case.lexile_band not in report.results_by_band:
            report.results_by_band[case.lexile_band] = {"total": 0, "passed": 0, "pass_rate": 0}
        report.results_by_band[case.lexile_band]["total"] += 1
        if result.passed:
            report.results_by_band[case.lexile_band]["passed"] += 1
        report.results_by_band[case.lexile_band]["pass_rate"] = (
            report.results_by_band[case.lexile_band]["passed"] /
            report.results_by_band[case.lexile_band]["total"]
        )

        # By genre
        if case.genre not in report.results_by_genre:
            report.results_by_genre[case.genre] = {"total": 0, "passed": 0, "pass_rate": 0}
        report.results_by_genre[case.genre]["total"] += 1
        if result.passed:
            report.results_by_genre[case.genre]["passed"] += 1
        report.results_by_genre[case.genre]["pass_rate"] = (
            report.results_by_genre[case.genre]["passed"] /
            report.results_by_genre[case.genre]["total"]
        )

        # By style (if applicable)
        style = case.style_profile or "none"
        if style not in report.results_by_style:
            report.results_by_style[style] = {"total": 0, "passed": 0, "pass_rate": 0}
        report.results_by_style[style]["total"] += 1
        if result.passed:
            report.results_by_style[style]["passed"] += 1
        report.results_by_style[style]["pass_rate"] = (
            report.results_by_style[style]["passed"] /
            report.results_by_style[style]["total"]
        )

    def save_report(self, report: EvaluationReport, path: str | Path) -> None:
        """Save evaluation report to a JSON file."""
        path = Path(path)
        with open(path, "w") as f:
            f.write(report.to_json())


def run_prompt_evaluation(
    output_path: str | Path | None = None,
) -> EvaluationReport:
    """
    Convenience function to run prompt-only evaluation with default settings.

    Args:
        output_path: Optional path to save the report

    Returns:
        EvaluationReport
    """
    harness = EvaluationHarness()
    cases = harness.generate_test_matrix()
    report = harness.evaluate_prompt_only(cases)

    if output_path:
        harness.save_report(report, output_path)

    return report
