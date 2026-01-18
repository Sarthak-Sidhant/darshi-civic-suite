<script lang="ts">
	import { onMount } from 'svelte';
	let { children } = $props();

	onMount(() => {
		// Force reflow on mount to fix width calculation
		document.body.style.width = '100vw';
		document.documentElement.style.width = '100vw';
	});
</script>

<!-- Admin pages use full width, no container wrapper -->
{@render children()}

<style>
	:global(html),
	:global(body) {
		margin: 0 !important;
		padding: 0 !important;
		width: 100vw !important;
		overflow-x: hidden !important;
	}

	/* Override parent layout styles */
	:global(.app-shell) {
		display: block !important;
		margin: 0 !important;
		padding: 0 !important;
		width: 100% !important;
	}

	:global(main) {
		margin: 0 !important;
		padding: 0 !important;
		max-width: none !important;
		width: 100% !important;
	}

	:global(.container) {
		max-width: none !important;
		padding: 0 !important;
		margin: 0 !important;
		width: 100% !important;
	}

	:global(.glass-header),
	:global(.mobile-nav) {
		display: none !important;
	}
</style>
