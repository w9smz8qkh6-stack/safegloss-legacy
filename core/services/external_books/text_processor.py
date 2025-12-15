"""Text processing utilities for imported books."""

import re
from typing import Optional
from .base import ChapterInfo


class TextProcessor:
    """
    Process raw text from external book sources.

    Handles:
    - Removing Gutenberg headers/footers
    - Chapter detection
    - Text truncation
    - Plain text to HTML conversion
    """

    # Gutenberg header/footer markers
    GUTENBERG_START_MARKERS = [
        r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK",
        r"\*\*\*START OF THE PROJECT GUTENBERG EBOOK",
        r"START OF THIS PROJECT GUTENBERG EBOOK",
    ]

    GUTENBERG_END_MARKERS = [
        r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK",
        r"\*\*\*END OF THE PROJECT GUTENBERG EBOOK",
        r"END OF THIS PROJECT GUTENBERG EBOOK",
        r"End of the Project Gutenberg EBook",
        r"End of Project Gutenberg",
    ]

    # Chapter detection patterns
    CHAPTER_PATTERNS = [
        r"^(CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\.?\s*(.*)$",  # CHAPTER I or Chapter 1
        r"^(PART|Part)\s+([IVXLCDM]+|\d+)\.?\s*(.*)$",  # PART I
        r"^([IVXLCDM]+)\.\s*(.*)$",  # Roman numerals alone
        r"^(\d+)\.\s+(.+)$",  # Numbered chapters: "1. The Beginning"
    ]

    @classmethod
    def clean_gutenberg_headers(cls, text: str) -> str:
        """
        Remove Project Gutenberg header and footer boilerplate.

        Args:
            text: Raw text from Gutenberg

        Returns:
            Cleaned text with boilerplate removed
        """
        # Find start marker
        start_pos = 0
        for pattern in cls.GUTENBERG_START_MARKERS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Start after the marker line
                start_pos = text.find("\n", match.end()) + 1
                break

        # Find end marker
        end_pos = len(text)
        for pattern in cls.GUTENBERG_END_MARKERS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                end_pos = match.start()
                break

        cleaned = text[start_pos:end_pos].strip()

        # Remove excessive whitespace
        cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)

        return cleaned

    @classmethod
    def list_chapters(cls, text: str) -> list[ChapterInfo]:
        """
        Detect chapter structure in text.

        Args:
            text: Book text

        Returns:
            List of ChapterInfo objects
        """
        chapters = []
        lines = text.split("\n")
        chapter_starts = []

        # Find chapter headings
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            for pattern in cls.CHAPTER_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # Get position in original text
                    pos = sum(len(lines[j]) + 1 for j in range(i))
                    chapter_starts.append({
                        "line_num": i,
                        "pos": pos,
                        "title": line_stripped,
                        "match": match,
                    })
                    break

        # Calculate chapter boundaries and word counts
        for idx, chapter in enumerate(chapter_starts):
            start_pos = chapter["pos"]

            # End position is start of next chapter or end of text
            if idx + 1 < len(chapter_starts):
                end_pos = chapter_starts[idx + 1]["pos"]
            else:
                end_pos = len(text)

            chapter_text = text[start_pos:end_pos]
            word_count = len(chapter_text.split())

            chapters.append(ChapterInfo(
                number=idx + 1,
                title=chapter["title"],
                start_pos=start_pos,
                end_pos=end_pos,
                word_count=word_count,
            ))

        return chapters

    @classmethod
    def extract_chapter(cls, text: str, chapter_num: int) -> Optional[str]:
        """
        Extract a specific chapter from text.

        Args:
            text: Full book text
            chapter_num: 1-indexed chapter number

        Returns:
            Chapter text or None if not found
        """
        chapters = cls.list_chapters(text)

        if not chapters:
            return None

        if chapter_num < 1 or chapter_num > len(chapters):
            return None

        chapter = chapters[chapter_num - 1]
        return text[chapter.start_pos:chapter.end_pos].strip()

    @classmethod
    def truncate_with_summary(
        cls,
        text: str,
        max_words: int,
        add_ellipsis: bool = True
    ) -> tuple[str, bool]:
        """
        Truncate text to a maximum word count.

        Tries to truncate at a paragraph boundary.

        Args:
            text: Text to truncate
            max_words: Maximum number of words
            add_ellipsis: Whether to add "..." to truncated text

        Returns:
            Tuple of (truncated text, was_truncated)
        """
        words = text.split()

        if len(words) <= max_words:
            return text, False

        # Truncate to max_words
        truncated_words = words[:max_words]
        truncated = " ".join(truncated_words)

        # Try to find a good break point (end of paragraph)
        # Look for double newline near the end
        last_para = truncated.rfind("\n\n")
        if last_para > len(truncated) * 0.7:  # Only if we keep at least 70%
            truncated = truncated[:last_para]
        else:
            # Try to end at a sentence
            for ending in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                last_sentence = truncated.rfind(ending)
                if last_sentence > len(truncated) * 0.9:  # Keep at least 90%
                    truncated = truncated[:last_sentence + 1]
                    break

        if add_ellipsis:
            truncated = truncated.rstrip() + "..."

        return truncated, True

    @classmethod
    def convert_to_html(cls, plain_text: str) -> str:
        """
        Convert plain text to HTML with paragraph tags.

        Args:
            plain_text: Plain text content

        Returns:
            HTML formatted text
        """
        import html

        # Escape HTML entities
        text = html.escape(plain_text)

        # Split into paragraphs (double newlines)
        paragraphs = re.split(r"\n\s*\n", text)

        # Wrap each non-empty paragraph in <p> tags
        html_parts = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # Convert single newlines to <br> within paragraphs
                para = para.replace("\n", "<br>\n")
                html_parts.append(f"<p>{para}</p>")

        return "\n\n".join(html_parts)

    @classmethod
    def estimate_reading_time(cls, text: str, wpm: int = 200) -> int:
        """
        Estimate reading time in minutes.

        Args:
            text: Text content
            wpm: Words per minute (default 200 for educational content)

        Returns:
            Estimated minutes to read
        """
        word_count = len(text.split())
        return max(1, round(word_count / wpm))

    @classmethod
    def get_text_stats(cls, text: str) -> dict:
        """
        Get basic statistics about text.

        Args:
            text: Text content

        Returns:
            Dict with word_count, paragraph_count, estimated_reading_time
        """
        words = text.split()
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]

        return {
            "word_count": len(words),
            "paragraph_count": len(paragraphs),
            "estimated_reading_time_minutes": cls.estimate_reading_time(text),
        }
