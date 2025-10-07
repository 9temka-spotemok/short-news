"""
Seed competitors from a CSV exported from the Google Sheet.

Usage:
  poetry run python -m app.tasks.seed_competitors --csv "/absolute/path/to/file.csv"
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.company import Company


def _extract_first_url(cells: List[str], domain_hint: Optional[str] = None) -> Optional[str]:
    for cell in cells:
        text = (cell or "").strip()
        if text.startswith("http://") or text.startswith("https://"):
            if domain_hint is None or domain_hint in text:
                return text
    return None


def _extract_social_handle(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        # Normalize and get the last non-empty path segment
        path = re.sub(r"https?://", "", url).split("/", 1)[-1]
        parts = [p for p in path.split("/") if p]
        if not parts:
            return None
        handle = parts[-1]
        # Remove possible querystring
        handle = handle.split("?")[0]
        handle = handle.split("#")[0]
        return handle or None
    except Exception:
        return None


def parse_competitor_row(cells: List[str]) -> Optional[Dict[str, Any]]:
    """
    Heuristic parser for the exported CSV rows. The sheet contains many empty
    spacer cells; we pick meaningful fields by pattern.
    """
    # Trim and drop purely empty cells while keeping order
    values = [c.strip() for c in cells]

    # Expect at least: index, name, website or socials, type/pricing/notes
    # Find candidate name: first non-empty that is not a URL and not numeric
    name: Optional[str] = None
    for v in values:
        if not v:
            continue
        if v.replace(" ", "").isdigit():
            continue
        if v.startswith("http://") or v.startswith("https://"):
            continue
        # Ignore known header markers
        if v.upper().startswith("✷") or v.upper().startswith("✦"):
            continue
        name = v
        break

    if not name:
        return None

    website = _extract_first_url(values)
    linkedin = _extract_first_url(values, domain_hint="linkedin.com")
    twitter = _extract_first_url(values, domain_hint="twitter.com") or _extract_first_url(values, domain_hint="x.com")
    instagram = _extract_first_url(values, domain_hint="instagram.com")

    # Year founded: first token with 4 digits
    year_founded: Optional[str] = None
    for v in values:
        m = re.search(r"(19|20)\d{2}", v)
        if m:
            year_founded = m.group(0)
            break

    # Type: choose the first small, descriptive phrase without URL/currency
    comp_type: Optional[str] = None
    for v in values:
        if not v or v.startswith("http"):
            continue
        if any(sym in v for sym in ["$", "€", "£", "/mo", "plan", "trial"]):
            continue
        if re.search(r"\d", v):
            continue
        # likely a short type label
        if len(v) <= 50 and any(token in v.lower() for token in ["monitor", "visibility", "geo", "overview", "seo", "tracker", "analytics", "brand", "llm"]):
            comp_type = v
            break

    # Pricing: any cell with currency or mentions of Free/credits
    pricing: Optional[str] = None
    for v in values:
        if any(sym in v for sym in ["$", "€", "£"]) or any(k in v.lower() for k in ["free", "trial", "credit", "pricing"]):
            pricing = v
            break

    # Notes: pick first longer descriptive sentence not URL
    notes: Optional[str] = None
    for v in values:
        if not v or v.startswith("http"):
            continue
        if v == name or v == comp_type or v == pricing:
            continue
        if len(v) > 20:
            notes = v
            break

    twitter_handle = _extract_social_handle(twitter)

    return {
        "name": name,
        "website": website,
        "description": notes,
        "category": comp_type,
        "twitter_handle": twitter_handle,
        "github_org": None,
        "logo_url": None,
        "year_founded": year_founded,
        "linkedin": linkedin,
        "instagram": instagram,
        "pricing": pricing,
    }


async def upsert_company(db: AsyncSession, data: Dict[str, Any]) -> None:
    # Check existing by name
    from sqlalchemy import select

    result = await db.execute(select(Company).where(Company.name == data["name"]))
    existing = result.scalar_one_or_none()
    if existing:
        updated_fields = {
            "website": data.get("website") or existing.website,
            "description": data.get("description") or existing.description,
            "category": data.get("category") or existing.category,
            "twitter_handle": data.get("twitter_handle") or existing.twitter_handle,
            "github_org": data.get("github_org") or existing.github_org,
            "logo_url": data.get("logo_url") or existing.logo_url,
        }
        for k, v in updated_fields.items():
            setattr(existing, k, v)
        await db.commit()
        return

    company = Company(
        name=data["name"],
        website=data.get("website"),
        description=data.get("description"),
        category=data.get("category"),
        twitter_handle=data.get("twitter_handle"),
        github_org=data.get("github_org"),
        logo_url=data.get("logo_url"),
    )
    db.add(company)
    await db.commit()


async def import_csv(csv_path: Path) -> int:
    count = 0
    async with AsyncSessionLocal() as db:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                # Skip header and empty lines
                if not row or all(not (c or "").strip() for c in row):
                    continue
                parsed = parse_competitor_row(row)
                if not parsed or not parsed.get("name"):
                    continue
                try:
                    await upsert_company(db, parsed)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to upsert company '{parsed.get('name')}': {e}")
                    await db.rollback()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed competitors into DB from CSV")
    parser.add_argument("--csv", required=True, help="Path to the exported CSV file")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    inserted = asyncio.run(import_csv(csv_path))
    logger.info(f"Imported/updated {inserted} companies from {csv_path}")


if __name__ == "__main__":
    main()



