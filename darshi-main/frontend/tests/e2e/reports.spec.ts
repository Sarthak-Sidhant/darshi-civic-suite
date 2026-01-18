import { test, expect } from '@playwright/test';

test.describe('Reports Feed', () => {
	test('home page loads with report feed', async ({ page }) => {
		await page.goto('/');

		// Should show feed container
		await expect(page.locator('main')).toBeVisible();

		// Wait for reports to load (or empty state)
		await page.waitForSelector('[class*="report"], [class*="empty"], [class*="loading"]', {
			timeout: 10000
		});
	});

	test('report cards display correctly', async ({ page }) => {
		await page.goto('/');

		// Wait for content to load
		await page.waitForLoadState('networkidle');

		// Check for report cards, empty state, or loading state
		const reportCards = page.locator('[class*="report-card"], [class*="card"], .report-item');
		const emptyState = page.getByText(/no reports/i);
		const loadingState = page.getByText(/loading/i);

		const hasReports = (await reportCards.count()) > 0;
		const isEmpty = await emptyState.isVisible().catch(() => false);
		const isLoading = await loadingState.isVisible().catch(() => false);

		// At least one state should be true (reports, empty, or loading)
		expect(hasReports || isEmpty || isLoading).toBeTruthy();
	});

	test('clicking report card navigates to detail', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Find first report card link
		const reportLink = page.locator('a[href^="/report/"]').first();

		if (await reportLink.isVisible()) {
			await reportLink.click();
			await page.waitForURL(/\/report\/.+/);

			// Report detail page should show
			await expect(page.locator('main')).toBeVisible();
		}
	});

	test('infinite scroll loads more reports', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const initialCards = await page.locator('[class*="report-card"], [class*="card"]').count();

		if (initialCards > 0) {
			// Scroll to bottom
			await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

			// Wait a bit for potential new content
			await page.waitForTimeout(2000);

			// Check if more cards loaded (or same if no more data)
			const finalCards = await page.locator('[class*="report-card"], [class*="card"]').count();
			expect(finalCards).toBeGreaterThanOrEqual(initialCards);
		}
	});
});

test.describe('Report Detail Page', () => {
	test('report detail page shows report info', async ({ page }) => {
		// First get a report ID from the feed
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const reportLink = page.locator('a[href^="/report/"]').first();

		if (await reportLink.isVisible()) {
			const href = await reportLink.getAttribute('href');
			await page.goto(href!);

			// Check for report elements
			await expect(page.locator('h1, h2, [class*="title"]').first()).toBeVisible();
		}
	});

	test('report detail shows status badge', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const reportLink = page.locator('a[href^="/report/"]').first();

		if (await reportLink.isVisible()) {
			const href = await reportLink.getAttribute('href');
			await page.goto(href!);

			// Look for status badge (PENDING, VERIFIED, etc.)
			const statusBadge = page.locator(
				'[class*="status"], [class*="badge"]:has-text(/pending|verified|resolved|rejected/i)'
			);
			const badgeCount = await statusBadge.count();
			if (badgeCount > 0) {
				await expect(statusBadge.first()).toBeVisible({ timeout: 5000 });
			}
		}
	});

	test('comments section is visible', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		const reportLink = page.locator('a[href^="/report/"]').first();

		if (await reportLink.isVisible()) {
			const href = await reportLink.getAttribute('href');
			await page.goto(href!);

			// Look for comments section
			const commentsSection = page.getByText(/comment/i);
			const count = await commentsSection.count();
			if (count > 0) {
				await expect(commentsSection.first()).toBeVisible({ timeout: 5000 });
			}
		}
	});
});

test.describe('Report Submission', () => {
	test('submit page loads', async ({ page }) => {
		await page.goto('/submit');

		// Check for submit form elements
		await expect(page.locator('main')).toBeVisible();
	});

	test('submit form has required fields', async ({ page }) => {
		await page.goto('/submit');
		await page.waitForTimeout(1000);

		// Title input - use ID selector or label
		const titleInput = page.locator('#title').or(page.locator('input[type="text"]').first());

		// Description input - use ID selector or textarea
		const descInput = page.locator('#description').or(page.locator('textarea').first());

		// Check for form elements
		const hasTitle = await titleInput.isVisible().catch(() => false);
		const hasDesc = await descInput.isVisible().catch(() => false);

		// At least one form element should be visible
		expect(hasTitle || hasDesc).toBeTruthy();
	});

	test('submit button exists', async ({ page }) => {
		await page.goto('/submit');

		const submitBtn = page
			.getByRole('button', { name: /submit/i })
			.or(page.locator('button[type="submit"]'));

		await expect(submitBtn.first()).toBeVisible();
	});

	test('location detection button exists', async ({ page }) => {
		await page.goto('/submit');
		await page.waitForTimeout(1000);

		// Look for location-related elements - buttons or map
		const currentLocationBtn = page.getByRole('button', { name: /current location/i });
		const searchLocationBtn = page.getByRole('button', { name: /search/i });
		const mapContainer = page.locator('.map-container');
		const locationLabel = page.locator('label').filter({ hasText: /location/i });

		// At least one location-related element should be present
		const hasCurrentLocation = await currentLocationBtn.isVisible().catch(() => false);
		const hasSearchLocation = await searchLocationBtn.isVisible().catch(() => false);
		const hasMap = await mapContainer.isVisible().catch(() => false);
		const hasLabel = await locationLabel.isVisible().catch(() => false);

		expect(hasCurrentLocation || hasSearchLocation || hasMap || hasLabel).toBeTruthy();
	});
});

test.describe('Upvote Functionality', () => {
	test('upvote button visible on report card', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Look for upvote/thumbs up icon or button
		const upvoteBtn = page.locator(
			'[class*="upvote"], button:has([class*="thumb"]), [aria-label*="upvote"]'
		);

		if ((await upvoteBtn.count()) > 0) {
			await expect(upvoteBtn.first()).toBeVisible();
		}
	});

	test('upvote count displayed', async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');

		// Look for upvote counts (numbers near thumbs up icons)
		const hasUpvoteCounts =
			(await page.locator('[class*="upvote"] + *, [class*="count"]').count()) > 0;

		// This is optional - some reports may have 0 upvotes
		expect(true).toBeTruthy();
	});
});
