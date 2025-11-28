"""Domain service for generating personalized digests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytz
from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.repositories import UserPreferencesRepository
from app.models import Company, NewsItem, User, UserPreferences
from app.models.preferences import DigestFormat
from app.core.access_control import get_user_company_ids


class DigestService:
    """Generates personalized news digests for users."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._preferences = UserPreferencesRepository(session)

    async def generate_user_digest(
        self,
        user_id: str,
        period: str = "daily",
        format_type: str = "short",
        custom_date_from: Optional[datetime] = None,
        custom_date_to: Optional[datetime] = None,
        tracked_only: bool = False,
    ) -> Dict[str, Any]:
        logger.info("Generating %s digest for user %s", period, user_id)
        user_uuid = UUID(user_id)

        user_prefs = await self._preferences.get(user_uuid)
        if user_prefs:
            logger.debug(
                "User preferences: telegram_digest_mode=%s subscribed=%s",
                user_prefs.telegram_digest_mode,
                user_prefs.subscribed_companies,
            )

        if not user_prefs:
            logger.info("Creating default preferences for user %s", user_id)
            user_prefs = await self._preferences.create_default(user_uuid)

        date_from, date_to = self._get_date_range(
            period=period,
            custom_from=custom_date_from,
            custom_to=custom_date_to,
            user_prefs=user_prefs,
        )

        news_items = await self._fetch_news(
            user_prefs=user_prefs,
            date_from=date_from,
            date_to=date_to,
            tracked_only=tracked_only,
        )
        filtered_news = self._filter_news_by_preferences(
            user_prefs=user_prefs,
            news_items=news_items,
            tracked_only=tracked_only,
        )
        ranked_news = self._rank_news_by_relevance(
            news_items=filtered_news,
            user_prefs=user_prefs,
        )

        digest = await self._format_digest_content(
            news_items=ranked_news,
            format_type=format_type,
            date_from=date_from,
            date_to=date_to,
            user_prefs=user_prefs,
            tracked_only=tracked_only,
        )

        logger.info("Digest generated with %s items", len(ranked_news))
        return digest

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_date_range(
        self,
        period: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        user_prefs: Optional[UserPreferences] = None,
    ) -> tuple[datetime, datetime]:
        user_tz_name = getattr(user_prefs, "timezone", "UTC") or "UTC"
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Unknown timezone: %s, using UTC", user_tz_name)
            user_tz = pytz.UTC

        now_utc = datetime.now(timezone.utc)
        now_user = now_utc.astimezone(user_tz)

        if period == "daily":
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "weekly":
            days_since_week_start = (now_user.weekday() + 1) % 7
            week_start = now_user - timedelta(days=days_since_week_start)
            week_end = now_user + timedelta(days=6 - days_since_week_start)
            date_from_user = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "custom" and custom_from and custom_to:
            date_from_user = self._localize_datetime(custom_from, user_tz, start=True)
            date_to_user = self._localize_datetime(custom_to, user_tz, start=False)
        elif period == "custom":
            date_from_user = (now_user - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)

        date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
        date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)

        logger.info(
            "Date range for %s digest (timezone: %s): %s to %s UTC",
            period,
            user_tz_name,
            date_from,
            date_to,
        )
        return date_from, date_to

    async def _fetch_news(
        self,
        user_prefs: UserPreferences,
        date_from: datetime,
        date_to: datetime,
        tracked_only: bool,
    ) -> List[NewsItem]:
        # ВСЕГДА получаем компании пользователя (user_id)
        # КРИТИЧЕСКИ ВАЖНО: Конвертируем user_id в стандартный UUID
        # чтобы избежать проблем с asyncpg.pgproto.UUID
        # asyncpg UUID не является экземпляром стандартного UUID, поэтому всегда конвертируем через str()
        try:
            user_id_uuid = UUID(str(user_prefs.user_id))
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid user_id type: {type(user_prefs.user_id)}, value: {user_prefs.user_id}, error: {e}")
            return []
        
        user = await self._session.get(User, user_id_uuid)
        if not user:
            logger.warning("User not found for user_id=%s", user_id_uuid)
            return []
        
        user_company_ids = await get_user_company_ids(user, self._session)
        
        if not user_company_ids:
            logger.info("User has no companies, returning empty digest for user_id=%s", user_id_uuid)
            return []
        
        logger.info(
            "Fetching news tracked_only=%s user_companies=%d subscribed=%s",
            tracked_only,
            len(user_company_ids),
            len(user_prefs.subscribed_companies) if user_prefs.subscribed_companies else 0,
        )

        # ОПТИМИЗИРОВАНО: Используем JOIN вместо IN для фильтрации по user_id
        # Это значительно быстрее при большом количестве компаний у пользователя
        # КРИТИЧЕСКИ ВАЖНО: Персонализация - только компании пользователя, БЕЗ глобальных
        from app.models.company import Company
        
        # Базовый запрос с JOIN для фильтрации по user_id (только компании пользователя, БЕЗ глобальных)
        query = (
            select(NewsItem)
            .join(Company, NewsItem.company_id == Company.id)
            .where(
                and_(
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to,
                    Company.user_id == user_id_uuid  # Только компании пользователя, БЕЗ глобальных
                )
            )
        )

        # Дополнительно фильтруем по subscribed_companies если tracked_only=True
        if tracked_only and user_prefs.subscribed_companies:
            # КРИТИЧЕСКИ ВАЖНО: Конвертируем subscribed_companies в UUID для правильного сравнения
            subscribed_ids_set = set()
            for sub_id in user_prefs.subscribed_companies:
                try:
                    # КРИТИЧЕСКИ ВАЖНО: Всегда конвертируем через str(), так как asyncpg UUID
                    # не является экземпляром стандартного UUID
                    uuid_id = UUID(str(sub_id))
                    subscribed_ids_set.add(uuid_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid subscribed_company ID: {sub_id}, error: {e}, skipping")
                    continue
            
            # Пересечение: только компании, которые и в user_id, и в subscribed_companies
            filtered_ids = [cid for cid in user_company_ids if cid in subscribed_ids_set]
            
            logger.info(
                "Tracked filter: user_companies=%d, subscribed=%d, intersection=%d",
                len(user_company_ids),
                len(subscribed_ids_set),
                len(filtered_ids)
            )
            
            if filtered_ids:
                # Используем IN для дополнительной фильтрации по subscribed_companies
                # Это нормально, так как список обычно небольшой
                query = query.where(NewsItem.company_id.in_(filtered_ids))
            else:
                # Если нет пересечения, возвращаем пустой список
                logger.info("No intersection between user companies and subscribed_companies, returning empty digest")
                return []

        if tracked_only and user_prefs.interested_categories:
            query = query.where(NewsItem.category.in_(user_prefs.interested_categories))

        query = query.order_by(desc(NewsItem.published_at))
        result = await self._session.execute(query)
        news_items = list(result.scalars().all())
        logger.info("Fetched %s news items for user_id=%s", len(news_items), user_id_uuid)
        return news_items

    def _filter_news_by_preferences(
        self,
        user_prefs: UserPreferences,
        news_items: List[NewsItem],
        tracked_only: bool,
    ) -> List[NewsItem]:
        # Если нет ключевых слов, возвращаем все новости
        # (они уже отфильтрованы по user_id компаний в _fetch_news)
        if not user_prefs.keywords:
            return news_items

        # Фильтруем по ключевым словам
        filtered: List[NewsItem] = []
        for news in news_items:
            has_keyword = any(
                keyword.lower() in (news.title or "").lower()
                or keyword.lower() in (news.content or "").lower()
                for keyword in user_prefs.keywords
            )
            
            # Если tracked_only=True и есть subscribed_companies, дополнительно проверяем
            if not has_keyword and tracked_only and user_prefs.subscribed_companies:
                # КРИТИЧЕСКИ ВАЖНО: Правильная конвертация типов для сравнения
                subscribed_set = set()
                for sub_id in user_prefs.subscribed_companies:
                    try:
                        # КРИТИЧЕСКИ ВАЖНО: Всегда конвертируем через str()
                        uuid_id = UUID(str(sub_id))
                        subscribed_set.add(uuid_id)
                    except (ValueError, TypeError):
                        continue
                
                if news.company_id:
                    # КРИТИЧЕСКИ ВАЖНО: Всегда конвертируем через str()
                    news_company_uuid = UUID(str(news.company_id))
                    if news_company_uuid not in subscribed_set:
                        continue
            
            filtered.append(news)
        return filtered

    def _rank_news_by_relevance(
        self,
        news_items: List[NewsItem],
        user_prefs: UserPreferences,
    ) -> List[NewsItem]:
        """
        Rank news items by relevance.
        
        ВАЖНО: Все новости уже отфильтрованы по user_id компаний в _fetch_news().
        Если tracked_only=True, то новости дополнительно отфильтрованы по subscribed_companies.
        
        Поэтому:
        - Проверка subscribed_companies используется для дополнительного бонуса ранжирования
        - Все новости гарантированно принадлежат компаниям пользователя
        """
        def calculate_score(news: NewsItem) -> float:
            score = news.priority_score or 0.5
            
            # Бонус для компаний в subscribed_companies (даже если tracked_only=False,
            # это показывает, что пользователь активно отслеживает эти компании)
            # Проверка subscribed_companies с правильной конвертацией типов
            if user_prefs.subscribed_companies and news.company_id:
                subscribed_set = set()
                for sub_id in user_prefs.subscribed_companies:
                    try:
                        # КРИТИЧЕСКИ ВАЖНО: Всегда конвертируем через str()
                        uuid_id = UUID(str(sub_id))
                        subscribed_set.add(uuid_id)
                    except (ValueError, TypeError):
                        continue
                
                # КРИТИЧЕСКИ ВАЖНО: Всегда конвертируем через str()
                news_company_uuid = UUID(str(news.company_id))
                if news_company_uuid in subscribed_set:
                    score += 0.3
            
            # Бонус для интересных категорий
            if user_prefs.interested_categories and news.category in user_prefs.interested_categories:
                score += 0.2
            
            # Бонус за совпадение ключевых слов
            if user_prefs.keywords:
                keyword_matches = sum(
                    1
                    for keyword in user_prefs.keywords
                    if keyword.lower() in (news.title or "").lower()
                    or keyword.lower() in (news.content or "").lower()
                )
                score += keyword_matches * 0.1

            # Бонус за свежесть (новости младше 24 часов)
            now = datetime.now(timezone.utc)
            published = news.published_at
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age_hours = (now - published).total_seconds() / 3600
            if age_hours < 24:
                score += 0.1

            return min(score, 1.0)

        scored_news = [(news, calculate_score(news)) for news in news_items]
        scored_news.sort(key=lambda item: item[1], reverse=True)
        return [news for news, _ in scored_news]

    async def _format_digest_content(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences,
        tracked_only: bool,
    ) -> Dict[str, Any]:
        return await self._format_digest_by_companies(
            news_items=news_items,
            format_type=format_type,
            date_from=date_from,
            date_to=date_to,
            user_prefs=user_prefs,
        )

    def format_digest_for_telegram(
        self,
        digest_data: Dict[str, Any],
        user_prefs: Optional[UserPreferences] = None,
    ) -> str:
        """Render digest payload to Telegram-friendly Markdown string."""
        if not digest_data:
            return "📰 *Digest*\n\n_No data available._"

        news_count = digest_data.get("news_count", 0) or 0
        companies_data = digest_data.get("companies") or {}

        timezone_name = getattr(user_prefs, "timezone", "UTC") or "UTC"
        try:
            user_tz = pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Unknown timezone for Telegram digest: %s", timezone_name)
            user_tz = pytz.UTC

        date_range_text = self._format_period_header(
            date_from=digest_data.get("date_from"),
            date_to=digest_data.get("date_to"),
            timezone_obj=user_tz,
        )
        mode_label = self._resolve_digest_mode_label(user_prefs)

        lines: List[str] = []
        lines.append("📰 *Daily Digest*")
        if date_range_text:
            lines.append(date_range_text)
        lines.append(f"Total news: *{news_count}*")
        if mode_label:
            lines.append(mode_label)

        if not companies_data:
            lines.append("")
            lines.append("_Nothing matched your filters today._")
            return "\n".join(lines).strip()

        sorted_companies = sorted(
            companies_data.values(),
            key=lambda company: company.get("stats", {}).get("total", 0),
            reverse=True,
        )

        for company in sorted_companies:
            company_info = company.get("company") or {}
            company_name = self._escape_markdown(company_info.get("name") or "Unknown Company")
            total_news = company.get("stats", {}).get("total", 0)
            lines.append("")
            lines.append(f"🏢 *{company_name}* — {total_news} news")

            for idx, news in enumerate(company.get("news") or []):
                if idx >= 5:
                    remaining = total_news - idx
                    if remaining > 0:
                        lines.append(f"  • …and {remaining} more")
                    break

                title = self._escape_markdown(news.get("title") or "Untitled update")
                published_text = self._format_published_time(news.get("published_at"), user_tz)
                summary = self._prepare_summary(news)
                source_url = news.get("source_url")

                bullet = f"  • {title}"
                if published_text:
                    bullet += f" ({published_text})"
                lines.append(bullet)

                if summary:
                    lines.append(f"    {summary}")

                if source_url:
                    lines.append(f"    🔗 {self._escape_markdown(source_url)}")

        return "\n".join(lines).strip()

    @staticmethod
    def _escape_markdown(value: str) -> str:
        if value is None:
            return ""
        escaped = value.replace("\\", "\\\\")
        for ch in ("_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
            escaped = escaped.replace(ch, f"\\{ch}")
        return escaped

    def _format_period_header(
        self,
        date_from: Optional[str],
        date_to: Optional[str],
        timezone_obj: pytz.BaseTzInfo,
    ) -> str:
        def _parse(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                return dt.astimezone(timezone_obj)
            except ValueError:
                logger.warning("Failed to parse digest datetime: %s", dt_str)
                return None

        start = _parse(date_from)
        end = _parse(date_to)

        if not start and not end:
            return ""

        if start and end and start.date() == end.date():
            date_part = start.strftime("%d %b %Y")
            start_time = start.strftime("%H:%M")
            end_time = end.strftime("%H:%M")
            return f"{date_part} {start_time}–{end_time} ({timezone_obj.zone})"

        formatted_start = start.strftime("%d %b %Y %H:%M") if start else ""
        formatted_end = end.strftime("%d %b %Y %H:%M") if end else ""
        return f"{formatted_start} → {formatted_end} ({timezone_obj.zone})".strip()

    def _format_published_time(
        self,
        published_iso: Optional[str],
        timezone_obj: pytz.BaseTzInfo,
    ) -> Optional[str]:
        if not published_iso:
            return None

        try:
            published_dt = datetime.fromisoformat(published_iso)
        except ValueError:
            logger.debug("Unable to parse published_at for Telegram digest: %s", published_iso)
            return None

        if published_dt.tzinfo is None:
            published_dt = pytz.UTC.localize(published_dt)

        localized = published_dt.astimezone(timezone_obj)
        return localized.strftime("%H:%M")

    def _prepare_summary(self, news: Dict[str, Any]) -> str:
        raw_summary = news.get("summary") or news.get("content") or ""
        summary = " ".join(raw_summary.split())
        if len(summary) > 220:
            summary = summary[:217].rstrip() + "…"
        return self._escape_markdown(summary) if summary else ""

    @staticmethod
    def _resolve_digest_mode_label(user_prefs: Optional[UserPreferences]) -> str:
        if not user_prefs:
            return ""
        mode = getattr(user_prefs, "telegram_digest_mode", None)
        if mode == "tracked":
            return "_Mode: tracked companies only_"
        if mode == "all":
            return "_Mode: all companies_"
        return ""

    async def _format_digest_by_companies(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences,
    ) -> Dict[str, Any]:
        by_company: Dict[str, Dict[str, Any]] = {}

        for item in news_items:
            if not item.company_id:
                continue

            # КРИТИЧЕСКИ ВАЖНО: Конвертируем company_id в стандартный UUID
            # чтобы избежать проблем с asyncpg.pgproto.UUID
            # asyncpg UUID не является экземпляром стандартного UUID, поэтому всегда конвертируем через str()
            try:
                company_id_uuid = UUID(str(item.company_id))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid company_id in news item: {type(item.company_id)}, value: {item.company_id}, error: {e}")
                continue

            company_id_str = str(company_id_uuid)
            if company_id_str not in by_company:
                company = await self._get_company(company_id_uuid)
                by_company[company_id_str] = {
                    "company": {
                        "id": company_id_str,  # Используем уже конвертированный company_id_str
                        "name": company.name if company else "Unknown Company",
                        "logo_url": company.logo_url if company else None,
                    },
                    "news": [],
                    "stats": {"total": 0, "by_category": {}},
                }

            formatted_item = await self._format_news_item(item, format_type, user_prefs)
            company_bucket = by_company[company_id_str]
            company_bucket["news"].append(formatted_item)
            company_bucket["stats"]["total"] += 1
            category = item.category or "other"
            company_bucket["stats"]["by_category"][category] = (
                company_bucket["stats"]["by_category"].get(category, 0) + 1
            )

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "news_count": len(news_items),
            "companies": by_company,
            "companies_count": len(by_company),
            "format": "by_company",
        }

    async def _format_news_item(
        self,
        news_item: NewsItem,
        format_type: str,
        user_prefs: UserPreferences,
    ) -> Dict[str, Any]:
        digest_format = format_type or user_prefs.digest_format or DigestFormat.SHORT.value

        source_value = getattr(news_item, "source", None)
        if not source_value:
            source_type = getattr(news_item, "source_type", None)
            if source_type:
                source_value = getattr(source_type, "value", str(source_type))

        impact_value = getattr(news_item, "impact_score", None)

        # КРИТИЧЕСКИ ВАЖНО: Конвертируем news_item.id в строку безопасно
        # чтобы избежать проблем с asyncpg.pgproto.UUID
        try:
            if hasattr(news_item.id, '__str__'):
                news_id_str = str(news_item.id)
            else:
                news_id_str = str(news_item.id)
        except Exception:
            logger.warning(f"Failed to convert news_item.id to string: {type(news_item.id)}")
            news_id_str = "unknown"

        base_data = {
            "id": news_id_str,
            "title": news_item.title,
            "summary": news_item.summary,
            "category": news_item.category,
            "published_at": news_item.published_at.isoformat() if news_item.published_at else None,
            "source": source_value,
            "source_url": news_item.source_url,
            "priority_score": news_item.priority_score,
            "impact_score": impact_value,
            "company_id": str(news_item.company_id) if news_item.company_id else None,  # Конвертация в строку безопасна
        }

        if digest_format == DigestFormat.DETAILED.value:
            base_data.update(
                {
                    "content": news_item.content,
                    "tags": news_item.tags,
                    "entities": news_item.entities,
                }
            )

        return base_data

    async def _get_company(self, company_id: UUID) -> Optional[Company]:
        # КРИТИЧЕСКИ ВАЖНО: Конвертируем company_id в стандартный UUID
        # чтобы избежать проблем с asyncpg.pgproto.UUID
        # asyncpg UUID не является экземпляром стандартного UUID, поэтому всегда конвертируем через str()
        try:
            uuid_id = UUID(str(company_id))
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid company_id type: {type(company_id)}, value: {company_id}, error: {e}")
            return None
        
        result = await self._session.execute(
            select(Company).where(Company.id == uuid_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _localize_datetime(dt: datetime, timezone_obj: pytz.BaseTzInfo, *, start: bool) -> datetime:
        if dt.tzinfo is None:
            dt = timezone_obj.localize(
                dt.replace(
                    hour=0 if start else 23,
                    minute=0 if start else 59,
                    second=0 if start else 59,
                    microsecond=0 if start else 999999,
                )
            )
        else:
            dt = dt.astimezone(timezone_obj).replace(
                hour=0 if start else 23,
                minute=0 if start else 59,
                second=0 if start else 59,
                microsecond=0 if start else 999999,
            )
        return dt

