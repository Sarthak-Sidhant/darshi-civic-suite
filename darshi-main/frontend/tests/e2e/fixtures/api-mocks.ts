import { Page, Route } from '@playwright/test';

// Mock data matching actual API response shapes
export const mockReports = [
	{
		id: 'test-report-001',
		report_id: 'test-report-001',
		username: 'testuser',
		title: 'Large pothole on Main Street',
		description: 'Causing traffic issues near the intersection',
		address: 'Main Street, Mumbai',
		city: 'Mumbai',
		state: 'Maharashtra',
		country: 'India',
		latitude: 19.076,
		longitude: 72.8777,
		image_urls: ['https://example.com/image1.jpg'],
		image_data: [
			{ webp_url: 'https://example.com/image1.webp', jpeg_url: 'https://example.com/image1.jpg' }
		],
		status: 'VERIFIED',
		category: 'Pothole',
		severity: 7,
		upvote_count: 15,
		has_upvoted: false,
		comment_count: 3,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		timeline: [
			{ event: 'CREATED', timestamp: new Date().toISOString(), details: 'Report submitted' },
			{
				event: 'VERIFIED',
				timestamp: new Date().toISOString(),
				details: 'AI verification passed'
			}
		]
	},
	{
		id: 'test-report-002',
		report_id: 'test-report-002',
		username: 'anotheruser',
		title: 'Broken streetlight near park',
		description: 'The streetlight has been broken for a week',
		address: 'Park Avenue, Mumbai',
		city: 'Mumbai',
		state: 'Maharashtra',
		country: 'India',
		latitude: 19.078,
		longitude: 72.88,
		image_urls: ['https://example.com/image2.jpg'],
		image_data: [
			{ webp_url: 'https://example.com/image2.webp', jpeg_url: 'https://example.com/image2.jpg' }
		],
		status: 'PENDING_VERIFICATION',
		category: 'Streetlight',
		severity: 5,
		upvote_count: 8,
		has_upvoted: false,
		comment_count: 1,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		timeline: [{ event: 'CREATED', timestamp: new Date().toISOString(), details: 'Report submitted' }]
	}
];

export const mockUser = {
	id: 1,
	username: 'testuser',
	email: 'test@example.com',
	phone: null,
	role: 'citizen',
	is_active: true,
	is_verified: true,
	email_verified: true,
	lat: 19.076,
	lng: 72.8777,
	city: 'Mumbai',
	state: 'Maharashtra',
	country: 'India',
	location_address: 'Mumbai, Maharashtra, India',
	created_at: new Date().toISOString(),
	last_login: new Date().toISOString()
};

export const mockAdminUser = {
	id: 1,
	username: 'admin',
	email: 'admin@darshi.gov.in',
	role: 'super_admin',
	is_active: true
};

export const mockDashboardData = {
	summary: {
		total_reports: 150,
		status_distribution: {
			PENDING_VERIFICATION: 20,
			VERIFIED: 80,
			IN_PROGRESS: 30,
			RESOLVED: 15,
			REJECTED: 5
		},
		average_severity: 5.5
	},
	top_categories: [
		{ category: 'Pothole', count: 45 },
		{ category: 'Garbage', count: 30 },
		{ category: 'Streetlight', count: 25 }
	],
	recent_admin_actions: []
};

export const mockComments = [
	{
		id: 'comment-1',
		report_id: 'test-report-001',
		user_id: 2,
		username: 'user1',
		text: 'Thanks for reporting this issue!',
		created_at: new Date().toISOString()
	},
	{
		id: 'comment-2',
		report_id: 'test-report-001',
		user_id: 3,
		username: 'user2',
		text: 'I noticed this too, very dangerous.',
		created_at: new Date().toISOString()
	}
];

export const mockAlerts = [
	{
		geohash: 'te7ud7q',
		location: 'Mumbai Central',
		count: 5,
		categories: 'Pothole, Garbage',
		status: 'ACTIVE',
		lat: 19.076,
		lng: 72.8777
	}
];

export type FailMode = 'network' | '401' | '500' | '404' | '429';

export interface SetupApiMocksOptions {
	reports?: boolean;
	auth?: boolean;
	admin?: boolean;
	failMode?: FailMode;
}

/**
 * Setup API route interception for E2E tests
 */
export async function setupApiMocks(
	page: Page,
	options: SetupApiMocksOptions = {}
): Promise<void> {
	const { reports = true, auth = true, admin = false, failMode } = options;

	// Mock reports endpoints
	if (reports) {
		await page.route('**/api/v1/reports**', async (route: Route) => {
			if (failMode === 'network') {
				await route.abort('connectionfailed');
			} else if (failMode === '500') {
				await route.fulfill({ status: 500, json: { error: 'Internal server error' } });
			} else {
				await route.fulfill({ status: 200, json: mockReports });
			}
		});

		await page.route('**/api/v1/report/*', async (route: Route) => {
			const url = route.request().url();
			// Extract report ID from URL
			const match = url.match(/\/report\/([^/?]+)/);
			const reportId = match ? match[1] : 'test-report-001';

			if (failMode === '404') {
				await route.fulfill({ status: 404, json: { error: 'Report not found' } });
			} else {
				await route.fulfill({
					status: 200,
					json: { ...mockReports[0], id: reportId, report_id: reportId }
				});
			}
		});
	}

	// Mock upvote endpoint
	await page.route('**/api/v1/report/*/upvote', async (route: Route) => {
		if (failMode === '401') {
			await route.fulfill({ status: 401, json: { error: 'Authentication required' } });
		} else if (failMode === '429') {
			await route.fulfill({
				status: 429,
				json: { error: 'Rate limit exceeded', detail: 'Please try again later' }
			});
		} else {
			await route.fulfill({ status: 200, json: { count: 16, status: 'voted' } });
		}
	});

	// Mock comments endpoints
	await page.route('**/api/v1/report/*/comments', async (route: Route) => {
		await route.fulfill({ status: 200, json: mockComments });
	});

	await page.route('**/api/v1/report/*/comment', async (route: Route) => {
		if (route.request().method() === 'POST') {
			const newComment = {
				id: 'comment-new',
				username: mockUser.username,
				text: 'New comment',
				created_at: new Date().toISOString()
			};
			await route.fulfill({ status: 201, json: newComment });
		} else {
			await route.continue();
		}
	});

	// Mock auth endpoints
	if (auth) {
		await page.route('**/api/v1/auth/me', async (route: Route) => {
			if (failMode === '401') {
				await route.fulfill({ status: 401, json: { error: 'Invalid token' } });
			} else {
				await route.fulfill({ status: 200, json: mockUser });
			}
		});

		await page.route('**/api/v1/auth/token', async (route: Route) => {
			if (failMode === '401') {
				await route.fulfill({ status: 401, json: { error: 'Invalid credentials' } });
			} else {
				await route.fulfill({
					status: 200,
					json: { access_token: 'mock-jwt-token', token_type: 'bearer' }
				});
			}
		});

		await page.route('**/api/v1/auth/register', async (route: Route) => {
			await route.fulfill({ status: 201, json: mockUser });
		});

		await page.route('**/api/v1/auth/magic-link**', async (route: Route) => {
			await route.fulfill({ status: 200, json: { message: 'Magic link sent' } });
		});

		await page.route('**/api/v1/auth/verify-magic-link**', async (route: Route) => {
			if (failMode === '401') {
				await route.fulfill({ status: 400, json: { error: 'Invalid or expired token' } });
			} else {
				await route.fulfill({
					status: 200,
					json: { access_token: 'mock-jwt-token', token_type: 'bearer', user: mockUser }
				});
			}
		});
	}

	// Mock admin endpoints
	if (admin) {
		await page.route('**/api/v1/admin/login', async (route: Route) => {
			if (failMode === '401') {
				await route.fulfill({ status: 401, json: { error: 'Invalid admin credentials' } });
			} else {
				await route.fulfill({
					status: 200,
					json: { token: 'admin-jwt-token', admin: mockAdminUser }
				});
			}
		});

		await page.route('**/api/v1/admin/analytics/dashboard', async (route: Route) => {
			if (failMode === '500') {
				await route.fulfill({ status: 500, json: { error: 'Server error' } });
			} else {
				await route.fulfill({ status: 200, json: mockDashboardData });
			}
		});

		await page.route('**/api/v1/admin/analytics/audit-logs**', async (route: Route) => {
			await route.fulfill({
				status: 200,
				json: {
					logs: [
						{
							action: 'STATUS_UPDATE',
							user_id: 'admin',
							timestamp: new Date().toISOString(),
							details: 'Updated report status'
						}
					]
				}
			});
		});

		await page.route('**/api/v1/admin/admins', async (route: Route) => {
			await route.fulfill({
				status: 200,
				json: {
					admins: [{ email: 'admin@darshi.gov.in', role: 'super_admin', is_active: true }]
				}
			});
		});

		await page.route('**/api/v1/admin/report/*/status', async (route: Route) => {
			await route.fulfill({ status: 200, json: { message: 'Status updated' } });
		});
	}

	// Mock geocoding
	await page.route('**/api/v1/geocode**', async (route: Route) => {
		if (failMode === '500') {
			await route.fulfill({ status: 500, json: { error: 'Geocoding failed' } });
		} else {
			await route.fulfill({
				status: 200,
				json: [
					{
						display_name: 'Mumbai, Maharashtra, India',
						lat: '19.0760',
						lon: '72.8777',
						address: { city: 'Mumbai', state: 'Maharashtra', country: 'India' }
					}
				]
			});
		}
	});

	// Mock reverse geocoding
	await page.route('**/api/v1/reverse-geocode**', async (route: Route) => {
		await route.fulfill({
			status: 200,
			json: {
				display_name: 'Main Street, Mumbai, Maharashtra, India',
				address: { road: 'Main Street', city: 'Mumbai', state: 'Maharashtra', country: 'India' }
			}
		});
	});

	// Mock alerts
	await page.route('**/api/v1/alerts', async (route: Route) => {
		await route.fulfill({ status: 200, json: mockAlerts });
	});

	// Mock user profile/settings endpoints
	await page.route('**/api/v1/users/me**', async (route: Route) => {
		if (route.request().method() === 'PUT' || route.request().method() === 'PATCH') {
			await route.fulfill({ status: 200, json: { ...mockUser, ...route.request().postDataJSON() } });
		} else {
			await route.fulfill({ status: 200, json: mockUser });
		}
	});

	await page.route('**/api/v1/users/me/reports**', async (route: Route) => {
		await route.fulfill({ status: 200, json: mockReports });
	});
}

/**
 * Setup API mocks that simulate specific error conditions
 */
export async function setupErrorMocks(
	page: Page,
	errorType: FailMode,
	endpoints: string[] = ['**/api/v1/**']
): Promise<void> {
	for (const endpoint of endpoints) {
		await page.route(endpoint, async (route: Route) => {
			switch (errorType) {
				case 'network':
					await route.abort('connectionfailed');
					break;
				case '401':
					await route.fulfill({ status: 401, json: { error: 'Unauthorized' } });
					break;
				case '500':
					await route.fulfill({ status: 500, json: { error: 'Internal server error' } });
					break;
				case '404':
					await route.fulfill({ status: 404, json: { error: 'Not found' } });
					break;
				case '429':
					await route.fulfill({
						status: 429,
						json: { error: 'Rate limit exceeded', detail: 'Please try again later' }
					});
					break;
			}
		});
	}
}
