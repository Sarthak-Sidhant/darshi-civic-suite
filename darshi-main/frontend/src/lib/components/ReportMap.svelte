<script lang="ts">
	import { onMount } from "svelte";

	type Props = {
		latitude: number;
		longitude: number;
		markerText?: string;
	};

	let {
		latitude,
		longitude,
		markerText = "Report Location",
	}: Props = $props();

	let mapContainer: HTMLDivElement;
	let map: any;
	let marker: any;

	onMount(async () => {
		await initializeMap();
	});

	async function initializeMap() {
		const L = (await import("leaflet")).default;
		await import("leaflet/dist/leaflet.css");

		// Define custom icon for marker
		const customIcon = L.icon({
			iconUrl:
				"https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
			iconRetinaUrl:
				"https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
			shadowUrl:
				"https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
			iconSize: [25, 41],
			iconAnchor: [12, 41],
			popupAnchor: [1, -34],
			shadowSize: [41, 41],
		});

		// Initialize map with India bounds
		map = L.map(mapContainer, {
			center: [latitude, longitude],
			zoom: 16,
			zoomControl: true,
			dragging: true,
			scrollWheelZoom: true,
			maxBounds: [
				[6.5, 68.0],
				[35.5, 97.5],
			], // India bounds
			maxBoundsViscosity: 0.5,
			minZoom: 5,
		});

		// Add OpenStreetMap tile layer
		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			attribution:
				'&copy; <a href="https://openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>',
			maxZoom: 19,
			detectRetina: true,
		}).addTo(map);

		// Add marker for report location
		marker = L.marker([latitude, longitude], { icon: customIcon })
			.addTo(map)
			.bindPopup(markerText)
			.openPopup();

		// Add scale control
		L.control.scale({ imperial: false, metric: true }).addTo(map);

		// Load India boundary overlay
		loadIndiaBoundary(L);

		// Invalidate size after map loads (fixes sizing issues)
		setTimeout(() => map.invalidateSize(), 100);
	}

	async function loadIndiaBoundary(L: any) {
		// Load boundary after short delay
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
				// Silently fail if boundary file not available
			}
		}, 300);
	}
</script>

<div class="report-map-container">
	<div bind:this={mapContainer} class="report-map"></div>
	<div class="map-overlay">
		<a
			href={`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=16/${latitude}/${longitude}`}
			target="_blank"
			rel="noopener noreferrer"
			class="view-on-osm"
		>
			View on OpenStreetMap →
		</a>
	</div>
</div>

<style>
	.report-map-container {
		position: relative;
		width: 100%;
		height: 400px;
		border-radius: var(--radius-md);
		overflow: hidden;
		border: 1px solid var(--c-border);
		margin: 1.5rem 0;
	}

	.report-map {
		width: 100%;
		height: 100%;
	}

	.map-overlay {
		position: absolute;
		bottom: 1rem;
		left: 1rem;
		z-index: 1000;
	}

	.view-on-osm {
		display: inline-block;
		padding: 0.5rem 1rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--c-text-primary);
		text-decoration: none;
		box-shadow: var(--shadow-sm);
		transition: all 0.2s ease;
	}

	.view-on-osm:hover {
		background: var(--c-bg-subtle);
		box-shadow: var(--shadow-md);
		transform: translateY(-1px);
	}

	.view-on-osm:active {
		transform: translateY(0);
	}

	/* Responsive adjustments */
	@media (max-width: 768px) {
		.report-map-container {
			height: 300px;
		}

		.map-overlay {
			bottom: 0.75rem;
			left: 0.75rem;
		}

		.view-on-osm {
			padding: 0.375rem 0.75rem;
			font-size: 0.8125rem;
		}
	}

	@media (max-width: 640px) {
		.report-map-container {
			height: 250px;
			margin: 1rem 0;
		}
	}

	/* Fix Leaflet CSS issues */
	:global(.leaflet-container) {
		font-family: var(--font-sans);
	}

	:global(.leaflet-popup-content-wrapper) {
		border-radius: var(--radius-sm);
		font-family: var(--font-sans);
	}

	:global(.leaflet-popup-content) {
		margin: 0.75rem;
		font-size: 0.875rem;
		line-height: 1.5;
	}
</style>
