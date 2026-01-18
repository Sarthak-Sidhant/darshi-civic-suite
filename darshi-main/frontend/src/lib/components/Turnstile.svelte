<script lang="ts">
	import { onMount } from 'svelte';

	export let onVerify: (token: string) => void;
	export let onError: () => void = () => {};
	export let onExpire: () => void = () => {};

	let turnstileContainer: HTMLDivElement;
	let widgetId: string | null = null;

	// Cloudflare Turnstile site key (will be set via env)
	const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'; // Test key

	onMount(() => {
		// Load Turnstile script
		const script = document.createElement('script');
		script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
		script.async = true;
		script.defer = true;

		script.onload = () => {
			// Render Turnstile widget
			if (window.turnstile && turnstileContainer) {
				widgetId = window.turnstile.render(turnstileContainer, {
					sitekey: TURNSTILE_SITE_KEY,
					callback: (token: string) => {
						onVerify(token);
					},
					'error-callback': () => {
						onError();
					},
					'expired-callback': () => {
						onExpire();
					},
					theme: 'light',
					size: 'normal'
				});
			}
		};

		document.head.appendChild(script);

		return () => {
			// Cleanup on unmount
			if (widgetId && window.turnstile) {
				window.turnstile.remove(widgetId);
			}
			script.remove();
		};
	});

	// Expose reset method
	export function reset() {
		if (widgetId && window.turnstile) {
			window.turnstile.reset(widgetId);
		}
	}
</script>

<div bind:this={turnstileContainer} class="turnstile-widget"></div>

<style>
	.turnstile-widget {
		display: flex;
		justify-content: center;
		margin: 1rem 0;
	}
</style>
