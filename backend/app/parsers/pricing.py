"""
Pricing page parser for competitor plans and feature matrices.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag


CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₽": "RUB",
    "₩": "KRW",
    "₺": "TRY",
    "₹": "INR",
    "₫": "VND",
    "₴": "UAH",
    "C$": "CAD",
    "CA$": "CAD",
    "A$": "AUD",
    "AU$": "AUD",
    "NZ$": "NZD",
    "HK$": "HKD",
    "S$": "SGD",
    "₦": "NGN",
    "R$": "BRL",
    "CHF": "CHF",
}

CURRENCY_CODES = {
    "USD",
    "EUR",
    "GBP",
    "AUD",
    "CAD",
    "NZD",
    "SGD",
    "HKD",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "RUB",
    "TRY",
    "INR",
    "JPY",
    "CNY",
    "TWD",
    "KRW",
    "BRL",
    "ZAR",
    "VND",
    "NGN",
    "ILS",
    "MXN",
    "CHF",
}

FREE_KEYWORDS = {"free", "complimentary", "no cost"}
CUSTOM_KEYWORDS = {"contact", "custom", "quote", "request", "talk to sales"}

BILLING_MAP = {
    "month": "monthly",
    "mo": "monthly",
    "monthly": "monthly",
    "year": "annual",
    "yr": "annual",
    "annual": "annual",
    "annually": "annual",
    "quarter": "quarterly",
    "weekly": "weekly",
    "week": "weekly",
    "day": "daily",
    "daily": "daily",
    "lifetime": "lifetime",
    "one-time": "one_time",
    "onetime": "one_time",
    "once": "one_time",
    "per user": "per_user",
    "per seat": "per_user",
    "per member": "per_user",
    "per teammate": "per_user",
    "per credit": "usage_based",
    "per run": "usage_based",
    "per request": "usage_based",
    "per prompt": "usage_based",
    "credit": "usage_based",
    "usage": "usage_based",
}

PRICE_REGEX = re.compile(
    r"(?P<currency>(?:USD|EUR|GBP|AUD|CAD|NZD|SGD|HKD|SEK|NOK|DKK|PLN|RUB|TRY|INR|JPY|CNY|TWD|KRW|BRL|ZAR|MXN|CHF)|[₹$€£¥₽₩₺₫₴]|(?:[A-Z]{1,2}\$))"
    r"[\s]*"
    r"(?P<amount>\d[\d\s.,]*)"
    r"(?:\s*(?:/|per)?\s*(?P<cycle>month|mo|monthly|year|yr|annual|annually|quarter|week|weekly|day|daily|user|seat|member|credit|prompt|request))?",
    re.IGNORECASE,
)


@dataclass
class PricingPlanFeature:
    feature_group: Optional[str]
    value: str


@dataclass
class PricingPlan:
    plan: str
    price: Optional[float]
    currency: Optional[str]
    billing_cycle: Optional[str]
    raw_price: Optional[str]
    price_label: Optional[str] = None
    features: List[PricingPlanFeature] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": self.plan,
            "price": self.price,
            "currency": self.currency,
            "billing_cycle": self.billing_cycle,
            "raw_price": self.raw_price,
            "price_label": self.price_label,
            "features": [
                {
                    "feature_group": feature.feature_group,
                    "value": feature.value,
                }
                for feature in self.features
            ],
        }


@dataclass
class PricingParseResult:
    plans: List[PricingPlan]
    warnings: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    parser_version: str = "2025.11.0"

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "plans": [plan.to_dict() for plan in self.plans],
            "warnings": self.warnings,
            "extraction_metadata": self.extraction_metadata,
            "parser_version": self.parser_version,
        }


class PricingPageParser:
    """Parser converting pricing HTML fragments into normalized structures."""

    VERSION = "2025.11.0"

    def parse(self, html: str, url: Optional[str] = None) -> PricingParseResult:
        soup = BeautifulSoup(html, "html.parser")
        warnings: List[str] = []

        plan_nodes = self._collect_plan_nodes(soup)
        plans: List[PricingPlan] = []

        unnamed_counter = 0
        for node in plan_nodes:
            plan = self._parse_plan_card(node, warnings)
            if plan:
                if not plan.plan:
                    unnamed_counter += 1
                    plan.plan = f"Plan {unnamed_counter}"
                plans.append(plan)

        table_plans = self._parse_pricing_tables(soup, warnings)
        plans.extend(table_plans)

        plans = self._deduplicate_plans(plans)

        metadata = {
            "url": url,
            "plan_candidates": len(plan_nodes),
            "table_candidates": len(table_plans),
            "plan_count": len(plans),
            "currencies": sorted(
                {plan.currency for plan in plans if plan.currency}
            ),
        }

        if not plans:
            warnings.append("No pricing plans detected on page.")

        return PricingParseResult(
            plans=plans,
            warnings=warnings,
            extraction_metadata=metadata,
            parser_version=self.VERSION,
        )

    # ---------------------------
    # Plan card parsing helpers
    # ---------------------------

    def _collect_plan_nodes(self, soup: BeautifulSoup) -> List[Tag]:
        candidates: List[Tag] = []
        for tag in soup.find_all(["section", "div", "article", "li"]):
            classes = " ".join(tag.get("class", [])).lower()
            if not classes:
                continue
            if not any(
                keyword in classes
                for keyword in (
                    "plan",
                    "pricing",
                    "tier",
                    "package",
                    "bundle",
                    "card",
                )
            ):
                continue
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            if self._contains_price_indicator(text):
                candidates.append(tag)

        unique: List[Tag] = []
        for node in candidates:
            if any(parent in candidates for parent in node.parents):
                continue
            unique.append(node)
        return unique

    def _contains_price_indicator(self, text: str) -> bool:
        lower = text.lower()
        if any(keyword in lower for keyword in FREE_KEYWORDS | CUSTOM_KEYWORDS):
            return True
        return bool(PRICE_REGEX.search(text))

    def _parse_plan_card(
        self,
        node: Tag,
        warnings: List[str],
    ) -> Optional[PricingPlan]:
        plan_name = self._extract_plan_name(node)
        price_str, price_source = self._extract_price_string(node)
        price, currency, billing_cycle, label = self._parse_price(price_str)

        features = self._extract_features(node)

        if not plan_name:
            plan_name = ""

        if not price and not label and not features and not plan_name:
            return None

        if price is None and not label:
            warnings.append(
                f"Unable to parse numeric price for plan '{plan_name or price_source}'."
            )

        return PricingPlan(
            plan=plan_name,
            price=price,
            currency=currency,
            billing_cycle=billing_cycle,
            raw_price=price_source,
            price_label=label,
            features=features,
        )

    def _extract_plan_name(self, node: Tag) -> Optional[str]:
        for heading in node.find_all(["h1", "h2", "h3", "h4", "h5"]):
            text = heading.get_text(" ", strip=True)
            if text and len(text) <= 80:
                return text
        data_label = node.get("data-plan")
        if data_label:
            return str(data_label)
        label_node = node.find(attrs={"data-tier": True})
        if label_node:
            text = label_node.get("data-tier")
            if text:
                return str(text)
        return None

    def _extract_price_string(self, node: Tag) -> Tuple[str, str]:
        price_nodes = node.find_all(
            attrs={"class": re.compile("price|cost|amount", re.IGNORECASE)}
        )
        if price_nodes:
            texts = [
                price_node.get_text(" ", strip=True) for price_node in price_nodes
            ]
            joined = " ".join(filter(None, texts))
            if joined:
                return joined, joined
        # fall back to first paragraph or node text
        paragraphs = node.find_all("p", limit=2)
        for para in paragraphs:
            text = para.get_text(" ", strip=True)
            if self._contains_price_indicator(text):
                return text, text
        return node.get_text(" ", strip=True), node.get_text(" ", strip=True)

    def _parse_price(
        self, price_text: str
    ) -> Tuple[Optional[float], Optional[str], Optional[str], Optional[str]]:
        if not price_text:
            return None, None, None, None

        lower = price_text.lower()
        if any(keyword in lower for keyword in FREE_KEYWORDS):
            return 0.0, None, None, "free"
        if any(keyword in lower for keyword in CUSTOM_KEYWORDS):
            return None, None, None, "contact"

        match = PRICE_REGEX.search(price_text)
        if not match:
            return None, None, None, None

        raw_amount = match.group("amount")
        raw_currency = match.group("currency")
        cycle_fragment = match.group("cycle")

        amount = self._normalise_amount(raw_amount)
        currency = self._normalise_currency(raw_currency, price_text)
        billing_cycle = self._normalise_billing(cycle_fragment, price_text)

        return amount, currency, billing_cycle, None

    def _normalise_amount(self, raw: str) -> Optional[float]:
        if not raw:
            return None
        cleaned = raw.strip()
        cleaned = cleaned.replace(" ", "")
        if cleaned.count(",") > 1 and "." not in cleaned:
            cleaned = cleaned.replace(",", "")
        elif cleaned.count(".") > 1 and "," not in cleaned:
            cleaned = cleaned.replace(".", "")
        elif "," in cleaned and "." in cleaned:
            if cleaned.rfind(".") > cleaned.rfind(","):
                cleaned = cleaned.replace(",", "")
            else:
                cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _normalise_currency(self, raw: str, context: str) -> Optional[str]:
        if not raw:
            return None
        raw = raw.strip()
        if raw in CURRENCY_SYMBOLS:
            return CURRENCY_SYMBOLS[raw]
        if raw.upper() in CURRENCY_CODES:
            return raw.upper()

        uppercase = raw.upper()
        if uppercase.endswith("$"):
            prefix = uppercase[:-1] + "$"
            if prefix in CURRENCY_SYMBOLS:
                return CURRENCY_SYMBOLS[prefix]

        for code in CURRENCY_CODES:
            if code in context.upper():
                return code
        return None

    def _normalise_billing(
        self, fragment: Optional[str], context: str
    ) -> Optional[str]:
        candidates = []
        if fragment:
            candidates.append(fragment.lower())
        candidates.extend(re.findall(r"(per\s+[a-z]+)", context.lower()))
        candidates.extend(context.lower().split())

        for candidate in candidates:
            candidate = candidate.strip()
            if candidate in BILLING_MAP:
                return BILLING_MAP[candidate]
            normalised = candidate.replace("per ", "")
            if normalised in BILLING_MAP:
                return BILLING_MAP[normalised]
        return None

    def _extract_features(self, node: Tag) -> List[PricingPlanFeature]:
        features: List[PricingPlanFeature] = []
        for ul in node.find_all("ul"):
            if len(ul.find_all("li")) == 0:
                continue
            if not self._looks_like_feature_list(ul):
                continue
            group_label = self._derive_feature_group(ul)
            for li in ul.find_all("li"):
                value = li.get_text(" ", strip=True)
                if value:
                    features.append(
                        PricingPlanFeature(
                            feature_group=group_label or "general", value=value
                        )
                    )
        return features

    def _looks_like_feature_list(self, ul: Tag) -> bool:
        classes = " ".join(ul.get("class", [])).lower()
        if any(keyword in classes for keyword in ("feature", "benefit", "include")):
            return True
        if ul.find_parent(["ul", "ol"]):
            return False
        return len(ul.find_all("li")) >= 2

    def _derive_feature_group(self, ul: Tag) -> Optional[str]:
        previous = ul.find_previous_sibling()
        while previous is not None and isinstance(previous, Tag):
            text = previous.get_text(" ", strip=True)
            if text and len(text) <= 60:
                tag_name = previous.name.lower()
                if tag_name in {"h3", "h4", "h5", "h6", "strong"}:
                    return text
            previous = previous.find_previous_sibling()
        parent = ul.find_parent(["section", "div"])
        if parent:
            heading = parent.find(["h3", "h4", "h5", "strong"])
            if heading:
                text = heading.get_text(" ", strip=True)
                if text:
                    return text
        return None

    def _deduplicate_plans(self, plans: List[PricingPlan]) -> List[PricingPlan]:
        unique: Dict[str, PricingPlan] = {}
        for plan in plans:
            key = plan.plan.strip().lower() if plan.plan else ""
            if key in unique:
                existing = unique[key]
                if not existing.price and plan.price:
                    existing.price = plan.price
                    existing.currency = plan.currency
                    existing.billing_cycle = plan.billing_cycle
                    existing.raw_price = plan.raw_price
                    existing.price_label = plan.price_label
                if len(existing.features) < len(plan.features):
                    existing.features = plan.features
            else:
                unique[key or f"plan_{len(unique)+1}"] = plan
        return list(unique.values())

    # ---------------------------
    # Table parsing helpers
    # ---------------------------

    def _parse_pricing_tables(
        self, soup: BeautifulSoup, warnings: List[str]
    ) -> List[PricingPlan]:
        tables = soup.find_all("table")
        parsed_plans: List[PricingPlan] = []
        for table in tables:
            table_classes = " ".join(table.get("class", [])).lower()
            if not table_classes and "pricing" not in table.get_text(" ", strip=True).lower():
                continue
            plans = self._parse_table(table, warnings)
            parsed_plans.extend(plans)
        return parsed_plans

    def _parse_table(
        self, table: Tag, warnings: List[str]
    ) -> List[PricingPlan]:
        headers = [
            cell.get_text(" ", strip=True)
            for cell in table.find_all("th")
            if cell.get_text(strip=True)
        ]
        rows = table.find_all("tr")
        if not headers or len(headers) <= 1 or not rows:
            return []

        plan_names = headers[1:]
        plan_columns: Dict[int, PricingPlan] = {}
        for index, name in enumerate(plan_names, start=1):
            plan_columns[index] = PricingPlan(
                plan=name,
                price=None,
                currency=None,
                billing_cycle=None,
                raw_price=None,
            )

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) != len(headers):
                continue
            feature_label = cells[0].get_text(" ", strip=True)
            for idx, cell in enumerate(cells[1:], start=1):
                plan = plan_columns.get(idx)
                if not plan:
                    continue
                text = cell.get_text(" ", strip=True)
                if not text:
                    continue
                amount, currency, billing_cycle, label = self._parse_price(text)
                if amount and not plan.price:
                    plan.price = amount
                    plan.currency = currency
                    plan.billing_cycle = billing_cycle
                    plan.raw_price = text
                    plan.price_label = label
                else:
                    plan.features.append(
                        PricingPlanFeature(
                            feature_group="table",
                            value=f"{feature_label}: {text}",
                        )
                    )

        parsed = []
        for plan in plan_columns.values():
            if not plan.plan.strip():
                continue
            if not plan.price and not plan.features:
                warnings.append(
                    f"Pricing table plan '{plan.plan}' contains no parsable values."
                )
            parsed.append(plan)
        return parsed


