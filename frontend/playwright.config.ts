import { defineConfig, devices, type PlaywrightTestConfig } from '@playwright/test'
import dotenv from 'dotenv'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const envFiles = ['.env', '.env.local', '.env.e2e']
for (const envFile of envFiles) {
  const envPath = path.resolve(__dirname, envFile)
  if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath, override: false })
  }
}

type WebServerDefinition = Extract<NonNullable<PlaywrightTestConfig['webServer']>, { command: string }>

const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4173'
const apiBaseUrl = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000'

const webServers: WebServerDefinition[] = []

const shouldStartFrontendServer =
  !process.env.E2E_SKIP_FRONTEND_SERVER && !process.env.E2E_BASE_URL

if (shouldStartFrontendServer) {
  webServers.push({
    command: 'npm run preview -- --host 0.0.0.0 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  })
}

const backendCommand = process.env.E2E_BACKEND_COMMAND
const backendUrl = process.env.E2E_BACKEND_URL ?? apiBaseUrl

if (backendCommand) {
  webServers.push({
    command: backendCommand,
    url: backendUrl,
    reuseExistingServer: true,
    timeout: 180 * 1000,
    env: process.env.E2E_BACKEND_ENV
      ? JSON.parse(process.env.E2E_BACKEND_ENV)
      : undefined,
  })
}

const resolvedWebServer: PlaywrightTestConfig['webServer'] =
  webServers.length === 0 ? undefined : webServers.length === 1 ? webServers[0] : [...webServers]

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 120 * 1000,
  expect: {
    timeout: 30 * 1000,
  },
  reporter: process.env.CI
    ? [
        ['list'],
        ['html', { outputFolder: 'playwright-report', open: 'never' }],
        ['junit', { outputFile: 'playwright-report/e2e-junit.xml' }],
      ]
    : [['html', { open: 'on-failure' }]],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: resolvedWebServer,
  metadata: {
    apiBaseUrl,
  },
})

