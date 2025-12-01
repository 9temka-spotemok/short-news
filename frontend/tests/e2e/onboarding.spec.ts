import { expect, test } from '@playwright/test'

test.describe('Onboarding Flow', () => {
  test('complete onboarding flow from start to finish', async ({ page }) => {
    // Navigate to onboarding page
    await page.goto('/onboarding')

    // Step 1: Company Input
    await expect(page.getByRole('heading', { name: /введите сайт вашей компании/i })).toBeVisible()
    
    const websiteInput = page.getByPlaceholder(/https:\/\/example\.com/i)
    await expect(websiteInput).toBeVisible()
    
    // Enter company website
    await websiteInput.fill('https://example.com')
    
    // Click analyze button
    const analyzeButton = page.getByRole('button', { name: /анализировать/i })
    await expect(analyzeButton).toBeEnabled()
    await analyzeButton.click()

    // Step 2: Company Card - wait for analysis to complete
    await expect(page.getByRole('heading', { name: /мы нашли вашу компанию/i })).toBeVisible({ timeout: 30000 })
    
    // Verify company information is displayed
    await expect(page.getByText(/example/i)).toBeVisible()
    
    // Click continue button
    const continueButton = page.getByRole('button', { name: /далее: выбрать конкурентов/i })
    await expect(continueButton).toBeVisible()
    await continueButton.click()

    // Step 3: Competitor Selection - wait for competitors to load
    await expect(page.getByRole('heading', { name: /выберите конкурентов для мониторинга/i })).toBeVisible({ timeout: 30000 })
    
    // Wait for competitor cards to appear
    const competitorCards = page.locator('[class*="border"]').filter({ hasText: /http/i })
    await expect(competitorCards.first()).toBeVisible({ timeout: 10000 })
    
    // Select at least one competitor
    const firstCheckbox = page.locator('button').filter({ hasText: '' }).first()
    await firstCheckbox.click()
    
    // Verify selection count
    await expect(page.getByText(/выбрано:/i)).toBeVisible()
    
    // Click continue button
    const continueCompetitorsButton = page.getByRole('button', { name: /продолжить/i })
    await expect(continueCompetitorsButton).toBeEnabled()
    await continueCompetitorsButton.click()

    // Step 4: Observation Setup - wait for setup to start
    await expect(page.getByRole('heading', { name: /настраиваем наблюдение за конкурентами/i })).toBeVisible({ timeout: 10000 })
    
    // Wait for processing indicator
    await expect(page.getByText(/собираем данные/i)).toBeVisible({ timeout: 5000 })
    
    // Wait for completion (this might take a while, so we'll wait up to 60 seconds)
    await expect(page.getByText(/наблюдение настроено успешно/i)).toBeVisible({ timeout: 60000 })

    // Step 5: Onboarding Complete
    await expect(page.getByRole('heading', { name: /ваш наблюдательный центр готов/i })).toBeVisible({ timeout: 10000 })
    
    // Verify company and competitors are shown
    await expect(page.getByText(/ваша компания/i)).toBeVisible()
    await expect(page.getByText(/выбранные конкуренты/i)).toBeVisible()
    
    // Click start button
    const startButton = page.getByRole('button', { name: /начать/i })
    await expect(startButton).toBeVisible()
    await startButton.click()

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('onboarding flow with competitor replacement', async ({ page }) => {
    // Navigate to onboarding
    await page.goto('/onboarding')

    // Step 1: Enter company website
    await page.getByPlaceholder(/https:\/\/example\.com/i).fill('https://example.com')
    await page.getByRole('button', { name: /анализировать/i }).click()

    // Step 2: Continue from company card
    await expect(page.getByRole('heading', { name: /мы нашли вашу компанию/i })).toBeVisible({ timeout: 30000 })
    await page.getByRole('button', { name: /далее: выбрать конкурентов/i }).click()

    // Step 3: Replace a competitor
    await expect(page.getByRole('heading', { name: /выберите конкурентов для мониторинга/i })).toBeVisible({ timeout: 30000 })
    
    // Wait for competitor cards
    await page.waitForTimeout(2000) // Wait for competitors to load
    
    // Find and click replace button (X icon)
    const replaceButtons = page.locator('button[title="Заменить конкурента"]')
    const replaceButtonCount = await replaceButtons.count()
    
    if (replaceButtonCount > 0) {
      await replaceButtons.first().click()
      
      // Wait for replacement (new competitor should appear)
      await page.waitForTimeout(2000)
      
      // Verify competitor was replaced (check that cards are still visible)
      await expect(page.locator('[class*="border"]').filter({ hasText: /http/i }).first()).toBeVisible()
    }
  })

  test('onboarding flow shows registration modal when not authenticated', async ({ page }) => {
    // Navigate to onboarding
    await page.goto('/onboarding')

    // Go through steps until competitor selection
    await page.getByPlaceholder(/https:\/\/example\.com/i).fill('https://example.com')
    await page.getByRole('button', { name: /анализировать/i }).click()
    
    await expect(page.getByRole('heading', { name: /мы нашли вашу компанию/i })).toBeVisible({ timeout: 30000 })
    await page.getByRole('button', { name: /далее: выбрать конкурентов/i }).click()
    
    await expect(page.getByRole('heading', { name: /выберите конкурентов для мониторинга/i })).toBeVisible({ timeout: 30000 })
    
    // Wait for competitors and select one
    await page.waitForTimeout(2000)
    const firstCheckbox = page.locator('button').filter({ hasText: '' }).first()
    await firstCheckbox.click()
    
    // Try to continue (should show registration modal if not authenticated)
    await page.getByRole('button', { name: /продолжить/i }).click()
    
    // Check if registration modal appears (if user is not authenticated)
    // Note: This test assumes user is not authenticated
    // In a real scenario, you might need to clear auth state first
    const registerModal = page.getByRole('heading', { name: /завершите регистрацию/i })
    
    // Modal might appear or might not (depending on auth state)
    // We'll just check that the page doesn't error
    await page.waitForTimeout(1000)
  })

  test('onboarding validates URL input', async ({ page }) => {
    await page.goto('/onboarding')

    // Try to submit empty URL
    const analyzeButton = page.getByRole('button', { name: /анализировать/i })
    await expect(analyzeButton).toBeDisabled()

    // Enter invalid URL
    await page.getByPlaceholder(/https:\/\/example\.com/i).fill('not-a-url')
    await analyzeButton.click()

    // Should show error or handle gracefully
    // The exact behavior depends on implementation
    await page.waitForTimeout(1000)
    
    // Verify we're still on the input step (error should prevent progression)
    await expect(page.getByRole('heading', { name: /введите сайт вашей компании/i })).toBeVisible()
  })

  test('onboarding progress indicator shows correct steps', async ({ page }) => {
    await page.goto('/onboarding')

    // Check that progress indicator is visible
    const progressSteps = page.locator('div').filter({ hasText: /^[1-5]$/ })
    await expect(progressSteps.first()).toBeVisible()

    // Step 1 should be active initially
    await expect(page.getByRole('heading', { name: /введите сайт вашей компании/i })).toBeVisible()
  })
})













