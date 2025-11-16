"""
Repository layer for the news domain.

Repositories encapsulate database access and SQLAlchemy queries. Higher layers
should depend on repository interfaces rather than raw sessions.
"""

from .news_repository import NewsRepository, NewsFilters  # noqa: F401
from .company_repository import CompanyRepository  # noqa: F401


