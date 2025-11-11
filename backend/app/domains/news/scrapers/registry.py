"""
Simple registry for resolving scraper providers.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from .adapters import AINewsScraperProvider, UniversalScraperProvider
from .interfaces import CompanyContext, ScraperProvider

ProviderPredicate = Callable[[CompanyContext], bool]
ProviderFactory = Callable[[], ScraperProvider]


class NewsScraperRegistry:
    """Resolve scraper providers for companies."""

    def __init__(self) -> None:
        self._default_factory: ProviderFactory = UniversalScraperProvider
        self._registrations: List[Tuple[ProviderPredicate, ProviderFactory]] = []
        self._register_builtin_providers()

    def _register_builtin_providers(self) -> None:
        for company in ("openai", "anthropic", "google"):
            self.register_provider(
                lambda ctx, name=company: bool(ctx.name) and ctx.name.lower() == name,
                lambda name=company: AINewsScraperProvider(name),
            )

    def register_provider(
        self,
        predicate: ProviderPredicate,
        factory: ProviderFactory,
    ) -> None:
        """
        Register a provider factory for companies matching predicate.
        """
        self._registrations.append((predicate, factory))

    def get_provider(
        self,
        company: Optional[CompanyContext] = None,
    ) -> ScraperProvider:
        if company is not None:
            for predicate, factory in self._registrations:
                try:
                    if predicate(company):
                        return factory()
                except Exception:
                    continue
        return self._default_factory()

