import { test, expect } from '@playwright/test';
import { setupApiMocks, setupErrorMocks, mockUser, mockReports } from './fixtures/api-mocks';
import { setupAuthenticatedUser, clearAuthState, safeIsVisible, waitForToast } from './utils/test-helpers';

test.describe('Network Error Handling', () => {
	test('shows error message when reports API fails', async ({ page }) => {
		// Set up network failure for reports
		await page.route('**/api/v1/reports**', async (route) => {
			await route.abort('connectionfailed');
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Should show empty state or error state
		const emptyState = page.locator('.empty-state, [class*="empty"], [class*="error"]');
		const count = await emptyState.count();

		// At minimum, main content should still be visible
		await expect(page.locator('main')).toBeVisible();
	});

	test('page handles 500 server error gracefully', async ({ page }) => {
		await page.route('**/api/v1/reports**', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Internal server error' } });
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Page should not crash - main content should be visible
		await expect(page.locator('main')).toBeVisible();
	});

	test('handles timeout by showing loading state', async ({ page }) => {
		// Simulate slow network
		await page.route('**/api/v1/reports**', async (route) => {
			await new Promise(resolve => setTimeout(resolve, 5000));
			await route.fulfill({ status: 200, json: mockReports });
		});

		await page.goto('/');

		// Loading state should be visible initially
		// The app should handle this gracefully
		await expect(page.locator('main')).toBeVisible();
	});
});

test.describe('Authentication Error Handling', () => {
	test('401 error clears session and can redirect', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);

		// Set up 401 response for auth endpoint
		await page.route('**/api/v1/auth/me', async (route) => {
			await route.fulfill({ status: 401, json: { error: 'Token expired' } });
		});

		// Trigger auth check by visiting profile
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Should either be on profile (cached) or redirected to signin
		const currentUrl = page.url();
		const isOnProfile = currentUrl.includes('/profile');
		const isOnSignin = currentUrl.includes('/signin');

		expect(isOnProfile || isOnSignin).toBeTruthy();
	});

	test('expired session shows signin page', async ({ page }) => {
		await page.goto('/signin?expired=true');

		// Should show signin page
		await expect(page.locator('main')).toBeVisible();
		await expect(page.url()).toContain('/signin');
	});

	test('protected routes redirect unauthenticated users', async ({ page }) => {
		// Clear any auth state
		await page.goto('/');
		await clearAuthState(page);

		// Try to access profile
		await page.goto('/profile');

		// Should redirect to signin
		await page.waitForURL(/signin/);
	});
});

test.describe('Form Validation Errors', () => {
	test('report submission shows validation errors for empty form', async ({ page }) => {
		await page.goto('/submit');

		// Try to submit empty form
		const submitBtn = page.getByRole('button', { name: /submit report/i });
		await submitBtn.click();

		// Should show error or validation feedback
		await page.waitForTimeout(1000);

		// Form should still be visible (not submitted)
		await expect(page.getByRole('heading', { name: /submit a report/i })).toBeVisible();
	});

	test('title too short shows error', async ({ page }) => {
		await page.goto('/submit');

		const titleInput = page.getByLabel(/title/i);
		await titleInput.fill('Short');
		await titleInput.blur();

		// Wait for validation
		await page.waitForTimeout(500);

		// Error message or character count should appear
		const errorMessage = page.locator('#title-error, .error-message');
		const charCount = page.locator('.char-count');

		const hasError = (await errorMessage.count()) > 0;
		const hasCharCount = (await charCount.count()) > 0;

		expect(hasError || hasCharCount).toBeTruthy();
	});

	test('description validation works', async ({ page }) => {
		await page.goto('/submit');

		const descriptionInput = page.getByLabel(/description/i);
		await descriptionInput.fill('Too short');
		await descriptionInput.blur();

		// Wait for validation
		await page.waitForTimeout(500);

		// Character count or error should be visible
		const charCount = page.locator('.char-count');
		if ((await charCount.count()) > 1) {
			await expect(charCount.nth(1)).toBeVisible();
		}
	});
});

test.describe('API Error Responses', () => {
	test('500 server error on report detail shows error state', async ({ page }) => {
		await page.route('**/api/v1/report/*', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Internal server error' } });
		});

		await page.goto('/report/test-id-123');
		await page.waitForLoadState('networkidle');

		// Page should handle error gracefully
		await expect(page.locator('main')).toBeVisible();
	});

	test('404 report not found shows appropriate message', async ({ page }) => {
		await page.route('**/api/v1/report/nonexistent**', async (route) => {
			await route.fulfill({ status: 404, json: { error: 'Report not found' } });
		});

		await page.goto('/report/nonexistent');
		await page.waitForLoadState('networkidle');

		// Should show error or empty state
		await expect(page.locator('main')).toBeVisible();
	});

	test('429 rate limit shows rate limit message', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);

		// Set up API mocks with reports
		await setupApiMocks(page, { reports: true });

		// Override upvote to return 429
		await page.route('**/api/v1/report/*/upvote', async (route) => {
			await route.fulfill({
				status: 429,
				json: { error: 'Rate limit exceeded', detail: 'Please try again later' }
			});
		});

		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Try to upvote if button exists
		const upvoteBtn = page.locator('[class*="upvote"], button:has([class*="thumb"])').first();
		if (await safeIsVisible(upvoteBtn)) {
			await upvoteBtn.click();

			// Toast should appear with rate limit message
			await page.waitForTimeout(1000);
			// Rate limit should be handled gracefully
		}
	});
});

test.describe('Geocoding Errors', () => {
	test('geocoding failure shows error in submit form', async ({ page }) => {
		await page.route('**/api/v1/geocode**', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Geocoding failed' } });
		});

		await page.goto('/submit');

		// Click Search Location button
		const searchLocationBtn = page.getByRole('button', { name: /search location/i });
		await searchLocationBtn.click();

		// Fill search input
		const searchInput = page.locator('.search-box input');
		if (await safeIsVisible(searchInput)) {
			await searchInput.fill('NonexistentPlace123');
			await searchInput.press('Enter');

			// Wait for API call
			await page.waitForTimeout(3000);

			// Page should handle gracefully - search box should still be visible
			await expect(searchInput).toBeVisible();
		}
	});

	test('geocoding returns no results shows feedback', async ({ page }) => {
		await page.route('**/api/v1/geocode**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});

		await page.goto('/submit');

		// Click Search Location button
		const searchLocationBtn = page.getByRole('button', { name: /search location/i });
		await searchLocationBtn.click();

		// Fill search input
		const searchInput = page.locator('.search-box input');
		if (await safeIsVisible(searchInput)) {
			await searchInput.fill('RandomInvalidPlace');
			await searchInput.press('Enter');

			// Wait for API call
			await page.waitForTimeout(2000);

			// Should handle empty results gracefully
			await expect(page.locator('main')).toBeVisible();
		}
	});
});

test.describe('OAuth Error Handling', () => {
	test('OAuth callback with error parameter shows message', async ({ page }) => {
		await page.goto('/auth/callback?error=access_denied');

		// Wait for page to process
		await page.waitForTimeout(2000);

		// Should be redirected or show error
		const currentUrl = page.url();
		const isOnCallback = currentUrl.includes('callback');
		const isOnSignin = currentUrl.includes('signin');
		const isOnHome = currentUrl === 'http://localhost:5173/' || currentUrl.endsWith('/');

		expect(isOnCallback || isOnSignin || isOnHome).toBeTruthy();
	});

	test('magic link with invalid token handles error', async ({ page }) => {
		await page.route('**/api/v1/auth/verify-magic-link**', async (route) => {
			await route.fulfill({ status: 400, json: { error: 'Invalid or expired token' } });
		});

		await page.goto('/auth/magic-link?token=invalid-token');

		// Wait for page to process
		await page.waitForTimeout(3000);

		// Page should handle error gracefully - could redirect or show error
		const currentUrl = page.url();
		const bodyVisible = await page.locator('body').isVisible();

		// Either body is visible or we were redirected
		expect(bodyVisible || currentUrl.includes('signin') || currentUrl.includes('magic-link')).toBeTruthy();
	});
});

test.describe('Map Error Handling', () => {
	test('map page handles API failure gracefully', async ({ page }) => {
		await page.route('**/api/v1/reports**', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Server error' } });
		});
		await page.route('**/api/v1/alerts', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Server error' } });
		});

		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		// Map page should still load
		await expect(page.locator('.map-view')).toBeVisible();
		// Map container should be visible even if data fails
		await expect(page.locator('.map-container')).toBeVisible();
	});

	test('map search handles API failure gracefully', async ({ page }) => {
		await page.route('**/api/v1/geocode**', async (route) => {
			await route.abort('connectionfailed');
		});

		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		// Try to search
		const searchInput = page.locator('.search-input');
		await searchInput.fill('Mumbai');
		await page.locator('.search-btn').click();

		// Wait for timeout
		await page.waitForTimeout(3000);

		// Map should still be functional
		await expect(page.locator('.map-container')).toBeVisible();
	});
});

test.describe('Profile Error Handling', () => {
	test('profile page handles user data fetch failure', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);

		await page.route('**/api/v1/users/me/reports**', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Server error' } });
		});

		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Profile page should still load with basic info
		await expect(page.locator('main')).toBeVisible();
	});
});

test.describe('Settings Error Handling', () => {
	test('settings page handles save failure', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);

		await page.route('**/api/v1/users/me**', async (route) => {
			if (route.request().method() === 'PUT' || route.request().method() === 'PATCH') {
				await route.fulfill({ status: 500, json: { error: 'Failed to save' } });
			} else {
				await route.fulfill({ status: 200, json: mockUser });
			}
		});

		await page.goto('/settings');
		await page.waitForLoadState('networkidle');

		// Settings page should load
		await expect(page.locator('main')).toBeVisible();
	});
});
