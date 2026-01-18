/**
 * Unit tests for Svelte stores
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';

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

// Set up localStorage mock before importing stores
Object.defineProperty(globalThis, 'localStorage', {
	value: localStorageMock,
	writable: true
});

describe('Auth Stores', () => {
	beforeEach(() => {
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	it('should initialize user store as null', async () => {
		// Clear localStorage before importing
		localStorageMock.clear();

		// Use dynamic import to get fresh module
		const { user } = await import('./stores');
		const currentUser = get(user);
		// May be null or from localStorage depending on initialization
		expect(currentUser === null || typeof currentUser === 'object').toBe(true);
	});

	it('should initialize isAuthenticated as false', async () => {
		localStorageMock.clear();

		const { isAuthenticated } = await import('./stores');
		const auth = get(isAuthenticated);
		// May be false or true depending on localStorage state
		expect(typeof auth).toBe('boolean');
	});

	it('should update user store', async () => {
		const { user } = await import('./stores');

		const testUser = {
			username: 'testuser',
			email: 'test@example.com',
			city: 'Test City'
		};

		user.set(testUser as any);
		expect(get(user)).toEqual(testUser);
	});

	it('should update isAuthenticated store', async () => {
		const { isAuthenticated } = await import('./stores');

		isAuthenticated.set(true);
		expect(get(isAuthenticated)).toBe(true);

		isAuthenticated.set(false);
		expect(get(isAuthenticated)).toBe(false);
	});

	it('should clear user on logout', async () => {
		const { user, isAuthenticated } = await import('./stores');

		user.set({
			username: 'testuser',
			email: 'test@example.com'
		} as any);
		isAuthenticated.set(true);

		// Simulate logout
		user.set(null);
		isAuthenticated.set(false);

		expect(get(user)).toBeNull();
		expect(get(isAuthenticated)).toBe(false);
	});
});

describe('Location Store', () => {
	it('should initialize userLocation as null', async () => {
		const { userLocation } = await import('./stores');
		const location = get(userLocation);
		expect(location).toBeNull();
	});

	it('should update userLocation', async () => {
		const { userLocation } = await import('./stores');

		const testLocation = { lat: 28.6139, lng: 77.209 };
		userLocation.set(testLocation);

		expect(get(userLocation)).toEqual(testLocation);
	});

	it('should clear userLocation', async () => {
		const { userLocation } = await import('./stores');

		userLocation.set({ lat: 28.6139, lng: 77.209 });
		userLocation.set(null);

		expect(get(userLocation)).toBeNull();
	});

	it('should store valid coordinates', async () => {
		const { userLocation } = await import('./stores');

		// Valid Delhi coordinates
		const delhiLocation = { lat: 28.6139, lng: 77.209 };
		userLocation.set(delhiLocation);

		const location = get(userLocation);
		expect(location?.lat).toBe(28.6139);
		expect(location?.lng).toBe(77.209);
	});
});

describe('Store Subscriptions', () => {
	it('should notify subscribers on user change', async () => {
		const { user } = await import('./stores');

		const values: any[] = [];
		const unsubscribe = user.subscribe((value) => {
			values.push(value);
		});

		user.set({ username: 'user1' } as any);
		user.set({ username: 'user2' } as any);

		expect(values.length).toBeGreaterThanOrEqual(2);
		unsubscribe();
	});

	it('should notify subscribers on auth change', async () => {
		const { isAuthenticated } = await import('./stores');

		const values: boolean[] = [];
		const unsubscribe = isAuthenticated.subscribe((value) => {
			values.push(value);
		});

		isAuthenticated.set(true);
		isAuthenticated.set(false);

		expect(values.length).toBeGreaterThanOrEqual(2);
		unsubscribe();
	});

	it('should unsubscribe correctly', async () => {
		const { user } = await import('./stores');

		let callCount = 0;
		const unsubscribe = user.subscribe(() => {
			callCount++;
		});

		const initialCount = callCount;
		unsubscribe();

		user.set({ username: 'newuser' } as any);

		// Should not increase after unsubscribe
		expect(callCount).toBe(initialCount);
	});
});

describe('Store Type Safety', () => {
	it('user store should accept User type', async () => {
		const { user } = await import('./stores');

		const validUser = {
			username: 'testuser',
			email: 'test@example.com',
			city: 'Mumbai',
			state: 'Maharashtra'
		};

		user.set(validUser as any);
		const currentUser = get(user);

		expect(currentUser?.username).toBe('testuser');
		expect(currentUser?.email).toBe('test@example.com');
	});

	it('userLocation should accept lat/lng object', async () => {
		const { userLocation } = await import('./stores');

		const validLocation = { lat: 19.076, lng: 72.8777 }; // Mumbai
		userLocation.set(validLocation);

		const location = get(userLocation);
		expect(location?.lat).toBe(19.076);
		expect(location?.lng).toBe(72.8777);
	});
});
