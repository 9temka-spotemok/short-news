import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'
import process from 'process'

type AuthResponse = {
  access_token: string
  token_type?: string
}

type CompanySearchResponse = {
  items: Array<{
    id: string
    name: string
  }>
}

const PRIMARY_COMPANY_NAME = process.env.E2E_PRIMARY_COMPANY_NAME ?? 'E2E Analytics Primary'
const PRIMARY_COMPANY_SLUG = process.env.E2E_PRIMARY_COMPANY_SLUG ?? 'e2e-analytics-primary'
const COMPETITOR_COMPANY_NAME = process.env.E2E_COMPETITOR_COMPANY_NAME ?? 'E2E Analytics Competitor'
const COMPETITOR_COMPANY_SLUG = process.env.E2E_COMPETITOR_COMPANY_SLUG ?? 'e2e-analytics-competitor'
const SECONDARY_COMPETITOR_NAME = process.env.E2E_SECONDARY_COMPETITOR_NAME ?? 'E2E Analytics Secondary'
const SECONDARY_COMPETITOR_SLUG = process.env.E2E_SECONDARY_COMPETITOR_SLUG ?? 'e2e-analytics-secondary'

test.describe.configure({ mode: 'serial' })

test.describe('@refactor-phase2', () => {
  test('@refactor-phase2 analytics lifecycle: recompute → display → export', async ({ page, request }, testInfo) => {
    const email = process.env.E2E_USER_EMAIL
    const password = process.env.E2E_USER_PASSWORD
    test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

    const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
    const authHeader = await authenticate(request, apiBaseUrl, email!, password!)

    const primaryCompany = await ensureCompanyExists(request, apiBaseUrl, authHeader, {
      name: PRIMARY_COMPANY_NAME,
      slug: PRIMARY_COMPANY_SLUG,
    })
    await ensureCompanyExists(request, apiBaseUrl, authHeader, {
      name: COMPETITOR_COMPANY_NAME,
      slug: COMPETITOR_COMPANY_SLUG,
    })

    await runAnalysisFlow(page, {
      baseUrl: resolveBaseUrl(testInfo),
      primaryCompanyName: primaryCompany.name,
      competitorName: COMPETITOR_COMPANY_NAME,
    })

    const recomputeRequest = waitForApi(page, '/api/v2/analytics/companies/', '/recompute')
    await page.getByRole('button', { name: 'Recompute' }).first().click()
    await recomputeRequest
    await expectToast(page, 'Analytics recompute queued')

    await page.getByRole('button', { name: 'Export' }).first().click()
    const exportRequest = waitForApi(page, '/api/v2/analytics/export')
    await page.getByRole('button', { name: 'Export as JSON' }).click()
    await exportRequest
    await expectToast(page, 'Exported analysis as JSON')
  })

  test('@refactor-phase2 apply A/B preset and capture impact chart snapshot', async ({ page, request }, testInfo) => {
    const email = process.env.E2E_USER_EMAIL
    const password = process.env.E2E_USER_PASSWORD
    test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

    const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
    const authHeader = await authenticate(request, apiBaseUrl, email!, password!)

    await ensureCompanyExists(request, apiBaseUrl, authHeader, {
      name: PRIMARY_COMPANY_NAME,
      slug: PRIMARY_COMPANY_SLUG,
    })
    await ensureCompanyExists(request, apiBaseUrl, authHeader, {
      name: COMPETITOR_COMPANY_NAME,
      slug: COMPETITOR_COMPANY_SLUG,
    })

    await runAnalysisFlow(page, {
      baseUrl: resolveBaseUrl(testInfo),
      primaryCompanyName: PRIMARY_COMPANY_NAME,
      competitorName: COMPETITOR_COMPANY_NAME,
    })

    const presetName = `Visual preset ${new Date().toISOString()}`
    await page.getByPlaceholder('Preset name').fill(presetName)
    await page.getByRole('button', { name: 'Save preset' }).click()
    await expectToast(page, 'Report preset saved')

    const presetCard = page.locator('div').filter({ hasText: presetName }).first()
    await expect(presetCard).toBeVisible()
    await presetCard.getByRole('button', { name: 'Apply preset' }).click()
    await expectToast(page, 'Preset applied')

    const abComparisonHeading = page.getByRole('heading', { name: 'Signals A/B comparison' })
    await expect(abComparisonHeading).toBeVisible()

    const abSection = abComparisonHeading.locator('xpath=ancestor::div[contains(@class,"rounded-lg")]').first()
    const abSelectors = abSection.locator('select')
    await abSelectors.nth(0).selectOption({ label: PRIMARY_COMPANY_NAME })
    await abSelectors.nth(1).selectOption({ label: COMPETITOR_COMPANY_NAME })

    const chart = page.locator('svg[aria-label="Impact score comparison chart"]').first()
    await chart.scrollIntoViewIfNeeded()
    await expect(chart).toBeVisible()
    await expect(chart).toHaveScreenshot('impact-score-comparison.png', {
      maxDiffPixelRatio: 0.02,
    })
  })

})

test('@refactor-phase2 export handles backend error', async ({ page, request }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
  const authHeader = await authenticate(request, apiBaseUrl, email!, password!)
  const baseUrl = resolveBaseUrl(testInfo)

  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: PRIMARY_COMPANY_NAME,
    slug: PRIMARY_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: COMPETITOR_COMPANY_NAME,
    slug: COMPETITOR_COMPANY_SLUG,
  })

  await runAnalysisFlow(page, {
    baseUrl,
    primaryCompanyName: PRIMARY_COMPANY_NAME,
    competitorName: COMPETITOR_COMPANY_NAME,
  })

  await page.route('**/api/v2/analytics/export', async route => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Internal error' }),
    })
  })

  await page.getByRole('button', { name: 'Export' }).first().click()
  await page.getByRole('button', { name: 'Export as JSON' }).click()

  await expectToast(page, 'Export failed. Please try again.')
})

test('@refactor-phase2 shows empty state when analytics snapshot missing', async ({ page, request }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
  const authHeader = await authenticate(request, apiBaseUrl, email!, password!)
  const baseUrl = resolveBaseUrl(testInfo)

  const primaryCompany = await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: PRIMARY_COMPANY_NAME,
    slug: PRIMARY_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: COMPETITOR_COMPANY_NAME,
    slug: COMPETITOR_COMPANY_SLUG,
  })

  await page.route(`**/api/v2/analytics/companies/${primaryCompany.id}/impact/latest**`, async route => {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Snapshot not found' }),
    })
  })

  await runAnalysisFlow(page, {
    baseUrl,
    primaryCompanyName: primaryCompany.name,
    competitorName: COMPETITOR_COMPANY_NAME,
  })

  await expect(page.getByText('Аналитика ещё не построена. Запустите пересчёт, чтобы получить метрики.')).toBeVisible()
})

test('@refactor-phase2 filters persist after reload', async ({ page, request }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
  const authHeader = await authenticate(request, apiBaseUrl, email!, password!)
  const baseUrl = resolveBaseUrl(testInfo)

  const primaryCompany = await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: PRIMARY_COMPANY_NAME,
    slug: PRIMARY_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: COMPETITOR_COMPANY_NAME,
    slug: COMPETITOR_COMPANY_SLUG,
  })

  await runAnalysisFlow(page, {
    baseUrl,
    primaryCompanyName: primaryCompany.name,
    competitorName: COMPETITOR_COMPANY_NAME,
  })

  await page.getByLabel('Blog').check()
  await page.getByRole('button', { name: 'Strategy' }).click()
  await page.getByLabel('Positive').check()

  await expect(page.getByText('Source: Blog')).toBeVisible()
  await expect(page.getByText('Topic: Strategy')).toBeVisible()
  await expect(page.getByText('Sentiment: Positive')).toBeVisible()

  await page.reload()

  await expect(page.getByText('Source: Blog')).toBeVisible()
  await expect(page.getByText('Topic: Strategy')).toBeVisible()
  await expect(page.getByText('Sentiment: Positive')).toBeVisible()
})

test('@refactor-phase2 manual competitor addition refreshes analytics', async ({ page, request }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
  const authHeader = await authenticate(request, apiBaseUrl, email!, password!)
  const baseUrl = resolveBaseUrl(testInfo)

  const primaryCompany = await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: PRIMARY_COMPANY_NAME,
    slug: PRIMARY_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: COMPETITOR_COMPANY_NAME,
    slug: COMPETITOR_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: SECONDARY_COMPETITOR_NAME,
    slug: SECONDARY_COMPETITOR_SLUG,
  })

  const comparisonRequests: string[] = []
  page.on('request', requestEvent => {
    if (requestEvent.method() === 'POST' && requestEvent.url().includes('/api/v2/analytics/comparisons')) {
      comparisonRequests.push(requestEvent.url())
    }
  })

  await runAnalysisFlow(page, {
    baseUrl,
    primaryCompanyName: primaryCompany.name,
    competitorName: COMPETITOR_COMPANY_NAME,
  })

  expect(comparisonRequests.length).toBeGreaterThan(0)

  await page.getByRole('button', { name: 'Back' }).first().click()
  await expect(page.getByRole('heading', { name: 'Choose Competitors' })).toBeVisible()

  await page.getByRole('button', { name: '+ Add manually' }).click()
  const modalSearch = page.getByPlaceholder('Search companies...')
  await modalSearch.fill(SECONDARY_COMPETITOR_NAME.slice(0, 5))
  const secondaryCompetitorRow = page.locator('div').filter({ hasText: SECONDARY_COMPETITOR_NAME }).last()
  await secondaryCompetitorRow.waitFor({ state: 'visible' })
  await secondaryCompetitorRow.getByRole('button', { name: 'Add' }).click()

  const nextComparison = waitForApi(page, '/api/v2/analytics/comparisons')
  await page.getByRole('button', { name: 'Analyze' }).click()
  await nextComparison

  await expect(page.getByRole('heading', { name: 'Analysis Results' })).toBeVisible()
  expect(comparisonRequests.length).toBeGreaterThan(1)
})

test('@refactor-phase2 export success flow', async ({ page, request }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const apiBaseUrl = resolveApiBaseUrl(testInfo.config.metadata)
  const authHeader = await authenticate(request, apiBaseUrl, email!, password!)
  const baseUrl = resolveBaseUrl(testInfo)

  const primaryCompany = await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: PRIMARY_COMPANY_NAME,
    slug: PRIMARY_COMPANY_SLUG,
  })
  await ensureCompanyExists(request, apiBaseUrl, authHeader, {
    name: COMPETITOR_COMPANY_NAME,
    slug: COMPETITOR_COMPANY_SLUG,
  })

  await runAnalysisFlow(page, {
    baseUrl,
    primaryCompanyName: primaryCompany.name,
    competitorName: COMPETITOR_COMPANY_NAME,
  })

  await page.route('**/api/v2/analytics/export', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Export scheduled',
        download_url: `https://example.com/downloads/${Date.now()}.json`,
      }),
    })
  })

  await page.getByRole('button', { name: 'Export' }).first().click()
  await page.getByRole('button', { name: 'Export as JSON' }).click()

  await expectToast(page, 'Exported analysis as JSON')
})

test('@refactor-phase2 notifications toggle surfaces toast feedback', async ({ page }, testInfo) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  test.skip(!email || !password, 'E2E_USER_EMAIL and E2E_USER_PASSWORD must be configured')

  const baseUrl = resolveBaseUrl(testInfo)

  await page.route('**/users/preferences', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          subscribed_companies: [],
          interested_categories: [],
          keywords: [],
          notification_frequency: 'daily',
          digest_enabled: false,
          digest_frequency: 'daily',
          digest_custom_schedule: {},
          digest_format: 'short',
          digest_include_summaries: false,
          telegram_chat_id: null,
          telegram_enabled: false,
          timezone: 'UTC',
          week_start_day: 1
        })
      })
      return
    }

    if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          preferences: {
            subscribed_companies: [],
            interested_categories: [],
            keywords: [],
            notification_frequency: 'daily'
          }
        })
      })
      return
    }

    await route.continue()
  })

  await page.route('**/users/preferences/digest', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' })
    })
  })

  await page.route('**/companies/', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          limit: 200,
          offset: 0
        })
      })
      return
    }

    await route.continue()
  })

  await page.route('**/news/categories/list', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        categories: [
          { value: 'ai', description: 'AI', total_news: 0 },
          { value: 'strategy', description: 'Strategy', total_news: 0 }
        ],
        source_types: []
      })
    })
  })

  await signIn(page, baseUrl, email!, password!)

  await page.goto(`${baseUrl}/settings`)

  await page.getByRole('button', { name: 'Notifications' }).click()

  const digestToggleLabel = page.locator('label').filter({
    has: page.locator('input[type="checkbox"][class*="peer"]')
  }).first()
  const digestCheckbox = digestToggleLabel.locator('input[type="checkbox"]')

  await digestToggleLabel.click()
  await expect(digestCheckbox).toBeChecked()
  await expect(page.getByText('Frequency')).toBeVisible()

  await page.locator('label', { hasText: 'Weekly' }).first().click()
  await page.locator('label', { hasText: 'Detailed' }).first().click()

  const preferencesRequestPromise = page.waitForRequest(request =>
    request.method() === 'PUT' && request.url().includes('/users/preferences')
  )
  const digestRequestPromise = page.waitForRequest(request =>
    request.method() === 'PUT' && request.url().includes('/users/preferences/digest')
  )

  await page.getByRole('button', { name: 'Save Changes' }).click()

  const preferencesRequest = await preferencesRequestPromise
  const digestRequest = await digestRequestPromise

  const digestPayload = digestRequest.postDataJSON() as Record<string, unknown>
  expect(digestPayload).toMatchObject({
    digest_enabled: true,
    digest_frequency: 'weekly',
    digest_format: 'detailed'
  })

  const preferencesPayload = preferencesRequest.postDataJSON() as Record<string, unknown>
  expect(preferencesPayload).toMatchObject({
    notification_frequency: 'daily'
  })

  await expectToast(page, 'Notification settings saved successfully')
})

function resolveBaseUrl(testInfo: TestInfo) {
  const config = testInfo.config as { use?: { baseURL?: string } }
  return config.use?.baseURL ?? 'http://127.0.0.1:4173'
}

async function authenticate(request: APIRequestContext, apiBaseUrl: string, email: string, password: string) {
  const response = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email, password },
  })
  expect(response.ok()).toBeTruthy()
  const auth = (await response.json()) as AuthResponse
  expect(auth.access_token).toBeTruthy()
  return `${(auth.token_type ?? 'Bearer').trim()} ${auth.access_token}`
}

async function ensureCompanyExists(
  request: APIRequestContext,
  apiBaseUrl: string,
  authHeader: string,
  details: { name: string; slug: string },
) {
  const existing = await searchCompanyByName(request, apiBaseUrl, authHeader, details.name)
  if (existing) {
    return existing
  }

  const now = new Date().toISOString()
  const payload = {
    company: {
      name: details.name,
      website: `https://${details.slug}.example.com`,
      description: 'E2E synthetic company used for analytics regression tests.',
      category: 'ai_platform',
      logo_url: `https://dummyimage.com/120x120/0f172a/ffffff&text=${encodeURIComponent(details.name.slice(0, 2))}`,
    },
    news_items: [
      buildNewsItem(details.slug, 'product_update', now),
      buildNewsItem(details.slug, 'strategic_announcement', now),
      buildNewsItem(details.slug, 'technical_update', now),
    ],
  }

  const response = await request.post(`${apiBaseUrl}/api/v1/companies/`, {
    data: payload,
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
  })
  expect(response.ok()).toBeTruthy()
  const data = await response.json()
  return { id: data.company.id as string, name: data.company.name as string }
}

async function searchCompanyByName(
  request: APIRequestContext,
  apiBaseUrl: string,
  authHeader: string,
  name: string,
) {
  const response = await request.get(
    `${apiBaseUrl}/api/v1/companies/?search=${encodeURIComponent(name)}&limit=1`,
    {
      headers: {
        Authorization: authHeader,
      },
    },
  )
  if (!response.ok()) {
    return null
  }
  const data = (await response.json()) as CompanySearchResponse
  const company = data.items?.[0]
  return company ? { id: company.id, name: company.name } : null
}

function buildNewsItem(slug: string, category: string, publishedAtIso: string) {
  const uid = generateUid()
  return {
    title: `E2E update ${uid}`,
    content: `Automated regression content for ${slug} (${uid}).`,
    summary: 'Synthetic news to drive analytics metrics.',
    source_url: `https://${slug}.example.com/news/${uid}`,
    source_type: 'blog',
    category,
    topic: 'technology',
    sentiment: 'neutral',
    priority_score: 0.6,
    published_at: publishedAtIso,
  }
}

async function signIn(page: Page, baseUrl: string, email: string, password: string) {
  await page.goto(`${baseUrl}/login`)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/dashboard/)
}

async function runAnalysisFlow(
  page: Page,
  options: { baseUrl: string; primaryCompanyName: string; competitorName: string },
) {
  await page.goto(`${options.baseUrl}/login`)
  await page.getByLabel('Email').fill(process.env.E2E_USER_EMAIL ?? '')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/dashboard/)

  await page.getByRole('link', { name: 'Competitors analysis' }).first().click()
  await expect(page).toHaveURL(/competitor-analysis/)

  await page.getByRole('heading', { name: 'Custom Analysis' }).click()
  await expect(page.getByRole('heading', { name: 'Select Your Company' })).toBeVisible()

  const searchInput = page.getByPlaceholder('Search for a company...')
  await searchInput.fill(options.primaryCompanyName.slice(0, 5))
  const companyButton = page.locator('button', { hasText: options.primaryCompanyName }).first()
  await companyButton.waitFor({ state: 'visible' })
  await companyButton.click()

  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByRole('heading', { name: 'Choose Competitors' })).toBeVisible()

  await page.getByRole('button', { name: '+ Add manually' }).click()
  const modalSearch = page.getByPlaceholder('Search companies...')
  await modalSearch.fill(options.competitorName.slice(0, 5))
  const competitorRow = page.locator('div').filter({ hasText: options.competitorName }).last()
  await competitorRow.waitFor({ state: 'visible' })
  await competitorRow.getByRole('button', { name: 'Add' }).click()

  const analyzeButton = page.getByRole('button', { name: 'Analyze' })
  await expect(analyzeButton).toBeEnabled()
  await analyzeButton.click()

  await expect(page.getByRole('heading', { name: 'Analysis Results' })).toBeVisible({ timeout: 120000 })
  await expect(page.getByRole('button', { name: 'Recompute' }).first()).toBeVisible()
}

async function expectToast(page: Page, message: string) {
  await expect(page.locator('div[role="status"], div[role="alert"]').filter({ hasText: message })).toBeVisible({
    timeout: 15000,
  })
}

function waitForApi(page: Page, prefix: string, suffix?: string) {
  return page.waitForResponse((response) => {
    const url = response.url()
    if (!url.includes(prefix)) {
      return false
    }
    if (suffix && !url.includes(suffix)) {
      return false
    }
    return response.request().method() === 'POST' && response.ok()
  })
}

function resolveApiBaseUrl(metadata: Record<string, unknown> | undefined) {
  if (metadata && typeof metadata.apiBaseUrl === 'string') {
    return metadata.apiBaseUrl
  }
  return process.env.E2E_API_URL ?? 'http://127.0.0.1:8000'
}

function generateUid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

