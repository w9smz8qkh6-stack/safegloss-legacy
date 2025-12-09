"""Utility functions for the core app."""
import re
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    """Extract plain text positions from HTML while preserving tag locations."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)


def markup_glossary_terms(html_content, terms):
    """
    Process HTML content and wrap glossary terms with clickable spans.

    Args:
        html_content: The HTML string to process
        terms: QuerySet or list of Term objects with term_text and pk

    Returns:
        HTML string with glossary terms wrapped in <span class="gloss-term" data-term-id="...">
    """
    if not html_content or not terms:
        return html_content

    # Build a lookup of term_text -> term for efficient matching
    # Sort by length descending to match longer phrases first
    term_lookup = {}
    for term in terms:
        # Store both the original and lowercase versions for matching
        term_text = term.term_text.strip()
        if term_text:
            term_lookup[term_text.lower()] = term

    if not term_lookup:
        return html_content

    # Sort terms by length (longest first) to handle overlapping matches correctly
    sorted_terms = sorted(term_lookup.keys(), key=len, reverse=True)

    # Build a regex pattern that matches any of the terms (case-insensitive, word boundaries)
    # Escape special regex characters in term text
    escaped_terms = [re.escape(term) for term in sorted_terms]
    pattern = r'\b(' + '|'.join(escaped_terms) + r')\b'

    def replace_term(match):
        """Replace matched term with wrapped span, preserving original case."""
        matched_text = match.group(0)
        term = term_lookup.get(matched_text.lower())
        if term:
            return f'<span class="gloss-term" data-term-id="{term.pk}">{matched_text}</span>'
        return matched_text

    # Process the HTML carefully - only replace in text nodes, not in tags
    result = []
    last_end = 0

    # Find all HTML tags to skip them during replacement
    tag_pattern = re.compile(r'<[^>]+>')

    # Split by tags and process text between them
    parts = tag_pattern.split(html_content)
    tags = tag_pattern.findall(html_content)

    for i, text_part in enumerate(parts):
        if text_part:
            # Apply term replacement to this text part
            processed_text = re.sub(pattern, replace_term, text_part, flags=re.IGNORECASE)
            result.append(processed_text)
        if i < len(tags):
            result.append(tags[i])

    return ''.join(result)


def get_story_terms(story):
    """
    Get all active glossary terms for a story.

    Args:
        story: Story model instance

    Returns:
        QuerySet of Term objects or empty list
    """
    try:
        glossary = story.glossary
        return glossary.terms.filter(is_selected_for_glossary=True)
    except Exception:
        return []
