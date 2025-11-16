"""
Domain-level analytics snapshot service.

This module contains the migrated logic from the legacy `AnalyticsService`
providing operations for computing company analytics snapshots and knowledge
graph edges.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import case, func, select, and_, or_, cast, String, bindparam, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import (
    AnalyticsEntityType,
    AnalyticsGraphEdge,
    AnalyticsPeriod,
    ChangeProcessingStatus,
    CompanyAnalyticsSnapshot,
    CompetitorChangeEvent,
    ImpactComponent,
    ImpactComponentType,
    NewsCategory,
    NewsItem,
    RelationshipType,
    SentimentLabel,
)


class SnapshotService:
    """High-level analytics snapshot operations."""

    IMPACT_WEIGHTS: Dict[str, float] = {
        "news_volume": 0.25,
        "sentiment_delta": 0.15,
        "priority": 0.10,
        "pricing_change": 0.20,
        "feature_update": 0.15,
        "funding_event": 0.10,
        "velocity": 0.05,
    }

    PERIOD_LOOKUPS: Dict[AnalyticsPeriod, timedelta] = {
        AnalyticsPeriod.DAILY: timedelta(days=1),
        AnalyticsPeriod.WEEKLY: timedelta(days=7),
        AnalyticsPeriod.MONTHLY: timedelta(days=30),
    }

    def __init__(self, session: AsyncSession):
        self.db = session

    @staticmethod
    def _coerce_period(period: AnalyticsPeriod | str) -> AnalyticsPeriod:
        if isinstance(period, AnalyticsPeriod):
            return period
        if isinstance(period, str):
            try:
                return AnalyticsPeriod(period)
            except ValueError:
                return AnalyticsPeriod(period.lower())
        raise ValueError(f"Unsupported period value: {period!r}")

    @staticmethod
    def _period_value(period: AnalyticsPeriod | str) -> str:
        if isinstance(period, AnalyticsPeriod):
            return period.value
        if isinstance(period, str):
            return period.lower()
        raise ValueError(f"Unsupported period value: {period!r}")

    def _period_filter(self, column, period: AnalyticsPeriod | str):
        period_enum = self._coerce_period(period)
        period_value = self._period_value(period_enum)
        return cast(column, String) == period_value

    async def get_snapshots(
        self,
        company_id: UUID,
        period: AnalyticsPeriod | str,
        limit: int = 30,
    ) -> List[CompanyAnalyticsSnapshot]:
        stmt = (
            select(CompanyAnalyticsSnapshot)
            .where(
                CompanyAnalyticsSnapshot.company_id == company_id,
                self._period_filter(CompanyAnalyticsSnapshot.period, period),
            )
            .order_by(CompanyAnalyticsSnapshot.period_start.desc())
            .options(selectinload(CompanyAnalyticsSnapshot.components))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        snapshots = list(result.scalars().all())
        snapshots.reverse()
        return snapshots

    async def get_latest_snapshot(
        self,
        company_id: UUID,
        period: AnalyticsPeriod | str = AnalyticsPeriod.DAILY,
    ) -> Optional[CompanyAnalyticsSnapshot]:
        period_enum = self._coerce_period(period)
        period_value = self._period_value(period_enum)
        logger.debug(
            "SnapshotService.get_latest_snapshot: company_id=%s, period=%s (value=%s)",
            company_id,
            period_enum,
            period_value,
        )
        stmt = (
            select(CompanyAnalyticsSnapshot)
            .where(
                CompanyAnalyticsSnapshot.company_id == company_id,
                self._period_filter(CompanyAnalyticsSnapshot.period, period),
            )
            .order_by(CompanyAnalyticsSnapshot.period_start.desc())
            .options(selectinload(CompanyAnalyticsSnapshot.components))
            .limit(1)
        )
        logger.debug("Executing SQL query for get_latest_snapshot...")
        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        logger.info(
            "SnapshotService.get_latest_snapshot result: %s (id=%s)",
            "found" if snapshot else "NOT FOUND",
            snapshot.id if snapshot else None,
        )
        return snapshot

    async def compute_snapshot_for_period(
        self,
        company_id: UUID,
        period_start: datetime,
        period: AnalyticsPeriod | str = AnalyticsPeriod.DAILY,
    ) -> CompanyAnalyticsSnapshot:
        """Calculate analytics snapshot for provided time bounds."""
        period_start = self._ensure_timezone(period_start)
        period_enum = self._coerce_period(period)
        period_duration = self.PERIOD_LOOKUPS[period_enum]
        period_end = period_start + period_duration

        news_stats = await self._aggregate_news(company_id, period_start, period_end)
        changes = await self._load_change_events(company_id, period_start, period_end)

        pricing_changes, feature_updates = self._summarise_change_events(changes)
        funding_events = news_stats.get("funding_events", 0)

        innovation_velocity = self._calculate_velocity(period_enum, pricing_changes, feature_updates)
        components = self._build_components(
            news_stats,
            pricing_changes,
            feature_updates,
            funding_events,
            innovation_velocity,
        )
        impact_score = sum(component["score"] for component in components)

        previous_snapshot = await self._get_previous_snapshot(company_id, period_enum, period_start)
        trend_delta = self._compute_trend_delta(previous_snapshot, impact_score)

        snapshot = await self._upsert_snapshot(
            company_id=company_id,
            period=period_enum,
            period_start=period_start,
            period_end=period_end,
            news_stats=news_stats,
            pricing_changes=pricing_changes,
            feature_updates=feature_updates,
            funding_events=funding_events,
            innovation_velocity=innovation_velocity,
            impact_score=impact_score,
            trend_delta=trend_delta,
        )

        await self.db.flush()
        await self._persist_components(snapshot, components)
        await self.db.commit()
        await self.db.refresh(snapshot)
        await self.db.refresh(snapshot, attribute_names=["components"])

        return snapshot

    async def refresh_company_snapshots(
        self,
        company_id: UUID,
        period: AnalyticsPeriod | str = AnalyticsPeriod.DAILY,
        lookback: int = 30,
    ) -> List[CompanyAnalyticsSnapshot]:
        """Recompute snapshots across lookback window."""
        snapshots: List[CompanyAnalyticsSnapshot] = []
        period_enum = self._coerce_period(period)
        period_duration = self.PERIOD_LOOKUPS[period_enum]
        anchor = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)

        for offset in range(lookback):
            period_start = anchor - period_duration * (offset + 1)
            snapshot = await self.compute_snapshot_for_period(company_id, period_start, period_enum)
            snapshots.append(snapshot)

        return list(reversed(snapshots))

    async def sync_knowledge_graph(
        self,
        company_id: UUID,
        period_start: datetime,
        period: AnalyticsPeriod | str = AnalyticsPeriod.DAILY,
    ) -> int:
        """Detect and persist knowledge graph edges for the period."""
        period_start = self._ensure_timezone(period_start)
        period_enum = self._coerce_period(period)
        period_end = period_start + self.PERIOD_LOOKUPS[period_enum]

        news_items = await self._load_news_items(company_id, period_start, period_end)
        change_events = await self._load_change_events(company_id, period_start, period_end)

        edge_count = 0
        for change_event in change_events:
            for news in news_items:
                if self._is_related(change_event, news):
                    created = await self._create_graph_edge(
                        company_id=company_id,
                        source_type=AnalyticsEntityType.CHANGE_EVENT,
                        source_id=change_event.id,
                        target_type=AnalyticsEntityType.NEWS_ITEM,
                        target_id=news.id,
                        relationship=RelationshipType.CAUSES,
                        confidence=self._estimate_confidence(change_event, news),
                        metadata={
                            "change_detected_at": change_event.detected_at.isoformat(),
                            "news_published_at": news.published_at.isoformat() if news.published_at else None,
                            "category": news.category.value if news.category else None,
                        },
                    )
                    if created:
                        edge_count += 1

        if edge_count:
            await self.db.commit()

        return edge_count

    async def _aggregate_news(
        self,
        company_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, float]:
        start_utc = self._to_naive_utc(period_start)
        end_utc = self._to_naive_utc(period_end)

        stmt = (
            select(
                func.count(NewsItem.id).label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (NewsItem.sentiment == SentimentLabel.POSITIVE, 1),
                            else_=0,
                        )
                    ),
                    0
                ).label("positive"),
                func.coalesce(
                    func.sum(
                        case(
                            (NewsItem.sentiment == SentimentLabel.NEGATIVE, 1),
                            else_=0,
                        )
                    ),
                    0
                ).label("negative"),
                func.coalesce(
                    func.sum(
                        case(
                            (NewsItem.sentiment == SentimentLabel.NEUTRAL, 1),
                            else_=0,
                        )
                    ),
                    0
                ).label("neutral"),
                func.coalesce(func.avg(NewsItem.priority_score), 0.0).label("avg_priority"),
                func.coalesce(
                    func.sum(
                        case(
                            (NewsItem.category == NewsCategory.FUNDING_NEWS, 1),
                            else_=0,
                        )
                    ),
                    0
                ).label("funding_events"),
            )
            .where(
                NewsItem.company_id == company_id,
                NewsItem.published_at >= start_utc,
                NewsItem.published_at < end_utc,
            )
        )

        result = await self.db.execute(stmt)
        row = result.one()

        total_news = row.total or 0
        positive = int(row.positive or 0)
        negative = int(row.negative or 0)
        neutral = int(row.neutral or 0)
        average_sentiment = 0.0
        if total_news:
            average_sentiment = (positive - negative) / float(total_news)

        return {
            "total_news": total_news,
            "positive_news": positive,
            "negative_news": negative,
            "neutral_news": neutral,
            "average_priority": float(row.avg_priority or 0.0),
            "average_sentiment": average_sentiment,
            "funding_events": int(row.funding_events or 0),
        }

    async def _load_change_events(
        self,
        company_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[CompetitorChangeEvent]:
        start_utc = self._to_naive_utc(period_start)
        end_utc = self._to_naive_utc(period_end)
        status_bind = bindparam(
            "change_status_success",
            ChangeProcessingStatus.SUCCESS.value,
            type_=String,
        )

        stmt = (
            select(CompetitorChangeEvent)
            .where(
                CompetitorChangeEvent.company_id == company_id,
                CompetitorChangeEvent.detected_at >= start_utc,
                CompetitorChangeEvent.detected_at < end_utc,
                cast(CompetitorChangeEvent.processing_status, String) == status_bind,
            )
            .order_by(CompetitorChangeEvent.detected_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _summarise_change_events(
        self, events: Iterable[CompetitorChangeEvent]
    ) -> Tuple[int, int]:
        pricing_changes = 0
        feature_updates = 0

        for event in events:
            pricing_flag = False
            feature_flag = False

            for change in event.changed_fields or []:
                change_type = (change.get("type") or "").lower()
                if change_type in {"pricing", "price", "plan"}:
                    pricing_flag = True
                if change_type in {"feature", "product", "integration", "capability"}:
                    feature_flag = True

            if pricing_flag:
                pricing_changes += 1
            if feature_flag or (not pricing_flag and not feature_flag):
                feature_updates += 1

        return pricing_changes, feature_updates

    def _calculate_velocity(
        self, period: AnalyticsPeriod, pricing_changes: int, feature_updates: int
    ) -> float:
        days = {
            AnalyticsPeriod.DAILY: 1,
            AnalyticsPeriod.WEEKLY: 7,
            AnalyticsPeriod.MONTHLY: 30,
        }[period]
        return (pricing_changes + feature_updates) / max(days, 1)

    def _build_components(
        self,
        news_stats: Dict[str, float],
        pricing_changes: int,
        feature_updates: int,
        funding_events: int,
        innovation_velocity: float,
    ) -> List[Dict[str, float]]:
        positive_delta = news_stats["positive_news"] - news_stats["negative_news"]
        news_signal = (
            news_stats["total_news"] * self.IMPACT_WEIGHTS["news_volume"]
            + positive_delta * self.IMPACT_WEIGHTS["sentiment_delta"]
            + news_stats["average_priority"] * self.IMPACT_WEIGHTS["priority"]
        )

        components = [
            {
                "component_type": ImpactComponentType.NEWS_SIGNAL,
                "weight": self.IMPACT_WEIGHTS["news_volume"],
                "score": news_signal,
                "metadata": {
                    "total_news": news_stats["total_news"],
                    "positive_delta": positive_delta,
                    "average_priority": news_stats["average_priority"],
                },
            },
            {
                "component_type": ImpactComponentType.PRICING_CHANGE,
                "weight": self.IMPACT_WEIGHTS["pricing_change"],
                "score": pricing_changes * self.IMPACT_WEIGHTS["pricing_change"],
                "metadata": {"pricing_changes": pricing_changes},
            },
            {
                "component_type": ImpactComponentType.FEATURE_RELEASE,
                "weight": self.IMPACT_WEIGHTS["feature_update"],
                "score": feature_updates * self.IMPACT_WEIGHTS["feature_update"],
                "metadata": {"feature_updates": feature_updates},
            },
            {
                "component_type": ImpactComponentType.FUNDING_EVENT,
                "weight": self.IMPACT_WEIGHTS["funding_event"],
                "score": funding_events * self.IMPACT_WEIGHTS["funding_event"],
                "metadata": {"funding_events": funding_events},
            },
            {
                "component_type": ImpactComponentType.OTHER,
                "weight": self.IMPACT_WEIGHTS["velocity"],
                "score": innovation_velocity * self.IMPACT_WEIGHTS["velocity"],
                "metadata": {"innovation_velocity": innovation_velocity},
            },
        ]
        return components

    async def _upsert_snapshot(
        self,
        company_id: UUID,
        period: AnalyticsPeriod,
        period_start: datetime,
        period_end: datetime,
        news_stats: Dict[str, float],
        pricing_changes: int,
        feature_updates: int,
        funding_events: int,
        innovation_velocity: float,
        impact_score: float,
        trend_delta: float,
    ) -> CompanyAnalyticsSnapshot:
        period_db_value = self._period_value(period)

        stmt = (
            select(CompanyAnalyticsSnapshot)
            .where(
                CompanyAnalyticsSnapshot.company_id == company_id,
                self._period_filter(CompanyAnalyticsSnapshot.period, period),
                CompanyAnalyticsSnapshot.period_start == period_start,
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        metrics_breakdown = {
            "news": news_stats,
            "pricing_changes": pricing_changes,
            "feature_updates": feature_updates,
            "funding_events": funding_events,
        }

        now = datetime.now(timezone.utc)

        if snapshot is None:
            snapshot = CompanyAnalyticsSnapshot(
                company_id=company_id,
                period=period_db_value,
                period_start=period_start,
                period_end=period_end,
                news_total=news_stats["total_news"],
                news_positive=news_stats["positive_news"],
                news_negative=news_stats["negative_news"],
                news_neutral=news_stats["neutral_news"],
                news_average_sentiment=news_stats["average_sentiment"],
                news_average_priority=news_stats["average_priority"],
                pricing_changes=pricing_changes,
                feature_updates=feature_updates,
                funding_events=funding_events,
                impact_score=impact_score,
                innovation_velocity=innovation_velocity,
                trend_delta=trend_delta,
                metric_breakdown=metrics_breakdown,
            )
            self.db.add(snapshot)
            snapshot.created_at = now
            snapshot.updated_at = now
        else:
            snapshot.period = period_db_value
            snapshot.period_end = period_end
            snapshot.news_total = news_stats["total_news"]
            snapshot.news_positive = news_stats["positive_news"]
            snapshot.news_negative = news_stats["negative_news"]
            snapshot.news_neutral = news_stats["neutral_news"]
            snapshot.news_average_sentiment = news_stats["average_sentiment"]
            snapshot.news_average_priority = news_stats["average_priority"]
            snapshot.pricing_changes = pricing_changes
            snapshot.feature_updates = feature_updates
            snapshot.funding_events = funding_events
            snapshot.impact_score = impact_score
            snapshot.innovation_velocity = innovation_velocity
            snapshot.trend_delta = trend_delta
            snapshot.metric_breakdown = metrics_breakdown
            snapshot.updated_at = now

        return snapshot

    async def _persist_components(
        self,
        snapshot: CompanyAnalyticsSnapshot,
        components: List[Dict[str, float]],
    ) -> None:
        from datetime import datetime, timezone
        
        await self.db.execute(
            delete(ImpactComponent).where(ImpactComponent.snapshot_id == snapshot.id)
        )

        now = datetime.now(timezone.utc)
        for component_data in components:
            component = ImpactComponent(
                snapshot_id=snapshot.id,
                company_id=snapshot.company_id,
                component_type=component_data["component_type"],
                weight=component_data["weight"],
                score_contribution=component_data["score"],
                metadata_json=component_data.get("metadata", {}),
            )
            component.created_at = now
            component.updated_at = now
            self.db.add(component)

    async def _get_previous_snapshot(
        self,
        company_id: UUID,
        period: AnalyticsPeriod,
        period_start: datetime,
    ) -> Optional[CompanyAnalyticsSnapshot]:
        stmt = (
            select(CompanyAnalyticsSnapshot)
            .where(
                CompanyAnalyticsSnapshot.company_id == company_id,
                self._period_filter(CompanyAnalyticsSnapshot.period, period),
                CompanyAnalyticsSnapshot.period_start < period_start,
            )
            .order_by(CompanyAnalyticsSnapshot.period_start.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _compute_trend_delta(
        self,
        previous_snapshot: Optional[CompanyAnalyticsSnapshot],
        current_score: float,
    ) -> float:
        if not previous_snapshot:
            return 0.0
        baseline = previous_snapshot.impact_score or 1.0
        return (current_score - baseline) / baseline

    async def _load_news_items(
        self,
        company_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NewsItem]:
        start_utc = self._to_naive_utc(period_start)
        end_utc = self._to_naive_utc(period_end)

        stmt = (
            select(NewsItem)
            .where(
                NewsItem.company_id == company_id,
                NewsItem.published_at >= start_utc,
                NewsItem.published_at < end_utc,
            )
            .order_by(NewsItem.published_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _is_related(
        self, change_event: CompetitorChangeEvent, news_item: NewsItem
    ) -> bool:
        if not news_item.published_at:
            return False
        delta = abs((news_item.published_at - change_event.detected_at).total_seconds())
        if delta > 48 * 3600:
            return False
        summary = (change_event.change_summary or "").lower()
        if summary and news_item.title:
            summary_tokens = summary.split()
            title = news_item.title.lower()
            if any(token in title for token in summary_tokens[:6]):
                return True
        return bool(news_item.category == NewsCategory.PRICING_CHANGE)

    async def _create_graph_edge(
        self,
        company_id: UUID,
        source_type: AnalyticsEntityType,
        source_id: UUID,
        target_type: AnalyticsEntityType,
        target_id: UUID,
        relationship: RelationshipType,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        stmt = insert(AnalyticsGraphEdge).values(
            company_id=company_id,
            source_entity_type=source_type,
            source_entity_id=source_id,
            target_entity_type=target_type,
            target_entity_id=target_id,
            relationship_type=relationship,
            confidence=confidence,
            metadata=metadata or {},
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                AnalyticsGraphEdge.source_entity_id,
                AnalyticsGraphEdge.target_entity_id,
                AnalyticsGraphEdge.relationship_type,
            ]
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    def _estimate_confidence(
        self, change_event: CompetitorChangeEvent, news_item: NewsItem
    ) -> float:
        base_confidence = 0.6
        if news_item.category == NewsCategory.PRICING_CHANGE:
            base_confidence += 0.1
        delta_hours = abs(
            (news_item.published_at - change_event.detected_at).total_seconds()
        ) / 3600
        proximity_bonus = max(0.0, 0.2 - (delta_hours / 240))
        return min(0.95, base_confidence + proximity_bonus)

    def _ensure_timezone(self, value: datetime) -> datetime:
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)

    def _to_naive_utc(self, value: datetime) -> datetime:
        value = self._ensure_timezone(value)
        return value.astimezone(timezone.utc).replace(tzinfo=None)


