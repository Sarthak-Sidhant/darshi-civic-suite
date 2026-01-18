<script lang="ts">
	import { onMount } from 'svelte';
	import { AlertTriangle } from 'lucide-svelte';

	let {
		src,
		imageData,
		alt = '',
		aspectRatio = '16/9',
		class: className = ''
	}: {
		src?: string;
		imageData?: { webp_url: string; jpeg_url: string };
		alt?: string;
		aspectRatio?: string;
		class?: string;
	} = $props();

	let loaded = $state(false);
	let error = $state(false);
	let pictureRef = $state<HTMLPictureElement>();

	// Determine image sources
	const webpUrl = $derived(imageData?.webp_url);
	const jpegUrl = $derived(imageData?.jpeg_url || src);

	onMount(() => {
		if (!pictureRef) return;

		// Use IntersectionObserver for lazy loading
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						const picture = entry.target as HTMLPictureElement;

						// Set srcset for WebP source
						const webpSource = picture.querySelector('source[type="image/webp"]') as HTMLSourceElement;
						if (webpSource && webpUrl) {
							webpSource.srcset = webpUrl;
						}

						// Set src for JPEG img
						const img = picture.querySelector('img') as HTMLImageElement;
						if (img && jpegUrl) {
							img.src = jpegUrl;
						}

						observer.unobserve(picture);
					}
				});
			},
			{
				rootMargin: '50px'
			}
		);

		observer.observe(pictureRef);

		return () => {
			if (pictureRef) observer.unobserve(pictureRef);
		};
	});

	function handleLoad() {
		loaded = true;
	}

	function handleError() {
		error = true;
	}
</script>

<div class="optimized-image {className}" style="aspect-ratio: {aspectRatio}">
	{#if !error}
		<picture bind:this={pictureRef}>
			{#if webpUrl}
				<source type="image/webp" srcset="" />
			{/if}
			<img
				{alt}
				onload={handleLoad}
				onerror={handleError}
				class:loaded
				decoding="async"
			/>
		</picture>
		{#if !loaded}
			<div class="image-placeholder">
				<div class="image-spinner"></div>
			</div>
		{/if}
	{:else}
		<div class="image-error">
			<AlertTriangle size={32} />
			<p>Failed to load image</p>
		</div>
	{/if}
</div>

<style>
	.optimized-image {
		position: relative;
		width: 100%;
		overflow: hidden;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
	}

	picture {
		display: block;
		width: 100%;
		height: 100%;
	}

	img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0;
		transition: opacity 0.3s ease-in-out;
	}

	img.loaded {
		opacity: 1;
	}

	.image-placeholder {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--c-bg-subtle);
	}

	.image-spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--c-border);
		border-top-color: var(--c-brand);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.image-error {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--c-text-secondary);
		font-size: 0.875rem;
	}

	.image-error :global(svg) {
		color: var(--c-warning);
	}

	.image-error p {
		margin: 0;
	}
</style>
