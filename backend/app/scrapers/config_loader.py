"""
Helpers for loading scraper source configuration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from app.core.config import settings


class SourceRateLimit(BaseModel):
    requests: int = Field(default=settings.SCRAPER_RATE_LIMIT_REQUESTS, ge=1, description="Max requests within the interval")
    interval: float = Field(default=settings.SCRAPER_RATE_LIMIT_PERIOD, gt=0, description="Interval length in seconds")


class SourceRetryConfig(BaseModel):
    attempts: int = Field(default=settings.SCRAPER_MAX_RETRIES, ge=0)
    backoff_factor: float = Field(default=settings.SCRAPER_RETRY_BACKOFF, gt=0)


class SourceConfig(BaseModel):
    """
    Configuration for a particular scraping source (blog, press, etc.).
    """

    id: str
    urls: List[HttpUrl]
    source_type: str = Field(default="blog", description="Logical source type, e.g. blog, press_release")
    timeout: Optional[float] = Field(default=None, gt=0)
    retry: SourceRetryConfig = Field(default_factory=SourceRetryConfig)
    rate_limit: SourceRateLimit = Field(default_factory=SourceRateLimit)
    min_delay: Optional[float] = Field(default=None, ge=0)
    use_headless: bool = Field(default=False)
    use_proxy: bool = Field(default=False)
    max_articles: Optional[int] = Field(default=None, ge=1)
    selectors: Optional[List[str]] = Field(default=None, description="Custom CSS selectors for article extraction")


class ScraperConfigRegistry:
    """
    Registry that holds optional per-company scraper configuration.
    """

    def __init__(self, config_path: Optional[str] = None):
        self._company_sources: Dict[str, List[SourceConfig]] = {}
        path = config_path or settings.SCRAPER_CONFIG_PATH
        if not path:
            return

        config_file = Path(path)
        if not config_file.exists():
            logger.warning("Scraper config file %s not found; falling back to defaults", config_file)
            return

        try:
            data = self._load_file(config_file)
            self._parse_config(data)
        except Exception as exc:
            logger.error("Failed to load scraper config from %s: %s", config_file, exc)

    def _load_file(self, path: Path) -> Dict[str, Any]:
        if path.suffix in {".yml", ".yaml"}:
            try:
                import yaml  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("PyYAML is required to read scraper configuration files") from exc
            with path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}

        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _parse_config(self, data: Dict[str, Any]) -> None:
        sources = data.get("sources", [])
        if not isinstance(sources, list):
            logger.warning("Scraper config 'sources' key must be a list")
            return

        for entry in sources:
            company_key = (entry.get("company") or "").strip().lower()
            if not company_key:
                logger.warning("Scraper source entry is missing 'company' field: %s", entry)
                continue
            try:
                config = SourceConfig(**entry)
            except ValidationError as exc:
                logger.warning("Invalid scraper source config for %s: %s", company_key, exc)
                continue
            self._company_sources.setdefault(company_key, []).append(config)

    def get_sources(
        self,
        company_name: str,
        website: str,
        manual_url: Optional[str] = None,
        overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> List[SourceConfig]:
        """
        Returns source configurations for specific company.
        Overrides have highest priority, then config file, then heuristics.
        """
        sources: List[SourceConfig] = []
        company_key = company_name.strip().lower()

        if overrides:
            for idx, entry in enumerate(overrides):
                entry = {**entry, "id": entry.get("id") or f"override_{idx}"}
                if "urls" not in entry and "url" in entry:
                    entry["urls"] = [entry.pop("url")]
                try:
                    config = SourceConfig(**entry)
                    sources.append(config)
                except ValidationError as exc:
                    logger.warning("Invalid source override for %s: %s", company_name, exc)

        if company_key in self._company_sources:
            sources.extend(self._company_sources[company_key])

        # If no explicit config is available, fall back to heuristics.
        if not sources:
            heuristic_sources = self._build_heuristic_sources(company_name, website, manual_url)
            sources.extend(heuristic_sources)

        return sources

    def _build_heuristic_sources(
        self,
        company_name: str,
        website: str,
        manual_url: Optional[str],
    ) -> List[SourceConfig]:
        base_sources: List[str] = []
        if manual_url:
            base_sources.append(manual_url)

        patterns = self._generate_default_urls(website)
        base_sources.extend(patterns)

        # Deduplicate while preserving order.
        seen = set()
        unique_urls = [url for url in base_sources if not (url in seen or seen.add(url))]

        return [
            SourceConfig(
                id=f"default_{idx}",
                urls=[url],
                source_type="blog",
                retry=SourceRetryConfig(attempts=0),
            )
            for idx, url in enumerate(unique_urls)
        ]

    @staticmethod
    def _generate_default_urls(website: str) -> List[str]:
        from urllib.parse import urlparse

        parsed = urlparse(website)
        if not parsed.scheme or not parsed.netloc:
            return []

        base_domain = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        patterns = [
            f"{base_domain}/blog",
            f"{base_domain}/blogs",
            f"{base_domain}/blog/",
            f"{base_domain}/blogs/",
            f"{base_domain}/news",
            f"{base_domain}/news/",
            f"{base_domain}/insights",
            f"{base_domain}/updates",
            f"{base_domain}/press",
            f"{base_domain}/newsroom",
            f"{base_domain}/press-releases",
            f"{base_domain}/company/blog",
            f"{base_domain}/company/news",
            f"{base_domain}/resources/blog",
            f"{base_domain}/hub/blog",
        ]
        return patterns


