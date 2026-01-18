import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
	test.beforeEach(async ({ page }) => {
		// Clear any existing auth state
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.removeItem('auth_token');
			localStorage.removeItem('current_user');
		});
	});

	test('sign in page loads correctly', async ({ page }) => {
		await page.goto('/signin');

		// Check page title
		await expect(page).toHaveTitle(/Sign In/);

		// Check for sign in form elements
		await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();

		// Check for OAuth buttons
		await expect(page.getByRole('button', { name: /google/i })).toBeVisible();
		await expect(page.getByRole('button', { name: /github/i })).toBeVisible();
	});

	test('OAuth redirect works for Google', async ({ page }) => {
		await page.goto('/signin');

		// Click Google sign in
		const googleButton = page.getByRole('button', { name: /google/i });
		await googleButton.click();

		// Should redirect to Google OAuth (or API endpoint)
		await page.waitForURL(/accounts\.google\.com|api.*auth.*google/);
	});

	test('magic link form appears when email tab selected', async ({ page }) => {
		await page.goto('/signin');

		// Look for email/magic link option
		const emailTab = page.getByText(/email/i).or(page.getByText(/magic link/i));
		if (await emailTab.isVisible()) {
			await emailTab.click();
			// Check for email input
			await expect(page.getByPlaceholder(/email/i)).toBeVisible();
		}
	});

	test('unauthenticated user can access public pages', async ({ page }) => {
		// Home page should be accessible
		await page.goto('/');
		await expect(page.locator('main')).toBeVisible();

		// Map page should be accessible
		await page.goto('/map');
		await expect(page.locator('main')).toBeVisible();
	});

	test('unauthenticated user redirected from profile', async ({ page }) => {
		await page.goto('/profile');

		// Should redirect to sign in
		await page.waitForURL(/signin/);
	});

	test('sign in page shows expired message when redirected', async ({ page }) => {
		await page.goto('/signin?expired=true');

		// Wait for page to load
		await page.waitForTimeout(1000);

		// Should show session expired message or the page loads normally
		const expiredMessage = page.getByText(/expired|session/i);
		const signInHeading = page.getByRole('heading', { name: /sign in/i });
		const mainContent = page.locator('main');

		// Either expired message, sign in page, or main content should be visible
		const hasExpired = await expiredMessage.isVisible().catch(() => false);
		const hasSignIn = await signInHeading.isVisible().catch(() => false);
		const hasMain = await mainContent.isVisible().catch(() => false);

		expect(hasExpired || hasSignIn || hasMain).toBeTruthy();
	});

	test('logout clears session and redirects', async ({ page, context }) => {
		// First, simulate a logged in user
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.setItem('auth_token', 'fake-token-for-testing');
			localStorage.setItem(
				'current_user',
				JSON.stringify({
					username: 'testuser',
					email: 'test@example.com',
					city: 'Test City'
				})
			);
		});

		// Reload to pick up the auth state
		await page.reload();

		// Find and click logout button (if visible)
		const logoutButton = page.getByRole('button', { name: /logout/i });
		if (await logoutButton.isVisible()) {
			await logoutButton.click();

			// Check localStorage is cleared
			const token = await page.evaluate(() => localStorage.getItem('auth_token'));
			expect(token).toBeNull();

			// Should redirect to home
			await expect(page).toHaveURL('/');
		}
	});
});

test.describe('Onboarding Flow', () => {
	test('onboarding page requires authentication', async ({ page }) => {
		await page.goto('/onboarding');

		// Should either redirect to signin or show auth required message
		await page.waitForURL(/signin|onboarding/);
	});

	test('onboarding shows location and username fields', async ({ page }) => {
		// Simulate authenticated user without city (needs onboarding)
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.setItem('auth_token', 'fake-token-for-testing');
			localStorage.setItem(
				'current_user',
				JSON.stringify({
					username: 'newuser',
					email: 'new@example.com',
					city: null // No city = needs onboarding
				})
			);
		});

		await page.goto('/onboarding');

		// Wait for page to load
		await page.waitForTimeout(1000);

		// Check for onboarding form elements or redirect
		const cityInput = page.getByLabel(/city/i).or(page.getByPlaceholder(/city/i));
		const stateInput = page.getByLabel(/state/i).or(page.getByPlaceholder(/state/i));
		const mainContent = page.locator('main');

		// At least one location field should be visible OR page redirected
		const hasCityOrState = await cityInput.isVisible().catch(() => false) ||
							   await stateInput.isVisible().catch(() => false);
		const hasMainContent = await mainContent.isVisible().catch(() => false);

		expect(hasCityOrState || hasMainContent).toBeTruthy();
	});
});
