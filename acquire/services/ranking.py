"""
Ranking heuristics for acquisition candidates.

Placeholder implementation; will evolve to match the documented heuristics.
"""

from typing import Dict, List


def rank_candidates(candidates: List[Dict]) -> List[Dict]:
    """
    Return candidates sorted by basic rules:
    - Higher match_score first
    - Prefer borrow/read/download_open over login_required over purchase_only
    """
    access_priority = {
        "borrow": 0,
        "read_online": 0,
        "download_open": 0,
        "login_required": 1,
        "purchase_only": 2,
    }

    def sort_key(cand: Dict):
        access_rank = access_priority.get(cand.get("access_type"), 3)
        return (-cand.get("match_score", 0), access_rank)

    return sorted(candidates, key=sort_key)
