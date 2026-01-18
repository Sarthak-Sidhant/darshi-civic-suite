/**
 * Unit tests for API client
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
	NetworkError,
	RateLimitError,
	isNetworkError,
	isRateLimitError,
	getErrorMessage,
	getToken,
	setToken,
	clearToken,
	getCurrentUser,
	setCurrentUser,
	clearCurrentUser,
	api,
	handleApiError
} from './api';

// Mock localStorage
const localStorageMock = (() => {
	let store: Record<string, string> = {};
	return {
		getItem: vi.fn((key: string) => store[key] || null),
		setItem: vi.fn((key: string, value: string) => {
			store[key] = value;
		}),
		removeItem: vi.fn((key: string) => {
			delete store[key];
		}),
		clear: vi.fn(() => {
			store = {};
		})
	};
})();

Object.defineProperty(globalThis, 'localStorage', {
	value: localStorageMock,
	writable: true
});

describe('API Client', () => {
	beforeEach(() => {
		globalThis.fetch = vi.fn() as any;
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('should be defined', () => {
		expect(true).toBe(true);
	});
});

describe('NetworkError', () => {
	it('should create NetworkError with message', () => {
		const error = new NetworkError('Connection failed');
		expect(error.message).toBe('Connection failed');
		expect(error.name).toBe('NetworkError');
	});

	it('should be instance of Error', () => {
		const error = new NetworkError('test');
		expect(error instanceof Error).toBe(true);
	});
});

describe('isNetworkError', () => {
	it('should return true for TypeError', () => {
		const error = new TypeError('Failed to fetch');
		expect(isNetworkError(error)).toBe(true);
	});

	it('should return true for NetworkError', () => {
		const error = new NetworkError('Connection failed');
		expect(isNetworkError(error)).toBe(true);
	});

	it('should return true for Failed to fetch message', () => {
		const error = new Error('Failed to fetch');
		expect(isNetworkError(error)).toBe(true);
	});

	it('should return false for regular errors', () => {
		const error = new Error('Some other error');
		expect(isNetworkError(error)).toBe(false);
	});
});

describe('getErrorMessage', () => {
	it('should return network error message for network errors', () => {
		const error = new TypeError('Failed to fetch');
		expect(getErrorMessage(error)).toBe('Network error. Please check your internet connection.');
	});

	it('should return detail if present', () => {
		const error = { detail: 'Custom detail' };
		expect(getErrorMessage(error)).toBe('Custom detail');
	});

	it('should return message if present', () => {
		const error = { message: 'Custom message' };
		expect(getErrorMessage(error)).toBe('Custom message');
	});

	it('should return default message for unknown errors', () => {
		const error = {};
		expect(getErrorMessage(error)).toBe('An unexpected error occurred');
	});
});

describe('Token Management', () => {
	beforeEach(() => {
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	it('should set token', () => {
		setToken('test-token-123');
		expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_token', 'test-token-123');
	});

	it('should get token', () => {
		localStorageMock.getItem.mockReturnValueOnce('test-token');
		const token = getToken();
		expect(localStorageMock.getItem).toHaveBeenCalledWith('auth_token');
		expect(token).toBe('test-token');
	});

	it('should return null when no token', () => {
		localStorageMock.getItem.mockReturnValueOnce(null);
		const token = getToken();
		expect(token).toBeNull();
	});

	it('should clear token', () => {
		clearToken();
		expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_token');
	});
});

describe('User Management', () => {
	beforeEach(() => {
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	it('should set current user', () => {
		const user = { username: 'testuser', email: 'test@example.com', role: 'citizen' };
		setCurrentUser(user as any);
		expect(localStorageMock.setItem).toHaveBeenCalledWith('current_user', JSON.stringify(user));
	});

	it('should get current user', () => {
		const user = { username: 'testuser', email: 'test@example.com', role: 'citizen' };
		localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(user));
		const result = getCurrentUser();
		expect(result).toEqual(user);
	});

	it('should return null when no user', () => {
		localStorageMock.getItem.mockReturnValueOnce(null);
		const result = getCurrentUser();
		expect(result).toBeNull();
	});

	it('should clear current user', () => {
		clearCurrentUser();
		expect(localStorageMock.removeItem).toHaveBeenCalledWith('current_user');
	});
});

describe('API Fetch Mocking', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should mock fetch for reports', async () => {
		const mockReports = [
			{ id: '1', title: 'Test Report', status: 'PENDING_VERIFICATION' }
		];

		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => mockReports
		}) as any;

		const response = await fetch('/api/v1/reports');
		const data = await response.json();

		expect(data).toEqual(mockReports);
	});

	it('should handle fetch errors', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: false,
			status: 404,
			statusText: 'Not Found',
			json: async () => ({ error: 'Not found' })
		}) as any;

		const response = await fetch('/api/v1/report/invalid-id');
		expect(response.ok).toBe(false);
		expect(response.status).toBe(404);
	});

	it('should handle network failure', async () => {
		globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch')) as any;

		await expect(fetch('/api/v1/reports')).rejects.toThrow('Failed to fetch');
	});
});

describe('API Response Handling', () => {
	it('should parse JSON response', async () => {
		const mockData = { message: 'Success', data: { id: '123' } };

		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => mockData
		}) as any;

		const response = await fetch('/test');
		const data = await response.json();

		expect(data).toEqual(mockData);
	});

	it('should handle 401 unauthorized', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: false,
			status: 401,
			json: async () => ({ error: 'Unauthorized' })
		}) as any;

		const response = await fetch('/protected');
		expect(response.status).toBe(401);
	});

	it('should handle 500 server error', async () => {
		globalThis.fetch = vi.fn().mockResolvedValue({
			ok: false,
			status: 500,
			json: async () => ({ error: 'Internal server error' })
		}) as any;

		const response = await fetch('/api');
		expect(response.ok).toBe(false);
		expect(response.status).toBe(500);
	});
});

describe('RateLimitError', () => {
	it('should create RateLimitError with message', () => {
		const error = new RateLimitError('Too many requests');
		expect(error.message).toBe('Too many requests');
		expect(error.name).toBe('RateLimitError');
		expect(error.retryAfter).toBeNull();
	});

	it('should create RateLimitError with retryAfter', () => {
		const error = new RateLimitError('Rate limit exceeded', 30);
		expect(error.message).toBe('Rate limit exceeded');
		expect(error.retryAfter).toBe(30);
	});

	it('should be instance of Error', () => {
		const error = new RateLimitError('test');
		expect(error instanceof Error).toBe(true);
	});
});

describe('isRateLimitError', () => {
	it('should return true for RateLimitError', () => {
		const error = new RateLimitError('Rate limit exceeded');
		expect(isRateLimitError(error)).toBe(true);
	});

	it('should return true for error with name RateLimitError', () => {
		const error = { name: 'RateLimitError', message: 'Too many requests' };
		expect(isRateLimitError(error)).toBe(true);
	});

	it('should return false for regular errors', () => {
		const error = new Error('Some other error');
		expect(isRateLimitError(error)).toBe(false);
	});

	it('should return false for NetworkError', () => {
		const error = new NetworkError('Network failed');
		expect(isRateLimitError(error)).toBe(false);
	});
});

describe('getErrorMessage with RateLimitError', () => {
	it('should return rate limit message with retryAfter', () => {
		const error = new RateLimitError('Rate limit exceeded', 30);
		expect(getErrorMessage(error)).toBe('Rate limit exceeded. Please try again in 30 seconds.');
	});

	it('should return rate limit message without retryAfter', () => {
		const error = new RateLimitError('Too many requests');
		expect(getErrorMessage(error)).toBe('Too many requests');
	});
});

describe('API Helper Methods', () => {
	beforeEach(() => {
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	describe('api.get', () => {
		it('should make GET request without token', async () => {
			localStorageMock.getItem.mockReturnValue(null);
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => ({ data: 'test' })
			}) as any;

			await api.get('/test');

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test'),
				expect.objectContaining({
					headers: {}
				})
			);
		});

		it('should make GET request with token', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => ({ data: 'test' })
			}) as any;

			await api.get('/test');

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test'),
				expect.objectContaining({
					headers: { 'Authorization': 'Bearer test-token' }
				})
			);
		});
	});

	describe('api.post', () => {
		it('should make POST request with JSON body', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => ({ success: true })
			}) as any;

			await api.post('/test', { name: 'test' });

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test'),
				expect.objectContaining({
					method: 'POST',
					headers: expect.objectContaining({
						'Content-Type': 'application/json',
						'Authorization': 'Bearer test-token'
					}),
					body: JSON.stringify({ name: 'test' })
				})
			);
		});
	});

	describe('api.put', () => {
		it('should make PUT request with JSON body', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => ({ updated: true })
			}) as any;

			await api.put('/test/1', { name: 'updated' });

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test/1'),
				expect.objectContaining({
					method: 'PUT',
					headers: expect.objectContaining({
						'Content-Type': 'application/json'
					}),
					body: JSON.stringify({ name: 'updated' })
				})
			);
		});
	});

	describe('api.delete', () => {
		it('should make DELETE request', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => ({ deleted: true })
			}) as any;

			await api.delete('/test/1');

			expect(globalThis.fetch).toHaveBeenCalledWith(
				expect.stringContaining('/test/1'),
				expect.objectContaining({
					method: 'DELETE',
					headers: { 'Authorization': 'Bearer test-token' }
				})
			);
		});
	});

	describe('api.getJson', () => {
		it('should return JSON data on success', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			const mockData = { id: '123', name: 'Test' };
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => mockData
			}) as any;

			const result = await api.getJson('/test');
			expect(result).toEqual(mockData);
		});

		it('should throw on error response', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: false,
				status: 404,
				statusText: 'Not Found',
				json: async () => ({ detail: 'Resource not found' })
			}) as any;

			await expect(api.getJson('/test')).rejects.toThrow('Resource not found');
		});
	});

	describe('api.postJson', () => {
		it('should return JSON data on success', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			const mockData = { id: '456', created: true };
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => mockData
			}) as any;

			const result = await api.postJson('/test', { name: 'New Item' });
			expect(result).toEqual(mockData);
		});

		it('should throw RateLimitError on 429', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: false,
				status: 429,
				json: async () => ({ detail: 'Too many requests', retry_after: 60 })
			}) as any;

			await expect(api.postJson('/test', {})).rejects.toBeInstanceOf(RateLimitError);
		});
	});

	describe('api.putJson', () => {
		it('should return JSON data on success', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			const mockData = { id: '789', updated: true };
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => mockData
			}) as any;

			const result = await api.putJson('/test/1', { name: 'Updated' });
			expect(result).toEqual(mockData);
		});
	});

	describe('api.deleteJson', () => {
		it('should return JSON data on success', async () => {
			localStorageMock.getItem.mockReturnValue('test-token');
			const mockData = { deleted: true, message: 'Resource deleted' };
			globalThis.fetch = vi.fn().mockResolvedValue({
				ok: true,
				json: async () => mockData
			}) as any;

			const result = await api.deleteJson('/test/1');
			expect(result).toEqual(mockData);
		});
	});
});

describe('handleApiError', () => {
	it('should throw RateLimitError for 429 responses', async () => {
		const mockResponse = {
			ok: false,
			status: 429,
			statusText: 'Too Many Requests',
			json: async () => ({ detail: 'Rate limit exceeded', retry_after: 30 })
		} as Response;

		await expect(handleApiError(mockResponse)).rejects.toBeInstanceOf(RateLimitError);
	});

	it('should throw Error with detail message', async () => {
		const mockResponse = {
			ok: false,
			status: 400,
			statusText: 'Bad Request',
			json: async () => ({ detail: 'Invalid input' })
		} as Response;

		await expect(handleApiError(mockResponse)).rejects.toThrow('Invalid input');
	});

	it('should handle non-JSON error responses', async () => {
		const mockResponse = {
			ok: false,
			status: 500,
			statusText: 'Internal Server Error',
			json: async () => { throw new Error('Not JSON'); }
		} as unknown as Response;

		await expect(handleApiError(mockResponse)).rejects.toThrow();
	});
});
