import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type Theme = 'light' | 'dark';

// Get initial theme from localStorage or system preference
function getInitialTheme(): Theme {
	if (!browser) return 'light';

	const stored = localStorage.getItem('theme');
	if (stored === 'dark' || stored === 'light') {
		return stored as Theme;
	}

	// Check system preference
	if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
		return 'dark';
	}

	return 'light';
}

// Create theme store
const initialTheme = getInitialTheme();
export const theme = writable<Theme>(initialTheme);

// Subscribe to changes and persist to localStorage + update DOM (client-side only)
if (browser) {
	// Apply initial theme immediately
	document.documentElement.setAttribute('data-theme', initialTheme);

	// Subscribe to future changes
	theme.subscribe(currentTheme => {
		localStorage.setItem('theme', currentTheme);
		document.documentElement.setAttribute('data-theme', currentTheme);
	});
}

// Toggle theme function
export function toggleTheme() {
	theme.update(current => current === 'light' ? 'dark' : 'light');
}
