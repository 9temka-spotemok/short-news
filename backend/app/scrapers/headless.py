"""
Optional headless fallback for scraping SPA / Cloudflare protected sources.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger

try:
    from playwright.async_api import async_playwright  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    async_playwright = None  # type: ignore


async def fetch_page_with_headless(url: str, timeout: float) -> Optional[str]:
    """
    Fetch page HTML using Playwright (headless browser). Returns HTML or None.
    """
    if async_playwright is None:
        logger.warning("Playwright is not installed; skipping headless fallback for %s", url)
        return None

    try:
        timeout_ms = int(timeout * 1000)
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:  # pragma: no cover - depends on runtime
        logger.warning("Headless fetch failed for %s: %s", url, exc)
        return None


