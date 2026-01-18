// API configuration and utility functions
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

// Request deduplication - prevents duplicate in-flight requests
const pendingRequests = new Map<string, Promise<any>>();

/**
 * Deduplicated fetch - returns existing promise if same request is in-flight.
 * This prevents duplicate API calls when multiple components request the same data.
 */
async function deduplicatedFetch<T>(
	key: string,
	fetchFn: () => Promise<T>,
	ttlMs: number = 100 // Dedup window in ms
): Promise<T> {
	// Check if request is already in-flight
	const existing = pendingRequests.get(key);
	if (existing) {
		return existing;
	}

	// Create new request promise
	const promise = fetchFn().finally(() => {
		// Remove from pending after TTL (allows slight overlap for rapid calls)
		setTimeout(() => pendingRequests.delete(key), ttlMs);
	});

	pendingRequests.set(key, promise);
	return promise;
}

export interface ApiError {
	error: string;
	detail?: string;
	message?: string;
	recoverable?: boolean;
	request_id?: string;
	retry_after?: number;
}

export class NetworkError extends Error {
	constructor(message: string) {
		super(message);
		this.name = 'NetworkError';
	}
}

export class RateLimitError extends Error {
	retryAfter: number | null;

	constructor(message: string, retryAfter: number | null = null) {
		super(message);
		this.name = 'RateLimitError';
		this.retryAfter = retryAfter;
	}
}

export async function handleApiError(response: Response): Promise<never> {
	// SECURITY: Handle 401 errors globally - token expired or invalid
	if (response.status === 401) {
		clearToken();
		clearCurrentUser();
		// Redirect to signin page
		if (typeof window !== 'undefined') {
			window.location.href = '/signin?expired=true';
		}
	}

	let errorData: ApiError;

	try {
		errorData = await response.json();
	} catch {
		errorData = {
			error: 'Request failed',
			detail: response.statusText || `HTTP ${response.status}`,
			recoverable: false
		};
	}

	// Handle rate limit errors specifically (HTTP 429)
	if (response.status === 429) {
		const retryAfter = errorData.retry_after || null;
		const message = errorData.detail || errorData.message || 'Rate limit exceeded. Please try again later.';
		throw new RateLimitError(message, retryAfter);
	}

	// Handle FastAPI validation errors where detail is an array
	let errorMessage: string;
	if (Array.isArray(errorData.detail)) {
		// FastAPI validation error format: detail: [{loc: [...], msg: "...", type: "..."}]
		errorMessage = errorData.detail
			.map((e: any) => e.msg || JSON.stringify(e))
			.join(', ');
	} else {
		errorMessage = errorData.detail || errorData.error || errorData.message || 'An error occurred';
	}

	const error = new Error(errorMessage) as Error & ApiError;
	error.name = 'ApiError';
	Object.assign(error, errorData);

	throw error;
}

export function isNetworkError(error: any): boolean {
	return error instanceof TypeError || error.name === 'NetworkError' || error.message === 'Failed to fetch';
}

export function isRateLimitError(error: any): boolean {
	return error instanceof RateLimitError || error.name === 'RateLimitError';
}

export function getErrorMessage(error: any): string {
	if (isNetworkError(error)) {
		return 'Network error. Please check your internet connection.';
	}

	if (isRateLimitError(error)) {
		if (error.retryAfter) {
			return `Rate limit exceeded. Please try again in ${error.retryAfter} seconds.`;
		}
		return error.message || 'Rate limit exceeded. Please try again later.';
	}

	if (error.detail) return error.detail;
	if (error.message) return error.message;
	return 'An unexpected error occurred';
}

export interface ImageData {
	webp_url: string;
	jpeg_url: string;
}

export interface Report {
	id: string;
	username: string;  // Changed from user_id to username
	title: string;
	description?: string;
	location: string;
	latitude?: number;  // Coordinates for map display
	longitude?: number;
	image_urls?: string[];  // Deprecated: backward compatibility
	image_data?: ImageData[];  // New: optimized WebP + JPEG
	status: string;
	category: string;
	severity: number;
	upvote_count: number;
	has_upvoted: boolean;  // Whether current user has upvoted
	submitted_by?: string;
	officer_username?: string;
	user_badges?: string[];
	comments_count: number;
	created_at: string;
	timeline?: TimelineEvent[];
	admin_note?: string;
	flag_reason?: string;  // Reason for rejection or flagging
	address?: string; // Human readable address
	ai_analysis?: {
		is_valid: boolean;
		category: string;
		severity: number;
		description: string;
	};
}

export interface TimelineEvent {
	event: string;
	timestamp: string;
	details: string;
}

export interface Comment {
	id: string;  // Comment ID for deletion
	username: string;  // Changed from user_id to username
	user_id?: string;  // Backwards compatibility
	text: string;
	created_at: string;
}

export interface User {
	username: string;  // Add username field
	email?: string;
	phone?: string;
	role: string;
	lat?: number;
	lng?: number;
	city?: string;
	state?: string;
	country?: string;
}

export interface Alert {
	location: string;
	count: number;
	categories: string;
	status: string;
}

export interface Landmark {
	name: string;
	type: string;
	distance_m: number;
	distance_text: string;
}

// Auth helpers
export function getToken(): string | null {
	if (typeof window === 'undefined') return null;
	return localStorage.getItem('auth_token');
}

export function setToken(token: string) {
	localStorage.setItem('auth_token', token);
}

export function clearToken() {
	localStorage.removeItem('auth_token');
}

export function getCurrentUser(): User | null {
	if (typeof window === 'undefined') return null;
	const user = localStorage.getItem('current_user');
	return user ? JSON.parse(user) : null;
}

export function setCurrentUser(user: User) {
	localStorage.setItem('current_user', JSON.stringify(user));
}

export function clearCurrentUser() {
	localStorage.removeItem('current_user');
}

// API functions
export async function register(
	username: string,
	email?: string,
	phone?: string,
	password?: string,
	lat?: number,
	lng?: number,
	address?: string
): Promise<User> {
	try {
		const res = await fetch(`${API_BASE_URL}/auth/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				username,
				email: email || null,
				phone: phone || null,
				password: password || null,
				lat,
				lng,
				location_address: address
			})
		});
		if (!res.ok) return handleApiError(res);
		return res.json();
	} catch (error) {
		if (isNetworkError(error)) throw new NetworkError('Failed to connect to server');
		throw error;
	}
}

export async function login(identifier: string, password: string): Promise<{ access_token: string; token_type: string }> {
	try {
		const formData = new URLSearchParams();
		formData.append('username', identifier);
		formData.append('password', password);

		const res = await fetch(`${API_BASE_URL}/auth/token`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
			body: formData
		});
		if (!res.ok) return handleApiError(res);
		const data = await res.json();

		// Save token to localStorage
		if (data.access_token) {
			setToken(data.access_token);
		}

		return data;
	} catch (error) {
		if (isNetworkError(error)) throw new NetworkError('Failed to connect to server');
		throw error;
	}
}

export async function getMe(): Promise<User> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/auth/me`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Unauthorized');
	return res.json();
}

export async function createReport(
	files: File[],
	location: string,
	username: string | undefined,
	title: string,
	description?: string
): Promise<{ report_id: string; status: string }> {
	try {
		const formData = new FormData();
		files.forEach(file => formData.append('files', file));
		formData.append('location', location);
		if (username) formData.append('username', username);
		formData.append('title', title);
		if (description) formData.append('description', description);

		// Add auth header if user is authenticated
		const token = getToken();
		const headers: HeadersInit = {};
		if (token) {
			headers['Authorization'] = `Bearer ${token}`;
		}

		const res = await fetch(`${API_BASE_URL}/report`, {
			method: 'POST',
			headers,
			body: formData
		});
		if (!res.ok) return handleApiError(res);
		return res.json();
	} catch (error) {
		if (isNetworkError(error)) throw new NetworkError('Failed to connect to server');
		throw error;
	}
}

export async function getReports(
	geohash?: string,
	startAfterId?: string,
	limit: number = 10,
	districtFilter?: DistrictFilter
): Promise<Report[]> {
	const params = new URLSearchParams();
	if (geohash) params.append('geohash', geohash);
	if (startAfterId) params.append('start_after_id', startAfterId);

	// District filtering - pass all available params for robustness
	if (districtFilter) {
		if (districtFilter.districtCode) {
			params.append('district_code', districtFilter.districtCode.toString());
		}
		if (districtFilter.districtName) {
			params.append('district', districtFilter.districtName);
		}
		if (districtFilter.stateName) {
			params.append('state', districtFilter.stateName);
		}
	}

	params.append('limit', limit.toString());

	const cacheKey = `reports:${params.toString()}`;
	return deduplicatedFetch(cacheKey, async () => {
		const res = await fetch(`${API_BASE_URL}/reports?${params}`);
		if (!res.ok) throw new Error('Failed to fetch reports');
		return res.json();
	});
}

export async function getReport(reportId: string): Promise<Report> {
	const cacheKey = `report:${reportId}`;
	return deduplicatedFetch(cacheKey, async () => {
		const res = await fetch(`${API_BASE_URL}/report/${reportId}`);
		if (!res.ok) throw new Error('Report not found');
		return res.json();
	});
}

export async function upvoteReport(reportId: string): Promise<{ count: number; status: string }> {
	// SECURITY FIX: Username extracted from JWT token by backend
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Please sign in to upvote.');
	}

	const res = await fetch(`${API_BASE_URL}/report/${reportId}/upvote`, {
		method: 'POST',
		headers: {
			'Authorization': `Bearer ${token}`
		}
		// No body needed - username extracted from token
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function addComment(reportId: string, text: string): Promise<Comment> {
	// SECURITY FIX: Username extracted from JWT token by backend
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Please sign in to comment.');
	}

	const formData = new FormData();
	formData.append('text', text);
	// No username needed - extracted from token

	const res = await fetch(`${API_BASE_URL}/report/${reportId}/comment`, {
		method: 'POST',
		headers: {
			'Authorization': `Bearer ${token}`
		},
		body: formData
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

// Flag and Moderation
export interface Flag {
	id: string;
	report_id: string;
	user_id: string;
	flag_type: string;
	reason?: string;
	image_url?: string;
	status: string;
	created_at: string;
	report_title?: string;
	report_category?: string;
}

export interface ReportUpdate {
	id: string;
	report_id: string;
	author_id: string;
	author_username?: string;
	author_role?: string;
	author_is_verified?: boolean;
	content: string;
	status: 'public' | 'internal';
	media_urls: string[];
	is_official: boolean;
	created_at: string;
}

export async function createReportUpdate(reportId: string, content: string, status: 'public' | 'internal' = 'public', isOfficial: boolean = false): Promise<ReportUpdate> {
	return api.postJson<ReportUpdate>(`/reports/${reportId}/updates`, { content, status, is_official: isOfficial });
}

export async function getReportUpdates(reportId: string): Promise<ReportUpdate[]> {
	// Use deduplicated fetch if needed, but updates might be fresh
	return api.getJson<ReportUpdate[]>(`/reports/${reportId}/updates`);
}

export async function getPendingFlags(limit: number = 50, offset: number = 0): Promise<{ flags: Flag[], total: number }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/flags?limit=${limit}&offset=${offset}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch flags');
	return res.json();
}

export async function reviewFlag(flagId: string, status: string, admin_note?: string): Promise<Flag> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/flags/${flagId}`, {
		method: 'PUT',
		headers: {
			'Authorization': `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ status, admin_note })
	});
	if (!res.ok) throw new Error('Failed to review flag');
	return res.json();
}

export async function getComments(reportId: string): Promise<Comment[]> {
	const cacheKey = `comments:${reportId}`;
	return deduplicatedFetch(cacheKey, async () => {
		const res = await fetch(`${API_BASE_URL}/report/${reportId}/comments`);
		if (!res.ok) throw new Error('Failed to fetch comments');
		return res.json();
	});
}

export async function updateReport(
	reportId: string,
	title?: string,
	description?: string
): Promise<{ message: string; report_id: string }> {
	// SECURITY FIX: Username extracted from JWT token by backend
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Please sign in to edit reports.');
	}

	const formData = new FormData();
	if (title) formData.append('title', title);
	if (description) formData.append('description', description);
	// No username needed - extracted from token

	const res = await fetch(`${API_BASE_URL}/report/${reportId}`, {
		method: 'PUT',
		headers: {
			'Authorization': `Bearer ${token}`
		},
		body: formData
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function deleteReport(reportId: string): Promise<{ message: string }> {
	// SECURITY FIX: Username extracted from JWT token by backend
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Please sign in to delete reports.');
	}

	const res = await fetch(`${API_BASE_URL}/report/${reportId}`, {
		method: 'DELETE',
		headers: {
			'Authorization': `Bearer ${token}`
		}
		// No body needed - username extracted from token
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export interface DistrictFilter {
	districtCode?: number;
	districtName?: string;
	stateName?: string;
}

export async function getAlerts(filter?: DistrictFilter): Promise<any[]> {
	// Deduplicate with longer TTL since alerts are cached server-side for 5 minutes
	const cacheKey = filter?.districtCode
		? `alerts-${filter.districtCode}`
		: filter?.districtName
			? `alerts-${filter.districtName}`
			: 'alerts';

	return deduplicatedFetch(cacheKey, async () => {
		const url = new URL(`${API_BASE_URL}/public/alerts`);

		if (filter) {
			// Pass district_code (preferred) AND text fallback for robustness
			if (filter.districtCode) {
				url.searchParams.set('district_code', filter.districtCode.toString());
			}
			if (filter.districtName) {
				url.searchParams.set('district', filter.districtName);
			}
			if (filter.stateName) {
				url.searchParams.set('state', filter.stateName);
			}
		}

		const res = await fetch(url.toString());
		if (!res.ok) throw new Error('Failed to fetch alerts');
		return res.json();
	}, 5000); // 5 second dedup window for alerts
}

export interface GeocodingAddress {
	city?: string;
	town?: string;
	village?: string;
	municipality?: string;
	county?: string;
	state?: string;
	country?: string;
	postcode?: string;
	road?: string;
	suburb?: string;
	[key: string]: string | undefined;
}

export interface GeocodingResult {
	display_name: string;
	lat: number;
	lng: number;
	address?: GeocodingAddress;
}

export async function geocodeAddress(query: string): Promise<GeocodingResult[]> {
	const res = await fetch(`${API_BASE_URL}/geocode?q=${encodeURIComponent(query)}`);
	if (!res.ok) throw new Error('Geocoding failed');
	return res.json();
}

// Alias for convenience
export const geocode = geocodeAddress;

export async function reverseGeocode(lat: number, lng: number): Promise<string> {
	const res = await fetch(`${API_BASE_URL}/reverse-geocode?lat=${lat}&lng=${lng}`);
	if (!res.ok) throw new Error('Reverse geocoding failed');
	const data = await res.json();
	return data.address;
}

export interface ReverseGeocodeDetailedResult {
	display_name: string;
	address: {
		city?: string;
		state?: string;
		country?: string;
		postcode?: string;
		road?: string;
		suburb?: string;
	};
}

export async function reverseGeocodeDetailed(lat: number, lng: number): Promise<ReverseGeocodeDetailedResult> {
	const res = await fetch(`${API_BASE_URL}/reverse-geocode-detailed?lat=${lat}&lng=${lng}`);
	if (!res.ok) throw new Error('Reverse geocoding failed');
	return res.json();
}

export async function getNearbyLandmarks(reportId: string): Promise<{ landmarks: Landmark[] }> {
	const cacheKey = `landmarks:${reportId}`;
	return deduplicatedFetch(cacheKey, async () => {
		const res = await fetch(`${API_BASE_URL}/report/${reportId}/nearby-landmarks`);
		if (!res.ok) throw new Error('Failed to fetch nearby landmarks');
		return res.json();
	});
}

// Get base URL for API
const getBaseUrl = () => {
	return import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
};

// Generic API wrapper for authenticated requests
export const api = {
	async get(url: string) {
		const token = getToken();
		const res = await fetch(`${getBaseUrl()}${url}`, {
			headers: token ? { 'Authorization': `Bearer ${token}` } : {}
		});
		if (!res.ok) return handleApiError(res);
		return res;
	},

	async post(url: string, body: any) {
		const token = getToken();
		const res = await fetch(`${getBaseUrl()}${url}`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token ? { 'Authorization': `Bearer ${token}` } : {})
			},
			body: JSON.stringify(body)
		});
		if (!res.ok) return handleApiError(res);
		return res;
	},

	async put(url: string, body: any) {
		const token = getToken();
		const res = await fetch(`${getBaseUrl()}${url}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				...(token ? { 'Authorization': `Bearer ${token}` } : {})
			},
			body: JSON.stringify(body)
		});
		if (!res.ok) return handleApiError(res);
		return res;
	},

	async delete(url: string) {
		const token = getToken();
		const res = await fetch(`${getBaseUrl()}${url}`, {
			method: 'DELETE',
			headers: token ? { 'Authorization': `Bearer ${token}` } : {}
		});
		if (!res.ok) return handleApiError(res);
		return res;
	},

	// Helper methods that throw on error - use for cleaner error handling
	async getJson<T>(url: string): Promise<T> {
		const res = await this.get(url);
		if (!res.ok) return handleApiError(res);
		return res.json();
	},

	async postJson<T>(url: string, body: any): Promise<T> {
		const res = await this.post(url, body);
		if (!res.ok) return handleApiError(res);
		return res.json();
	},

	async putJson<T>(url: string, body: any): Promise<T> {
		const res = await this.put(url, body);
		if (!res.ok) return handleApiError(res);
		return res.json();
	},

	async deleteJson<T>(url: string): Promise<T> {
		const res = await this.delete(url);
		if (!res.ok) return handleApiError(res);
		return res.json();
	}
};

// Admin functions
export async function adminLogin(email: string, password: string): Promise<{ token: string; admin: { email: string; role: string } }> {
	const res = await fetch(`${API_BASE_URL}/admin/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	if (!res.ok) throw new Error('Invalid admin credentials');
	return res.json();
}

export async function updateReportStatus(reportId: string, status: string, note?: string, resolutionSummary?: string, resolutionImageUrl?: string): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}/status`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ status, note, resolution_summary: resolutionSummary, resolution_image_url: resolutionImageUrl })
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

// Admin Analytics
export async function getAdminDashboard(): Promise<any> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/analytics/dashboard`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch dashboard');
	return res.json();
}

/**
 * Get reports for admin view - INCLUDES REJECTED and FLAGGED reports
 * Unlike getReports() which filters these out for public view
 */
export async function getAdminReports(filters?: {
	status?: string;
	limit?: number;
	start_after_id?: string;
}): Promise<Report[]> {
	const token = getToken();
	const params = new URLSearchParams();
	if (filters?.status) params.append('status', filters.status);
	if (filters?.limit) params.append('limit', filters.limit.toString());
	if (filters?.start_after_id) params.append('start_after_id', filters.start_after_id);

	const res = await fetch(`${API_BASE_URL}/admin/reports?${params}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch admin reports');
	return res.json();
}

export async function getAuditLogs(filters?: {
	user_id?: string;
	resource_type?: string;
	resource_id?: string;
	action?: string;
	limit?: number;
}): Promise<any> {
	const token = getToken();
	const params = new URLSearchParams();
	if (filters?.user_id) params.append('user_id', filters.user_id);
	if (filters?.resource_type) params.append('resource_type', filters.resource_type);
	if (filters?.resource_id) params.append('resource_id', filters.resource_id);
	if (filters?.action) params.append('action', filters.action);
	if (filters?.limit) params.append('limit', filters.limit.toString());

	const res = await fetch(`${API_BASE_URL}/admin/analytics/audit-logs?${params}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch audit logs');
	return res.json();
}

export async function getReportHistory(reportId: string): Promise<any> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/analytics/report-history/${reportId}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch report history');
	return res.json();
}

export async function listAdmins(): Promise<{ admins: any[] }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/admins`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch admins');
	return res.json();
}

// Municipality Management
export interface Municipality {
	id: string;
	name: string;
	short_code?: string;
	state?: string;
	is_active: boolean;
}

export interface Department {
	id: string;
	name: string;
	municipality_id?: string;
	categories: string[];
	is_active: boolean;
}

export async function getMunicipalities(): Promise<{ municipalities: Municipality[] }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/municipalities`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch municipalities');
	return res.json();
}

export async function getDepartments(municipalityId?: string): Promise<{ departments: Department[] }> {
	const token = getToken();
	const url = municipalityId
		? `${API_BASE_URL}/admin/departments?municipality_id=${municipalityId}`
		: `${API_BASE_URL}/admin/departments`;
	const res = await fetch(url, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch departments');
	return res.json();
}

export async function assignReportToMunicipality(
	reportId: string,
	municipalityId: string,
	departmentId?: string,
	resolutionEta?: string
): Promise<{ success: boolean; message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}/assign`, {
		method: 'PUT',
		headers: {
			'Authorization': `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			municipality_id: municipalityId,
			department_id: departmentId,
			resolution_eta: resolutionEta
		})
	});
	if (!res.ok) throw new Error('Failed to assign report');
	return res.json();
}

export async function updateReportResolution(
	reportId: string,
	resolutionNotes?: string,
	resolutionEta?: string
): Promise<{ success: boolean }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}/resolution`, {
		method: 'PUT',
		headers: {
			'Authorization': `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			resolution_notes: resolutionNotes,
			resolution_eta: resolutionEta
		})
	});
	if (!res.ok) throw new Error('Failed to update resolution');
	return res.json();
}

// Notification API
export interface Notification {
	id: string;
	type: string;
	title: string;
	message?: string;
	data?: Record<string, any>;
	read: boolean;
	read_at?: string;
	created_at: string;
}

export async function getNotifications(unreadOnly = false): Promise<{ notifications: Notification[]; unread_count: number }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/notifications?unread_only=${unreadOnly}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch notifications');
	return res.json();
}

export async function getUnreadNotificationCount(): Promise<{ unread_count: number }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/notifications/count`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch notification count');
	return res.json();
}

export async function markNotificationRead(notificationId: string): Promise<{ success: boolean }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
		method: 'PUT',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to mark notification read');
	return res.json();
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/notifications/read-all`, {
		method: 'PUT',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to mark all notifications read');
	return res.json();
}

export async function deleteComment(reportId: string, commentId: string): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}/comment/${commentId}`, {
		method: 'DELETE',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to delete comment');
	return res.json();
}

export async function deleteReportAdmin(reportId: string): Promise<{ message: string }> {
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Admin access needed.');
	}

	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}`, {
		method: 'DELETE',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function updateReportCategory(reportId: string, category: string): Promise<{ message: string }> {
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Admin access needed.');
	}

	const res = await fetch(`${API_BASE_URL}/admin/report/${reportId}/category`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ category })
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function createAdmin(email: string, password: string, role: string = 'moderator'): Promise<{ message: string; admin: any }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/create-admin`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ email, password, role })
	});
	if (!res.ok) throw new Error('Failed to create admin');
	return res.json();
}

export async function updateAdminStatus(adminEmail: string, isActive: boolean): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/admin/manage/${adminEmail}/status`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ is_active: isActive })
	});
	if (!res.ok) throw new Error('Failed to update admin status');
	return res.json();
}

export async function deleteAccount(): Promise<{ message: string }> {
	const token = getToken();
	if (!token) {
		throw new Error('Authentication required. Please sign in.');
	}

	const res = await fetch(`${API_BASE_URL}/users/me/account`, {
		method: 'DELETE',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}


// ============================================================================
// MUNICIPALITY DASHBOARD APIs
// ============================================================================

export interface MunicipalityStats {
	total_reports: number;
	pending_reports: number;
	resolved_reports: number;
	avg_resolution_time_hours: number;
	active_alerts: number;
	reports_by_category: Record<string, number>;
	reports_by_status: Record<string, number>;
}

export interface BroadcastAlert {
	id: string;
	title: string;
	description?: string;
	category: string;
	severity: string;
	geohash?: string;
	latitude?: number;
	longitude?: number;
	radius_meters: number;
	status: string;
	source: string;
	author_id?: string;
	created_at: string;
	expires_at?: string;
	resolved_at?: string;
	sent_count?: number;
	delivery_count?: number;
	read_count?: number;
}

export interface AlertCreate {
	title: string;
	description?: string;
	category: string;
	severity?: string;
	geohash?: string;
	latitude?: number;
	longitude?: number;
	radius_meters?: number;
	expires_in_hours?: number;
}

export interface AlertPreferences {
	user_id?: string;
	enabled: boolean;
	categories: string[];
	severity_threshold: string;
	notify_in_app: boolean;
	notify_whatsapp: boolean;
	subscription_radius_km: number;
	home_geohash?: string;
	work_geohash?: string;
	configured?: boolean;
}

export async function getMunicipalityDashboard(): Promise<MunicipalityStats> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/dashboard`, {
		headers: token ? { 'Authorization': `Bearer ${token}` } : {}
	});
	if (!res.ok) throw new Error('Failed to fetch dashboard');
	return res.json();
}

export async function getMunicipalityReports(filters?: {
	status?: string;
	category?: string;
	geohash?: string;
	limit?: number;
	offset?: number;
}): Promise<{ reports: Report[]; count: number }> {
	const token = getToken();
	const params = new URLSearchParams();
	if (filters?.status) params.append('status', filters.status);
	if (filters?.category) params.append('category', filters.category);
	if (filters?.geohash) params.append('geohash', filters.geohash);
	if (filters?.limit) params.append('limit', filters.limit.toString());
	if (filters?.offset) params.append('offset', filters.offset.toString());

	const res = await fetch(`${API_BASE_URL}/municipality/reports?${params}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch reports');
	return res.json();
}

// Note: updateReportStatus is defined in the Admin API section above (line ~685)

export async function updateReportStatusMuni(
	reportId: string,
	status: string,
	note?: string
): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/report/${reportId}/status`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ status, note })
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function assignReport(
	reportId: string,
	department: string,
	note?: string
): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/report/${reportId}/assign`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify({ department, assigned_note: note })
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function getMunicipalityAlerts(status: string = 'ACTIVE'): Promise<{ alerts: BroadcastAlert[]; count: number }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/alerts?status=${status}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch alerts');
	return res.json();
}

export async function createBroadcast(alert: AlertCreate): Promise<{ id: string; status: string; data: BroadcastAlert }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/alert`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify(alert)
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function updateBroadcast(alertId: string, updates: Partial<AlertCreate>): Promise<{ message: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/alert/${alertId}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify(updates)
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function endBroadcast(alertId: string): Promise<{ status: string; id: string }> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/alert/${alertId}/end`, {
		method: 'POST',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function getMunicipalityAnalytics(period: string = '7d'): Promise<any> {
	const token = getToken();
	const res = await fetch(`${API_BASE_URL}/municipality/analytics?period=${period}`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch analytics');
	return res.json();
}


// ============================================================================
// PUBLIC ALERT APIs (for citizens)
// ============================================================================

export async function getPublicAlerts(filters?: {
	geohash?: string;
	category?: string;
	limit?: number;
}): Promise<{ alerts: BroadcastAlert[]; count: number }> {
	const params = new URLSearchParams();
	if (filters?.geohash) params.append('geohash', filters.geohash);
	if (filters?.category) params.append('category', filters.category);
	if (filters?.limit) params.append('limit', filters.limit.toString());

	const res = await fetch(`${API_BASE_URL}/alerts?${params}`);
	if (!res.ok) throw new Error('Failed to fetch alerts');
	return res.json();
}

export async function getPublicAlertById(alertId: string): Promise<BroadcastAlert> {
	const res = await fetch(`${API_BASE_URL}/alerts/${alertId}`);
	if (!res.ok) throw new Error('Alert not found');
	return res.json();
}

export async function getAlertsInMyArea(): Promise<{ alerts: BroadcastAlert[]; count: number; location_found: boolean }> {
	const token = getToken();
	if (!token) throw new Error('Authentication required');

	const res = await fetch(`${API_BASE_URL}/alerts/my-area`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch alerts');
	return res.json();
}

export async function getAlertPreferences(): Promise<AlertPreferences> {
	const token = getToken();
	if (!token) throw new Error('Authentication required');

	const res = await fetch(`${API_BASE_URL}/user/alert-preferences`, {
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) throw new Error('Failed to fetch preferences');
	return res.json();
}

export async function updateAlertPreferences(preferences: Partial<AlertPreferences>): Promise<{ message: string; subscription: AlertPreferences }> {
	const token = getToken();
	if (!token) throw new Error('Authentication required');

	const res = await fetch(`${API_BASE_URL}/user/alert-preferences`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify(preferences)
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function subscribeToAlerts(preferences: Partial<AlertPreferences>): Promise<{ message: string }> {
	const token = getToken();
	if (!token) throw new Error('Authentication required');

	const res = await fetch(`${API_BASE_URL}/alerts/subscribe`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${token}`
		},
		body: JSON.stringify(preferences)
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function unsubscribeFromAlerts(): Promise<{ message: string }> {
	const token = getToken();
	if (!token) throw new Error('Authentication required');

	const res = await fetch(`${API_BASE_URL}/alerts/unsubscribe`, {
		method: 'POST',
		headers: { 'Authorization': `Bearer ${token}` }
	});
	if (!res.ok) return handleApiError(res);
	return res.json();
}

export async function markAlertRead(alertId: string): Promise<void> {
	const token = getToken();
	if (!token) return;

	try {
		await fetch(`${API_BASE_URL}/alerts/${alertId}/mark-read`, {
			method: 'POST',
			headers: { 'Authorization': `Bearer ${token}` }
		});
	} catch (error) {
		console.error("Failed to mark alert as read", error);
	}
}

// Cities & Location
export interface City {
	id: string;
	name: string;
	state: string;
	country: string;
	latitude: number;
	longitude: number;
	radius_km: number;
	is_active: boolean;
}

export async function getCities(): Promise<City[]> {
	const res = await fetch(`${API_BASE_URL}/cities`);
	if (!res.ok) throw new Error('Failed to fetch cities');
	return res.json();
}

export async function getNearestCity(lat: number, lng: number): Promise<{ found: boolean; city?: City; message?: string }> {
	const res = await fetch(`${API_BASE_URL}/cities/nearest?lat=${lat}&lng=${lng}`);
	if (!res.ok) throw new Error('Failed to find nearest city');
	return res.json();
}

export async function getCity(cityId: string): Promise<City> {
	const res = await fetch(`${API_BASE_URL}/cities/${cityId}`);
	if (!res.ok) throw new Error('Failed to fetch city');
	return res.json();
}
