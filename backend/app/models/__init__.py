"""
Models package
"""

from .base import Base, BaseModel
from .user import User
from .company import Company
from .keyword import NewsKeyword
from .news import NewsItem, NewsCategory, SourceType
from .preferences import UserPreferences, NotificationFrequency, DigestFrequency, DigestFormat
from .activity import UserActivity, ActivityType
from .scraper import ScraperState
from .notifications import Notification, NotificationSettings, NotificationType, NotificationPriority
from .competitor import CompetitorComparison

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "Company",
    "NewsKeyword",
    "NewsItem",
    "NewsCategory",
    "SourceType",
    "UserPreferences",
    "NotificationFrequency",
    "DigestFrequency",
    "DigestFormat",
    "UserActivity",
    "ActivityType",
    "ScraperState",
    "Notification",
    "NotificationSettings",
    "NotificationType",
    "NotificationPriority",
    "CompetitorComparison",
]
