# Story Engine - Lexile-aligned story generation system
# Milestone A: Foundations (Rules + Prompting)
# Milestone B: Validation & Rewrite Loop

from .rules import RulesLoader, get_rules_loader
from .profile_builder import WritingProfileBuilder, WritingProfile
from .prompt_composer import PromptComposer, ComposedPrompt, compose_story_prompt
from .guardrails import ContentGuardrails, get_guardrails
from .text_metrics import TextMetrics, TextMetricsExtractor, extract_metrics
from .validator import (
    StoryValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_story,
)
from .rewrite_loop import RewriteLoop, RewriteResult, process_story

__all__ = [
    # Milestone A
    'RulesLoader',
    'get_rules_loader',
    'WritingProfileBuilder',
    'WritingProfile',
    'PromptComposer',
    'ComposedPrompt',
    'compose_story_prompt',
    'ContentGuardrails',
    'get_guardrails',
    # Milestone B
    'TextMetrics',
    'TextMetricsExtractor',
    'extract_metrics',
    'StoryValidator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'validate_story',
    'RewriteLoop',
    'RewriteResult',
    'process_story',
]
