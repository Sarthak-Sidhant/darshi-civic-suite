<script lang="ts">
	import { onMount } from "svelte";
	import {
		getReports,
		getAlerts,
		geocode,
		type Report,
		type Alert,
	} from "$lib/api";
	import { Search, MapPin, AlertCircle, Clock } from "lucide-svelte";

	import { selectedDistrict } from "$lib/stores/districtStore";

	let mapContainer: HTMLDivElement;
	let map: any;
	let markerClusterGroup: any;
	let L: any; // Cache Leaflet reference
	let reports: Report[] = $state([]);
	let alerts: Alert[] = $state([]);
	let loading = $state(true);
	let mapReady = $state(false);
	let activeLayer = $state<"issues" | "alerts">("issues");
	let selectedCategory = $state<string | null>(null);
	let searchQuery = $state("");
	let searchResults: any[] = $state([]);
	let isSearching = $state(false);

	const categories = [
		"Pothole",
		"Garbage",
		"Streetlight",
		"Water",
		"Drainage",
		"Other",
	];

	// Reload data when district changes
	$effect(() => {
		// Use the store value directly
		const district = $selectedDistrict;
		loadData(district);
	});

	onMount(() => {
		// Start map initialization immediately (non-blocking)
		initializeMap();

		// Handle geolocation in background (non-blocking)
		handleGeolocation();
	});

	async function loadData(district: any = null) {
		loading = true;
		try {
			// Build filter
			const filter = district
				? {
						districtCode: district.districtCode,
						districtName: district.districtName,
						stateName: district.stateName,
					}
				: undefined;

			// Load reports first with limit (priority)
			reports = await getReports(undefined, undefined, 50, filter);
			loading = false; // Show content immediately

			// Load alerts after (non-blocking)
			getAlerts(filter)
				.then((alertsData) => {
					alerts = alertsData;
				})
				.catch(() => {
					// Alerts are optional, don't fail
				});
		} catch (e) {
			loading = false;
		}
	}

	function handleGeolocation() {
		// Non-blocking geolocation request
		if (navigator.geolocation) {
			navigator.geolocation.getCurrentPosition(
				(position) => {
					if (map) {
						map.setView(
							[
								position.coords.latitude,
								position.coords.longitude,
							],
							13,
						);
					}
				},
				() => {
					// Silently fail - map already shows default view
				},
			);
		}
	}

	async function initializeMap() {
		try {
			// Cache Leaflet import at module level (only import once)
			L = (await import("leaflet")).default;
			await import("leaflet/dist/leaflet.css");

			// Import marker cluster plugin - need to import it differently
			try {
				await import("leaflet.markercluster");
				await import("leaflet.markercluster/dist/MarkerCluster.css");
				await import(
					"leaflet.markercluster/dist/MarkerCluster.Default.css"
				);
			} catch (e) {
				// Error handled silently
			}

			// Initialize map centered on India with specific bounds
			// Custom bounds optimized for 16:9 screens
			const indiaBounds: [[number, number], [number, number]] = [
				[4.592917, 44.579417], // Southwest corner
				[39.55325, 114.273], // Northeast corner
			];

			map = L.map(mapContainer, {
				zoomControl: false,
				maxBounds: indiaBounds,
				maxBoundsViscosity: 1.0,
				worldview: "IN",
				// Performance optimizations
				preferCanvas: true,
				renderer: L.canvas({ padding: 0.5 }),
			}).setView([22.5937, 78.9629], 5);

			// Add OpenStreetMap tiles
			L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
				attribution:
					'<a href="https://leafletjs.com" target="_blank">Leaflet</a> | <a href="https://openstreetmap.org/copyright" target="_blank">OSM</a>',
				maxZoom: 19,
				minZoom: 4,
				bounds: indiaBounds,
				crossOrigin: true,
				// Performance: update on move end only
				updateWhenIdle: true,
				keepBuffer: 2,
			}).addTo(map);

			// Add custom zoom control on bottom right
			L.control.zoom({ position: "bottomright" }).addTo(map);

			// Initialize marker cluster group with optimizations
			try {
				if (typeof (L as any).markerClusterGroup === "function") {
					markerClusterGroup = (L as any).markerClusterGroup({
						maxClusterRadius: 80,
						spiderfyOnMaxZoom: true,
						showCoverageOnHover: false,
						zoomToBoundsOnClick: true,
						// Performance optimizations
						disableClusteringAtZoom: 18,
						removeOutsideVisibleBounds: true,
						animate: true,
						animateAddingMarkers: false,
						iconCreateFunction: function (cluster: any) {
							const count = cluster.getChildCount();
							let sizeClass = "small";
							if (count > 20) sizeClass = "large";
							else if (count > 10) sizeClass = "medium";

							return L.divIcon({
								html: `<div class="cluster-icon cluster-${sizeClass}">${count}</div>`,
								className: "marker-cluster-custom",
								iconSize: L.point(40, 40),
							});
						},
					});
					map.addLayer(markerClusterGroup);
				}
			} catch (e) {
				// Error handled silently
			}

			mapReady = true;

			// Lazy-load India boundary AFTER map is interactive
			loadIndiaBoundaryLazy();

			// Render markers when data is ready
			if (reports.length > 0) {
				renderMarkers();
			}
		} catch (error) {
			mapReady = true;
		}
	}

	function loadIndiaBoundaryLazy() {
		// Load boundary in background after map is ready
		setTimeout(async () => {
			try {
				const response = await fetch(
					"/india-boundary-simplified.geojson",
				);
				if (!response.ok) return;

				const indiaGeoJSON = await response.json();

				// Add thin greyish-purple international border style
				L.geoJSON(indiaGeoJSON, {
					style: {
						color: "#887191",
						weight: 3,
						opacity: 0.75,
						fillColor: "transparent",
						dashArray: "2, 3",
					},
				}).addTo(map);
			} catch (error) {
				// Error handled silently
			}
		}, 500); // Load after 500ms delay
	}

	function renderMarkers() {
		if (!map || !L) return;

		// Clear existing markers from cluster group if it exists
		if (markerClusterGroup) {
			markerClusterGroup.clearLayers();
		}

		const dataToShow = activeLayer === "issues" ? reports : [];

		// Batch marker creation for better performance
		const markers: any[] = [];

		dataToShow.forEach((report) => {
			// Use latitude/longitude fields if available, otherwise parse from location string
			let lat: number, lng: number;

			if (report.latitude && report.longitude) {
				lat = report.latitude;
				lng = report.longitude;
			} else if (report.location) {
				// Fallback for old reports with coordinate strings
				try {
					const coords = report.location.split(",").map(Number);
					if (
						coords.length !== 2 ||
						isNaN(coords[0]) ||
						isNaN(coords[1])
					)
						return;
					lat = coords[0];
					lng = coords[1];
				} catch {
					return;
				}
			} else {
				return;
			}

			try {
				// Filter by category if selected
				if (selectedCategory && report.category !== selectedCategory)
					return;

				// Custom marker based on severity
				const color = getSeverityColor(report.severity);
				const icon = L.divIcon({
					className: "custom-marker",
					html: `<div style="background: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"></div>`,
					iconSize: [24, 24],
					iconAnchor: [12, 12],
				});

				const marker = L.marker([lat, lng], { icon });

				// Popup with report info
				marker.bindPopup(`
					<div style="font-family: var(--font-sans); min-width: 200px;">
						<h3 style="margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 700;">${report.title}</h3>
						<p style="margin: 0 0 0.5rem 0; font-size: 0.875rem; color: #6b7280;">${report.category}</p>
						<p style="margin: 0 0 0.75rem 0; font-size: 0.8125rem; color: #4b5563;">
							<span style="display:inline-block; margin-right:4px;">📍</span>
							${report.location || "Location not available"}
						</p>
						${report.description ? `<p style="margin: 0 0 0.75rem 0; font-size: 0.875rem;">${report.description.substring(0, 100)}...</p>` : ""}
						<a href="/report/${report.id}" style="display: inline-block; padding: 0.5rem 1rem; background: black; color: white; text-decoration: none; border-radius: 6px; font-size: 0.875rem; font-weight: 600;">View Details</a>
					</div>
				`);

				markers.push(marker);
			} catch (e) {
				// Error handled silently
			}
		});

		// Add all markers at once for better performance
		if (markerClusterGroup) {
			markerClusterGroup.addLayers(markers);
		} else {
			markers.forEach((marker) => marker.addTo(map));
		}
	}

	// Watch for data changes and re-render markers
	$effect(() => {
		if (mapReady && reports.length > 0) {
			renderMarkers();
		}
	});

	function getSeverityColor(severity: number): string {
		if (severity >= 8) return "#dc2626";
		if (severity >= 6) return "#ea580c";
		if (severity >= 4) return "#ca8a04";
		return "#16a34a";
	}

	function toggleLayer(layer: "issues" | "alerts") {
		activeLayer = layer;
		// Use cached Leaflet reference
		if (map && L) {
			renderMarkers();
		}
	}

	function filterByCategory(category: string | null) {
		selectedCategory = category;
		// Use cached Leaflet reference
		if (map && L) {
			renderMarkers();
		}
	}

	async function searchLocation() {
		if (!searchQuery.trim()) return;

		isSearching = true;
		searchResults = [];

		try {
			const results = await geocode(searchQuery);
			searchResults = results;
		} catch (e) {
			// Search failed silently
		} finally {
			isSearching = false;
		}
	}

	function selectSearchResult(result: any) {
		// Handle both lat/lon and lat/lng formats
		const latitude = result.lat || result.latitude;
		const longitude = result.lon || result.lng || result.longitude;

		if (map && latitude && longitude) {
			const lat = parseFloat(latitude);
			const lon = parseFloat(longitude);

			// Zoom in more for accurate location (16-17 is street level)
			map.setView([lat, lon], 17);

			searchResults = [];
			searchQuery = "";
		}
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === "Enter") {
			searchLocation();
		}
	}
</script>

<svelte:head>
	<title>Map View - Darshi</title>
</svelte:head>

<div class="map-view">
	<!-- Map Container -->
	<div bind:this={mapContainer} class="map-container"></div>

	<!-- Controls Overlay -->
	<div class="map-controls">
		<!-- Search Box -->
		<div class="search-container">
			<div class="search-box">
				<input
					type="text"
					bind:value={searchQuery}
					onkeydown={handleSearchKeydown}
					placeholder="Search location or pincode..."
					class="search-input"
				/>
				<button
					onclick={searchLocation}
					class="search-btn"
					disabled={isSearching}
				>
					{#if isSearching}
						<Clock size={18} />
					{:else}
						<Search size={18} />
					{/if}
				</button>
			</div>
			{#if searchResults.length > 0}
				<div class="search-results">
					{#each searchResults as result}
						<button
							onclick={() => selectSearchResult(result)}
							class="search-result-item"
						>
							<div class="search-result-name">
								{result.display_name || result.name}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Layer Toggle -->
		<div class="control-group">
			<button
				class="control-btn"
				class:active={activeLayer === "issues"}
				onclick={() => toggleLayer("issues")}
			>
				<MapPin size={16} /> Issues
			</button>
			<button
				class="control-btn"
				class:active={activeLayer === "alerts"}
				onclick={() => toggleLayer("alerts")}
			>
				<AlertCircle size={16} /> Alerts
			</button>
		</div>

		<!-- Category Filter -->
		<div class="control-group categories">
			<button
				class="category-chip"
				class:active={selectedCategory === null}
				onclick={() => filterByCategory(null)}
			>
				All
			</button>
			{#each categories as category}
				<button
					class="category-chip"
					class:active={selectedCategory === category}
					onclick={() => filterByCategory(category)}
				>
					{category}
				</button>
			{/each}
		</div>

		<!-- Stats -->
		<div class="stats-card">
			<div class="stat">
				<span class="stat-value">{reports.length}</span>
				<span class="stat-label">Total Reports</span>
			</div>
			<div class="stat">
				<span class="stat-value">{alerts.length}</span>
				<span class="stat-label">Active Alerts</span>
			</div>
		</div>
	</div>

	<!-- Loading Overlay with Skeleton -->
	{#if loading && !mapReady}
		<div class="loading-overlay">
			<div class="loading-skeleton">
				<div class="sk-controls">
					<div class="sk-search"></div>
					<div class="sk-buttons"></div>
					<div class="sk-categories"></div>
					<div class="sk-stats"></div>
				</div>
				<div class="spinner"></div>
				<p>Loading map...</p>
			</div>
		</div>
	{:else if loading && mapReady}
		<div class="data-loading-indicator">
			<div class="mini-spinner"></div>
			<span>Loading reports...</span>
		</div>
	{/if}
</div>

<style>
	.map-view {
		position: fixed;
		top: var(--header-height);
		left: 0;
		right: 0;
		bottom: 0;
		background: var(--c-bg-page);
	}

	.map-container {
		width: 100%;
		height: 100%;
	}

	/* Map Controls */
	.map-controls {
		position: absolute;
		top: 1rem;
		left: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		z-index: 1000;
		pointer-events: none;
		will-change: transform;
	}

	.map-controls > * {
		pointer-events: auto;
		transition:
			transform 0.2s ease,
			opacity 0.2s ease;
		will-change: transform, opacity;
	}

	.map-controls > *:active {
		transform: scale(0.98);
	}

	/* Search Container */
	.search-container {
		position: relative;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(12px);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
		overflow: visible;
		z-index: 1100;
	}

	.search-box {
		display: flex;
		gap: 0.5rem;
		padding: 0.5rem;
	}

	.search-input {
		flex: 1;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-family: var(--font-sans);
		font-size: 0.875rem;
		outline: none;
		transition: border-color 0.2s;
	}

	.search-input:focus {
		border-color: var(--c-brand);
	}

	.search-btn {
		padding: 0.5rem 0.75rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-sm);
		font-size: 1rem;
		cursor: pointer;
		transition:
			opacity 0.2s ease,
			transform 0.15s ease;
		font-family: var(--font-sans);
		min-height: 44px;
		min-width: 44px;
		will-change: opacity, transform;
	}

	.search-btn:hover:not(:disabled) {
		opacity: 0.9;
	}

	.search-btn:active:not(:disabled) {
		transform: scale(0.95);
	}

	.search-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.search-results {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		margin-top: 0.5rem;
		background: var(--c-bg-surface);
		border-radius: var(--radius-md);
		box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
		max-height: 300px;
		overflow-y: auto;
		z-index: 1200;
		pointer-events: auto;
		animation: slideDown 0.2s ease-out;
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.search-result-item {
		width: 100%;
		padding: 0.75rem 1rem;
		border: none;
		background: transparent;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s ease;
		border-bottom: 1px solid var(--c-border);
		font-family: var(--font-sans);
		pointer-events: auto;
	}

	.search-result-item:last-child {
		border-bottom: none;
		border-bottom-left-radius: var(--radius-md);
		border-bottom-right-radius: var(--radius-md);
	}

	.search-result-item:first-child {
		border-top-left-radius: var(--radius-md);
		border-top-right-radius: var(--radius-md);
	}

	.search-result-item:hover {
		background: var(--c-bg-subtle);
	}

	.search-result-item:active {
		background: var(--c-border);
	}

	.search-result-name {
		font-size: 0.875rem;
		color: var(--c-text-primary);
		line-height: 1.4;
	}

	.control-group {
		display: flex;
		gap: 0.5rem;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(12px);
		padding: 0.5rem;
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
	}

	.control-btn {
		padding: 0.5rem 1rem;
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--c-text-secondary);
		cursor: pointer;
		transition: all 0.2s ease;
		font-family: var(--font-sans);
		min-height: 44px;
		will-change: background, color, transform;
	}

	.control-btn:hover {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	.control-btn:active {
		transform: scale(0.95);
	}

	.control-btn.active {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
	}

	/* Categories */
	.categories {
		flex-wrap: wrap;
		max-width: 320px;
	}

	.category-chip {
		padding: 0.375rem 0.75rem;
		background: var(--c-bg-subtle);
		border: 1px solid var(--c-border);
		border-radius: 99px;
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--c-text-secondary);
		cursor: pointer;
		transition: all 0.2s ease;
		font-family: var(--font-sans);
		min-height: 36px;
		will-change: background, border-color, color, transform;
	}

	.category-chip:hover {
		border-color: var(--c-text-primary);
		color: var(--c-text-primary);
	}

	.category-chip:active {
		transform: scale(0.95);
	}

	.category-chip.active {
		background: var(--c-brand);
		border-color: var(--c-brand);
		color: var(--c-brand-contrast);
	}

	/* Stats Card */
	.stats-card {
		display: flex;
		gap: 1rem;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(12px);
		padding: 1rem;
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
	}

	.stat {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
		font-family: var(--font-display);
		color: var(--c-text-primary);
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--c-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Loading */
	.loading-overlay {
		position: absolute;
		inset: 0;
		background: var(--c-bg-page);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		z-index: 2000;
	}

	.loading-skeleton {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2rem;
		width: 100%;
		max-width: 400px;
		padding: 2rem;
	}

	.sk-controls {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		width: 100%;
	}

	.sk-search,
	.sk-buttons,
	.sk-categories,
	.sk-stats {
		background: linear-gradient(
			90deg,
			var(--c-bg-subtle) 25%,
			#f0f0f0 50%,
			var(--c-bg-subtle) 75%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: var(--radius-md);
	}

	.sk-search {
		height: 48px;
		width: 100%;
	}

	.sk-buttons {
		height: 44px;
		width: 60%;
	}

	.sk-categories {
		height: 64px;
		width: 80%;
	}

	.sk-stats {
		height: 72px;
		width: 50%;
	}

	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--c-bg-subtle);
		border-top-color: var(--c-brand);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.mini-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--c-bg-subtle);
		border-top-color: var(--c-brand);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-overlay p {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 500;
	}

	/* Data loading indicator (after map is ready) */
	.data-loading-indicator {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(8px);
		padding: 1rem 1.5rem;
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
		z-index: 1500;
	}

	.data-loading-indicator span {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
		font-weight: 500;
	}

	/* Mobile Responsive */
	@media (max-width: 768px) {
		.categories {
			max-width: 400px;
		}

		.category-chip {
			padding: 0.3rem 0.6rem;
			font-size: 0.75rem;
			min-height: 34px;
		}

		.stats-card {
			gap: 0.75rem;
			padding: 0.875rem;
		}

		.stat-value {
			font-size: 1.25rem;
		}

		.control-btn {
			min-height: 42px;
		}
	}

	@media (max-width: 640px) {
		.map-controls {
			left: 0.5rem;
			right: 0.5rem;
			top: 0.5rem;
			gap: 0.5rem;
		}

		.search-container {
			width: 100%;
		}

		.control-group {
			width: 100%;
			padding: 0.375rem;
			gap: 0.375rem;
		}

		.control-btn {
			padding: 0.5rem 0.875rem;
			font-size: 0.8125rem;
			min-height: 40px;
		}

		.categories {
			max-width: 100%;
			gap: 0.375rem;
		}

		.category-chip {
			padding: 0.25rem 0.5rem;
			font-size: 0.7rem;
			min-height: 32px;
		}

		.stats-card {
			width: 100%;
			gap: 0.5rem;
			padding: 0.75rem;
		}

		.stat-value {
			font-size: 1.125rem;
		}

		.stat-label {
			font-size: 0.6875rem;
		}

		.search-input {
			font-size: 0.875rem;
			padding: 0.5rem;
		}

		.search-btn {
			min-height: 40px;
			min-width: 40px;
			padding: 0.5rem;
		}
	}

	@media (max-width: 480px) {
		.map-controls {
			gap: 0.375rem;
		}

		.control-group {
			padding: 0.25rem;
		}

		.control-btn {
			padding: 0.5rem 0.75rem;
			font-size: 0.75rem;
			min-height: 38px;
		}

		.category-chip {
			padding: 0.25rem 0.45rem;
			font-size: 0.6875rem;
			min-height: 30px;
		}

		.stats-card {
			padding: 0.625rem;
			gap: 0.375rem;
		}

		.stat-value {
			font-size: 1rem;
		}

		.stat-label {
			font-size: 0.625rem;
		}
	}

	/* Leaflet overrides for theming */
	:global(.leaflet-container) {
		font-family: var(--font-sans);
	}

	:global(.leaflet-popup-content-wrapper) {
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
	}

	:global(.leaflet-popup-tip) {
		background: var(--c-bg-surface);
	}

	:global(.custom-marker) {
		background: transparent !important;
		border: none !important;
	}

	/* Marker Clustering Styles */
	:global(.marker-cluster-custom) {
		background: transparent !important;
		border: none !important;
	}

	:global(.cluster-icon) {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: var(--c-brand);
		color: white;
		font-weight: 700;
		font-size: 0.875rem;
		font-family: var(--font-sans);
		box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
		border: 3px solid white;
	}

	:global(.cluster-icon.cluster-medium) {
		width: 50px;
		height: 50px;
		font-size: 1rem;
	}

	:global(.cluster-icon.cluster-large) {
		width: 60px;
		height: 60px;
		font-size: 1.125rem;
	}

	/* Fix zoom control z-index to be above mobile nav */
	:global(.leaflet-control-zoom) {
		z-index: 800 !important;
		margin-bottom: 80px !important;
	}

	:global(.leaflet-bottom.leaflet-right) {
		z-index: 800 !important;
		margin-bottom: 80px !important;
	}

	:global(.leaflet-top.leaflet-right) {
		z-index: 800 !important;
	}

	@media (min-width: 641px) {
		:global(.leaflet-control-zoom) {
			margin-bottom: 10px !important;
		}

		:global(.leaflet-bottom.leaflet-right) {
			margin-bottom: 10px !important;
		}
	}

	/* India Boundary Overlay Styles */
	:global(.india-boundary-tooltip) {
		background: rgba(139, 125, 155, 0.95) !important;
		border: 1px solid rgba(255, 255, 255, 0.3) !important;
		border-radius: var(--radius-sm) !important;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
		color: white !important;
		font-family: var(--font-sans) !important;
		font-size: 0.8125rem !important;
		padding: 0.5rem 0.75rem !important;
		line-height: 1.4 !important;
		font-weight: 500 !important;
	}

	:global(.india-boundary-tooltip::before) {
		border-top-color: rgba(139, 125, 155, 0.95) !important;
	}

	:global(.india-boundary-tooltip small) {
		font-size: 0.6875rem !important;
		font-weight: 400 !important;
		opacity: 0.85 !important;
	}

	/* Dark Mode Overrides */
	:global([data-theme="dark"]) .search-container {
		background: rgba(0, 0, 0, 0.9);
	}

	:global([data-theme="dark"]) .search-results {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .control-group {
		background: rgba(0, 0, 0, 0.9);
	}

	:global([data-theme="dark"]) .stats-card {
		background: rgba(0, 0, 0, 0.9);
	}

	:global([data-theme="dark"]) .loading-overlay {
		background: var(--c-bg-page);
	}

	:global([data-theme="dark"]) .loading-skeleton {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .data-loading-indicator {
		background: rgba(0, 0, 0, 0.9);
	}

	:global([data-theme="dark"]) .sk-search,
	:global([data-theme="dark"]) .sk-buttons,
	:global([data-theme="dark"]) .sk-categories,
	:global([data-theme="dark"]) .sk-stats {
		background: var(--c-bg-subtle);
	}

	:global([data-theme="dark"]) :global(.leaflet-popup-content-wrapper) {
		background: var(--c-bg-surface) !important;
		color: var(--c-text-primary) !important;
	}

	:global([data-theme="dark"]) :global(.leaflet-popup-tip) {
		background: var(--c-bg-surface) !important;
	}
</style>
