"""
Utilities for persisting raw HTML snapshots for traceability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import settings


def _slugify(value: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9\-]+", "-", value.lower()).strip("-") or "unknown"


def persist_snapshot(
    scope: str,
    company_identifier: str,
    source_id: str,
    url: str,
    html: str,
) -> Optional[str]:
    """
    Persist raw HTML snapshot and return absolute path.

    Args:
        scope: Logical namespace (e.g. "pricing").
        company_identifier: Company name or ID.
        source_id: Stable identifier for the source entry.
        url: Source URL.
        html: Raw HTML content.
    """
    if not settings.SCRAPER_SNAPSHOTS_ENABLED:
        return None

    base_dir = Path(settings.SCRAPER_SNAPSHOT_DIR)
    slug = _slugify(company_identifier)
    digest_input = f"{url}|{html}".encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()
    file_name = f"{source_id}_{digest}.html"
    target_path = base_dir / scope / slug / file_name

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists():
            target_path.write_text(html, encoding="utf-8")
        return str(target_path.resolve())
    except Exception as exc:  # pragma: no cover - IO error path
        logger.warning(
            "Failed to persist snapshot for %s (%s): %s", company_identifier, url, exc
        )
        return None


