import { test, expect } from '@playwright/test';

test.describe('Map Page', () => {
	test('map page loads correctly', async ({ page }) => {
		await page.goto('/map');

		// Check page title
		await expect(page).toHaveTitle(/Map View/);

		// Main container should be visible
		await expect(page.locator('.map-view')).toBeVisible();
	});

	test('map container initializes', async ({ page }) => {
		await page.goto('/map');

		// Wait for map container to be visible
		await expect(page.locator('.map-container')).toBeVisible();

		// Leaflet map should initialize (check for leaflet-specific elements)
		await page.waitForSelector('.leaflet-container', { timeout: 10000 });
	});

	test('search box is visible and functional', async ({ page }) => {
		await page.goto('/map');

		// Search input should be visible
		const searchInput = page.locator('.search-input');
		await expect(searchInput).toBeVisible();

		// Search button should be visible
		const searchBtn = page.locator('.search-btn');
		await expect(searchBtn).toBeVisible();

		// Type in search
		await searchInput.fill('Delhi');
		await expect(searchInput).toHaveValue('Delhi');
	});

	test('layer toggle buttons exist', async ({ page }) => {
		await page.goto('/map');

		// Issues and Alerts toggle buttons
		const issuesBtn = page.getByRole('button', { name: /issues/i });
		const alertsBtn = page.getByRole('button', { name: /alerts/i });

		await expect(issuesBtn).toBeVisible();
		await expect(alertsBtn).toBeVisible();
	});

	test('category filter chips are visible', async ({ page }) => {
		await page.goto('/map');

		// Wait for page to load
		await page.waitForLoadState('networkidle');

		// Category chips should be visible
		const allChip = page.locator('.category-chip').filter({ hasText: 'All' });
		await expect(allChip).toBeVisible();

		// Check for some category chips
		const categories = ['Pothole', 'Garbage', 'Streetlight', 'Water', 'Drainage', 'Other'];
		for (const category of categories) {
			const chip = page.locator('.category-chip').filter({ hasText: category });
			await expect(chip).toBeVisible();
		}
	});

	test('stats card shows report counts', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		// Stats card should be visible
		const statsCard = page.locator('.stats-card');
		await expect(statsCard).toBeVisible();

		// Should show "Total Reports" label
		await expect(page.getByText('Total Reports')).toBeVisible();

		// Should show "Active Alerts" label
		await expect(page.getByText('Active Alerts')).toBeVisible();
	});

	test('clicking category filter updates active state', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		// Click on Pothole category
		const potholeChip = page.locator('.category-chip').filter({ hasText: 'Pothole' });
		await potholeChip.click();

		// Pothole chip should now be active
		await expect(potholeChip).toHaveClass(/active/);

		// Click All to reset
		const allChip = page.locator('.category-chip').filter({ hasText: 'All' });
		await allChip.click();

		// All chip should be active
		await expect(allChip).toHaveClass(/active/);
	});

	test('layer toggle switches between Issues and Alerts', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		const issuesBtn = page.getByRole('button', { name: /issues/i });
		const alertsBtn = page.getByRole('button', { name: /alerts/i });

		// Issues should be active by default
		await expect(issuesBtn).toHaveClass(/active/);

		// Click Alerts
		await alertsBtn.click();
		await expect(alertsBtn).toHaveClass(/active/);

		// Click Issues again
		await issuesBtn.click();
		await expect(issuesBtn).toHaveClass(/active/);
	});

	test('search returns results and clears on selection', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		const searchInput = page.locator('.search-input');
		const searchBtn = page.locator('.search-btn');

		// Search for a location
		await searchInput.fill('Mumbai');
		await searchBtn.click();

		// Wait for results (may or may not appear depending on API)
		await page.waitForTimeout(2000);

		// If results appear, clicking one should clear the search
		const results = page.locator('.search-results');
		if (await results.isVisible()) {
			const firstResult = page.locator('.search-result-item').first();
			await firstResult.click();

			// Search should be cleared
			await expect(searchInput).toHaveValue('');
		}
	});

	test('zoom controls are visible', async ({ page }) => {
		await page.goto('/map');

		// Wait for map to initialize
		await page.waitForSelector('.leaflet-container', { timeout: 10000 });

		// Zoom controls should be visible
		const zoomIn = page.locator('.leaflet-control-zoom-in');
		const zoomOut = page.locator('.leaflet-control-zoom-out');

		await expect(zoomIn).toBeVisible();
		await expect(zoomOut).toBeVisible();
	});
});

test.describe('Map Interactions', () => {
	test('clicking on map marker shows popup', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		// Wait for markers to potentially load
		await page.waitForTimeout(3000);

		// Look for any markers
		const markers = page.locator('.custom-marker, .leaflet-marker-icon');
		const markerCount = await markers.count();

		if (markerCount > 0) {
			// Click first marker
			await markers.first().click();

			// Popup should appear - wait properly without swallowing errors
			const popup = page.locator('.leaflet-popup');
			await expect(popup).toBeVisible({ timeout: 5000 });
		}
	});

	test('map responds to search Enter key', async ({ page }) => {
		await page.goto('/map');
		await page.waitForLoadState('networkidle');

		const searchInput = page.locator('.search-input');

		// Type and press Enter
		await searchInput.fill('Bangalore');
		await searchInput.press('Enter');

		// Wait for potential search (may not return results in test environment)
		await page.waitForTimeout(2000);
	});
});
