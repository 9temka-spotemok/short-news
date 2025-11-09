"""
Service for competitor pricing snapshots and change detection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    Company,
    CompetitorChangeEvent,
    CompetitorPricingSnapshot,
    SourceType,
)
from app.parsers.pricing import PricingPageParser
from app.utils.snapshots import persist_snapshot


class CompetitorChangeService:
    """Encapsulates pricing snapshot parsing and change detection."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = PricingPageParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_change_events(
        self,
        company_id: uuid.UUID,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[CompetitorChangeEvent]:
        query = (
            select(CompetitorChangeEvent)
            .where(CompetitorChangeEvent.company_id == company_id)
            .order_by(desc(CompetitorChangeEvent.detected_at))
            .limit(limit)
            .options(
                selectinload(CompetitorChangeEvent.current_snapshot),
                selectinload(CompetitorChangeEvent.previous_snapshot),
            )
        )
        if status:
            query = query.where(CompetitorChangeEvent.processing_status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def process_pricing_page(
        self,
        company_id: uuid.UUID,
        source_url: str,
        source_type: SourceType,
        html: str,
    ) -> CompetitorChangeEvent:
        """
        Parse pricing HTML, store snapshot and create change event.
        """
        now = datetime.now(timezone.utc)
        snapshot = CompetitorPricingSnapshot(
            company_id=company_id,
            source_url=source_url,
            source_type=source_type,
            parser_version=self.parser.VERSION,
            extracted_at=now,
        )
        self.db.add(snapshot)

        try:
            parse_result = self.parser.parse(html, url=source_url)
            normalized_plans = [plan.to_dict() for plan in parse_result.plans]
            data_hash = self._compute_hash(normalized_plans)

            previous_snapshot = await self._fetch_previous_snapshot(
                company_id, source_url
            )

            diff = self._compute_diff(
                previous_snapshot.normalized_data if previous_snapshot else [],
                normalized_plans,
            )
            has_changes = self._has_changes(diff)
            change_summary = self._build_summary(diff)
            changed_fields = self._flatten_changes(diff)

            company_label = await self._get_company_label(company_id)
            snapshot_path = persist_snapshot(
                scope="pricing",
                company_identifier=company_label,
                source_id=self._snapshot_identifier(source_type, source_url),
                url=source_url,
                html=html,
            )

            snapshot.normalized_data = normalized_plans
            snapshot.data_hash = data_hash
            snapshot.raw_snapshot_url = snapshot_path
            snapshot.extraction_metadata = {
                **parse_result.extraction_metadata,
                "company_label": company_label,
                "source_url": source_url,
            }
            snapshot.warnings = parse_result.warnings
            snapshot.processing_status = (
                ChangeProcessingStatus.SUCCESS
                if has_changes
                else ChangeProcessingStatus.SKIPPED
            )

            event = CompetitorChangeEvent(
                company_id=company_id,
                source_type=source_type,
                change_summary=change_summary,
                changed_fields=changed_fields,
                raw_diff=diff,
                detected_at=now,
                current_snapshot=snapshot,
                previous_snapshot=previous_snapshot,
                processing_status=snapshot.processing_status,
                notification_status=(
                    ChangeNotificationStatus.PENDING
                    if has_changes
                    else ChangeNotificationStatus.SKIPPED
                ),
            )
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except Exception as exc:
            logger.exception("Pricing parser failed: %s", exc)
            snapshot.processing_status = ChangeProcessingStatus.ERROR
            snapshot.processing_notes = str(exc)
            snapshot.warnings = snapshot.warnings or [str(exc)]
            snapshot.normalized_data = []
            snapshot.raw_snapshot_url = None
            snapshot.data_hash = None

            event = CompetitorChangeEvent(
                company_id=company_id,
                source_type=source_type,
                change_summary="Failed to parse pricing page",
                changed_fields=[],
                raw_diff={"error": str(exc)},
                detected_at=datetime.now(timezone.utc),
                current_snapshot=snapshot,
                previous_snapshot=None,
                processing_status=ChangeProcessingStatus.ERROR,
                notification_status=ChangeNotificationStatus.FAILED,
            )
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            return event

    async def recompute_diff(
        self,
        event_id: uuid.UUID,
    ) -> Optional[CompetitorChangeEvent]:
        event = await self.db.get(
            CompetitorChangeEvent,
            event_id,
            options=[
                selectinload(CompetitorChangeEvent.current_snapshot),
                selectinload(CompetitorChangeEvent.previous_snapshot),
            ],
        )
        if not event or not event.current_snapshot:
            return None

        previous_data = (
            event.previous_snapshot.normalized_data
            if event.previous_snapshot
            else []
        )
        current_data = event.current_snapshot.normalized_data or []
        diff = self._compute_diff(previous_data, current_data)
        has_changes = self._has_changes(diff)

        event.change_summary = self._build_summary(diff)
        event.changed_fields = self._flatten_changes(diff)
        event.raw_diff = diff
        event.processing_status = (
            ChangeProcessingStatus.SUCCESS
            if has_changes
            else ChangeProcessingStatus.SKIPPED
        )
        event.notification_status = (
            ChangeNotificationStatus.PENDING
            if has_changes
            else ChangeNotificationStatus.SKIPPED
        )
        await self.db.commit()
        await self.db.refresh(event)
        return event

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_previous_snapshot(
        self,
        company_id: uuid.UUID,
        source_url: str,
    ) -> Optional[CompetitorPricingSnapshot]:
        query = (
            select(CompetitorPricingSnapshot)
            .where(
                CompetitorPricingSnapshot.company_id == company_id,
                CompetitorPricingSnapshot.source_url == source_url,
                CompetitorPricingSnapshot.processing_status.in_(
                    [
                        ChangeProcessingStatus.SUCCESS,
                        ChangeProcessingStatus.SKIPPED,
                    ]
                ),
            )
            .order_by(desc(CompetitorPricingSnapshot.extracted_at))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def _get_company_label(self, company_id: uuid.UUID) -> str:
        query = select(Company.name).where(Company.id == company_id)
        result = await self.db.execute(query)
        name = result.scalar_one_or_none()
        return name or str(company_id)

    def _snapshot_identifier(
        self,
        source_type: SourceType,
        source_url: str,
    ) -> str:
        digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
        return f"{source_type.value}_{digest}"

    def _compute_hash(self, payload: List[Dict[str, Any]]) -> str:
        serialised = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    # ----------------------
    # Diff helpers
    # ----------------------

    def _compute_diff(
        self,
        previous: Optional[Iterable[Dict[str, Any]]],
        current: Optional[Iterable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        prev_items = list(previous or [])
        curr_items = list(current or [])

        prev_map = {self._plan_key(plan): plan for plan in prev_items}
        curr_map = {self._plan_key(plan): plan for plan in curr_items}

        diff = {
            "added_plans": [],
            "removed_plans": [],
            "updated_plans": [],
        }

        for key, plan in curr_map.items():
            if key not in prev_map:
                diff["added_plans"].append(plan)
            else:
                prev_plan = prev_map[key]
                changes = self._compare_plan(prev_plan, plan)
                if changes:
                    diff["updated_plans"].append(
                        {"plan": plan.get("plan"), "changes": changes}
                    )

        for key, plan in prev_map.items():
            if key not in curr_map:
                diff["removed_plans"].append(plan)

        return diff

    def _compare_plan(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        changes: List[Dict[str, Any]] = []

        prev_price = previous.get("price")
        curr_price = current.get("price")
        prev_currency = previous.get("currency")
        curr_currency = current.get("currency")

        if self._numeric_changed(prev_price, curr_price) or prev_currency != curr_currency:
            changes.append(
                {
                    "field": "price",
                    "previous": prev_price,
                    "current": curr_price,
                    "previous_currency": prev_currency,
                    "current_currency": curr_currency,
                }
            )

        if previous.get("billing_cycle") != current.get("billing_cycle"):
            changes.append(
                {
                    "field": "billing_cycle",
                    "previous": previous.get("billing_cycle"),
                    "current": current.get("billing_cycle"),
                }
            )

        feature_diff = self._diff_features(
            previous.get("features") or [],
            current.get("features") or [],
        )
        if feature_diff["added"] or feature_diff["removed"]:
            changes.append(
                {
                    "field": "features",
                    **feature_diff,
                }
            )

        return changes

    def _diff_features(
        self,
        previous: List[Dict[str, Any]],
        current: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        prev_set = {
            self._feature_key(item)
            for item in previous
            if item.get("value")
        }
        curr_set = {
            self._feature_key(item)
            for item in current
            if item.get("value")
        }
        added = curr_set - prev_set
        removed = prev_set - curr_set

        return {
            "added": [value for _, value in sorted(added)],
            "removed": [value for _, value in sorted(removed)],
        }

    def _plan_key(self, plan: Dict[str, Any]) -> str:
        return (plan.get("plan") or "").strip().lower()

    def _feature_key(self, feature: Dict[str, Any]) -> Tuple[str, str]:
        return (
            (feature.get("feature_group") or "general").strip().lower(),
            feature.get("value", "").strip(),
        )

    def _numeric_changed(
        self,
        previous: Optional[float],
        current: Optional[float],
        tolerance: float = 0.01,
    ) -> bool:
        if previous is None and current is None:
            return False
        if previous is None or current is None:
            return True
        return abs(current - previous) > tolerance

    def _has_changes(self, diff: Dict[str, Any]) -> bool:
        return any(
            diff.get(key)
            for key in ("added_plans", "removed_plans", "updated_plans")
        )

    def _build_summary(self, diff: Dict[str, Any]) -> str:
        parts: List[str] = []

        added = diff.get("added_plans") or []
        if added:
            parts.append(
                "Added plans: " + ", ".join(plan.get("plan", "Unnamed") for plan in added)
            )

        removed = diff.get("removed_plans") or []
        if removed:
            parts.append(
                "Removed plans: "
                + ", ".join(plan.get("plan", "Unnamed") for plan in removed)
            )

        for updated in diff.get("updated_plans") or []:
            plan_name = updated.get("plan") or "Unnamed plan"
            change_parts: List[str] = []
            for change in updated.get("changes", []):
                field = change.get("field")
                if field == "price":
                    change_parts.append(
                        f"price {self._format_price(change.get('previous'), change.get('previous_currency'))}"
                        f" → {self._format_price(change.get('current'), change.get('current_currency'))}"
                    )
                elif field == "billing_cycle":
                    change_parts.append(
                        f"billing {change.get('previous') or '—'} → {change.get('current') or '—'}"
                    )
                elif field == "features":
                    added_count = len(change.get("added") or [])
                    removed_count = len(change.get("removed") or [])
                    detail_parts = []
                    if added_count:
                        detail_parts.append(f"+{added_count} feature(s)")
                    if removed_count:
                        detail_parts.append(f"-{removed_count} feature(s)")
                    if detail_parts:
                        change_parts.append(", ".join(detail_parts))
            if change_parts:
                parts.append(f"{plan_name}: " + "; ".join(change_parts))

        return "; ".join(parts) if parts else "No significant changes detected"

    def _flatten_changes(self, diff: Dict[str, Any]) -> List[Dict[str, Any]]:
        changes: List[Dict[str, Any]] = []

        for plan in diff.get("added_plans", []):
            changes.append(
                {
                    "plan": plan.get("plan"),
                    "field": "plan",
                    "change": "added",
                    "current": plan,
                }
            )

        for plan in diff.get("removed_plans", []):
            changes.append(
                {
                    "plan": plan.get("plan"),
                    "field": "plan",
                    "change": "removed",
                    "previous": plan,
                }
            )

        for updated in diff.get("updated_plans", []):
            plan_name = updated.get("plan")
            for change in updated.get("changes", []):
                record = {
                    "plan": plan_name,
                    "field": change.get("field"),
                }
                record.update({k: v for k, v in change.items() if k not in {"field"}})
                changes.append(record)

        return changes

    def _format_price(
        self,
        amount: Optional[float],
        currency: Optional[str],
    ) -> str:
        if amount is None:
            return currency or "n/a"
        if currency:
            return f"{currency} {amount:,.2f}"
        return f"{amount:,.2f}"


