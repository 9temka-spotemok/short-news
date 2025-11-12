import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const vus = Number(__ENV.VUS || 50);
const duration = __ENV.DURATION || "1m";
const baseUrl = __ENV.BASE_URL || "http://localhost:8000";
const authToken = __ENV.AUTH_TOKEN;
const newsLimit = Number(__ENV.NEWS_LIMIT || 25);

export const errorRate = new Rate("news_errors");

export const options = {
  vus,
  duration,
  thresholds: {
    news_errors: ["rate<0.05"],
    http_req_duration: [
      "p(50)<250",
      "p(95)<750",
      "p(99)<1200",
    ],
  },
};

export default function () {
  const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
  const response = http.get(
    `${baseUrl}/api/v1/news?limit=${newsLimit}`,
    { headers }
  );

  const ok = check(response, {
    "status is 200": (r) => r.status === 200,
    "returns items": (r) => r.json("items")?.length >= 0,
  });

  if (!ok) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
  }

  sleep(0.2);
}


