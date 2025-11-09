import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { randomUUID } from 'crypto'

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

test.describe.configure({ mode: 'serial' })

test('analytics lifecycle: recompute → display → export', async ({ page, request }, testInfo) => {
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
    baseUrl: testInfo.config.use.baseURL ?? 'http://127.0.0.1:4173',
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

test('apply A/B preset and capture impact chart snapshot', async ({ page, request }, testInfo) => {
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
    baseUrl: testInfo.config.use.baseURL ?? 'http://127.0.0.1:4173',
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
  const uid = randomUUID()
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

