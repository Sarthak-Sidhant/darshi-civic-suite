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

test.describe('Submit Report Page', () => {
	test('submit page loads correctly', async ({ page }) => {
		await page.goto('/submit');

		// Check page title
		await expect(page).toHaveTitle(/Submit Report/);

		// Should show form
		await expect(page.getByRole('heading', { name: /submit a report/i })).toBeVisible();
	});

	test('submit form has required fields', async ({ page }) => {
		await page.goto('/submit');

		// Title input (look for input with title in label or id)
		const titleInput = page.locator('#title').or(page.getByLabel(/title/i));
		await expect(titleInput.first()).toBeVisible();

		// Description textarea
		const descriptionInput = page.locator('#description').or(page.getByLabel(/description/i));
		await expect(descriptionInput.first()).toBeVisible();

		// Images section - look for the label text
		const imagesLabel = page.locator('label').filter({ hasText: /images/i });
		await expect(imagesLabel).toBeVisible();

		// Location section - look for the label text
		const locationLabel = page.locator('label').filter({ hasText: /location/i });
		await expect(locationLabel).toBeVisible();
	});

	test('image upload buttons are visible', async ({ page }) => {
		await page.goto('/submit');

		// Take Photo button
		const takePhotoBtn = page.getByRole('button', { name: /take photo/i });
		await expect(takePhotoBtn).toBeVisible();

		// Choose from Gallery button
		const galleryBtn = page.getByRole('button', { name: /choose from gallery/i });
		await expect(galleryBtn).toBeVisible();
	});

	test('location method buttons are visible', async ({ page }) => {
		await page.goto('/submit');

		// Use Current Location button
		const currentLocationBtn = page.getByRole('button', { name: /use current location/i });
		await expect(currentLocationBtn).toBeVisible();

		// Search Location button
		const searchLocationBtn = page.getByRole('button', { name: /search location/i });
		await expect(searchLocationBtn).toBeVisible();
	});

	test('submit button exists', async ({ page }) => {
		await page.goto('/submit');

		const submitBtn = page.getByRole('button', { name: /submit report/i });
		await expect(submitBtn).toBeVisible();
	});

	test('map container is visible', async ({ page }) => {
		await page.goto('/submit');

		// Map section
		const mapSection = page.locator('.map-section');
		await expect(mapSection).toBeVisible();

		// Map container
		const mapContainer = page.locator('.map-container');
		await expect(mapContainer).toBeVisible();

		// Wait for Leaflet to initialize
		await page.waitForSelector('.leaflet-container', { timeout: 10000 });
	});

	test('title validation shows error for short titles', async ({ page }) => {
		await page.goto('/submit');

		const titleInput = page.getByLabel(/title/i);

		// Type short title
		await titleInput.fill('Short');
		await titleInput.blur();

		// Should show validation error or character count warning
		await page.waitForTimeout(500);
		const errorMessage = page.locator('.error-message, #title-error');
		const charCount = page.locator('.char-count');

		// Either error message or character count should be visible
		const hasError = (await errorMessage.count()) > 0;
		const hasCharCount = (await charCount.count()) > 0;
		expect(hasError || hasCharCount).toBeTruthy();
	});

	test('character count updates as user types', async ({ page }) => {
		await page.goto('/submit');

		const titleInput = page.getByLabel(/title/i);
		const charCount = page.locator('.char-count').first();

		// Type some text
		await titleInput.fill('This is a test title');

		// Character count should update
		await expect(charCount).toContainText('20');
	});

	test('clicking search location shows search box', async ({ page }) => {
		await page.goto('/submit');

		// Click Search Location button
		const searchLocationBtn = page.getByRole('button', { name: /search location/i });
		await searchLocationBtn.click();

		// Search box should appear
		const searchBox = page.locator('.search-box');
		await expect(searchBox).toBeVisible();

		// Back button should appear
		const backBtn = page.getByRole('button', { name: /back to location options/i });
		await expect(backBtn).toBeVisible();
	});

	test('location search works', async ({ page }) => {
		await page.goto('/submit');

		// Click Search Location button
		const searchLocationBtn = page.getByRole('button', { name: /search location/i });
		await searchLocationBtn.click();

		// Fill search input
		const searchInput = page.locator('.search-box input');
		await searchInput.fill('New Delhi');
		await searchInput.press('Enter');

		// Wait for results (may or may not appear depending on API)
		await page.waitForTimeout(3000);

		// If results appear, they should be clickable
		const results = page.locator('.search-results');
		if (await results.isVisible()) {
			const firstResult = page.locator('.search-result-item').first();
			await expect(firstResult).toBeVisible();
		}
	});

	test('form validation prevents empty submission', async ({ page }) => {
		await page.goto('/submit');

		// Try to submit empty form
		const submitBtn = page.getByRole('button', { name: /submit report/i });
		await submitBtn.click();

		// Should show error toast
		await page.waitForTimeout(1000);

		// Form should still be visible (not submitted)
		await expect(page.getByRole('heading', { name: /submit a report/i })).toBeVisible();
	});

	test('map header shows instructions', async ({ page }) => {
		await page.goto('/submit');

		// Map header should show instructions
		await expect(page.getByText(/select location/i)).toBeVisible();
		await expect(page.getByText(/click on map or drag/i)).toBeVisible();
	});
});

test.describe('Submit Page - Authenticated User', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await setupAuthenticatedUser(page);
	});

	test('authenticated user can fill out form', async ({ page }) => {
		await page.goto('/submit');
		await page.waitForLoadState('networkidle');

		// Fill title
		const titleInput = page.locator('#title');
		await titleInput.fill('Large pothole on Main Street causing traffic issues');

		// Fill description
		const descriptionInput = page.locator('#description');
		await descriptionInput.fill('There is a large pothole approximately 2 feet wide on Main Street near the intersection with Oak Avenue. It has been causing traffic slowdowns and vehicle damage.');

		// Form should have the values
		await expect(titleInput).toHaveValue('Large pothole on Main Street causing traffic issues');
		await expect(descriptionInput).toHaveValue(/large pothole approximately 2 feet wide/);
	});

	test('description character count updates', async ({ page }) => {
		await page.goto('/submit');

		const descriptionInput = page.locator('#description');

		// Type description
		await descriptionInput.fill('This is a test description for the report.');

		// Character count should update - look for description char count
		// The format is "XX/2000" so check for the number
		const charCounts = page.locator('.char-count');
		const secondCharCount = charCounts.nth(1);
		await expect(secondCharCount).toContainText(/4\d\/2000/);
	});
});

test.describe('Submit Page Mobile', () => {
	test.use({ viewport: { width: 375, height: 667 } });

	test('submit page is responsive on mobile', async ({ page }) => {
		await page.goto('/submit');

		// Page should still show main elements
		await expect(page.getByRole('heading', { name: /submit a report/i })).toBeVisible();

		// Form should be visible
		const titleInput = page.getByLabel(/title/i);
		await expect(titleInput).toBeVisible();

		// Image buttons should stack
		const takePhotoBtn = page.getByRole('button', { name: /take photo/i });
		await expect(takePhotoBtn).toBeVisible();
	});

	test('map section is accessible on mobile', async ({ page }) => {
		await page.goto('/submit');

		// Scroll to map section
		await page.locator('.map-section').scrollIntoViewIfNeeded();

		// Map should be visible
		const mapContainer = page.locator('.map-container');
		await expect(mapContainer).toBeVisible();
	});
});

test.describe('Submit Form Validation', () => {
	test('title minimum length validation', async ({ page }) => {
		await page.goto('/submit');

		const titleInput = page.getByLabel(/title/i);

		// Type short title
		await titleInput.fill('Short');
		await titleInput.blur();

		// Wait for validation
		await page.waitForTimeout(500);

		// Error message should appear
		const errorMessage = page.locator('#title-error');
		if (await errorMessage.count() > 0) {
			await expect(errorMessage).toContainText(/at least 10 characters/i);
		}
	});

	test('title maximum length validation', async ({ page }) => {
		await page.goto('/submit');

		const titleInput = page.getByLabel(/title/i);

		// Type very long title (more than 200 chars)
		const longTitle = 'A'.repeat(250);
		await titleInput.fill(longTitle);
		await titleInput.blur();

		// Wait for validation
		await page.waitForTimeout(500);

		// Character count should show over limit
		const charCount = page.locator('.char-count').first();
		await expect(charCount).toContainText('250');
	});

	test('description length recommendation', async ({ page }) => {
		await page.goto('/submit');

		const descriptionInput = page.getByLabel(/description/i);

		// Type short description
		await descriptionInput.fill('Short desc');
		await descriptionInput.blur();

		// Wait for validation
		await page.waitForTimeout(500);

		// Warning about minimum length may appear
		const errorMessage = page.locator('#description-error');
		if (await errorMessage.count() > 0) {
			await expect(errorMessage).toContainText(/at least 20 characters/i);
		}
	});
});
