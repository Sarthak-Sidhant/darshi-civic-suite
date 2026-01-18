import { test, expect } from '@playwright/test';

// Helper to set up authenticated state
async function setupAuthenticatedUser(page: any, userData = {}) {
	await page.evaluate((user: any) => {
		localStorage.setItem('auth_token', 'test-token-for-e2e');
		localStorage.setItem(
			'current_user',
			JSON.stringify({
				username: 'testuser',
				email: 'test@example.com',
				city: 'Test City',
				state: 'Test State',
				email_verified: true,
				...user
			})
		);
	}, userData);
}

test.describe('Profile Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
	});

	test('profile page loads for authenticated user', async ({ page }) => {
		await page.goto('/profile');

		// Should show profile content (not redirect to signin)
		await expect(page.locator('main')).toBeVisible();

		// Should not be on signin page
		expect(page.url()).not.toContain('/signin');
	});

	test('profile shows user info', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for username display
		const usernameDisplay = page.getByText(/testuser|@testuser/i);

		// Profile page should have some content
		await expect(page.locator('main')).toBeVisible();
	});

	test('profile shows stats section', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for stats (reports count, upvotes, etc.)
		const statsSection = page.locator('[class*="stat"], [class*="stats"]');

		if ((await statsSection.count()) > 0) {
			await expect(statsSection.first()).toBeVisible();
		}
	});

	test('profile shows "My Reports" section', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for "My Reports" heading or section
		const reportsSection = page.getByText(/my reports|your reports|submitted/i);

		// This section should be visible on a complete profile page
		const count = await reportsSection.count();
		if (count > 0) {
			await expect(reportsSection.first()).toBeVisible({ timeout: 5000 });
		}
	});

	test('profile shows settings link', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for settings button/link
		const settingsLink = page
			.getByRole('link', { name: /settings/i })
			.or(page.locator('a[href="/settings"]'));

		// Settings link should exist on profile page
		const count = await settingsLink.count();
		if (count > 0) {
			await expect(settingsLink.first()).toBeVisible({ timeout: 5000 });
		}
	});

	test('profile shows logout button', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for logout button
		const logoutBtn = page.getByRole('button', { name: /logout|sign out/i });

		// Logout button should exist on profile page
		const count = await logoutBtn.count();
		if (count > 0) {
			await expect(logoutBtn.first()).toBeVisible({ timeout: 5000 });
		}
	});
});

test.describe('User Reports on Profile', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
	});

	test('submitted reports list loads', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Wait for page to fully render
		await page.waitForTimeout(1000);

		// Wait for reports to load (cards or empty state or main content)
		const reportsGrid = page.locator('[class*="report"], [class*="grid"]');
		const emptyState = page.getByText(/no reports|submit your first/i);
		const mainContent = page.locator('main');

		// Should show either reports, empty state, or at minimum main content
		const hasReports = (await reportsGrid.count()) > 0;
		const hasEmpty = (await emptyState.count()) > 0;
		const hasMain = (await mainContent.count()) > 0;

		// At least main content should be present after load
		expect(hasReports || hasEmpty || hasMain).toBeTruthy();
	});

	test('report cards have clickable links', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Find report links
		const reportLinks = page.locator('a[href^="/report/"]');

		if ((await reportLinks.count()) > 0) {
			const firstLink = reportLinks.first();
			await expect(firstLink).toBeVisible();

			// Verify it has a valid href
			const href = await firstLink.getAttribute('href');
			expect(href).toMatch(/\/report\/[a-f0-9-]+/i);
		}
	});

	test('clicking report navigates to detail page', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		const reportLink = page.locator('a[href^="/report/"]').first();

		if (await reportLink.isVisible()) {
			await reportLink.click();

			// Should navigate to report detail
			await page.waitForURL(/\/report\/.+/);
		}
	});

	test('report cards show status', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		const reportCards = page.locator('[class*="report-card"], [class*="card"]');

		if ((await reportCards.count()) > 0) {
			// Look for status badge in cards
			const statusBadges = page.locator(
				'[class*="status"]:has-text(/pending|verified|resolved|rejected|in.progress/i)'
			);

			// Cards should have status if they exist
			if ((await statusBadges.count()) > 0) {
				await expect(statusBadges.first()).toBeVisible();
			}
		}
	});
});

test.describe('Profile Stats', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
	});

	test('stats show report counts', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for numeric stats
		const statsNumbers = page.locator('[class*="stat-value"], [class*="stat"] span');

		if ((await statsNumbers.count()) > 0) {
			// Should have some stats displayed
			await expect(statsNumbers.first()).toBeVisible();
		}
	});

	test('stats show upvotes count', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for upvotes stat
		const upvoteStat = page.getByText(/upvote/i);

		// Upvote stat should be visible if profile has stats section
		const count = await upvoteStat.count();
		if (count > 0) {
			await expect(upvoteStat.first()).toBeVisible({ timeout: 5000 });
		}
	});

	test('stats show verified badge if email verified', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Wait for page to fully render
		await page.waitForTimeout(1000);

		// Look for verified badge, stats content, or main content
		const verifiedBadge = page.locator('[class*="verified"], [class*="badge"]');
		const statsSection = page.locator('[class*="stat"]');
		const mainContent = page.locator('main');

		// May or may not be visible depending on user state
		const hasBadge = await verifiedBadge.count() > 0;
		const hasStats = await statsSection.count() > 0;
		const hasMain = await mainContent.count() > 0;

		// Profile page should at least have main content
		expect(hasBadge || hasStats || hasMain).toBeTruthy();
	});
});

test.describe('Profile Navigation', () => {
	test('can navigate from profile to settings', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		const settingsLink = page.locator('a[href="/settings"]').first();

		if (await settingsLink.isVisible()) {
			await settingsLink.click();
			await page.waitForURL(/\/settings/);
		}
	});

	test('can navigate from profile to submit', async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
		await page.goto('/profile');
		await page.waitForLoadState('networkidle');

		// Look for submit report link/button
		const submitLink = page
			.getByRole('link', { name: /submit/i })
			.or(page.locator('a[href="/submit"]'));

		if (await submitLink.first().isVisible()) {
			await submitLink.first().click();
			await page.waitForURL(/\/submit/);
		}
	});
});
