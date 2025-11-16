"""
Service helpers for building multi-subject analytics comparisons and export payloads.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AnalyticsGraphEdge,
    AnalyticsPeriod,
    Company,
    CompanyAnalyticsSnapshot,
    ImpactComponent,
    NewsTopic,
    SentimentLabel,
    SourceType,
    User,
    UserPreferences,
    UserReportPreset,
)
from app.schemas.analytics import (
    AggregatedImpactComponent,
    AnalyticsExportRequest,
    AnalyticsExportResponse,
    ComparisonFilters,
    ComparisonMetricSummary,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonSeries,
    ComparisonSeriesPoint,
    ComparisonSubjectSummary,
    ComparisonCompanySummary,
    NotificationSettingsSummary,
    KnowledgeGraphEdgeResponse,
    CompanyAnalyticsSnapshotSummary,
    ReportPresetResponse,
)
from app.schemas.competitor_events import CompetitorChangeEventSchema
from app.services.analytics_service import AnalyticsService
from app.services.competitor_change_service import CompetitorChangeService
from app.services.competitor_service import CompetitorAnalysisService


@dataclass
class _ResolvedSubject:
    """Internal representation of the comparison subject."""

    subject_type: str  # "company" | "preset"
    reference_id: UUID
    subject_key: str
    label: str
    company_ids: List[UUID]
    companies: List[Company]
    preset: Optional[UserReportPreset]
    color: Optional[str]
    filters_for_fetch: Optional[Dict[str, Any]]
    filters_display: ComparisonFilters


class AnalyticsComparisonService:
    """Aggregates analytics comparison data across companies and presets."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)
        self.competitor_service = CompetitorAnalysisService(db)
        self.change_service = CompetitorChangeService(db)

    async def build_comparison(
        self,
        payload: ComparisonRequest,
        *,
        user: User,
    ) -> ComparisonResponse:
        """Build aggregated comparison response for the provided subjects."""
        if not payload.subjects:
            raise ValueError("At least one comparison subject must be provided")

        window_start, window_end = self._resolve_window(payload)
        resolved_subjects = await self._resolve_subjects(payload, user=user)

        if not resolved_subjects:
            raise ValueError("Unable to resolve any comparison subjects")

        unique_company_ids = self._collect_company_ids(resolved_subjects)
        company_details_map = await self._load_company_map(unique_company_ids)

        # Load snapshots per company for impact series and breakdowns
        company_snapshots: Dict[UUID, List[CompanyAnalyticsSnapshot]] = {}
        for company_id in unique_company_ids:
            snapshots = await self.analytics_service.get_snapshots(
                company_id,
                payload.period,
                payload.lookback,
            )
            company_snapshots[company_id] = snapshots

        subject_summaries: List[ComparisonSubjectSummary] = []
        metric_summaries: List[ComparisonMetricSummary] = []
        series_collection: List[ComparisonSeries] = []
        change_log_map: Dict[str, List[CompetitorChangeEventSchema]] = {}
        knowledge_graph_map: Dict[str, List[KnowledgeGraphEdgeResponse]] = {}

        for subject in resolved_subjects:
            subject_company_metrics = await self._load_metrics_for_subject(
                subject,
                window_start=window_start,
                window_end=window_end,
                top_news_limit=payload.top_news_limit,
            )
            subject_companies = [
                company_details_map[company_id]
                for company_id in subject.company_ids
                if company_id in company_details_map
            ]
            subject_summary = self._build_subject_summary(subject, subject_companies)
            subject_summaries.append(subject_summary)

            metrics_summary, latest_snapshot = self._aggregate_metrics_for_subject(
                subject,
                company_metrics=subject_company_metrics,
                company_snapshots=company_snapshots,
                top_news_limit=payload.top_news_limit,
                include_components=payload.include_components,
            )
            metric_summaries.append(metrics_summary)

            if payload.include_series:
                series_points = self._build_series_for_subject(
                    subject,
                    company_snapshots=company_snapshots,
                    latest_snapshot=latest_snapshot,
                )
                series_collection.append(
                    ComparisonSeries(
                        subject_key=subject.subject_key,
                        subject_id=subject.reference_id,
                        snapshots=series_points,
                    )
                )

            if payload.include_change_log:
                change_events = await self._load_change_events(
                    subject.company_ids,
                    limit=payload.change_log_limit,
                )
                change_log_map[subject.subject_key] = change_events

            if payload.include_knowledge_graph:
                edges = await self._load_graph_edges(
                    subject.company_ids,
                    limit=payload.knowledge_graph_limit,
                )
                knowledge_graph_map[subject.subject_key] = edges

        return ComparisonResponse(
            generated_at=datetime.now(timezone.utc),
            period=payload.period,
            lookback=payload.lookback,
            date_from=window_start,
            date_to=window_end,
            subjects=subject_summaries,
            metrics=metric_summaries,
            series=series_collection,
            change_log=change_log_map,
            knowledge_graph=knowledge_graph_map,
        )

    async def build_export_payload(
        self,
        payload: AnalyticsExportRequest,
        *,
        user: User,
    ) -> AnalyticsExportResponse:
        """Build full export payload containing comparison data and user context."""
        comparison_response = await self.build_comparison(payload, user=user)

        notification_summary: Optional[NotificationSettingsSummary] = None
        if payload.include.include_notifications:
            notification_summary = await self._load_notification_settings(user.id)

        preset_rows: List[Dict[str, Any]] = []
        if payload.include.include_presets:
            preset_rows = await self._load_user_presets(user.id)
            logger.debug("Export presets fetched", preset_count=len(preset_rows))
            if preset_rows:
                logger.debug("First preset payload", preset_example=preset_rows[0])
        else:
            logger.debug("Preset inclusion disabled on payload")

        return AnalyticsExportResponse(
            version="2.0.0",
            generated_at=datetime.now(timezone.utc),
            export_format=payload.export_format,
            timeframe={
                "period": comparison_response.period,
                "lookback": comparison_response.lookback,
                "date_from": comparison_response.date_from,
                "date_to": comparison_response.date_to,
            },
            comparison=comparison_response,
            notification_settings=notification_summary,
            presets=[
                ReportPresetResponse.model_validate(preset_row)
                for preset_row in preset_rows
            ],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_window(self, payload: ComparisonRequest) -> Tuple[datetime, datetime]:
        """Determine the analysis window."""
        now = datetime.now(timezone.utc)
        date_to = payload.date_to or now
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)
        date_from = payload.date_from or (date_to - timedelta(days=payload.lookback))
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)

        if date_from >= date_to:
            raise ValueError("date_from must be earlier than date_to")

        # Normalize to naive UTC timestamps to match DB columns (timestamp without tz)
        return date_from.replace(tzinfo=None), date_to.replace(tzinfo=None)

    async def _resolve_subjects(
        self,
        payload: ComparisonRequest,
        *,
        user: User,
    ) -> List[_ResolvedSubject]:
        """Resolve incoming subject definitions into internal representation."""
        resolved: List[_ResolvedSubject] = []
        preset_map: Dict[UUID, UserReportPreset] = {}

        # Load presets in a single query for efficiency
        preset_ids = [
            subject.reference_id
            for subject in payload.subjects
            if subject.subject_type == "preset"
        ]
        if preset_ids:
            preset_map = await self._load_preset_map(user.id, preset_ids)

        # Prepare base filters (applied to every subject)
        base_filters = self._normalize_filters(payload.filters)

        for subject in payload.subjects:
            if subject.subject_type == "company":
                company_id = subject.reference_id
                filters_for_fetch = base_filters
                display_filters = self._serialize_filters(filters_for_fetch)
                subject_key = f"company:{company_id}"
                resolved.append(
                    _ResolvedSubject(
                        subject_type="company",
                        reference_id=company_id,
                        subject_key=subject_key,
                        label=subject.label or "",
                        company_ids=[company_id],
                        companies=[],
                        preset=None,
                        color=subject.color,
                        filters_for_fetch=filters_for_fetch,
                        filters_display=display_filters,
                    )
                )
                continue

            if subject.subject_type == "preset":
                preset = preset_map.get(subject.reference_id)
                if not preset:
                    logger.warning("Preset %s not found for user %s", subject.reference_id, user.id)
                    continue

                preset_company_ids = [
                    UUID(str(company_id))
                    for company_id in (preset.companies or [])
                ]
                if not preset_company_ids:
                    logger.debug("Preset %s has no companies; skipping", preset.id)
                    continue

                preset_filters = self._normalize_filters_from_preset(preset)
                merged_filters = self._merge_filters(base_filters, preset_filters)
                display_filters = self._serialize_filters(merged_filters)
                subject_key = f"preset:{preset.id}"

                resolved.append(
                    _ResolvedSubject(
                        subject_type="preset",
                        reference_id=preset.id,
                        subject_key=subject_key,
                        label=subject.label or preset.name,
                        company_ids=preset_company_ids,
                        companies=[],
                        preset=preset,
                        color=subject.color,
                        filters_for_fetch=merged_filters,
                        filters_display=display_filters,
                    )
                )
                continue

            raise ValueError(f"Unsupported subject type {subject.subject_type}")

        return resolved

    def _collect_company_ids(self, subjects: Iterable[_ResolvedSubject]) -> List[UUID]:
        company_ids: List[UUID] = []
        seen: set[UUID] = set()
        for subject in subjects:
            for company_id in subject.company_ids:
                if company_id not in seen:
                    company_ids.append(company_id)
                    seen.add(company_id)
        return company_ids

    async def _load_company_map(self, company_ids: Sequence[UUID]) -> Dict[UUID, Company]:
        if not company_ids:
            return {}

        stmt = (
            select(Company)
            .where(Company.id.in_(company_ids))
            .options(selectinload(Company.analytics_graph_edges))
        )
        result = await self.db.execute(stmt)
        companies = list(result.scalars().all())
        return {company.id: company for company in companies}

    def _build_subject_summary(
        self,
        subject: _ResolvedSubject,
        companies: Sequence[Company],
    ) -> ComparisonSubjectSummary:
        company_summaries = [
            ComparisonCompanySummary(
                id=company.id,
                name=company.name,
                category=company.category,
                logo_url=company.logo_url,
            )
            for company in companies
        ]

        label = subject.label
        if not label and companies:
            label = ", ".join(company.name for company in companies)

        return ComparisonSubjectSummary(
            subject_key=subject.subject_key,
            subject_id=subject.reference_id,
            subject_type=subject.subject_type,
            label=label,
            company_ids=subject.company_ids,
            preset_id=subject.preset.id if subject.preset else None,
            color=subject.color,
            companies=company_summaries,
            filters=subject.filters_display,
        )

    async def _load_metrics_for_subject(
        self,
        subject: _ResolvedSubject,
        *,
        window_start: datetime,
        window_end: datetime,
        top_news_limit: int,
    ) -> Dict[UUID, Dict[str, Any]]:
        metrics: Dict[UUID, Dict[str, Any]] = {}
        for company_id in subject.company_ids:
            metrics[company_id] = await self.competitor_service.build_company_metrics(
                company_id,
                window_start,
                window_end,
                filters=subject.filters_for_fetch,
                top_news_limit=top_news_limit,
            )
        return metrics

    def _aggregate_metrics_for_subject(
        self,
        subject: _ResolvedSubject,
        *,
        company_metrics: Dict[UUID, Dict[str, Any]],
        company_snapshots: Dict[UUID, List[CompanyAnalyticsSnapshot]],
        top_news_limit: int,
        include_components: bool,
    ) -> Tuple[ComparisonMetricSummary, Optional[CompanyAnalyticsSnapshotSummary]]:
        metrics_list = [
            company_metrics[company_id]
            for company_id in subject.company_ids
            if company_id in company_metrics
        ]

        if not metrics_list:
            empty_summary = ComparisonMetricSummary(
                subject_key=subject.subject_key,
                subject_id=subject.reference_id,
                news_volume=0,
                activity_score=0.0,
                avg_priority=0.0,
                impact_score=0.0,
                trend_delta=0.0,
                innovation_velocity=0.0,
                sentiment_distribution={},
                category_distribution={},
                topic_distribution={},
                daily_activity={},
                top_news=[],
                impact_components=[],
                snapshot=None,
            )
            return empty_summary, None

        news_volume = sum(metric["news_volume"] for metric in metrics_list)
        activity_scores = [metric["activity_score"] for metric in metrics_list]
        avg_priority_values = [metric["avg_priority"] for metric in metrics_list]

        category_distribution = self._merge_counter(
            (metric["category_distribution"] for metric in metrics_list)
        )
        topic_distribution = self._merge_counter(
            (metric["topic_distribution"] for metric in metrics_list)
        )
        sentiment_distribution = self._merge_counter(
            (metric["sentiment_distribution"] for metric in metrics_list)
        )
        daily_activity = self._merge_counter(
            (metric["daily_activity"] for metric in metrics_list)
        )
        top_news = self._aggregate_top_news(metrics_list, limit=top_news_limit)

        latest_snapshot_summary = self._aggregate_latest_snapshot(
            subject,
            company_snapshots=company_snapshots,
            include_components=include_components,
        )

        impact_score = latest_snapshot_summary.impact_score if latest_snapshot_summary else 0.0
        trend_delta = latest_snapshot_summary.trend_delta if latest_snapshot_summary else 0.0
        innovation_velocity = (
            latest_snapshot_summary.innovation_velocity if latest_snapshot_summary else 0.0
        )

        components = latest_snapshot_summary.components if (latest_snapshot_summary and include_components) else []

        summary = ComparisonMetricSummary(
            subject_key=subject.subject_key,
            subject_id=subject.reference_id,
            news_volume=news_volume,
            activity_score=self._safe_mean(activity_scores),
            avg_priority=self._safe_mean(avg_priority_values),
            impact_score=impact_score,
            trend_delta=trend_delta,
            innovation_velocity=innovation_velocity,
            sentiment_distribution=sentiment_distribution,
            category_distribution=category_distribution,
            topic_distribution=topic_distribution,
            daily_activity=daily_activity,
            top_news=top_news,
            impact_components=components,
            snapshot=latest_snapshot_summary,
        )

        return summary, latest_snapshot_summary

    def _build_series_for_subject(
        self,
        subject: _ResolvedSubject,
        *,
        company_snapshots: Dict[UUID, List[CompanyAnalyticsSnapshot]],
        latest_snapshot: Optional[CompanyAnalyticsSnapshotSummary],
    ) -> List[ComparisonSeriesPoint]:
        bucket: Dict[datetime, Dict[str, Any]] = defaultdict(lambda: {
            "impact_scores": [],
            "innovation_velocities": [],
            "news_total": 0,
            "news_positive": 0,
            "news_negative": 0,
            "news_neutral": 0,
            "pricing_changes": 0,
            "feature_updates": 0,
            "funding_events": 0,
        })

        for company_id in subject.company_ids:
            snapshots = company_snapshots.get(company_id) or []
            for snapshot in snapshots:
                entry = bucket[snapshot.period_start]
                entry["impact_scores"].append(snapshot.impact_score)
                entry["innovation_velocities"].append(snapshot.innovation_velocity)
                entry["news_total"] += snapshot.news_total
                entry["news_positive"] += snapshot.news_positive or 0
                entry["news_negative"] += snapshot.news_negative or 0
                entry["news_neutral"] += snapshot.news_neutral
                entry["pricing_changes"] += snapshot.pricing_changes
                entry["feature_updates"] += snapshot.feature_updates
                entry["funding_events"] += snapshot.funding_events

        series: List[ComparisonSeriesPoint] = []
        previous_score: Optional[float] = None
        for period_start in sorted(bucket.keys()):
            entry = bucket[period_start]
            impact_score = self._safe_mean(entry["impact_scores"])
            trend_delta = None
            if previous_score not in (None, 0):
                trend_delta = round(((impact_score - previous_score) / abs(previous_score)) * 100.0, 2)
            previous_score = impact_score
            series.append(
                ComparisonSeriesPoint(
                    period_start=period_start,
                    impact_score=impact_score,
                    innovation_velocity=self._safe_mean(entry["innovation_velocities"]),
                    trend_delta=trend_delta,
                    news_total=entry["news_total"],
                    news_positive=entry["news_positive"],
                    news_negative=entry["news_negative"],
                    news_neutral=entry["news_neutral"],
                    pricing_changes=entry["pricing_changes"],
                    feature_updates=entry["feature_updates"],
                    funding_events=entry["funding_events"],
                )
            )

        # Recompute trend delta based on series progression if snapshot summary was absent
        if series and (not latest_snapshot or latest_snapshot.trend_delta is None):
            trend = self._compute_trend(series)
            if series:
                series[-1].trend_delta = trend

        return series

    async def _load_change_events(
        self,
        company_ids: Sequence[UUID],
        *,
        limit: int,
    ) -> List[CompetitorChangeEventSchema]:
        events: List[CompetitorChangeEventSchema] = []
        for company_id in company_ids:
            serialised = await self.change_service.list_change_events_payload(
                company_id, limit=limit
            )
            events.extend(
                CompetitorChangeEventSchema.model_validate(event)
                for event in serialised
            )

        events.sort(key=lambda event: event.detected_at, reverse=True)
        return events[:limit]

    async def _load_graph_edges(
        self,
        company_ids: Sequence[UUID],
        *,
        limit: int,
    ) -> List[KnowledgeGraphEdgeResponse]:
        if not company_ids:
            return []

        stmt = (
            select(AnalyticsGraphEdge)
            .where(
                AnalyticsGraphEdge.company_id.in_(company_ids),
                AnalyticsGraphEdge.company_id.isnot(None),
            )
            .order_by(AnalyticsGraphEdge.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        edges = list(result.scalars().all())

        return [
            KnowledgeGraphEdgeResponse(
                id=edge.id,
                company_id=edge.company_id,
                source_entity_type=edge.source_entity_type,
                source_entity_id=edge.source_entity_id,
                target_entity_type=edge.target_entity_type,
                target_entity_id=edge.target_entity_id,
                relationship_type=edge.relationship_type,
                confidence=edge.confidence,
                weight=edge.weight,
                metadata=edge.metadata_json or {},
            )
            for edge in edges
        ]

    async def _load_notification_settings(self, user_id: UUID) -> Optional[NotificationSettingsSummary]:
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await self.db.execute(stmt)
        preferences = result.scalar_one_or_none()
        if not preferences:
            return None

        return NotificationSettingsSummary(
            notification_frequency=self._enum_value(preferences.notification_frequency),
            digest_enabled=preferences.digest_enabled,
            digest_frequency=self._enum_value(preferences.digest_frequency),
            digest_format=self._enum_value(preferences.digest_format),
            digest_custom_schedule=preferences.digest_custom_schedule or {},
            subscribed_companies=[company for company in preferences.subscribed_companies or []],
            interested_categories=[
                category.value if hasattr(category, "value") else str(category)
                for category in preferences.interested_categories or []
            ],
            keywords=preferences.keywords or [],
            telegram_enabled=preferences.telegram_enabled,
            telegram_chat_id=preferences.telegram_chat_id,
            telegram_digest_mode=self._enum_value(preferences.telegram_digest_mode),
            timezone=preferences.timezone,
            week_start_day=preferences.week_start_day,
        )

    async def _load_user_presets(self, user_id: UUID) -> List[Dict[str, Any]]:
        stmt = (
            select(
                UserReportPreset.id,
                UserReportPreset.user_id,
                UserReportPreset.name,
                UserReportPreset.description,
                UserReportPreset.companies,
                UserReportPreset.filters,
                UserReportPreset.visualization_config,
                UserReportPreset.is_favorite,
                UserReportPreset.created_at,
                UserReportPreset.updated_at,
            )
            .where(UserReportPreset.user_id == user_id)
            .order_by(UserReportPreset.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = []
        for mapping in result.mappings():
            row_dict = dict(mapping)
            logger.debug("Raw preset mapping: {}", row_dict)
            companies = [str(company_id) for company_id in self._normalise_array(row_dict.get("companies"))]
            filters = self._normalise_json(row_dict.get("filters"), default={})
            visualization = self._normalise_json(row_dict.get("visualization_config"), default={})

            serialised_row: Dict[str, Any] = {
                "id": str(row_dict["id"]),
                "user_id": str(row_dict["user_id"]),
                "name": row_dict["name"],
                "description": row_dict.get("description"),
                "companies": companies,
                "filters": filters,
                "visualization_config": visualization,
                "is_favorite": row_dict["is_favorite"],
                "created_at": row_dict["created_at"].isoformat() if row_dict.get("created_at") else None,
                "updated_at": row_dict["updated_at"].isoformat() if row_dict.get("updated_at") else None,
            }
            logger.debug("Serialised preset row: {}", serialised_row)
            rows.append(serialised_row)
        return rows

    async def _load_preset_map(
        self,
        user_id: UUID,
        preset_ids: Sequence[UUID],
    ) -> Dict[UUID, UserReportPreset]:
        if not preset_ids:
            return {}

        stmt = (
            select(UserReportPreset)
            .where(
                UserReportPreset.user_id == user_id,
                UserReportPreset.id.in_(preset_ids),
            )
        )
        result = await self.db.execute(stmt)
        presets = list(result.scalars().all())
        return {preset.id: preset for preset in presets}

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _merge_filters(
        self,
        base_filters: Optional[Dict[str, Any]],
        preset_filters: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not preset_filters:
            return base_filters
        if not base_filters:
            return preset_filters

        merged: Dict[str, Any] = {}
        merged["topics"] = self._merge_list_filters(
            base_filters.get("topics"),
            preset_filters.get("topics"),
        )
        merged["sentiments"] = self._merge_list_filters(
            base_filters.get("sentiments"),
            preset_filters.get("sentiments"),
        )
        merged["source_types"] = self._merge_list_filters(
            base_filters.get("source_types"),
            preset_filters.get("source_types"),
        )

        base_min_priority = base_filters.get("min_priority")
        preset_min_priority = preset_filters.get("min_priority")
        if base_min_priority is not None and preset_min_priority is not None:
            merged["min_priority"] = max(base_min_priority, preset_min_priority)
        else:
            merged["min_priority"] = base_min_priority if base_min_priority is not None else preset_min_priority

        cleaned = {
            key: value
            for key, value in merged.items()
            if value is not None and (value != [] and value != ())
        }
        if merged.get("min_priority") is not None:
            cleaned["min_priority"] = merged["min_priority"]

        return cleaned or None

    def _merge_list_filters(
        self,
        base: Optional[Sequence[Any]],
        extra: Optional[Sequence[Any]],
    ) -> Optional[List[Any]]:
        values: List[Any] = []
        seen: set[Any] = set()
        for source in (base or []), (extra or []):
            for item in source:
                if item not in seen:
                    seen.add(item)
                    values.append(item)
        return values or None

    @staticmethod
    def _enum_value(value: Optional[Any]) -> str:
        if value is None:
            return ""
        serialised = value.value if hasattr(value, "value") else str(value)
        logger.debug("Normalised enum value", original=value, serialised=serialised)
        return serialised

    @staticmethod
    def _normalise_array(value: Optional[Any]) -> List[UUID]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [UUID(str(item)) if not isinstance(item, UUID) else item for item in value]
        try:
            parsed = json.loads(value)
            return [
                UUID(str(item)) if not isinstance(item, UUID) else item
                for item in parsed or []
            ]
        except (json.JSONDecodeError, TypeError, ValueError):
            return [UUID(str(value))]

    @staticmethod
    def _normalise_json(value: Optional[Any], *, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if parsed is not None else default
            except json.JSONDecodeError:
                return default
        logger.debug("Returning raw JSON value", raw=value)
        return value

    def _normalize_filters(self, filters: Optional[ComparisonFilters]) -> Optional[Dict[str, Any]]:
        if not filters:
            return None

        normalized: Dict[str, Any] = {}

        if filters.topics:
            normalized["topics"] = [NewsTopic(topic) for topic in filters.topics]
        if filters.sentiments:
            normalized["sentiments"] = [SentimentLabel(sentiment) for sentiment in filters.sentiments]
        if filters.source_types:
            normalized["source_types"] = [SourceType(source) for source in filters.source_types]
        if filters.min_priority is not None:
            normalized["min_priority"] = float(filters.min_priority)

        return normalized or None

    def _normalize_filters_from_preset(
        self,
        preset: UserReportPreset,
    ) -> Optional[Dict[str, Any]]:
        filters = preset.filters or {}
        if not filters:
            return None

        normalized: Dict[str, Any] = {}
        topics = filters.get("topics") or []
        sentiments = filters.get("sentiments") or []
        source_types = filters.get("source_types") or []
        min_priority = filters.get("min_priority")

        if topics:
            normalized["topics"] = [NewsTopic(topic) for topic in topics]
        if sentiments:
            normalized["sentiments"] = [SentimentLabel(sentiment) for sentiment in sentiments]
        if source_types:
            normalized["source_types"] = [SourceType(source) for source in source_types]
        if min_priority is not None:
            normalized["min_priority"] = float(min_priority)

        return normalized or None

    def _serialize_filters(self, filters: Optional[Dict[str, Any]]) -> ComparisonFilters:
        if not filters:
            return ComparisonFilters()

        topics = [
            topic.value if hasattr(topic, "value") else str(topic)
            for topic in (filters.get("topics") or [])
        ]
        sentiments = [
            sentiment.value if hasattr(sentiment, "value") else str(sentiment)
            for sentiment in (filters.get("sentiments") or [])
        ]
        source_types = [
            source.value if hasattr(source, "value") else str(source)
            for source in (filters.get("source_types") or [])
        ]
        min_priority = filters.get("min_priority")

        return ComparisonFilters(
            topics=topics,
            sentiments=sentiments,
            source_types=source_types,
            min_priority=min_priority,
        )

    def _merge_counter(
        self,
        dictionaries: Iterable[Dict[str, Any]],
    ) -> Dict[str, int]:
        counter: Dict[str, int] = defaultdict(int)
        for dictionary in dictionaries:
            for key, value in dictionary.items():
                label = key.value if hasattr(key, "value") else str(key)
                counter[label] += int(value)
        return dict(counter)

    def _aggregate_top_news(
        self,
        metrics_list: Sequence[Dict[str, Any]],
        *,
        limit: int,
    ) -> List[Dict[str, Any]]:
        news_items: List[Dict[str, Any]] = []
        for metrics in metrics_list:
            news_items.extend(metrics.get("top_news") or [])

        news_items.sort(key=lambda item: item.get("priority_score", 0), reverse=True)
        return news_items[:limit]

    def _aggregate_latest_snapshot(
        self,
        subject: _ResolvedSubject,
        *,
        company_snapshots: Dict[UUID, List[CompanyAnalyticsSnapshot]],
        include_components: bool,
    ) -> Optional[CompanyAnalyticsSnapshotSummary]:
        latest_snapshots: List[CompanyAnalyticsSnapshot] = []
        for company_id in subject.company_ids:
            snapshots = company_snapshots.get(company_id) or []
            if snapshots:
                latest_snapshots.append(snapshots[-1])

        if not latest_snapshots:
            return None

        total_news = sum(snapshot.news_total for snapshot in latest_snapshots)
        positive_news = sum(snapshot.news_positive or 0 for snapshot in latest_snapshots)
        negative_news = sum(snapshot.news_negative or 0 for snapshot in latest_snapshots)
        neutral_news = sum(snapshot.news_neutral or 0 for snapshot in latest_snapshots)
        pricing_changes = sum(snapshot.pricing_changes for snapshot in latest_snapshots)
        feature_updates = sum(snapshot.feature_updates for snapshot in latest_snapshots)
        funding_events = sum(snapshot.funding_events for snapshot in latest_snapshots)

        impact_components: List[AggregatedImpactComponent] = []
        if include_components:
            impact_components = self._aggregate_components(
                component_lists=[
                    snapshot.components or []
                    for snapshot in latest_snapshots
                ]
            )

        innovation_velocities = [snapshot.innovation_velocity for snapshot in latest_snapshots]
        impact_scores = [snapshot.impact_score for snapshot in latest_snapshots]
        trend_deltas = [snapshot.trend_delta for snapshot in latest_snapshots if snapshot.trend_delta is not None]

        return CompanyAnalyticsSnapshotSummary(
            period_start=latest_snapshots[-1].period_start,
            impact_score=self._safe_mean(impact_scores),
            innovation_velocity=self._safe_mean(innovation_velocities),
            trend_delta=self._safe_mean(trend_deltas) if trend_deltas else 0.0,
            news_total=total_news,
            news_positive=positive_news,
            news_negative=negative_news,
            news_neutral=neutral_news,
            pricing_changes=pricing_changes,
            feature_updates=feature_updates,
            funding_events=funding_events,
            components=impact_components,
        )

    def _aggregate_components(
        self,
        component_lists: Iterable[Sequence[ImpactComponent]],
    ) -> List[AggregatedImpactComponent]:
        accumulator: Dict[str, Dict[str, float]] = defaultdict(lambda: {"score": 0.0, "weight": 0.0, "count": 0})

        for components in component_lists:
            for component in components:
                key = component.component_type.value if hasattr(component.component_type, "value") else str(component.component_type)
                accumulator[key]["score"] += component.score_contribution
                accumulator[key]["weight"] += component.weight
                accumulator[key]["count"] += 1

        aggregated: List[AggregatedImpactComponent] = []
        for key, value in accumulator.items():
            count = max(value["count"], 1)
            aggregated.append(
                AggregatedImpactComponent(
                    component_type=key,
                    score_contribution=value["score"],
                    weight=value["weight"] / count,
                )
            )

        aggregated.sort(key=lambda component: component.score_contribution, reverse=True)
        return aggregated

    def _compute_trend(self, series: Sequence[ComparisonSeriesPoint]) -> float:
        if len(series) < 2:
            return 0.0
        previous = series[-2].impact_score
        current = series[-1].impact_score
        if not previous:
            return 0.0
        delta = ((current - previous) / abs(previous)) * 100.0
        return round(delta, 2)

    def _safe_mean(self, values: Sequence[float]) -> float:
        meaningful = [value for value in values if value is not None]
        if not meaningful:
            return 0.0
        return statistics.fmean(meaningful)


