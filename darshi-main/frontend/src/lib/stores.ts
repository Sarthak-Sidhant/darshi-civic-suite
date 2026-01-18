import { writable } from 'svelte/store';
import type { User, City } from './api';

// Auth store
export const user = writable<User | null>(null);
export const isAuthenticated = writable(false);

// Location store
export const userLocation = writable<{ lat: number; lng: number } | null>(null);
export const currentCity = writable<City | null>(null);

// Initialize from localStorage
if (typeof window !== 'undefined') {
	const storedUser = localStorage.getItem('current_user');
	if (storedUser) {
		user.set(JSON.parse(storedUser));
		isAuthenticated.set(true);
	}

	const storedCity = localStorage.getItem('current_city');
	if (storedCity) {
		currentCity.set(JSON.parse(storedCity));
	}

	// Persist city changes
	currentCity.subscribe(value => {
		if (value) localStorage.setItem('current_city', JSON.stringify(value));
		else localStorage.removeItem('current_city');
	});
}
