<script lang="ts">
	type ImageData = {
		webp_url: string;
		jpeg_url: string;
	};

	let {
		images = [],
		imageData = [],
		class: className = ''
	}: {
		images?: string[];
		imageData?: ImageData[];
		class?: string;
	} = $props();

	let currentIndex = $state(0);
	let touchStartX = 0;
	let touchEndX = 0;
	let isDragging = $state(false);
	let imageCache = new Map<string, HTMLImageElement>();

	// Determine which format we're using (backward compatibility)
	const usingImageData = $derived(imageData.length > 0);
	const totalImages = $derived(usingImageData ? imageData.length : images.length);

	// Get current image URLs
	const getCurrentImageUrls = (index: number) => {
		if (usingImageData && imageData[index]) {
			return {
				webp: imageData[index].webp_url,
				jpeg: imageData[index].jpeg_url
			};
		} else if (images[index]) {
			return {
				webp: null,
				jpeg: images[index]
			};
		}
		return { webp: null, jpeg: null };
	};

	// Preload only adjacent images for smoother transitions
	$effect(() => {
		// Preload current and next/prev images only
		const indices = [currentIndex, currentIndex - 1, currentIndex + 1];

		indices.forEach((idx) => {
			if (idx < 0 || idx >= totalImages) return;

			const urls = getCurrentImageUrls(idx);

			// Preload JPEG (all browsers support)
			if (urls.jpeg && !imageCache.has(urls.jpeg)) {
				const img = new Image();
				img.src = urls.jpeg;
				imageCache.set(urls.jpeg, img);
			}

			// Preload WebP if available
			if (urls.webp && !imageCache.has(urls.webp)) {
				const img = new Image();
				img.src = urls.webp;
				imageCache.set(urls.webp, img);
			}
		});
	});

	function goToSlide(index: number) {
		if (index < 0) {
			currentIndex = 0;
		} else if (index >= totalImages) {
			currentIndex = totalImages - 1;
		} else {
			currentIndex = index;
		}
	}

	function handleTouchStart(e: TouchEvent) {
		touchStartX = e.touches[0].clientX;
		isDragging = true;
	}

	function handleTouchEnd(e: TouchEvent) {
		if (!isDragging) return;
		touchEndX = e.changedTouches[0].clientX;
		handleSwipe();
		isDragging = false;
	}

	function handleSwipe() {
		const swipeThreshold = 50;
		const diff = touchStartX - touchEndX;

		if (Math.abs(diff) > swipeThreshold) {
			if (diff > 0) {
				// Swipe left - next image
				goToSlide(currentIndex + 1);
			} else {
				// Swipe right - previous image
				goToSlide(currentIndex - 1);
			}
		}
	}

	function next() {
		goToSlide(currentIndex + 1);
	}

	function prev() {
		goToSlide(currentIndex - 1);
	}
</script>

{#if totalImages > 0}
	{@const currentUrls = getCurrentImageUrls(currentIndex)}
	<div
		class="image-carousel {className}"
		ontouchstart={handleTouchStart}
		ontouchend={handleTouchEnd}
		role="region"
		aria-label="Image carousel"
	>
		<!-- Single Image Display -->
		<div class="carousel-image-container" style="--bg-image: url('{currentUrls.jpeg}');">
			<picture>
				{#if currentUrls.webp}
					<source type="image/webp" srcset={currentUrls.webp} />
				{/if}
				<img
					src={currentUrls.jpeg}
					alt="Image {currentIndex + 1} of {totalImages}"
					loading={currentIndex === 0 ? "eager" : "lazy"}
					decoding="async"
					fetchpriority={currentIndex === 0 ? "high" : "low"}
					style="content-visibility: auto;"
				/>
			</picture>
		</div>

		{#if totalImages > 1}
			<!-- Swipe instruction for mobile -->
			<div class="swipe-hint" aria-hidden="true">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
				Swipe
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>

			<!-- Navigation Dots -->
			<div class="carousel-dots">
				{#each Array(totalImages) as _, i}
					<button
						class="dot"
						class:active={i === currentIndex}
						onclick={(e) => {
							e.stopPropagation();
							goToSlide(i);
						}}
						aria-label="Go to image {i + 1}"
					></button>
				{/each}
			</div>

			<!-- Navigation Arrows -->
			{#if currentIndex > 0}
				<button
					class="carousel-nav prev"
					onclick={(e) => {
						e.stopPropagation();
						prev();
					}}
					aria-label="Previous image"
				>
					‹
				</button>
			{/if}
			{#if currentIndex < totalImages - 1}
				<button
					class="carousel-nav next"
					onclick={(e) => {
						e.stopPropagation();
						next();
					}}
					aria-label="Next image"
				>
					›
				</button>
			{/if}

			<!-- Counter -->
			<div class="carousel-counter">
				{currentIndex + 1} / {totalImages}
			</div>
		{/if}
	</div>
{/if}

<style>
	.image-carousel {
		position: relative;
		width: 100%;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.carousel-image-container {
		position: relative;
		width: 100%;
		height: 500px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--c-bg-page);
		overflow: hidden;
		border-radius: var(--radius-md);
	}

	.carousel-image-container::before {
		content: '';
		position: absolute;
		inset: 0;
		background-image: var(--bg-image);
		background-size: cover;
		background-position: center;
		filter: blur(40px) brightness(0.8);
		transform: scale(1.1);
		z-index: 0;
		transition: background-image 0.3s ease-in-out;
	}

	.carousel-image-container picture {
		display: block;
		width: 100%;
		height: 100%;
		position: relative;
		z-index: 1;
	}

	.carousel-image-container img {
		position: relative;
		width: 100%;
		height: 100%;
		object-fit: contain;
		display: block;
		z-index: 1;
		opacity: 1;
		transition: opacity 0.2s ease-in-out;
		will-change: opacity;
		image-rendering: auto;
	}

	/* Optimize image rendering on mobile for faster loading */
	@media (max-width: 768px) {
		.carousel-image-container img {
			image-rendering: -webkit-optimize-contrast;
		}
	}

	/* Navigation Dots */
	.carousel-dots {
		position: absolute;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(8px);
		border-radius: 99px;
		z-index: 2;
	}

	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.5);
		border: none;
		padding: 0;
		cursor: pointer;
		transition: all 0.2s;
	}

	.dot.active {
		background: white;
		width: 24px;
		border-radius: 4px;
	}

	/* Navigation Arrows */
	.carousel-nav {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(8px);
		color: white;
		border: none;
		font-size: 2rem;
		line-height: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		z-index: 3;
		transition: all 0.2s;
	}

	.carousel-nav.prev {
		left: 1rem;
	}

	.carousel-nav.next {
		right: 1rem;
	}

	.carousel-nav:hover {
		background: rgba(0, 0, 0, 0.8);
		transform: translateY(-50%) scale(1.1);
	}

	.carousel-nav:active {
		transform: translateY(-50%) scale(0.95);
	}

	/* Counter */
	.carousel-counter {
		position: absolute;
		top: 1rem;
		right: 1rem;
		padding: 0.5rem 0.75rem;
		background: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(8px);
		color: white;
		border-radius: 99px;
		font-size: 0.8125rem;
		font-weight: 600;
		z-index: 2;
	}

	/* Swipe Hint */
	.swipe-hint {
		display: none;
		position: absolute;
		bottom: 4rem;
		left: 50%;
		transform: translateX(-50%);
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(8px);
		color: white;
		padding: 0.75rem 1.5rem;
		border-radius: 99px;
		font-size: 0.875rem;
		font-weight: 600;
		z-index: 10;
		pointer-events: none;
		align-items: center;
		gap: 0.5rem;
		animation: fadeInOut 3s ease-in-out;
	}

	@keyframes fadeInOut {
		0%, 100% { opacity: 0; }
		10%, 90% { opacity: 1; }
	}

	/* Responsive adjustments */
	@media (max-width: 1024px) {
		.carousel-image-container {
			height: 450px;
		}
	}

	@media (max-width: 768px) {
		.carousel-image-container {
			height: 400px;
		}

		/* Reduce blur on mobile for better performance */
		.carousel-image-container::before {
			filter: blur(20px) brightness(0.8);
		}

		.carousel-counter {
			font-size: 0.75rem;
			padding: 0.4rem 0.65rem;
		}
	}

	/* Mobile adjustments */
	@media (max-width: 640px) {
		.carousel-nav {
			display: none;
		}

		.swipe-hint {
			display: flex;
		}

		.carousel-image-container {
			height: 350px;
		}

		/* Further reduce blur on smaller screens */
		.carousel-image-container::before {
			filter: blur(10px) brightness(0.8);
		}

		.carousel-counter {
			top: 0.75rem;
			right: 0.75rem;
		}

		.severity-indicator {
			top: 0.75rem;
			right: 0.75rem;
		}
	}

	@media (max-width: 480px) {
		.carousel-image-container {
			height: 300px;
		}

		/* Minimal blur on very small screens for best performance */
		.carousel-image-container::before {
			filter: blur(5px) brightness(0.8);
		}

		.swipe-hint {
			bottom: 3.5rem;
			font-size: 0.8125rem;
			padding: 0.625rem 1.25rem;
		}

		.carousel-dots {
			bottom: 0.75rem;
			padding: 0.375rem 0.75rem;
		}

		.dot {
			width: 6px;
			height: 6px;
		}

		.dot.active {
			width: 20px;
		}
	}

	@media (max-width: 375px) {
		.carousel-image-container {
			height: 280px;
		}

		.carousel-counter {
			font-size: 0.7rem;
			padding: 0.35rem 0.6rem;
		}

		.swipe-hint {
			font-size: 0.75rem;
			padding: 0.5rem 1rem;
		}
	}
</style>
