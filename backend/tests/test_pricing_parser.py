from app.parsers.pricing import PricingPageParser
from app.services.competitor_change_service import CompetitorChangeService


def test_pricing_parser_extracts_basic_plan() -> None:
    html = """
    <div class="pricing-card">
        <h3>Starter</h3>
        <div class="price">$29 per month</div>
        <ul class="features">
            <li>100 tracked prompts</li>
            <li>Email alerts</li>
        </ul>
    </div>
    """
    parser = PricingPageParser()
    result = parser.parse(html)
    assert len(result.plans) == 1
    plan = result.plans[0]
    assert plan.plan == "Starter"
    assert plan.price == 29.0
    assert plan.currency == "USD"
    assert plan.billing_cycle == "monthly"
    assert any(feature.value == "100 tracked prompts" for feature in plan.features)


def test_pricing_parser_understands_free_plan() -> None:
    html = """
    <section class="plan-tier">
        <h3>Community</h3>
        <p class="pricing">Free forever</p>
        <ul>
            <li>Access to shared prompts</li>
        </ul>
    </section>
    """
    parser = PricingPageParser()
    result = parser.parse(html)
    assert result.plans[0].price == 0.0
    assert result.plans[0].price_label == "free"


def test_pricing_parser_handles_pricing_table() -> None:
    html = """
    <table class="pricing-table">
        <thead>
            <tr>
                <th>Features</th>
                <th>Basic</th>
                <th>Pro</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Price</td>
                <td>$19/mo</td>
                <td>$49/mo</td>
            </tr>
            <tr>
                <td>Projects</td>
                <td>3</td>
                <td>10</td>
            </tr>
        </tbody>
    </table>
    """
    parser = PricingPageParser()
    result = parser.parse(html)
    assert len(result.plans) == 2
    pro_plan = next(plan for plan in result.plans if plan.plan == "Pro")
    assert pro_plan.price == 49.0
    assert pro_plan.currency == "USD"
    assert pro_plan.features


def test_change_service_detects_price_update() -> None:
    service = CompetitorChangeService(db=None)  # type: ignore[arg-type]
    previous = [
        {
            "plan": "Starter",
            "price": 29.0,
            "currency": "USD",
            "billing_cycle": "monthly",
            "features": [],
        }
    ]
    current = [
        {
            "plan": "Starter",
            "price": 39.0,
            "currency": "USD",
            "billing_cycle": "monthly",
            "features": [],
        }
    ]
    diff = service._compute_diff(previous, current)
    assert diff["updated_plans"]
    summary = service._build_summary(diff)
    assert "Starter" in summary
    assert "39.00" in summary

