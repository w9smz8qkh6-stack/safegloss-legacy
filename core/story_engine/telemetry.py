"""
Story Generation Telemetry

Logs per-story generation data for observability and debugging.
Stores: request params, merged profile, prompt hash, validation metrics,
iteration count, and final metrics.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
from pathlib import Path

from .profile_builder import WritingProfile
from .validator import ValidationResult
from .text_metrics import TextMetrics


logger = logging.getLogger(__name__)


@dataclass
class GenerationRecord:
    """
    Complete record of a story generation attempt.

    This is the primary telemetry object that captures all data
    about a generation request for auditing and analysis.
    """
    # Request identification
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Request parameters
    age_band: str = ""
    genre: str = ""
    lexile_band: str = ""
    theme: str = ""
    word_count: int = 0
    style_profile: str | None = None
    ell_mode: str | None = None
    study_mode: bool = False
    vocabulary_mode: str = "none"

    # Profile data
    profile_hash: str = ""
    profile_version: str = "1.0.0"

    # Generation data
    prompt_hash: str = ""
    model_used: str = ""
    generation_time_ms: int = 0

    # Validation data
    validation_score: float = 0.0
    validation_passed: bool = False
    validation_issues: list[dict] = field(default_factory=list)
    iteration_count: int = 1

    # Final metrics
    final_word_count: int = 0
    final_avg_sentence_length: float = 0.0
    final_dialogue_ratio: float = 0.0
    final_passive_voice_ratio: float = 0.0

    # Status
    status: str = "pending"  # pending, success, failed, validation_failed
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class TelemetryLogger:
    """
    Logs story generation telemetry data.

    Supports multiple output modes:
    - Python logging (default)
    - JSON file output
    - In-memory storage (for testing)
    """

    def __init__(
        self,
        log_to_file: bool = False,
        file_path: str | Path | None = None,
        in_memory: bool = False,
    ):
        self.log_to_file = log_to_file
        self.file_path = Path(file_path) if file_path else None
        self.in_memory = in_memory
        self._records: list[GenerationRecord] = []

    def start_generation(
        self,
        request_id: str,
        profile: WritingProfile,
        theme: str,
        word_count: int,
    ) -> GenerationRecord:
        """
        Start tracking a new generation request.

        Args:
            request_id: Unique identifier for this request
            profile: The assembled WritingProfile
            theme: Story theme
            word_count: Target word count

        Returns:
            GenerationRecord to be updated as generation progresses
        """
        record = GenerationRecord(
            request_id=request_id,
            age_band=profile.age_band,
            genre=profile.genre,
            lexile_band=profile.lexile_band,
            theme=theme,
            word_count=word_count,
            style_profile=profile.style_profile,
            ell_mode=profile.ell_mode,
            study_mode=profile.study_mode,
            vocabulary_mode=profile.vocab_constraints.mode,
            profile_hash=profile.profile_hash,
            profile_version=profile.version,
            status="in_progress",
        )

        logger.info(
            f"Generation started: {request_id} | "
            f"age={profile.age_band} lexile={profile.lexile_band} "
            f"genre={profile.genre} style={profile.style_profile}"
        )

        return record

    def record_prompt(self, record: GenerationRecord, prompt_hash: str) -> None:
        """Record the prompt hash."""
        record.prompt_hash = prompt_hash

    def record_model(self, record: GenerationRecord, model: str) -> None:
        """Record the model used for generation."""
        record.model_used = model

    def record_generation_time(self, record: GenerationRecord, time_ms: int) -> None:
        """Record generation time in milliseconds."""
        record.generation_time_ms = time_ms

    def record_validation(
        self,
        record: GenerationRecord,
        result: ValidationResult,
        iteration: int = 1,
    ) -> None:
        """
        Record validation results.

        Args:
            record: The generation record to update
            result: Validation result from StoryValidator
            iteration: Which iteration this is (for rewrite loops)
        """
        record.validation_score = result.score
        record.validation_passed = result.valid
        record.validation_issues = [
            {
                "code": issue.code,
                "severity": issue.severity.value,
                "message": issue.message,
                "metric": issue.metric_name,
                "actual": issue.actual_value,
            }
            for issue in result.issues
        ]
        record.iteration_count = iteration

        if result.metrics:
            record.final_word_count = result.metrics.total_words
            record.final_avg_sentence_length = result.metrics.avg_sentence_length
            record.final_dialogue_ratio = result.metrics.dialogue_ratio
            record.final_passive_voice_ratio = result.metrics.passive_voice_ratio

    def record_metrics(self, record: GenerationRecord, metrics: TextMetrics) -> None:
        """Record final text metrics."""
        record.final_word_count = metrics.total_words
        record.final_avg_sentence_length = metrics.avg_sentence_length
        record.final_dialogue_ratio = metrics.dialogue_ratio
        record.final_passive_voice_ratio = metrics.passive_voice_ratio

    def complete_generation(
        self,
        record: GenerationRecord,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """
        Mark generation as complete and log the record.

        Args:
            record: The generation record to finalize
            success: Whether generation succeeded
            error: Error message if failed
        """
        if success:
            record.status = "success" if record.validation_passed else "validation_failed"
        else:
            record.status = "failed"
            record.error_message = error

        # Log the completion
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"Generation complete: {record.request_id} | "
            f"status={record.status} score={record.validation_score:.2f} "
            f"iterations={record.iteration_count} words={record.final_word_count}"
        )

        # Store/output the record
        self._output_record(record)

    def _output_record(self, record: GenerationRecord) -> None:
        """Output the record to configured destinations."""
        if self.in_memory:
            self._records.append(record)

        if self.log_to_file and self.file_path:
            self._write_to_file(record)

        # Always log structured data at DEBUG level
        logger.debug(f"Generation record: {record.to_json()}")

    def _write_to_file(self, record: GenerationRecord) -> None:
        """Append record to JSON lines file."""
        try:
            with open(self.file_path, "a") as f:
                f.write(record.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write telemetry to file: {e}")

    def get_records(self) -> list[GenerationRecord]:
        """Get all in-memory records (for testing)."""
        return self._records.copy()

    def clear_records(self) -> None:
        """Clear in-memory records (for testing)."""
        self._records.clear()


# Global telemetry logger instance
_telemetry_logger: TelemetryLogger | None = None


def get_telemetry_logger() -> TelemetryLogger:
    """Get the global telemetry logger instance."""
    global _telemetry_logger
    if _telemetry_logger is None:
        _telemetry_logger = TelemetryLogger()
    return _telemetry_logger


def configure_telemetry(
    log_to_file: bool = False,
    file_path: str | Path | None = None,
    in_memory: bool = False,
) -> TelemetryLogger:
    """
    Configure the global telemetry logger.

    Args:
        log_to_file: Whether to write records to a file
        file_path: Path to the telemetry log file
        in_memory: Whether to store records in memory (for testing)

    Returns:
        The configured TelemetryLogger instance
    """
    global _telemetry_logger
    _telemetry_logger = TelemetryLogger(
        log_to_file=log_to_file,
        file_path=file_path,
        in_memory=in_memory,
    )
    return _telemetry_logger


class GenerationTelemetryContext:
    """
    Context manager for tracking a complete generation cycle.

    Usage:
        with GenerationTelemetryContext(request_id, profile, theme, word_count) as ctx:
            ctx.record_prompt(prompt_hash)
            # ... do generation ...
            ctx.record_validation(result)
    """

    def __init__(
        self,
        request_id: str,
        profile: WritingProfile,
        theme: str,
        word_count: int,
        telemetry: TelemetryLogger | None = None,
    ):
        self.telemetry = telemetry or get_telemetry_logger()
        self.record = self.telemetry.start_generation(
            request_id, profile, theme, word_count
        )
        self._success = True
        self._error: str | None = None

    def __enter__(self) -> "GenerationTelemetryContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._success = False
            self._error = str(exc_val)
        self.telemetry.complete_generation(self.record, self._success, self._error)
        return False  # Don't suppress exceptions

    def record_prompt(self, prompt_hash: str) -> None:
        """Record prompt hash."""
        self.telemetry.record_prompt(self.record, prompt_hash)

    def record_model(self, model: str) -> None:
        """Record model used."""
        self.telemetry.record_model(self.record, model)

    def record_generation_time(self, time_ms: int) -> None:
        """Record generation time."""
        self.telemetry.record_generation_time(self.record, time_ms)

    def record_validation(self, result: ValidationResult, iteration: int = 1) -> None:
        """Record validation result."""
        self.telemetry.record_validation(self.record, result, iteration)

    def record_metrics(self, metrics: TextMetrics) -> None:
        """Record final metrics."""
        self.telemetry.record_metrics(self.record, metrics)

    def mark_failed(self, error: str) -> None:
        """Mark generation as failed."""
        self._success = False
        self._error = error
