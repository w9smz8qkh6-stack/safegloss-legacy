from typing import Any, Dict, List, Protocol


class TextSourceConnector(Protocol):
    """
    Base protocol for text acquisition connectors.

    Implementations should remain link-first and return metadata suitable for
    building AcquisitionCandidate records.
    """

    capabilities: set

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Return ranked candidate records for a given text.

        `text` should include identifiers (isbn13/isbn10/oclc) and normalized
        title/author/edition fields.
        """
        raise NotImplementedError

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Optional: return availability/hold/borrow state for a candidate."""
        raise NotImplementedError

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        """Return the canonical reader or deep-link URL for a candidate."""
        raise NotImplementedError
