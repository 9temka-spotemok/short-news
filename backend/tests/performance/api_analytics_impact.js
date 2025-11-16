import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const vus = Number(__ENV.VUS || 40);
const duration = __ENV.DURATION || "1m";
const baseUrl = __ENV.BASE_URL || "http://localhost:8000";
const authToken = __ENV.AUTH_TOKEN;
const companyId = __ENV.COMPANY_ID;
const period = __ENV.PERIOD || "daily";

if (!companyId) {
  throw new Error("COMPANY_ID environment variable is required for analytics impact load test.");
}

export const errorRate = new Rate("analytics_impact_errors");

export const options = {
  vus,
  duration,
  thresholds: {
    analytics_impact_errors: ["rate<0.05"],
    http_req_duration: [
      "p(50)<300",
      "p(95)<900",
      "p(99)<1500",
    ],
  },
};

export default function () {
  const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
  const response = http.get(
    `${baseUrl}/api/v2/analytics/companies/${companyId}/impact/latest?period=${period}`,
    { headers }
  );

  const ok = check(response, {
    "status is 200": (r) => r.status === 200,
    "has impact score": (r) => r.json("impact_score") !== undefined,
  });

  errorRate.add(ok ? 0 : 1);

  sleep(0.25);
}


