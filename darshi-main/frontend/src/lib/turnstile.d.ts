// Cloudflare Turnstile TypeScript definitions
interface TurnstileOptions {
	sitekey: string;
	callback?: (token: string) => void;
	'error-callback'?: () => void;
	'expired-callback'?: () => void;
	theme?: 'light' | 'dark' | 'auto';
	size?: 'normal' | 'compact';
	tabindex?: number;
	'response-field'?: boolean;
	'response-field-name'?: string;
}

interface Turnstile {
	render(container: string | HTMLElement, options: TurnstileOptions): string;
	reset(widgetId: string): void;
	remove(widgetId: string): void;
	getResponse(widgetId: string): string;
}

interface Window {
	turnstile?: Turnstile;
}
