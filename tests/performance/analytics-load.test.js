import http from 'k6/http'
import { check, sleep } from 'k6'
import { Trend, Rate } from 'k6/metrics'

const API_BASE_URL = __ENV.API_BASE_URL ?? 'http://127.0.0.1:8000'
const API_TOKEN = __ENV.API_TOKEN
const COMPANY_IDS = (__ENV.COMPANY_IDS ?? '')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean)

if (!API_TOKEN) {
  throw new Error('API_TOKEN environment variable is required for the load scenario')
}

if (COMPANY_IDS.length === 0) {
  throw new Error('COMPANY_IDS environment variable must provide at least one company id')
}

export const options = {
  discardResponseBodies: false,
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1500'],
    export_latency: ['p(95)<1200'],
  },
  scenarios: {
    moderate_load: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 20,
      maxVUs: 80,
      stages: [
        { target: 10, duration: '1m' },
        { target: 20, duration: '2m' },
        { target: 40, duration: '2m' },
        { target: 10, duration: '1m' },
        { target: 0, duration: '30s' },
      ],
    },
  },
}

const exportLatency = new Trend('export_latency')
const recomputeFailures = new Rate('recompute_failures')
const exportFailures = new Rate('export_failures')

export default function analyticsLoadScenario() {
  const headers = {
    Authorization: `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/json',
  }

  const companyId = COMPANY_IDS[Math.floor(Math.random() * COMPANY_IDS.length)]

  const recomputeResponse = http.post(
    `${API_BASE_URL}/api/v2/analytics/companies/${companyId}/recompute?period=daily&lookback=60`,
    null,
    { headers },
  )

  const recomputeOk = check(recomputeResponse, {
    'recompute accepted (202)': (res) => res.status === 202,
  })
  if (!recomputeOk) {
    recomputeFailures.add(1)
  }

  const payload = JSON.stringify({
    subjects: COMPANY_IDS.slice(0, Math.min(3, COMPANY_IDS.length)).map((id) => ({
      subject_type: 'company',
      reference_id: id,
    })),
    period: 'daily',
    lookback: 30,
    include_series: true,
    include_change_log: false,
    include_components: false,
    include_knowledge_graph: false,
    top_news_limit: 3,
    export_format: 'json',
    include: {
      include_notifications: false,
      include_presets: false,
    },
  })

  const exportStart = Date.now()
  const exportResponse = http.post(`${API_BASE_URL}/api/v2/analytics/export`, payload, {
    headers,
  })
  const latency = Date.now() - exportStart
  exportLatency.add(latency)

  const exportOk = check(exportResponse, {
    'export payload collected (200)': (res) => res.status === 200,
    'export contains comparison block': (res) => res.json('comparison') !== undefined,
  })
  if (!exportOk) {
    exportFailures.add(1)
  }

  sleep(1)
}

