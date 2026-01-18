<script lang="ts">
	import { onMount, onDestroy } from "svelte";
	import { goto } from "$app/navigation";
	import {
		createReport,
		geocode,
		reverseGeocode,
		getErrorMessage,
	} from "$lib/api";
	import { user, isAuthenticated } from "$lib/stores";
	import { toast } from "$lib/stores/toast";
	import {
		validationRules,
		validateField,
		getCharacterCount,
	} from "$lib/validation";
	import LoadingButton from "$lib/components/LoadingButton.svelte";
	import { MapPin, Search, Send } from "lucide-svelte";
	import { resizeImages } from "$lib/imageCompression";

	let title = $state("");
	let description = $state("");
	let files: FileList | null = $state(null);
	let location = $state("");
	let lat = $state(23.3729);
	let lng = $state(85.3371);
	let loading = $state(false);
	let gettingLocation = $state(false);
	let resizing = $state(false);
	let searchQuery = $state("");
	let searchResults: any[] = $state([]);
	let searching = $state(false);
	let mapContainer: HTMLDivElement;
	let map: any;
	let marker: any;

	// Location method selection
	let locationMethod: "none" | "current" | "search" = $state("none");
	let displayAddress = $state("");
	let useCurrentLocationOnSubmit = $state(false);

	// Validation state
	let titleErrors = $state<string[]>([]);
	let descriptionErrors = $state<string[]>([]);
	let titleTouched = $state(false);
	let descriptionTouched = $state(false);

	// Image previews
	let imagePreviews = $state<string[]>([]);
	let fileInput: HTMLInputElement;
	let cameraInput: HTMLInputElement;

	onMount(async () => {
		// Initialize map (no auth required)
		await initializeMap();
	});

	async function initializeMap() {
		const L = (await import("leaflet")).default;
		await import("leaflet/dist/leaflet.css");

		// India bounds
		const indiaBounds: [[number, number], [number, number]] = [
			[4.592917, 44.579417],
			[39.55325, 114.273],
		];

		map = L.map(mapContainer, {
			zoomControl: true,
			maxBounds: indiaBounds,
			maxBoundsViscosity: 1.0,
		}).setView([lat, lng], 5);

		// Add tiles
		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			attribution:
				'<a href="https://leafletjs.com" target="_blank">Leaflet</a> | <a href="https://openstreetmap.org/copyright" target="_blank">OSM</a>',
			maxZoom: 19,
			minZoom: 4,
			bounds: indiaBounds,
			crossOrigin: true,
		}).addTo(map);

		// Add India boundary
		await addIndiaBoundary(L);

		// Add draggable marker
		addMarker(L, lat, lng);

		// Get user location - use fast initial fetch for better UX
		if (navigator.geolocation) {
			navigator.geolocation.getCurrentPosition(
				(position) => {
					const userLat = position.coords.latitude;
					const userLng = position.coords.longitude;
					lat = userLat;
					lng = userLng;
					location = `${lat},${lng}`;

					map.setView([userLat, userLng], 17);
					if (marker) {
						marker.setLatLng([userLat, userLng]);
					}
				},
				() => {
					// Silently fail - user can still manually select location
				},
				{
					enableHighAccuracy: false, // Faster initial fetch (uses cell towers/wifi)
					timeout: 5000, // 5 second timeout
					maximumAge: 60000, // Accept cached location up to 1 min old
				},
			);
		}

		// Click on map to place marker
		map.on("click", (e: any) => {
			lat = e.latlng.lat;
			lng = e.latlng.lng;
			location = `${lat},${lng}`;

			if (marker) {
				marker.setLatLng([lat, lng]);
			}
		});
	}

	async function addIndiaBoundary(L: any) {
		try {
			const response = await fetch("/india-boundary-simplified.geojson");
			if (!response.ok) return;

			const indiaGeoJSON = await response.json();
			L.geoJSON(indiaGeoJSON, {
				style: {
					color: "#887191",
					weight: 3,
					opacity: 0.75,
					fillColor: "transparent",
					dashArray: "2, 3",
				},
			}).addTo(map);
		} catch (_error) {
			// Silently handle boundary loading errors
		}
	}

	function validateTitle() {
		if (!titleTouched) return;
		const result = validateField(title, [
			validationRules.required("Title is required"),
			validationRules.minLength(
				10,
				"Title must be at least 10 characters",
			),
			validationRules.maxLength(
				200,
				"Title must be less than 200 characters",
			),
		]);
		titleErrors = result.errors;
	}

	function validateDescription() {
		if (!descriptionTouched) return;
		const result = validateField(description, [
			validationRules.minLength(
				20,
				"Description should be at least 20 characters for better context",
			),
			validationRules.maxLength(
				2000,
				"Description must be less than 2000 characters",
			),
		]);
		descriptionErrors = result.errors;
	}

	async function handleFilesChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const newFiles = input.files;

		if (newFiles && newFiles.length > 0) {
			resizing = true;

			try {
				// Merge with existing files if any
				const existingFiles = files ? Array.from(files) : [];
				const newFilesArray = Array.from(newFiles);
				const allFiles = [...existingFiles, ...newFilesArray];

				// Limit to 5 files
				if (allFiles.length > 5) {
					toast.show(
						"Maximum 5 images allowed. Only the first 5 will be used.",
						"warning",
					);
				}

				const selectedFiles = allFiles.slice(0, 5);

				// Lightweight resize if needed (only if > 1920px, fast)
				const resizedFiles = await resizeImages(selectedFiles);

				// Create new FileList with resized files
				const dataTransfer = new DataTransfer();
				for (const file of resizedFiles) {
					dataTransfer.items.add(file);
				}
				files = dataTransfer.files;

				// Generate image previews using Object URLs
				// Revoke old URLs to prevent memory leaks
				imagePreviews.forEach((url) => {
					if (url.startsWith("blob:")) {
						URL.revokeObjectURL(url);
					}
				});

				imagePreviews = [];
				for (let i = 0; i < resizedFiles.length; i++) {
					const file = resizedFiles[i];
					const objectUrl = URL.createObjectURL(file);
					imagePreviews = [...imagePreviews, objectUrl];
				}

				toast.show(`${resizedFiles.length} image(s) ready`, "success");
			} catch (error) {
				console.error("Image resize error:", error);
				toast.show(
					"Image processing had issues, but you can still submit",
					"warning",
				);
			} finally {
				resizing = false;
			}
		}
	}

	function removeImage(index: number) {
		if (!files) return;

		// Revoke the Object URL for the removed image to prevent memory leaks
		const urlToRevoke = imagePreviews[index];
		if (urlToRevoke && urlToRevoke.startsWith("blob:")) {
			URL.revokeObjectURL(urlToRevoke);
		}

		const filesArray = Array.from(files);
		filesArray.splice(index, 1);

		const dataTransfer = new DataTransfer();
		filesArray.forEach((file) => dataTransfer.items.add(file));
		files = dataTransfer.files;

		imagePreviews.splice(index, 1);
		imagePreviews = [...imagePreviews];

		if (filesArray.length === 0) {
			files = null;
		}
	}

	// Cleanup Object URLs on component destroy to prevent memory leaks
	onDestroy(() => {
		imagePreviews.forEach((url) => {
			if (url.startsWith("blob:")) {
				URL.revokeObjectURL(url);
			}
		});
	});

	function openCamera() {
		cameraInput?.click();
	}

	function openGallery() {
		fileInput?.click();
	}

	function addMarker(L: any, latitude: number, longitude: number) {
		const icon = L.icon({
			iconUrl:
				'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"%3E%3Cpath fill="%23ff0000" d="M16 2C10.5 2 6 6.5 6 12c0 8 10 18 10 18s10-10 10-18c0-5.5-4.5-10-10-10zm0 14c-2.2 0-4-1.8-4-4s1.8-4 4-4 4 1.8 4 4-1.8 4-4 4z"/%3E%3C/svg%3E',
			iconSize: [32, 32],
			iconAnchor: [16, 32],
			popupAnchor: [0, -32],
		});

		marker = L.marker([latitude, longitude], {
			icon: icon,
			draggable: true,
		}).addTo(map);

		marker.bindPopup(
			"<strong>Your Report Location</strong><br>Drag me to adjust!",
		);

		// Update coordinates when marker is dragged
		marker.on("dragend", (e: any) => {
			const pos = e.target.getLatLng();
			lat = pos.lat;
			lng = pos.lng;
			location = `${lat},${lng}`;
		});
	}

	async function getCurrentLocation() {
		gettingLocation = true;

		if (!navigator.geolocation) {
			toast.show("Geolocation is not supported by your browser", "error");
			gettingLocation = false;
			return;
		}

		navigator.geolocation.getCurrentPosition(
			async (position) => {
				lat = position.coords.latitude;
				lng = position.coords.longitude;
				location = `${lat},${lng}`;
				locationMethod = "current";
				useCurrentLocationOnSubmit = true;

				// Fetch human-readable address
				try {
					displayAddress = await reverseGeocode(lat, lng);
					toast.show("Current location set successfully", "success");
				} catch (e) {
					displayAddress = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
					toast.show(
						"Location set (address lookup failed)",
						"warning",
					);
				}

				if (map && marker) {
					map.setView([lat, lng], 17);
					marker.setLatLng([lat, lng]);
				}

				gettingLocation = false;
			},
			(err) => {
				let message =
					"Unable to get location. Please enable location access.";
				if (err.code === 1) {
					message =
						"Location access denied. Please enable location permissions.";
				} else if (err.code === 2) {
					message = "Location unavailable. Please try again.";
				} else if (err.code === 3) {
					message = "Location request timed out. Please try again.";
				}
				toast.show(message, "warning");
				gettingLocation = false;
			},
			{
				enableHighAccuracy: true, // Use GPS for better accuracy
				timeout: 10000, // 10 second timeout
				maximumAge: 30000, // Accept cached location up to 30 seconds old
			},
		);
	}

	async function searchLocation() {
		if (!searchQuery.trim()) return;

		searching = true;

		try {
			searchResults = await geocode(searchQuery);
			if (searchResults.length === 0) {
				toast.show(
					"No locations found. Try a different search term.",
					"info",
				);
			}
		} catch (e) {
			toast.show(getErrorMessage(e), "error");
		} finally {
			searching = false;
		}
	}

	function selectLocation(result: any) {
		const latitude = result.lat || result.latitude;
		const longitude = result.lon || result.lng || result.longitude;

		if (latitude && longitude) {
			lat = parseFloat(latitude);
			lng = parseFloat(longitude);
			location = `${lat},${lng}`;
			displayAddress =
				result.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
			locationMethod = "search";
			useCurrentLocationOnSubmit = false;
			searchQuery = "";
			searchResults = [];

			if (map && marker) {
				map.setView([lat, lng], 17);
				marker.setLatLng([lat, lng]);
			}
		}
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === "Enter") {
			e.preventDefault();
			searchLocation();
		}
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		// Mark all fields as touched
		titleTouched = true;
		descriptionTouched = true;

		// Validate all fields
		validateTitle();
		validateDescription();

		if (!title.trim() || !files || files.length === 0 || !location) {
			toast.show("Please fill in all required fields", "error");
			return;
		}

		if (titleErrors.length > 0 || descriptionErrors.length > 0) {
			toast.show(
				"Please fix validation errors before submitting",
				"error",
			);
			return;
		}

		if (files.length > 5) {
			toast.show(
				"Maximum 5 images allowed. Please select fewer images.",
				"error",
			);
			return;
		}

		loading = true;

		try {
			// If user chose "current location", refetch it now to ensure accuracy
			if (useCurrentLocationOnSubmit) {
				if (!navigator.geolocation) {
					toast.show(
						"Geolocation is not supported by your browser",
						"error",
					);
					loading = false;
					return;
				}

				// Get fresh location
				await new Promise<void>((resolve, reject) => {
					navigator.geolocation.getCurrentPosition(
						(position) => {
							lat = position.coords.latitude;
							lng = position.coords.longitude;
							location = `${lat},${lng}`;
							resolve();
						},
						(err) => {
							reject(err);
						},
						{
							enableHighAccuracy: true,
							timeout: 10000,
							maximumAge: 0,
						},
					);
				}).catch(() => {
					toast.show(
						"Failed to get current location. Using last known location.",
						"warning",
					);
				});
			}

			const fileArray = Array.from(files);
			// Username is optional - authenticated users use their username, anonymous users use undefined
			const username = $user?.username || undefined;
			const result = await createReport(
				fileArray,
				location,
				username,
				title,
				description,
			);

			// Show success toast
			toast.show(`Report submitted successfully!`, "success");

			// Reset form
			title = "";
			description = "";
			files = null;
			imagePreviews = [];
			titleTouched = false;
			descriptionTouched = false;
			locationMethod = "none";
			displayAddress = "";
			useCurrentLocationOnSubmit = false;

			// Immediate navigation to report page (optimistic UI)
			// Images are still being processed in background on server
			goto(`/report/${result.report_id}`);
		} catch (e) {
			toast.show(getErrorMessage(e), "error");
		} finally {
			loading = false;
		}
	}

	// Effects
	$effect(() => {
		validateTitle();
	});

	$effect(() => {
		validateDescription();
	});

	$effect(() => {
		if (files && files.length >= 5) {
			// Disable camera button if 5 images already selected
			if (cameraInput) {
				cameraInput.disabled = true;
			}
			if (fileInput) {
				fileInput.disabled = true;
			}
		} else {
			if (cameraInput) {
				cameraInput.disabled = false;
			}
			if (fileInput) {
				fileInput.disabled = false;
			}
		}
	});
</script>

<svelte:head>
	<title>Submit Report - Darshi</title>
</svelte:head>

<div class="submit-page">
	<div class="submit-container">
		<!-- Form Section -->
		<section class="form-section" aria-labelledby="form-heading">
			<h1 id="form-heading">Submit a Report</h1>

			<form onsubmit={handleSubmit} aria-label="Report submission form">
				<div class="form-group">
					<label for="title"
						>Title * <span class="char-count"
							>{getCharacterCount(title, 200)}</span
						></label
					>
					<input
						id="title"
						type="text"
						bind:value={title}
						onblur={() => (titleTouched = true)}
						placeholder="e.g., Pothole on Main Street"
						required
						aria-required="true"
						aria-invalid={titleTouched && titleErrors.length > 0}
						aria-describedby={titleTouched && titleErrors.length > 0
							? "title-error"
							: undefined}
					/>
					{#if titleTouched && titleErrors.length > 0}
						<div
							id="title-error"
							class="error-message"
							role="alert"
						>
							{titleErrors[0]}
						</div>
					{/if}
				</div>

				<div class="form-group">
					<label for="description"
						>Description <span class="char-count"
							>{getCharacterCount(description, 2000)}</span
						></label
					>
					<textarea
						id="description"
						bind:value={description}
						onblur={() => (descriptionTouched = true)}
						placeholder="Provide additional details about the issue (recommended: at least 20 characters)"
						rows="4"
						aria-invalid={descriptionTouched &&
							descriptionErrors.length > 0}
						aria-describedby={descriptionTouched &&
						descriptionErrors.length > 0
							? "description-error"
							: undefined}
					></textarea>
					{#if descriptionTouched && descriptionErrors.length > 0}
						<div
							id="description-error"
							class="error-message"
							role="alert"
						>
							{descriptionErrors[0]}
						</div>
					{/if}
				</div>

				<div class="form-group">
					<label for="images">Images * (Max 5 images)</label>

					<!-- Hidden file inputs -->
					<input
						bind:this={fileInput}
						type="file"
						onchange={handleFilesChange}
						accept="image/*"
						multiple
						style="display: none;"
						aria-hidden="true"
					/>
					<input
						bind:this={cameraInput}
						type="file"
						onchange={handleFilesChange}
						accept="image/*"
						capture="environment"
						style="display: none;"
						aria-hidden="true"
					/>

					<!-- Visible buttons -->
					<div class="image-upload-buttons">
						<button
							type="button"
							class="btn-upload"
							onclick={openCamera}
							disabled={(files && files.length >= 5) || resizing}
						>
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path
									d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"
								></path>
								<circle cx="12" cy="13" r="4"></circle>
							</svg>
							{resizing ? "Processing..." : "Take Photo"}
						</button>
						<button
							type="button"
							class="btn-upload"
							onclick={openGallery}
							disabled={(files && files.length >= 5) || resizing}
						>
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect
									x="3"
									y="3"
									width="18"
									height="18"
									rx="2"
									ry="2"
								></rect>
								<circle cx="8.5" cy="8.5" r="1.5"></circle>
								<polyline points="21 15 16 10 5 21"></polyline>
							</svg>
							{resizing ? "Processing..." : "Choose from Gallery"}
						</button>
					</div>

					<p id="images-hint" class="hint">
						{#if resizing}
							Preparing images for upload...
						{:else if files && files.length > 0}
							{files.length} file(s) ready • Click buttons again to
							add more (max 5 total)
						{:else}
							Take photos with camera or choose existing images
							from gallery
						{/if}
					</p>

					{#if imagePreviews.length > 0}
						<div
							class="image-previews"
							role="region"
							aria-label="Image previews"
						>
							{#each imagePreviews as preview, index}
								<div class="preview-wrapper">
									<img
										src={preview}
										alt="Preview {index + 1}"
										class="preview-image"
									/>
									<button
										type="button"
										class="remove-image"
										onclick={() => removeImage(index)}
										aria-label="Remove image {index + 1}"
									>
										<svg
											width="16"
											height="16"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<line x1="18" y1="6" x2="6" y2="18"
											></line>
											<line x1="6" y1="6" x2="18" y2="18"
											></line>
										</svg>
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<div class="form-group">
					<label>Location *</label>

					{#if locationMethod === "none"}
						<div class="location-method-buttons">
							<LoadingButton
								type="button"
								loading={gettingLocation}
								onclick={getCurrentLocation}
								variant="primary"
							>
								<MapPin size={16} /> Use Current Location
							</LoadingButton>
							<button
								type="button"
								class="btn-secondary-outline"
								onclick={() => (locationMethod = "search")}
							>
								<Search size={16} /> Search Location
							</button>
						</div>
						<p class="hint">Choose how to set your location</p>
					{:else if locationMethod === "current"}
						<div class="location-display">
							<div class="location-info-card">
								<div class="location-icon">
									<MapPin size={20} />
								</div>
								<div class="location-text">
									<p class="location-label">
										Current Location
									</p>
									<p class="location-address">
										{displayAddress}
									</p>
								</div>
							</div>
							<button
								type="button"
								class="btn-change"
								onclick={() => {
									locationMethod = "none";
									displayAddress = "";
									useCurrentLocationOnSubmit = false;
								}}
							>
								Change
							</button>
						</div>
						<p class="hint">
							Location will be refreshed when you submit for
							accuracy
						</p>
					{:else if locationMethod === "search"}
						<div class="search-location-section">
							{#if displayAddress}
								<div class="location-display">
									<div class="location-info-card">
										<div class="location-icon">
											<MapPin size={20} />
										</div>
										<div class="location-text">
											<p class="location-label">
												Selected Location
											</p>
											<p class="location-address">
												{displayAddress}
											</p>
										</div>
									</div>
									<button
										type="button"
										class="btn-change"
										onclick={() => {
											displayAddress = "";
											searchQuery = "";
										}}
									>
										Change
									</button>
								</div>
							{:else}
								<div class="search-box">
									<input
										id="search"
										type="text"
										bind:value={searchQuery}
										onkeydown={handleSearchKeydown}
										placeholder="Search address, landmark, or pincode..."
										aria-label="Search for a location"
									/>
									<LoadingButton
										type="button"
										loading={searching}
										onclick={searchLocation}
										variant="primary"
									>
										<Search size={16} />
									</LoadingButton>
								</div>
								{#if searchResults.length > 0}
									<div
										class="search-results"
										role="listbox"
										aria-label="Search results"
									>
										{#each searchResults as result}
											<button
												type="button"
												role="option"
												class="search-result-item"
												onclick={() =>
													selectLocation(result)}
											>
												{result.display_name}
											</button>
										{/each}
									</div>
								{/if}
								<button
									type="button"
									class="btn-back"
									onclick={() => (locationMethod = "none")}
								>
									← Back to location options
								</button>
							{/if}
						</div>
					{/if}

					<!-- Hidden input for validation -->
					<input
						type="hidden"
						bind:value={location}
						required
						aria-required="true"
					/>
				</div>

				<LoadingButton type="submit" {loading} variant="primary">
					<Send size={16} /> Submit Report
				</LoadingButton>
			</form>
		</section>

		<!-- Map Section -->
		<div class="map-section">
			<div class="map-header">
				<h3>Select Location</h3>
				<p>Click on map or drag the marker to set exact location</p>
			</div>
			<div bind:this={mapContainer} class="map-container"></div>
		</div>
	</div>
</div>

<style>
	.submit-page {
		min-height: calc(100vh - var(--header-height));
		background: var(--c-bg-page);
		padding: 2rem 0;
	}

	.submit-container {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 1.5rem;
		display: grid;
		grid-template-columns: minmax(400px, 1fr) minmax(400px, 1.2fr);
		gap: 2rem;
		align-items: start;
	}

	/* Wide screens: improve spacing */
	@media (min-width: 1600px) {
		.submit-container {
			max-width: 1600px;
			gap: 3rem;
			padding: 0 2rem;
		}

		.map-container {
			height: 600px;
		}
	}

	/* Form Section */
	.form-section {
		background: var(--c-bg-surface);
		padding: 2rem;
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-md);
	}

	h1 {
		font-family: var(--font-display);
		font-size: 2rem;
		font-weight: 700;
		margin-bottom: 1.5rem;
		color: var(--c-text-primary);
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	label {
		display: block;
		margin-bottom: 0.5rem;
		font-weight: 600;
		font-size: 0.875rem;
		color: var(--c-text-primary);
	}

	input[type="text"],
	textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
		font-family: var(--font-sans);
		transition: border-color 0.2s;
	}

	input[type="text"]:focus,
	textarea:focus {
		outline: none;
		border-color: var(--c-brand);
	}

	input[type="file"] {
		width: 100%;
		padding: 0.5rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
	}

	.image-upload-buttons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.btn-upload {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.875rem 1rem;
		background: var(--c-bg-surface);
		border: 2px solid var(--c-brand);
		border-radius: var(--radius-sm);
		color: var(--c-brand);
		font-size: 0.875rem;
		font-weight: 600;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-upload:hover {
		background: var(--c-brand);
		color: white;
		transform: translateY(-1px);
		box-shadow: var(--shadow-sm);
	}

	.btn-upload:active {
		transform: translateY(0);
	}

	.btn-upload svg {
		flex-shrink: 0;
	}

	.btn-upload:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		pointer-events: none;
	}

	/* Location selection styles */
	.location-method-buttons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
	}

	.btn-secondary-outline {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.875rem 1rem;
		background: var(--c-bg-surface);
		border: 2px solid var(--c-text-secondary);
		border-radius: var(--radius-sm);
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 600;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-secondary-outline:hover {
		background: var(--c-text-secondary);
		color: white;
		transform: translateY(-1px);
		box-shadow: var(--shadow-sm);
	}

	.btn-secondary-outline:active {
		transform: translateY(0);
	}

	.location-display {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
	}

	.location-info-card {
		flex: 1;
		display: flex;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--c-bg-subtle);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
	}

	.location-icon {
		flex-shrink: 0;
		width: 40px;
		height: 40px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--c-brand);
		color: white;
		border-radius: var(--radius-sm);
	}

	.location-text {
		flex: 1;
		min-width: 0;
	}

	.location-label {
		margin: 0 0 0.25rem 0;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--c-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.location-address {
		margin: 0;
		font-size: 0.875rem;
		color: var(--c-text-primary);
		line-height: 1.4;
		word-wrap: break-word;
	}

	.btn-change {
		flex-shrink: 0;
		padding: 0.5rem 1rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 600;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: all 0.2s;
		white-space: nowrap;
	}

	.btn-change:hover {
		background: var(--c-bg-subtle);
		border-color: var(--c-text-secondary);
		color: var(--c-text-primary);
	}

	.btn-back {
		margin-top: 0.75rem;
		padding: 0.5rem;
		background: transparent;
		border: none;
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 500;
		font-family: var(--font-sans);
		cursor: pointer;
		transition: color 0.2s;
	}

	.btn-back:hover {
		color: var(--c-brand);
	}

	.search-location-section {
		display: flex;
		flex-direction: column;
	}

	textarea {
		resize: vertical;
	}

	.hint {
		margin-top: 0.5rem;
		font-size: 0.75rem;
		color: var(--c-text-secondary);
	}

	.error-message {
		margin-top: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-error);
		font-weight: 500;
	}

	.char-count {
		float: right;
		font-size: 0.75rem;
		color: var(--c-text-tertiary);
		font-weight: 400;
	}

	.image-previews {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
		gap: 0.5rem;
		margin-top: 1rem;
	}

	.preview-wrapper {
		position: relative;
	}

	.preview-image {
		width: 100%;
		height: 100px;
		object-fit: cover;
		border-radius: var(--radius-sm);
		border: 1px solid var(--c-border);
	}

	.remove-image {
		position: absolute;
		top: 4px;
		right: 4px;
		width: 24px;
		height: 24px;
		padding: 0;
		background: rgba(255, 0, 0, 0.85);
		border: none;
		border-radius: 50%;
		color: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.remove-image:hover {
		background: rgba(255, 0, 0, 1);
		transform: scale(1.1);
	}

	.remove-image:active {
		transform: scale(0.95);
	}

	input:focus-visible,
	textarea:focus-visible {
		outline: 2px solid var(--c-brand);
		outline-offset: 2px;
	}

	.search-box {
		display: flex;
		gap: 0.5rem;
	}

	.search-box input {
		flex: 1;
	}

	.search-results {
		margin-top: 0.5rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		max-height: 200px;
		overflow-y: auto;
		box-shadow: var(--shadow-md);
		animation: slideDown 0.2s ease-out;
		width: 100%;
		box-sizing: border-box;
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
		text-align: left;
		background: transparent;
		border: none;
		border-bottom: 1px solid var(--c-border);
		cursor: pointer;
		transition: background 0.15s;
		font-family: var(--font-sans);
		font-size: 0.875rem;
	}

	.search-result-item:hover {
		background: var(--c-bg-subtle);
	}

	.search-result-item:active {
		background: var(--c-border);
	}

	.search-result-item:last-child {
		border-bottom: none;
	}

	/* Map Section */
	.map-section {
		position: sticky;
		top: calc(var(--header-height) + 1rem);
		background: var(--c-bg-surface);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-md);
		overflow: hidden;
	}

	.map-header {
		padding: 1.5rem;
		border-bottom: 1px solid var(--c-border);
		background: var(--c-bg-subtle);
	}

	.map-header h3 {
		font-family: var(--font-display);
		font-size: 1.25rem;
		font-weight: 700;
		margin: 0 0 0.5rem 0;
		color: var(--c-text-primary);
	}

	.map-header p {
		margin: 0;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.map-container {
		height: 500px;
		width: 100%;
	}

	/* Leaflet overrides */
	:global(.leaflet-container) {
		font-family: var(--font-sans);
	}

	:global(.leaflet-popup-content-wrapper) {
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
	}

	/* Responsive */
	@media (max-width: 1024px) {
		.submit-container {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}

		.map-section {
			position: relative;
			top: 0;
			order: 2;
		}

		.form-section {
			order: 1;
		}

		.map-container {
			height: 400px;
		}
	}

	@media (max-width: 768px) {
		.submit-container {
			padding: 0 1rem;
		}

		.map-container {
			height: 350px;
		}

		.form-section {
			padding: 1.5rem;
		}

		h1 {
			font-size: 1.75rem;
		}

		.image-previews {
			grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
		}

		.preview-image {
			height: 90px;
		}
	}

	@media (max-width: 640px) {
		.submit-page {
			padding: 1rem 0;
		}

		.submit-container {
			gap: 1rem;
		}

		.form-section {
			padding: 1.25rem;
		}

		h1 {
			font-size: 1.5rem;
			margin-bottom: 1.25rem;
		}

		.form-group {
			margin-bottom: 1.25rem;
		}

		.search-box {
			flex-direction: row;
			gap: 0.5rem;
		}

		.search-result-item {
			padding: 0.625rem 0.75rem;
			font-size: 0.8125rem;
		}

		.map-container {
			height: 300px;
		}

		.map-header {
			padding: 1.25rem;
		}

		.map-header h3 {
			font-size: 1.125rem;
		}

		.map-header p {
			font-size: 0.8125rem;
		}

		.image-upload-buttons {
			grid-template-columns: 1fr;
			gap: 0.5rem;
		}

		.btn-upload {
			padding: 0.75rem 1rem;
			font-size: 0.8125rem;
		}

		.location-method-buttons {
			grid-template-columns: 1fr;
			gap: 0.5rem;
		}

		.location-display {
			flex-direction: column;
		}

		.btn-change {
			width: 100%;
		}

		.location-info-card {
			padding: 0.875rem;
		}

		.location-icon {
			width: 36px;
			height: 36px;
		}
	}

	@media (max-width: 480px) {
		.submit-page {
			padding: 0.75rem 0;
		}

		.submit-container {
			padding: 0 0.75rem;
		}

		.form-section {
			padding: 1rem;
		}

		h1 {
			font-size: 1.375rem;
			margin-bottom: 1rem;
		}

		.form-group {
			margin-bottom: 1rem;
		}

		label {
			font-size: 0.8125rem;
		}

		input[type="text"],
		textarea {
			font-size: 0.8125rem;
			padding: 0.625rem;
		}

		.map-container {
			height: 280px;
		}

		.map-header {
			padding: 1rem;
		}

		.map-header h3 {
			font-size: 1rem;
		}

		.image-previews {
			grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
		}

		.preview-image {
			height: 80px;
		}

		.hint {
			font-size: 0.7rem;
		}
	}

	@media (max-width: 375px) {
		.form-section {
			padding: 0.875rem;
		}

		h1 {
			font-size: 1.25rem;
		}

		.btn-upload {
			padding: 0.625rem 0.875rem;
			font-size: 0.75rem;
		}

		.map-container {
			height: 260px;
		}
	}

	/* Dark Mode Overrides */
	:global([data-theme="dark"]) .form-section {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .btn-upload {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) input[type="text"],
	:global([data-theme="dark"]) textarea {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	:global([data-theme="dark"]) .search-result-item {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .search-result-item:hover {
		background: var(--c-bg-subtle);
	}

	:global([data-theme="dark"]) .map-section {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .map-header {
		background: var(--c-bg-surface);
		border-bottom: 1px solid var(--c-border);
	}

	:global([data-theme="dark"]) .preview-image {
		background: var(--c-bg-subtle);
	}

	:global([data-theme="dark"]) .location-info-card {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .btn-change {
		background: var(--c-bg-surface);
	}

	:global([data-theme="dark"]) .btn-change:hover {
		background: var(--c-bg-subtle);
	}

	:global([data-theme="dark"]) .search-results {
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
	}
</style>
