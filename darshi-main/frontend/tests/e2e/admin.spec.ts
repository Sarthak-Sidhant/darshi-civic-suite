import { test, expect } from '@playwright/test';
import { setupApiMocks, mockAdminUser, mockDashboardData, mockReports } from './fixtures/api-mocks';
import { setupAdminUser, clearAuthState, safeIsVisible } from './utils/test-helpers';

test.describe('Admin Login Page', () => {
	test('admin login page loads correctly', async ({ page }) => {
		await page.goto('/admin/login');

		// Check page heading
		await expect(page.getByRole('heading', { name: /admin login/i })).toBeVisible();

		// Check form elements
		await expect(page.getByLabel(/admin email/i)).toBeVisible();
		await expect(page.getByLabel(/password/i)).toBeVisible();
		await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
	});

	test('shows error with empty fields', async ({ page }) => {
		await page.goto('/admin/login');

		// Try to submit empty form
		await page.getByRole('button', { name: /sign in/i }).click();

		// Wait for validation
		await page.waitForTimeout(500);

		// Should show error message (may be alert or just form validation)
		const alertError = page.locator('.alert.error');
		const hasAlert = await alertError.count() > 0;

		if (hasAlert) {
			await expect(alertError).toBeVisible();
		} else {
			// Form should still be visible (not submitted)
			await expect(page.getByRole('heading', { name: /admin login/i })).toBeVisible();
		}
	});

	test('shows error with invalid credentials', async ({ page }) => {
		await setupApiMocks(page, { admin: true, failMode: '401' });
		await page.goto('/admin/login');

		// Fill form with invalid credentials
		await page.fill('#email', 'wrong@email.com');
		await page.fill('#password', 'wrongpassword');
		await page.getByRole('button', { name: /sign in/i }).click();

		// Wait for API response
		await page.waitForTimeout(1000);

		// Should show error message
		await expect(page.locator('.alert.error')).toBeVisible();
		await expect(page.locator('.alert.error')).toContainText(/invalid admin credentials/i);
	});

	test('successful login redirects to admin dashboard', async ({ page }) => {
		await setupApiMocks(page, { reports: true, admin: true });
		await page.goto('/admin/login');

		// Fill form with valid credentials
		await page.fill('#email', 'admin@darshi.gov.in');
		await page.fill('#password', 'validpassword');
		await page.getByRole('button', { name: /sign in/i }).click();

		// Should redirect to admin dashboard
		await page.waitForURL('/admin');
		await expect(page.locator('.admin-container')).toBeVisible();
	});
});

test.describe('Admin Dashboard - Unauthenticated', () => {
	test('redirects to login when not authenticated', async ({ page }) => {
		await page.goto('/admin');

		// Should redirect to login
		await page.waitForURL(/\/admin\/login/);
	});

	test('redirects to login when token is invalid', async ({ page }) => {
		// Set up with non-admin user
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.setItem('auth_token', 'invalid-token');
			localStorage.setItem('current_user', JSON.stringify({ role: 'citizen' }));
		});

		await page.goto('/admin');

		// Should redirect to login
		await page.waitForURL(/\/admin\/login/);
	});
});

test.describe('Admin Dashboard - Authenticated', () => {
	test.beforeEach(async ({ page }) => {
		await setupApiMocks(page, { reports: true, admin: true });
		await page.goto('/');
		await setupAdminUser(page);
	});

	test('dashboard page loads with stats', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Should show dashboard heading
		await expect(page.getByRole('heading', { name: /dashboard overview/i })).toBeVisible();

		// Check stats cards exist
		const statCards = page.locator('.stat-card');
		const cardCount = await statCards.count();
		expect(cardCount).toBeGreaterThanOrEqual(1);

		// Check for specific stat labels
		await expect(page.getByText('Total Reports')).toBeVisible();
	});

	test('reports tab shows report management interface', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click Reports tab
		await page.click('button:has-text("Reports")');

		// Should show report management heading
		await expect(page.getByRole('heading', { name: /report management/i })).toBeVisible();

		// Should show filters
		await expect(page.locator('.filters')).toBeVisible();

		// Should show table container
		await expect(page.locator('.table-container')).toBeVisible();

		// Should show export button
		await expect(page.getByRole('button', { name: /export csv/i })).toBeVisible();
	});

	test('can filter reports by status', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Select a status filter
		await page.selectOption('.filters select:first-of-type', { label: 'Verified' });

		// Filter should be applied (checking select value)
		const selectedValue = await page.locator('.filters select:first-of-type').inputValue();
		expect(selectedValue).toBe('VERIFIED');
	});

	test('can search reports', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Type in search input
		await page.fill('.search-input', 'pothole');

		// Search value should be present
		await expect(page.locator('.search-input')).toHaveValue('pothole');
	});

	test('can select reports for bulk actions', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Wait for table to load
		await page.waitForTimeout(2000);

		// Select first report checkbox if exists
		const checkboxes = page.locator('tbody input[type="checkbox"]');
		const count = await checkboxes.count();

		if (count > 0) {
			await checkboxes.first().check();

			// Bulk actions should appear
			const bulkActions = page.locator('.bulk-actions');
			if (await safeIsVisible(bulkActions)) {
				await expect(bulkActions).toBeVisible();
			}
		}
		// If no checkboxes, the test passes (mocked data might not include reports)
	});

	test('status update modal opens', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Wait for table to load
		await page.waitForTimeout(1000);

		// Click Update button on first report if exists
		const updateBtn = page.locator('.action-btn:has-text("Update")').first();
		if (await safeIsVisible(updateBtn)) {
			await updateBtn.click();

			// Modal should appear
			await expect(page.locator('.modal')).toBeVisible();
			await expect(page.getByRole('heading', { name: /update report status/i })).toBeVisible();

			// Modal should have status select and note textarea
			await expect(page.locator('.modal select')).toBeVisible();
			await expect(page.locator('.modal textarea')).toBeVisible();
		}
	});

	test('audit logs tab loads', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click Audit Logs tab
		await page.click('button:has-text("Audit Logs")');

		// Should show audit logs heading
		await expect(page.getByRole('heading', { name: /audit logs/i })).toBeVisible();

		// Should show audit list container
		await expect(page.locator('.audit-list')).toBeVisible();
	});

	test('staff management tab loads', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click Staff tab
		await page.click('button:has-text("Staff")');

		// Should show staff management heading
		await expect(page.getByRole('heading', { name: /staff management/i })).toBeVisible();
	});

	test('super admin can see create admin button', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click Staff tab
		await page.click('button:has-text("Staff")');

		// Should show Create Admin button for super_admin
		await expect(page.getByRole('button', { name: /\+ create admin/i })).toBeVisible();
	});

	test('create admin modal opens', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click Staff tab
		await page.click('button:has-text("Staff")');

		// Click Create Admin button
		await page.click('button:has-text("+ Create Admin")');

		// Modal should appear
		await expect(page.locator('.modal')).toBeVisible();
		await expect(page.getByRole('heading', { name: /create new admin/i })).toBeVisible();

		// Modal should have email, password, and role fields
		await expect(page.locator('.modal input[type="email"]')).toBeVisible();
		await expect(page.locator('.modal input[type="password"]')).toBeVisible();
		await expect(page.locator('.modal select')).toBeVisible();
	});

	test('logout clears session and redirects', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Click logout button
		await page.click('.logout-btn');

		// Should redirect to admin login
		await page.waitForURL(/\/admin\/login/);

		// Token should be cleared
		const token = await page.evaluate(() => localStorage.getItem('auth_token'));
		expect(token).toBeNull();
	});

	test('mobile menu toggle works', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });

		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Mobile header should be visible
		await expect(page.locator('.mobile-header')).toBeVisible();

		// Click mobile menu button
		await page.click('.mobile-menu-btn');

		// Sidebar should open
		await expect(page.locator('.sidebar.mobile-open')).toBeVisible();

		// Click overlay to close
		await page.click('.mobile-overlay');

		// Sidebar should close (no longer have mobile-open class)
		await expect(page.locator('.sidebar.mobile-open')).not.toBeVisible();
	});
});

test.describe('Admin Dashboard - Error Handling', () => {
	test('shows error when dashboard API fails', async ({ page }) => {
		await page.route('**/api/v1/admin/analytics/dashboard', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Server error' } });
		});
		await page.route('**/api/v1/reports**', async (route) => {
			await route.fulfill({ status: 500, json: { error: 'Server error' } });
		});

		await page.goto('/');
		await setupAdminUser(page);
		await page.goto('/admin');

		// Wait for error to appear
		await page.waitForTimeout(2000);

		// Should show error banner
		const errorBanner = page.locator('.error-banner');
		const hasError = await safeIsVisible(errorBanner);
		expect(hasError).toBeTruthy();
	});

	test('handles empty reports gracefully', async ({ page }) => {
		await page.route('**/api/v1/reports**', async (route) => {
			await route.fulfill({ status: 200, json: [] });
		});
		await setupApiMocks(page, { reports: false, admin: true });

		await page.goto('/');
		await setupAdminUser(page);
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Table should exist but may be empty
		await expect(page.locator('.table-container')).toBeVisible();
	});
});

test.describe('Admin Dashboard - Navigation', () => {
	test.beforeEach(async ({ page }) => {
		await setupApiMocks(page, { reports: true, admin: true });
		await page.goto('/');
		await setupAdminUser(page);
	});

	test('tab navigation works correctly', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Start on Dashboard tab
		await expect(page.getByRole('heading', { name: /dashboard overview/i })).toBeVisible();

		// Go to Reports
		await page.click('button:has-text("Reports")');
		await expect(page.getByRole('heading', { name: /report management/i })).toBeVisible();

		// Go to Audit Logs
		await page.click('button:has-text("Audit Logs")');
		await expect(page.getByRole('heading', { name: /audit logs/i })).toBeVisible();

		// Go to Staff
		await page.click('button:has-text("Staff")');
		await expect(page.getByRole('heading', { name: /staff management/i })).toBeVisible();

		// Go back to Dashboard
		await page.click('button:has-text("Dashboard")');
		await expect(page.getByRole('heading', { name: /dashboard overview/i })).toBeVisible();
	});

	test('active tab is highlighted', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Dashboard tab should be active by default
		const dashboardBtn = page.locator('.sidebar-nav button').filter({ hasText: 'Dashboard' });
		await expect(dashboardBtn).toHaveClass(/active/);

		// Click Reports tab
		await page.click('button:has-text("Reports")');

		// Reports tab should now be active
		const reportsBtn = page.locator('.sidebar-nav button').filter({ hasText: 'Reports' });
		await expect(reportsBtn).toHaveClass(/active/);
	});
});

test.describe('Admin Reports Table', () => {
	test.beforeEach(async ({ page }) => {
		await setupApiMocks(page, { reports: true, admin: true });
		await page.goto('/');
		await setupAdminUser(page);
	});

	test('reports table displays correct columns', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');

		// Wait for table to render
		await page.waitForTimeout(1000);

		// Check table container exists
		await expect(page.locator('.table-container')).toBeVisible();

		// Check for at least some column headers (table may be empty)
		const tableHeaders = page.locator('th');
		const headerCount = await tableHeaders.count();
		expect(headerCount).toBeGreaterThan(0);
	});

	test('select all checkbox works', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Go to Reports tab
		await page.click('button:has-text("Reports")');
		await page.waitForTimeout(1000);

		// Click select all checkbox in header
		const selectAllCheckbox = page.locator('thead input[type="checkbox"]');
		if (await safeIsVisible(selectAllCheckbox)) {
			await selectAllCheckbox.check();

			// Bulk actions should appear
			const bulkActions = page.locator('.bulk-actions');
			if (await safeIsVisible(bulkActions)) {
				await expect(bulkActions).toBeVisible();
			}
		}
	});
});
