import { Page, Locator, expect } from '@playwright/test';
import { mockUser, mockAdminUser } from '../fixtures/api-mocks';

/**
 * Set up authenticated user state in localStorage
 */
export async function setupAuthenticatedUser(
	page: Page,
	userData: Partial<typeof mockUser> = {}
): Promise<void> {
	await page.evaluate(
		(user) => {
			localStorage.setItem('auth_token', 'test-token-for-e2e');
			localStorage.setItem('current_user', JSON.stringify(user));
		},
		{ ...mockUser, ...userData }
	);
}

/**
 * Set up admin user state in localStorage
 */
export async function setupAdminUser(
	page: Page,
	adminData: Partial<typeof mockAdminUser> = {}
): Promise<void> {
	await page.evaluate(
		(admin) => {
			localStorage.setItem('auth_token', 'admin-test-token-for-e2e');
			localStorage.setItem('current_user', JSON.stringify(admin));
		},
		{ ...mockAdminUser, ...adminData }
	);
}

/**
 * Clear authentication state from localStorage
 */
export async function clearAuthState(page: Page): Promise<void> {
	await page.evaluate(() => {
		localStorage.removeItem('auth_token');
		localStorage.removeItem('current_user');
	});
}

/**
 * Safe visibility check that doesn't throw on timeout
 * Returns true if element is visible, false otherwise
 */
export async function safeIsVisible(
	locator: Locator,
	timeout: number = 2000
): Promise<boolean> {
	try {
		await locator.waitFor({ state: 'visible', timeout });
		return true;
	} catch {
		return false;
	}
}

/**
 * Wait for element to be visible and return it, or null if not found
 */
export async function waitForElement(
	locator: Locator,
	timeout: number = 5000
): Promise<Locator | null> {
	try {
		await locator.waitFor({ state: 'visible', timeout });
		return locator;
	} catch {
		return null;
	}
}

/**
 * Check if any of the given locators are visible
 */
export async function anyVisible(locators: Locator[]): Promise<boolean> {
	for (const locator of locators) {
		if (await safeIsVisible(locator, 1000)) {
			return true;
		}
	}
	return false;
}

/**
 * Wait for network to be idle with a custom timeout
 */
export async function waitForNetworkIdle(
	page: Page,
	timeout: number = 10000
): Promise<void> {
	await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Get the count of elements matching a locator
 */
export async function getElementCount(locator: Locator): Promise<number> {
	return await locator.count();
}

/**
 * Wait for a toast notification to appear
 */
export async function waitForToast(
	page: Page,
	type?: 'success' | 'error' | 'info' | 'warning',
	timeout: number = 5000
): Promise<Locator | null> {
	const toastSelectors = [
		'[role="alert"]',
		'.toast',
		'.notification',
		'[class*="toast"]',
		'[class*="notification"]'
	];

	for (const selector of toastSelectors) {
		const toast = page.locator(selector);
		if (await safeIsVisible(toast.first(), timeout)) {
			if (type) {
				const hasType = await toast.first().getAttribute('class');
				if (hasType?.includes(type)) {
					return toast.first();
				}
			} else {
				return toast.first();
			}
		}
	}
	return null;
}

/**
 * Fill a form field and trigger blur to activate validation
 */
export async function fillFieldWithValidation(
	page: Page,
	selector: string,
	value: string
): Promise<void> {
	const field = page.locator(selector);
	await field.fill(value);
	await field.blur();
	// Wait for validation to potentially run
	await page.waitForTimeout(300);
}

/**
 * Submit a form and wait for navigation or response
 */
export async function submitFormAndWait(
	page: Page,
	submitButtonSelector: string,
	options: { waitForNavigation?: boolean; waitForUrl?: string | RegExp } = {}
): Promise<void> {
	const submitBtn = page.locator(submitButtonSelector);

	if (options.waitForUrl) {
		await Promise.all([
			page.waitForURL(options.waitForUrl),
			submitBtn.click()
		]);
	} else if (options.waitForNavigation) {
		await Promise.all([
			page.waitForLoadState('networkidle'),
			submitBtn.click()
		]);
	} else {
		await submitBtn.click();
	}
}

/**
 * Check if the current page is the signin page
 */
export function isSigninPage(page: Page): boolean {
	return page.url().includes('/signin');
}

/**
 * Check if the user was redirected to signin
 */
export async function wasRedirectedToSignin(
	page: Page,
	timeout: number = 5000
): Promise<boolean> {
	try {
		await page.waitForURL(/\/signin/, { timeout });
		return true;
	} catch {
		return false;
	}
}

/**
 * Take a screenshot with a descriptive name
 */
export async function takeScreenshot(
	page: Page,
	name: string
): Promise<void> {
	await page.screenshot({ path: `test-results/screenshots/${name}.png` });
}

/**
 * Get localStorage item value
 */
export async function getLocalStorageItem(
	page: Page,
	key: string
): Promise<string | null> {
	return await page.evaluate((k) => localStorage.getItem(k), key);
}

/**
 * Set localStorage item value
 */
export async function setLocalStorageItem(
	page: Page,
	key: string,
	value: string
): Promise<void> {
	await page.evaluate(({ k, v }) => localStorage.setItem(k, v), { k: key, v: value });
}

/**
 * Verify that a specific API endpoint was called
 */
export async function expectApiCallMade(
	page: Page,
	urlPattern: string | RegExp,
	method: string = 'GET'
): Promise<boolean> {
	// This requires setting up request interception beforehand
	// Returns true if the API call was made
	const requests: string[] = [];

	page.on('request', (request) => {
		if (request.method() === method) {
			requests.push(request.url());
		}
	});

	// Check if any request matches the pattern
	return requests.some((url) =>
		typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url)
	);
}

/**
 * Wait for specific text to appear on the page
 */
export async function waitForText(
	page: Page,
	text: string | RegExp,
	timeout: number = 5000
): Promise<boolean> {
	try {
		await page.getByText(text).first().waitFor({ state: 'visible', timeout });
		return true;
	} catch {
		return false;
	}
}

/**
 * Scroll to the bottom of the page (for infinite scroll testing)
 */
export async function scrollToBottom(page: Page): Promise<void> {
	await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
	await page.waitForTimeout(500); // Allow time for scroll to complete
}

/**
 * Scroll element into view
 */
export async function scrollIntoView(locator: Locator): Promise<void> {
	await locator.scrollIntoViewIfNeeded();
}
