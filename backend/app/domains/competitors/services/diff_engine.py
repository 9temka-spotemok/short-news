"""
Utility functions for computing pricing diffs and summaries.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


def compute_hash(payload: List[Dict[str, Any]]) -> str:
    """Stable hash for normalised pricing data."""
    serialised = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    import hashlib

    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def compute_diff(
    previous: Optional[Iterable[Dict[str, Any]]],
    current: Optional[Iterable[Dict[str, Any]]],
) -> Dict[str, Any]:
    prev_items = list(previous or [])
    curr_items = list(current or [])

    prev_map = {plan_key(plan): plan for plan in prev_items}
    curr_map = {plan_key(plan): plan for plan in curr_items}

    diff: Dict[str, Any] = {
        "added_plans": [],
        "removed_plans": [],
        "updated_plans": [],
    }

    for key, plan in curr_map.items():
        if key not in prev_map:
            diff["added_plans"].append(plan)
        else:
            prev_plan = prev_map[key]
            changes = compare_plan(prev_plan, plan)
            if changes:
                diff["updated_plans"].append(
                    {"plan": plan.get("plan"), "changes": changes}
                )

    for key, plan in prev_map.items():
        if key not in curr_map:
            diff["removed_plans"].append(plan)

    return diff


def compare_plan(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []

    prev_price = previous.get("price")
    curr_price = current.get("price")
    prev_currency = previous.get("currency")
    curr_currency = current.get("currency")

    if numeric_changed(prev_price, curr_price) or prev_currency != curr_currency:
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

    feature_diff = diff_features(
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


def diff_features(
    previous: List[Dict[str, Any]],
    current: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    prev_set = {feature_key(item) for item in previous if item.get("value")}
    curr_set = {feature_key(item) for item in current if item.get("value")}
    added = curr_set - prev_set
    removed = prev_set - curr_set

    return {
        "added": [value for _, value in sorted(added)],
        "removed": [value for _, value in sorted(removed)],
    }


def plan_key(plan: Dict[str, Any]) -> str:
    return (plan.get("plan") or "").strip().lower()


def feature_key(feature: Dict[str, Any]) -> Tuple[str, str]:
    return (
        (feature.get("feature_group") or "general").strip().lower(),
        feature.get("value", "").strip(),
    )


def numeric_changed(
    previous: Optional[float],
    current: Optional[float],
    *,
    tolerance: float = 0.01,
) -> bool:
    if previous is None and current is None:
        return False
    if previous is None or current is None:
        return True
    return abs(current - previous) > tolerance


def has_changes(diff: Dict[str, Any]) -> bool:
    return any(diff.get(key) for key in ("added_plans", "removed_plans", "updated_plans"))


def build_summary(diff: Dict[str, Any]) -> str:
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
                    f"price {format_price(change.get('previous'), change.get('previous_currency'))}"
                    f" → {format_price(change.get('current'), change.get('current_currency'))}"
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


def flatten_changes(diff: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            record.update({k: v for k, v in change.items() if k != "field"})
            changes.append(record)

    return changes


def format_price(
    amount: Optional[float],
    currency: Optional[str],
) -> str:
    if amount is None:
        return currency or "n/a"
    if currency:
        return f"{currency} {amount:,.2f}"
    return f"{amount:,.2f}"





