from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class NewsStatistics:
    total_count: int
    category_counts: Dict[str, int]
    source_type_counts: Dict[str, int]
    recent_count: int
    high_priority_count: int




