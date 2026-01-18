<script lang="ts">
	import { onMount } from "svelte";
	import { geocodeAddress, getErrorMessage, reverseGeocode } from "$lib/api";
	import { toast } from "$lib/stores/toast";
	import LoadingSpinner from "./LoadingSpinner.svelte";
	import { MapPin, Search, X, Target, Navigation } from "lucide-svelte";

	type Props = {
		onFilterChange: (
			lat: number | null,
			lng: number | null,
			radiusKm: number,
			active: boolean,
		) => void;
	};

	let { onFilterChange }: Props = $props();

	let locationQuery = $state("");
	let radiusKm = $state(5);
	let filterActive = $state(false);
	let filterLat: number | null = $state(null);
	let filterLng: number | null = $state(null);
	let searchingLocation = $state(false);
	let gettingLocation = $state(false);
	let showModal = $state(false);

	async function handleLocationSearch(e: Event) {
		e.preventDefault();

		if (!locationQuery.trim()) {
			toast.show("Please enter a location", "warning");
			return;
		}

		searchingLocation = true;
		try {
			const results = await geocodeAddress(locationQuery);

			if (results.length === 0) {
				toast.show(
					"Location not found. Try a different search.",
					"warning",
				);
				searchingLocation = false;
				return;
			}

			// Use first result
			const result = results[0];
			filterLat = result.lat;
			filterLng = result.lng;
			filterActive = true;

			// Notify parent
			onFilterChange(filterLat, filterLng, radiusKm, true);

			toast.show(`Showing reports within ${radiusKm}km`, "success");
			closeModal();
		} catch (err) {
			toast.show(getErrorMessage(err), "error");
		} finally {
			searchingLocation = false;
		}
	}

	function clearLocationFilter() {
		locationQuery = "";
		radiusKm = 5;
		filterActive = false;
		filterLat = null;
		filterLng = null;

		// Notify parent
		onFilterChange(null, null, 5, false);
		closeModal();
	}

	function handleRadiusChange() {
		if (filterActive && filterLat && filterLng) {
			onFilterChange(filterLat, filterLng, radiusKm, true);
		}
	}

	async function useCurrentLocation() {
		if (!navigator.geolocation) {
			toast.show("Geolocation is not supported by your browser", "error");
			return;
		}

		gettingLocation = true;
		try {
			const position = await new Promise<GeolocationPosition>(
				(resolve, reject) => {
					navigator.geolocation.getCurrentPosition(resolve, reject, {
						enableHighAccuracy: true,
						timeout: 10000,
						maximumAge: 60000,
					});
				},
			);

			filterLat = position.coords.latitude;
			filterLng = position.coords.longitude;
			filterActive = true;

			// Try to get a human-readable address for the search field
			try {
				const address = await reverseGeocode(filterLat, filterLng);
				if (address) {
					locationQuery = address;
				}
			} catch {
				locationQuery = "Current Location";
			}

			onFilterChange(filterLat, filterLng, radiusKm, true);
			toast.show(
				`Filtering within ${radiusKm}km of your location`,
				"success",
			);
			closeModal();
		} catch (err: any) {
			let message = "Could not get your location";
			if (err.code === 1) {
				message =
					"Location access denied. Please enable location permissions.";
			} else if (err.code === 2) {
				message = "Location unavailable. Please try again.";
			} else if (err.code === 3) {
				message = "Location request timed out. Please try again.";
			}
			toast.show(message, "error");
		} finally {
			gettingLocation = false;
		}
	}

	function openModal() {
		showModal = true;
		if (typeof document !== "undefined") {
			document.body.style.overflow = "hidden";
		}
	}

	function closeModal() {
		showModal = false;
		if (typeof document !== "undefined") {
			document.body.style.overflow = "";
		}
	}

	onMount(() => {
		return () => {
			if (typeof document !== "undefined") {
				document.body.style.overflow = "";
			}
		};
	});
</script>

<div class="location-filter">
	<button
		class="filter-toggle"
		class:active={filterActive}
		onclick={openModal}
		aria-label="Location filter"
		type="button"
	>
		<MapPin size={18} />
		{#if filterActive}
			<span class="filter-badge">{radiusKm}km</span>
		{/if}
	</button>
</div>

{#if showModal}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-overlay" onclick={closeModal} role="presentation"></div>

	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="modal-content"
		onclick={(e) => e.stopPropagation()}
		role="dialog"
		aria-modal="true"
	>
		<div class="modal-header">
			<h3>Filter by Location</h3>
			<button
				type="button"
				class="close-btn"
				onclick={closeModal}
				aria-label="Close"
			>
				<X size={24} />
			</button>
		</div>

		<form onsubmit={handleLocationSearch} class="modal-body">
			<!-- Use Current Location Button -->
			<button
				type="button"
				class="current-location-btn"
				onclick={useCurrentLocation}
				disabled={gettingLocation || searchingLocation}
			>
				{#if gettingLocation}
					<LoadingSpinner size="sm" />
					<span>Getting location...</span>
				{:else}
					<Navigation size={18} />
					<span>Use Current Location</span>
				{/if}
			</button>

			<div class="divider">
				<span>or search</span>
			</div>

			<div class="form-group">
				<label for="location-input" class="label">Location</label>
				<div class="input-wrapper">
					<span class="input-icon" aria-hidden="true"
						><MapPin size={16} /></span
					>
					<input
						id="location-input"
						type="text"
						bind:value={locationQuery}
						placeholder="Search location..."
						class="text-input"
						disabled={searchingLocation || gettingLocation}
					/>
				</div>
			</div>

			<div class="form-group">
				<label for="radius-input" class="label">Radius</label>
				<select
					id="radius-input"
					bind:value={radiusKm}
					onchange={handleRadiusChange}
					class="select-input"
				>
					<option value={1}>1 km</option>
					<option value={2}>2 km</option>
					<option value={5}>5 km</option>
					<option value={10}>10 km</option>
					<option value={25}>25 km</option>
					<option value={50}>50 km</option>
				</select>
			</div>

			<div class="modal-actions">
				<button
					type="submit"
					class="submit-btn"
					disabled={searchingLocation || !locationQuery.trim()}
				>
					{#if searchingLocation}
						<LoadingSpinner size="sm" />
						<span>Searching...</span>
					{:else}
						<Search size={16} />
						<span>Apply Filter</span>
					{/if}
				</button>

				{#if filterActive}
					<button
						type="button"
						class="clear-btn"
						onclick={clearLocationFilter}
					>
						<X size={16} />
						<span>Clear Filter</span>
					</button>
				{/if}
			</div>

			{#if filterActive}
				<div class="active-indicator">
					<Target size={14} />
					<span>Filter active ({radiusKm}km radius)</span>
				</div>
			{/if}
		</form>
	</div>
{/if}

<style>
	.location-filter {
		position: relative;
	}

	.filter-toggle {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 44px;
		min-height: 44px;
		padding: 0.5rem;
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--c-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.filter-toggle:hover {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	.filter-toggle.active {
		color: var(--c-brand);
		background: rgba(0, 0, 0, 0.05);
	}

	.filter-badge {
		position: absolute;
		top: 4px;
		right: 4px;
		background: var(--c-brand);
		color: white;
		font-size: 0.625rem;
		font-weight: 700;
		padding: 2px 4px;
		border-radius: 4px;
		line-height: 1;
	}

	/* Modal styles */
	.modal-overlay {
		display: none;
	}

	.modal-content {
		display: none;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.modal-header h3 {
		font-size: 1rem;
		font-weight: 600;
		color: var(--c-text-primary);
		margin: 0;
	}

	.close-btn {
		background: transparent;
		border: none;
		color: var(--c-text-secondary);
		cursor: pointer;
		padding: 0.25rem;
		line-height: 1;
		transition: color 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.close-btn:hover {
		color: var(--c-text-primary);
	}

	.modal-body {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.current-location-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.875rem 1.25rem;
		background: var(--c-brand);
		color: white;
		border: none;
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-weight: 600;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: all 0.2s;
	}

	.current-location-btn:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.current-location-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none;
	}

	.divider {
		display: flex;
		align-items: center;
		gap: 1rem;
		color: var(--c-text-tertiary);
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.divider::before,
	.divider::after {
		content: "";
		flex: 1;
		height: 1px;
		background: var(--c-border);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.label {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--c-text-primary);
	}

	.input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.input-icon {
		position: absolute;
		left: 0.75rem;
		color: var(--c-text-tertiary);
		display: flex;
		align-items: center;
		pointer-events: none;
	}

	.text-input {
		width: 100%;
		padding: 0.75rem 0.75rem 0.75rem 2.5rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-family: var(--font-sans);
		transition: border-color 0.2s;
	}

	.text-input:focus {
		outline: none;
		border-color: var(--c-brand);
	}

	.text-input:disabled {
		background: var(--c-bg-subtle);
		cursor: not-allowed;
	}

	.select-input {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-family: var(--font-sans);
		background: var(--c-bg-surface);
		cursor: pointer;
		transition: border-color 0.2s;
	}

	.select-input:focus {
		outline: none;
		border-color: var(--c-brand);
	}

	.modal-actions {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	.submit-btn,
	.clear-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.875rem 1.25rem;
		border: none;
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-weight: 600;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: all 0.2s;
	}

	.submit-btn {
		background: var(--c-brand);
		color: white;
	}

	.submit-btn:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.submit-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none;
	}

	.clear-btn {
		background: transparent;
		color: var(--c-error);
		border: 1px solid var(--c-error);
	}

	.clear-btn:hover {
		background: var(--c-error);
		color: white;
	}

	.active-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: var(--c-success-bg);
		border: 1px solid var(--c-success-border);
		border-radius: var(--radius-sm);
		color: var(--c-success-dark);
		font-size: 0.875rem;
		font-weight: 500;
	}

	/* Desktop dropdown */
	@media (min-width: 641px) {
		.modal-overlay {
			display: none;
		}

		.modal-content {
			display: block;
			position: absolute;
			top: calc(100% + 0.5rem);
			left: 0;
			width: 320px;
			background: var(--c-bg-surface);
			border: 1px solid var(--c-border);
			border-radius: var(--radius-md);
			box-shadow: var(--shadow-lg);
			padding: 1.25rem;
			z-index: 1000;
			animation: dropdownFadeIn 0.2s ease-out;
		}

		@keyframes dropdownFadeIn {
			from {
				opacity: 0;
				transform: translateY(-10px);
			}
			to {
				opacity: 1;
				transform: translateY(0);
			}
		}
	}

	/* Mobile bottom sheet */
	@media (max-width: 640px) {
		.filter-toggle {
			background: #ef4444;
			color: white;
			border-radius: var(--radius-full);
			min-width: 40px;
			min-height: 40px;
		}

		.filter-toggle:hover,
		.filter-toggle:active {
			background: #dc2626;
			color: white;
		}

		.filter-toggle.active {
			background: #dc2626;
			color: white;
		}

		.filter-badge {
			background: var(--c-bg-surface);
			color: #ef4444;
		}

		.modal-overlay {
			display: block;
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			background: rgba(0, 0, 0, 0.5);
			z-index: 9998;
			animation: fadeIn 0.2s ease-out;
		}

		@keyframes fadeIn {
			from {
				opacity: 0;
			}
			to {
				opacity: 1;
			}
		}

		.modal-content {
			display: block;
			position: fixed;
			top: var(--header-height, 56px);
			left: 0;
			right: 0;
			max-height: calc(100vh - var(--header-height, 56px));
			background: var(--c-bg-surface);
			border-radius: 0 0 var(--radius-lg) var(--radius-lg);
			padding: 1.5rem;
			padding-bottom: max(1.5rem, env(safe-area-inset-bottom));
			overflow-y: auto;
			z-index: 9999;
			box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
			animation: slideDown 0.25s ease-out;
		}

		@keyframes slideDown {
			from {
				opacity: 0;
				transform: translateY(-20px);
			}
			to {
				opacity: 1;
				transform: translateY(0);
			}
		}

		.modal-header {
			margin-bottom: 1.5rem;
		}

		.modal-header h3 {
			font-size: 1.125rem;
		}
	}

	/* Very small screens */
	@media (max-width: 360px) {
		.modal-content {
			padding: 1rem;
		}

		.modal-header {
			margin-bottom: 1rem;
		}

		.submit-btn,
		.clear-btn {
			padding: 0.75rem 1rem;
			font-size: 0.8125rem;
		}
	}

	/* Dark Mode */
	:global([data-theme="dark"]) .modal-content {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .select-input,
	:global([data-theme="dark"]) .text-input {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	:global([data-theme="dark"]) .location-result {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .location-result:hover {
		background: var(--c-bg-subtle);
	}

	:global([data-theme="dark"]) .filter-toggle {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .filter-toggle.active {
		background: #ef4444;
	}

	:global([data-theme="dark"]) .filter-badge {
		background: var(--c-bg-page);
		color: #ef4444;
	}
</style>
