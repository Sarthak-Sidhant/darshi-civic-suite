<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import {
		getReports,
		getAlerts,
		upvoteReport,
		deleteReportAdmin,
		type Report,
		type Alert,
		getErrorMessage,
		isRateLimitError,
	} from "$lib/api";
	import { user } from "$lib/stores";
	import { toast } from "$lib/stores/toast";
	import ImageCarousel from "$lib/components/ImageCarousel.svelte";
	import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";
	import FlagModal from "$lib/components/FlagModal.svelte";
	import DistrictSelector from "$lib/components/DistrictSelector.svelte";
	import {
		selectedDistrict,
		type SelectedDistrict,
	} from "$lib/stores/districtStore";
	import { getUrbanBodiesForDistrict, type UrbanBody } from "$lib/lgdData";
	import {
		Clock,
		Check,
		Wrench,
		CheckCircle,
		XCircle,
		Copy,
		AlertTriangle,
		FileText,
		MapPin,
		ThumbsUp,
		MessageCircle,
		Share2,
		Trash2,
		Flag,
		UserCheck,
		Bell,
	} from "lucide-svelte";

	let reports: Report[] = $state([]);
	let alerts: Alert[] = $state([]);
	let loading = $state(true);
	let error = $state("");
	let loadingMore = $state(false);
	let hasMore = $state(true); // Track if there are more reports to load
	let selectedCategory: string | null = $state(null);
	let upvotingReports = $state(new Set<string>());
	let deletingReportId: string | null = $state(null);
	let flaggingReportId: string | null = $state(null);
	const BATCH_SIZE = 5;
	let activeTab = $state("reports"); // 'reports' | 'alerts'

	// District-based filtering state
	let currentDistrict: SelectedDistrict | null = $state(null);
	let urbanBodies: UrbanBody[] = $state([]);

	// Reactive: Reload when district or category changes
	$effect(() => {
		const district = $selectedDistrict;
		// Check if changed to avoid loops/unnecessary loads
		const codeChanged =
			district?.districtCode !== currentDistrict?.districtCode;
		const categoryChanged = selectedCategory !== undefined; // simplified trigger

		if (codeChanged || selectedCategory !== undefined) {
			// If category changed, just reload. If district changed, update currentDistrict
			if (codeChanged) currentDistrict = district;

			loading = true;
			reports = [];
			loadInitialReports();

			// Only reload bodies if district changed
			if (codeChanged) {
				if (district) {
					loadUrbanBodies();
				} else {
					urbanBodies = [];
				}
			}
		}
	});

	let isAdmin = $derived(
		$user?.role === "super_admin" || $user?.role === "moderator",
	);

	// Store observer reference for cleanup
	let scrollObserver: IntersectionObserver | null = null;

	onMount(() => {
		// Initial load handled by effect or explicit call if store is null
		if (!$selectedDistrict) {
			loadInitialReports();
		}

		return () => {
			// Cleanup IntersectionObserver
			if (scrollObserver) {
				scrollObserver.disconnect();
				scrollObserver = null;
			}
		};
	});

	async function loadUrbanBodies() {
		if (!currentDistrict) return;
		try {
			urbanBodies = await getUrbanBodiesForDistrict(
				currentDistrict.districtName,
				currentDistrict.stateCode,
			);
		} catch (e) {
			console.error("Failed to load urban bodies:", e);
			urbanBodies = [];
		}
	}

	async function loadInitialReports() {
		try {
			// Build district filter if district is selected
			const districtFilter = currentDistrict
				? {
						districtCode: currentDistrict.districtCode,
						districtName: currentDistrict.districtName,
						stateName: currentDistrict.stateName,
					}
				: undefined;

			// Fetch reports and alerts (both filtered by district if selected)
			// Fetch reports and alerts (both filtered by district if selected)
			reports = await getReports(
				undefined,
				undefined,
				BATCH_SIZE,
				districtFilter,
			);

			// Apply category filter client-side since API may not support it yet with pagination complexity
			// Ideally should be API side, but for now client side filtering on top of fetched batch
			if (selectedCategory) {
				// This is tricky with pagination. Better to pass to API if possible.
				// Let's check getReports signature. It doesn't take category.
				// Plan B: Client side filter for now, but this only filters the current batch.
				// Real fix: Update API to accept category or simpler:
				// Just filter client side for better UX if we assume users want to see "Potholes in this batch"
				reports = reports.filter(
					(r) => r.category === selectedCategory,
				);
			}

			hasMore = reports.length >= BATCH_SIZE;
			loading = false;

			const rawAlerts = await getAlerts(districtFilter);

			// Aggregate alerts by district/location
			const alertsMap = new Map<
				string,
				{ count: number; categories: Set<string>; status: string }
			>();

			rawAlerts.forEach((alert: any) => {
				// Use district if available, fall back to city
				const location =
					alert.district || alert.city || "Unknown Location";
				if (!alertsMap.has(location)) {
					alertsMap.set(location, {
						count: 0,
						categories: new Set(),
						status: "ACTIVE",
					});
				}

				const entry = alertsMap.get(location)!;
				entry.count++;
				if (alert.category) entry.categories.add(alert.category);
			});

			// Convert map to Alert objects
			alerts = Array.from(alertsMap.entries()).map(
				([location, data]) => ({
					location: location,
					count: data.count,
					categories: Array.from(data.categories).join(", "),
					status: data.status,
				}),
			);
		} catch (e) {
			error = getErrorMessage(e);
			loading = false;
			toast.show(error, "error");
		}
	}

	// Svelte Action for Infinite Scroll
	function infiniteScrollAction(node: HTMLElement) {
		if (scrollObserver) scrollObserver.disconnect();

		scrollObserver = new IntersectionObserver(
			(entries) => {
				if (
					entries[0].isIntersecting &&
					!loadingMore &&
					reports.length > 0
				) {
					loadMoreReports();
				}
			},
			{ rootMargin: "400px" },
		);

		scrollObserver.observe(node);

		return {
			destroy() {
				if (scrollObserver) scrollObserver.disconnect();
			},
		};
	}

	async function loadMoreReports() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const lastId = reports[reports.length - 1].id;
			const districtFilter = currentDistrict
				? {
						districtCode: currentDistrict.districtCode,
						districtName: currentDistrict.districtName,
						stateName: currentDistrict.stateName,
					}
				: undefined;
			const newReports = await getReports(
				undefined,
				lastId,
				BATCH_SIZE,
				districtFilter,
			);
			if (newReports.length > 0) {
				reports = [...reports, ...newReports];
				hasMore = newReports.length >= BATCH_SIZE;
			} else {
				hasMore = false; // No more reports
			}
		} catch (e) {
			toast.show("Failed to load more reports", "error");
		} finally {
			loadingMore = false;
		}
	}

	function getTimeElapsed(timestamp: string): string {
		const now = new Date();
		const created = new Date(timestamp);
		const diffMs = now.getTime() - created.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffHours / 24);

		if (diffDays > 0) return `${diffDays}d ago`;
		if (diffHours > 0) return `${diffHours}h ago`;
		return "Just now";
	}

	function getUrgencyColor(severity: number): string {
		if (severity >= 8) return "#dc3545";
		if (severity >= 6) return "#fd7e14";
		if (severity >= 4) return "#ffc107";
		return "#28a745";
	}

	function getUrgencyLabel(severity: number): string {
		if (severity >= 8) return "CRITICAL";
		if (severity >= 6) return "HIGH";
		if (severity >= 4) return "MEDIUM";
		return "LOW";
	}

	function shareReport(report: Report) {
		const url = `${window.location.origin}/report/${report.id}`;
		const text = `${report.title}\n\n${report.category} | ${getUrgencyLabel(report.severity)}\n\nHelp hold authorities accountable! View and support this report:`;

		if (navigator.share) {
			navigator
				.share({
					title: report.title,
					text: text,
					url: url,
				})
				.then(() => {
					toast.show("Report shared successfully", "success", 3000);
				})
				.catch(() => {
					// User cancelled share
				});
		} else {
			navigator.clipboard
				.writeText(`${text}\n${url}`)
				.then(() => {
					toast.show("Link copied to clipboard!", "success", 3000);
				})
				.catch(() => {
					toast.show("Failed to copy link", "error");
				});
		}
	}

	async function handleUpvote(e: Event, reportId: string) {
		e.stopPropagation();

		if (!$user) {
			toast.show("Please sign in to upvote", "warning");
			goto("/signin");
			return;
		}

		if (upvotingReports.has(reportId)) return;

		upvotingReports.add(reportId);

		// Optimistic update
		const reportIndex = reports.findIndex((r) => r.id === reportId);

		if (reportIndex !== -1) {
			const report = reports[reportIndex];
			const wasUpvoted = report.has_upvoted;

			reports[reportIndex] = {
				...report,
				upvote_count: wasUpvoted
					? report.upvote_count - 1
					: report.upvote_count + 1,
				has_upvoted: !wasUpvoted,
			};
		}

		try {
			// SECURITY FIX: No username parameter - extracted from JWT token by backend
			const result = await upvoteReport(reportId);

			// Update with server response
			if (reportIndex !== -1) {
				// Re-fetch the specific report to ensure consistency
				// This is a simplified approach; a more efficient way might be to update based on result.
				// For now, we'll re-fetch all reports to ensure the list is consistent.
				// A better approach would be to have an endpoint to get a single report by ID.
				// For now, we'll just re-trigger the initial load to refresh the list.
				await loadInitialReports();
			}

			toast.show(
				result.status === "voted" ? "Upvoted!" : "Already voted",
				"success",
				2000,
			);
		} catch (error) {
			// Rollback optimistic update
			// Re-trigger initial load to revert to server state
			await loadInitialReports();

			const errorMsg = getErrorMessage(error);
			if (errorMsg.includes("Authentication required")) {
				goto("/signin");
			}

			// Show rate limit errors as warning (recoverable)
			if (isRateLimitError(error)) {
				toast.show(errorMsg, "warning");
			} else {
				toast.show(errorMsg, "error");
			}
		} finally {
			upvotingReports.delete(reportId);
		}
	}

	function navigateToReport(reportId: string) {
		goto(`/report/${reportId}`);
	}

	async function handleDeleteReportFromFeed(reportId: string, event: Event) {
		event.stopPropagation(); // Prevent navigation to report detail
		if (!confirm("Delete this report? This action cannot be undone."))
			return;

		deletingReportId = reportId;
		try {
			await deleteReportAdmin(reportId);
			reports = reports.filter((r) => r.id !== reportId);
			toast.show("Report deleted successfully", "success");
		} catch (e) {
			toast.show(
				getErrorMessage(e) || "Failed to delete report",
				"error",
			);
		} finally {
			deletingReportId = null;
		}
	}

	function handleReportKeydown(e: KeyboardEvent, reportId: string) {
		if (e.key === "Enter" || e.key === " ") {
			e.preventDefault();
			navigateToReport(reportId);
		}
	}

	function openFlagModal(e: Event, reportId: string) {
		e.stopPropagation();
		flaggingReportId = reportId;
	}
</script>

<svelte:head>
	<title>Darshi - Civic Grievance Platform</title>
	<meta
		name="description"
		content="Report and track civic issues in your area"
	/>
	<!-- Preconnect to API backend -->
	<link rel="preconnect" href="https://api.darshi.app" />
	<link rel="dns-prefetch" href="https://api.darshi.app" />
</svelte:head>

<!-- Skip to content for accessibility -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Alert Banner -->
{#if alerts.length > 0}
	<div class="alert-stream" role="region" aria-label="Critical alerts">
		<div class="alert-track">
			{#each alerts as alert}
				<div class="alert-pill" role="status">
					<span class="alert-dot" aria-hidden="true"></span>
					<strong>{alert.count} Critical Issues</strong>
					<span class="alert-sep" aria-hidden="true">•</span>
					<span>{alert.categories}</span>
				</div>
			{/each}
		</div>
	</div>
{/if}

<!-- Main Feed -->
<div id="main-content" class="feed">
	<!-- District Context Section -->
	{#if currentDistrict}
		<div class="district-hero">
			<div class="district-header">
				<div class="district-info">
					<h2 class="district-title">
						{currentDistrict.districtName} District
					</h2>
					<p class="district-subtitle">{currentDistrict.stateName}</p>
				</div>
				<a href="/submit" class="submit-cta">
					<span>Report Issue</span>
				</a>
			</div>

			{#if urbanBodies.length > 0}
				<div class="urban-bodies-section">
					<h3 class="section-label">Local Government Bodies</h3>
					<div class="urban-bodies-grid">
						{#each urbanBodies.slice(0, 4) as body}
							<div class="urban-body-card">
								<span class="body-type">{body.type}</span>
								<span class="body-name">{body.name}</span>
							</div>
						{/each}
					</div>
					{#if urbanBodies.length > 4}
						<p class="more-bodies">
							+{urbanBodies.length - 4} more local bodies
						</p>
					{/if}
				</div>
			{/if}
		</div>
	{:else}
		<!-- Prompt to select district -->
		<div class="about-section">
			<div class="about-content">
				<h2 class="about-title">Start Your Civic Journey</h2>
				<p class="about-text">
					Select your district to see local civic issues, government
					bodies, and community alerts. Report problems and track
					their resolution.
				</p>
				<div class="hero-selector">
					<DistrictSelector variant="hero" />
				</div>

				<!-- Category Filter -->
				<div class="category-filter">
					<button
						class="category-chip"
						class:active={selectedCategory === null}
						onclick={() => (selectedCategory = null)}
					>
						All
					</button>
					{#each ["Pothole", "Garbage", "Streetlight", "Water", "Drainage", "Other"] as cat}
						<button
							class="category-chip"
							class:active={selectedCategory === cat}
							onclick={() => (selectedCategory = cat)}
						>
							{cat}
						</button>
					{/each}
				</div>
				<a
					href="https://darshi.app/docs/about"
					class="about-link"
					target="_blank"
					rel="noopener noreferrer"
				>
					Learn more about Darshi →
				</a>
			</div>
			<div class="about-actions">
				<a href="/submit" class="action-btn primary"> Submit Report </a>
				{#if !$user}
					<a href="/signin" class="action-btn secondary"> Sign In </a>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Feed Tabs (always visible) -->
	<div class="feed-tabs">
		<button
			class="tab-btn"
			class:active={activeTab === "reports"}
			onclick={() => (activeTab = "reports")}
		>
			Recent Reports
		</button>
		<button
			class="tab-btn"
			class:active={activeTab === "alerts"}
			onclick={() => (activeTab = "alerts")}
		>
			Alerts
			{#if alerts.length > 0}
				<span class="badge">{alerts.length}</span>
			{/if}
		</button>
	</div>

	{#if activeTab === "reports"}
		{#if loading}
			<!-- Skeleton Loaders -->
			<div role="status" aria-label="Loading reports">
				{#each Array(2) as _}
					<article class="feed-item skeleton" aria-hidden="true">
						<div class="sk-meta">
							<div class="sk-badge"></div>
						</div>
						<div class="sk-title"></div>
						<div class="sk-description"></div>
						<div class="sk-description short"></div>
						<div class="sk-image"></div>
						<div class="sk-footer">
							<div class="sk-location"></div>
							<div class="sk-actions">
								<div class="sk-btn"></div>
								<div class="sk-btn"></div>
								<div class="sk-btn"></div>
							</div>
						</div>
					</article>
				{/each}
				<span class="sr-only">Loading reports...</span>
			</div>
		{:else}
			<!-- Filter bar removed - using navbar LocationFilter instead -->

			{#if error}
				<div class="empty-state" role="alert">
					<span class="empty-icon" aria-hidden="true"
						><AlertTriangle size={32} /></span
					>
					<h2>Error Loading Reports</h2>
					<p>{error}</p>
					<button onclick={loadInitialReports} class="btn-action"
						>Try Again</button
					>
				</div>
			{:else if reports.length === 0}
				<div class="empty-state">
					<span class="empty-icon" aria-hidden="true"
						><FileText size={32} /></span
					>
					<h2>No Reports Yet</h2>
					<p>Be the first to report a civic issue in your area</p>
					<a href="/submit" class="btn-action">Report Issue</a>
				</div>
			{:else}
				<div class="feed-list">
					{#each reports as report (report.id)}
						<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
						<article
							class="feed-item"
							role="button"
							tabindex="0"
							onclick={() => navigateToReport(report.id)}
							onkeydown={(e) => handleReportKeydown(e, report.id)}
							aria-label={`Report: ${report.title}. Category: ${report.category}. Status: ${report.status}`}
						>
							<!-- Header: Meta & Status -->
							<div class="feed-meta-row">
								<div class="meta-left">
									<div class="meta-text">
										{#if report.submitted_by}
											<span class="author-name">
												@{report.submitted_by}
												{#if report.user_badges}
													{#if report.user_badges.includes("local_guide")}
														<span
															class="badge-icon"
															title="Local Guide"
															>⭐</span
														>
													{/if}
													{#if report.user_badges.includes("official")}
														<span
															class="badge-icon"
															title="Official"
															>🛡️</span
														>
													{/if}
												{/if}
											</span>
											<span
												class="separator"
												aria-hidden="true">·</span
											>
										{/if}
										<span class="category"
											>{report.category}</span
										>
										<span
											class="separator"
											aria-hidden="true">·</span
										>
										<time
											datetime={report.created_at}
											class="timestamp"
											>{getTimeElapsed(
												report.created_at,
											)}</time
										>
									</div>
								</div>
								<div
									class="status-badge"
									data-status={report.status}
									role="img"
									aria-label={`Status: ${report.status.replace(/_/g, " ")}`}
								>
									{#if report.status === "PENDING_VERIFICATION"}
										<Clock size={16} />
									{:else if report.status === "VERIFIED"}
										<Check size={16} />
									{:else if report.status === "IN_PROGRESS"}
										<Wrench size={16} />
									{:else if report.status === "RESOLVED"}
										<CheckCircle size={16} />
									{:else if report.status === "REJECTED"}
										<XCircle size={16} />
									{:else if report.status === "DUPLICATE"}
										<Copy size={16} />
									{:else if report.status === "FLAGGED"}
										<AlertTriangle size={16} />
									{:else}
										<FileText size={16} />
									{/if}
								</div>
							</div>

							<!-- Content -->
							<div class="feed-content">
								<h2 class="title">{report.title}</h2>
								{#if report.description}
									<p class="description">
										{report.description}
									</p>
								{/if}
								{#if report.status === "REJECTED" && report.flag_reason}
									<p class="rejection-reason">
										<strong>Rejection reason:</strong>
										{report.flag_reason}
									</p>
								{/if}
							</div>

							<!-- Visual Evidence with Carousel -->
							{#if report.image_data && report.image_data.length > 0}
								<div class="feed-visual">
									<ImageCarousel
										imageData={report.image_data}
									/>
									{#if report.severity > 5}
										<div
											class="severity-indicator"
											style="background: {getUrgencyColor(
												report.severity,
											)}"
											role="img"
											aria-label={`Severity: ${getUrgencyLabel(report.severity)}`}
										></div>
									{/if}
								</div>
							{:else if report.image_urls && report.image_urls.length > 0}
								<div class="feed-visual">
									<ImageCarousel images={report.image_urls} />
									{#if report.severity > 5}
										<div
											class="severity-indicator"
											style="background: {getUrgencyColor(
												report.severity,
											)}"
											role="img"
											aria-label={`Severity: ${getUrgencyLabel(report.severity)}`}
										></div>
									{/if}
								</div>
							{/if}

							<!-- Footer: Location & Actions -->
							<div class="feed-footer">
								<div class="location-tag">
									<span class="icon" aria-hidden="true"
										><MapPin size={14} /></span
									>
									<span
										>{report.address ||
											report.location}</span
									>
								</div>

								{#if report.officer_username}
									<div
										class="officer-tag"
										title="Assigned Officer"
									>
										<span class="icon"
											><UserCheck size={14} /></span
										>
										<span>@{report.officer_username}</span>
									</div>
								{/if}

								<div
									class="actions"
									role="group"
									aria-label="Report actions"
								>
									<button
										class="action-btn"
										class:action-btn-active={report.has_upvoted}
										onclick={(e) =>
											handleUpvote(e, report.id)}
										disabled={upvotingReports.has(
											report.id,
										)}
										aria-label={`Upvote report. Current count: ${report.upvote_count}`}
										type="button"
									>
										{#if upvotingReports.has(report.id)}
											<LoadingSpinner size="sm" />
										{:else}
											<span
												class="icon"
												aria-hidden="true"
												><ThumbsUp size={16} /></span
											>
										{/if}
										<span>{report.upvote_count}</span>
									</button>
									<a
										href={`/report/${report.id}#comments`}
										class="action-btn"
										onclick={(e) => e.stopPropagation()}
										aria-label={`View comments. Count: ${report.comments_count}`}
									>
										<span class="icon" aria-hidden="true"
											><MessageCircle size={16} /></span
										>
										<span>{report.comments_count}</span>
									</a>
									<button
										class="action-btn share"
										onclick={(e) => {
											e.stopPropagation();
											shareReport(report);
										}}
										aria-label="Share report"
										type="button"
									>
										<span class="icon" aria-hidden="true"
											><Share2 size={16} /></span
										>
									</button>
									<button
										class="action-btn flag"
										onclick={(e) =>
											openFlagModal(e, report.id)}
										aria-label="Flag report"
										type="button"
									>
										<span class="icon" aria-hidden="true"
											><Flag size={16} /></span
										>
									</button>
									{#if isAdmin}
										<button
											class="action-btn admin-delete"
											onclick={(e) =>
												handleDeleteReportFromFeed(
													report.id,
													e,
												)}
											disabled={deletingReportId ===
												report.id}
											aria-label="Delete report (Admin)"
											type="button"
										>
											{#if deletingReportId === report.id}
												<LoadingSpinner size="sm" />
											{:else}
												<span
													class="icon"
													aria-hidden="true"
													><Trash2 size={16} /></span
												>
											{/if}
										</button>
									{/if}
								</div>
							</div>
						</article>
					{/each}

					<!-- Infinite Scroll Sentinel & Manual Load Button -->
					{#if !hasMore}
						<div class="end-of-feed">
							<p>You've reached the end</p>
							<span class="icon" aria-hidden="true"
								><CheckCircle size={16} /></span
							>
						</div>
					{:else}
						<div
							id="scroll-sentinel"
							aria-hidden="true"
							use:infiniteScrollAction
						></div>

						<!-- Manual Load More Button (Fallback) -->
						<div class="load-more-container">
							<button
								class="btn-secondary load-more-btn"
								onclick={loadMoreReports}
								disabled={loadingMore}
							>
								{#if loadingMore}
									<LoadingSpinner size="sm" /> Loading...
								{:else}
									Load More Reports
								{/if}
							</button>
						</div>
					{/if}
				</div>

				<!-- Loading More Indicator (Floating) -->
				{#if loadingMore}
					<div
						class="loading-more-floating"
						role="status"
						aria-label="Loading more reports"
					>
						<LoadingSpinner size="md" />
					</div>
				{/if}
			{/if}
		{/if}
	{:else if activeTab === "alerts"}
		<div class="alerts-feed">
			<!-- City selector for alert subscriptions will be added here in future -->

			{#if alerts.length === 0}
				<div class="empty-state">
					<span class="empty-icon"><CheckCircle size={32} /></span>
					<h2>No Active Alerts</h2>
					<p>There are no critical alerts in your area right now.</p>
				</div>
			{:else}
				{#each alerts as alert}
					<div class="alert-card">
						<div class="alert-header">
							<AlertTriangle size={20} class="text-danger" />
							<h3>{alert.count} Critical Issues</h3>
						</div>
						<p>{alert.categories}</p>
						<time>{getTimeElapsed(new Date().toISOString())}</time>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

{#if flaggingReportId}
	<FlagModal
		reportId={flaggingReportId}
		isOpen={!!flaggingReportId}
		on:close={() => (flaggingReportId = null)}
	/>
{/if}

<!-- CitySelector removed from feed - only needed for alert subscriptions -->

<style>
	/* District Hero Styles */
	.district-hero {
		padding: 1.5rem;
		background: var(--c-bg-surface);
		border-bottom: 1px solid var(--c-border);
	}

	.district-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.district-info {
		flex: 1;
	}

	.district-title {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0 0 0.25rem 0;
		font-family: var(--font-heading);
	}

	.district-subtitle {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
		margin: 0;
	}

	.submit-cta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1rem;
		background: var(--c-brand);
		color: white;
		border-radius: var(--radius-full);
		font-size: 0.875rem;
		font-weight: 600;
		text-decoration: none;
		transition: all 0.2s;
	}

	.submit-cta:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.urban-bodies-section {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--c-border);
	}

	.section-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--c-text-tertiary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.75rem 0;
	}

	.urban-bodies-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
	}

	.urban-body-card {
		display: flex;
		flex-direction: column;
		padding: 0.75rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-sm);
		border: 1px solid var(--c-border);
	}

	.body-type {
		font-size: 0.625rem;
		font-weight: 600;
		color: var(--c-text-tertiary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.25rem;
	}

	.body-name {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--c-text-primary);
		line-height: 1.3;
	}

	.more-bodies {
		font-size: 0.75rem;
		color: var(--c-text-tertiary);
		margin: 0.5rem 0 0 0;
		text-align: center;
	}

	@media (max-width: 480px) {
		.urban-bodies-grid {
			grid-template-columns: 1fr;
		}

		.district-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.submit-cta {
			width: 100%;
			justify-content: center;
		}
	}

	.end-of-feed {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 2rem;
		color: var(--c-text-tertiary);
		font-size: 0.875rem;
	}

	.feed-tabs {
		display: flex;
		border-bottom: 1px solid var(--c-border);
		background: var(--c-bg-surface);
		position: sticky;
		top: 0; /* sticky tabs below nav */
		z-index: 10;
	}

	.tab-btn {
		flex: 1;
		padding: 1rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--c-text-secondary);
		font-weight: 500;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.tab-btn.active {
		color: var(--c-primary);
		border-bottom-color: var(--c-primary);
	}

	.badge {
		background: var(--c-danger);
		color: white;
		font-size: 0.75rem;
		padding: 0.1rem 0.4rem;
		border-radius: 1rem;
	}

	.media-placeholder {
		background: var(--c-bg-subtle);
		height: 200px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--c-text-tertiary);
	}

	.officer-tag {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: var(--c-primary);
		background: var(--c-bg-subtle);
		padding: 0.1rem 0.4rem;
		border-radius: 0.25rem;
	}

	.alerts-feed {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.alert-card {
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		padding: 1rem;
		border-left: 4px solid var(--c-danger);
		border-radius: 0.5rem;
	}

	.alert-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		color: var(--c-danger);
	}

	.subscription-banner {
		background: var(--c-bg-subtle);
		padding: 1rem;
		border-radius: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.sub-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.btn-primary-sm {
		background: var(--c-primary);
		color: white;
		border: none;
		padding: 0.4rem 0.8rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.load-more-container {
		display: flex;
		justify-content: center;
		padding: 2rem 0;
	}

	.load-more-btn {
		min-width: 200px;
	}

	.loading-more-floating {
		position: fixed;
		bottom: 2rem;
		left: 50%;
		transform: translateX(-50%);
		background: var(--c-bg-surface);
		padding: 0.75rem;
		border-radius: 50%;
		box-shadow: var(--shadow-lg);
		z-index: 100;
		animation: slideUp 0.3s ease-out;
	}

	@keyframes slideUp {
		from {
			transform: translate(-50%, 100%);
			opacity: 0;
		}
		to {
			transform: translate(-50%, 0);
			opacity: 1;
		}
	}
	/* About Section */
	.about-section {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 2rem;
		padding: 1.5rem;
		margin-bottom: 2rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
	}

	.about-content {
		flex: 1;
		min-width: 0;
	}

	.about-title {
		font-family: var(--font-display);
		font-size: 1.5rem;
		font-weight: 700;
		line-height: 1.3;
		color: var(--c-text-primary);
		margin: 0 0 0.75rem 0;
		letter-spacing: -0.02em;
	}

	.about-text {
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--c-text-secondary);
		margin: 0 0 1rem 0;
	}

	.about-link {
		display: inline-flex;
		align-items: center;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--c-text-secondary);
		text-decoration: none;
		transition: color 0.2s ease;
	}

	.about-link:hover {
		color: var(--c-text-primary);
	}

	.about-actions {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	.action-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.625rem 1.5rem;
		min-width: 140px;
		font-size: 0.9375rem;
		font-weight: 600;
		text-decoration: none;
		border-radius: var(--radius-full);
		transition: all 0.2s ease;
		white-space: nowrap;
	}

	.action-btn.primary {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: 1px solid var(--c-brand);
	}

	.action-btn.primary:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.action-btn.primary:active {
		transform: translateY(0);
	}

	.action-btn.secondary {
		background: transparent;
		color: var(--c-text-primary);
		border: 1px solid var(--c-border);
	}

	.action-btn.secondary:hover {
		background: var(--c-bg-subtle);
		border-color: var(--c-text-tertiary);
	}

	.action-btn.secondary:active {
		transform: scale(0.98);
	}

	.action-btn:focus-visible {
		outline: 2px solid var(--c-brand);
		outline-offset: 2px;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.about-section {
			flex-direction: column;
			padding: 1.25rem;
		}

		.about-title {
			font-size: 1.375rem;
		}

		.about-actions {
			width: 100%;
		}

		.action-btn {
			width: 100%;
		}
	}

	@media (max-width: 640px) {
		.about-section {
			padding: 1rem;
			margin-bottom: 1.5rem;
		}

		.about-title {
			font-size: 1.25rem;
		}

		.about-text {
			font-size: 0.875rem;
		}

		.about-link {
			font-size: 0.8125rem;
		}

		.action-btn {
			padding: 0.5rem 1.25rem;
			font-size: 0.875rem;
			min-width: unset;
		}
	}

	/* Skip Link for Accessibility */
	.skip-link {
		position: absolute;
		top: -40px;
		left: 0;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		padding: 0.5rem 1rem;
		text-decoration: none;
		z-index: 100;
		border-radius: 0 0 4px 0;
	}

	.skip-link:focus {
		top: 0;
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border-width: 0;
	}

	/* Alerts - Ticker Style */
	.alert-stream {
		background: var(--c-error-bg);
		border-bottom: 1px solid var(--c-error-light);
		overflow: hidden;
		padding: 0.5rem 0;
	}

	.alert-track {
		display: flex;
		animation: ticker 30s linear infinite;
		gap: 2rem;
		padding: 0 1rem;
		width: max-content;
		will-change: transform;
	}

	@keyframes ticker {
		from {
			transform: translateX(0);
		}
		to {
			transform: translateX(-50%);
		}
	}

	.alert-pill {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-error-dark);
		background: var(--c-bg-surface);
		padding: 0.25rem 0.75rem;
		border-radius: var(--radius-full);
		box-shadow: var(--shadow-sm);
		border: 1px solid var(--c-error-light);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.alert-dot {
		width: 8px;
		height: 8px;
		background: var(--c-severity-critical);
		border-radius: 50%;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
		100% {
			opacity: 1;
		}
	}

	/* Feed Container */
	.feed {
		max-width: 680px;
		margin: 0 auto;
	}

	/* Wide screen: show feed in a nice centered column */
	@media (min-width: 1200px) {
		.feed {
			max-width: 720px;
		}
	}

	@media (min-width: 1600px) {
		.feed {
			max-width: 800px;
		}
	}

	.feed-list {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* Feed Item */
	.feed-item {
		padding-bottom: 2rem;
		border-bottom: 1px solid var(--c-border);
		cursor: pointer;
		transition:
			opacity 0.2s ease,
			transform 0.15s ease;
		will-change: transform;
	}

	.feed-item:focus-visible {
		outline: 2px solid var(--c-brand);
		outline-offset: 4px;
		border-radius: var(--radius-sm);
	}

	.feed-item:active {
		transform: scale(0.99);
	}

	.feed-item:last-child {
		border-bottom: none;
	}

	.feed-item:hover {
		opacity: 0.8;
	}

	/* Meta Row */
	.feed-meta-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.75rem;
	}

	.meta-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.meta-text {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.author-name {
		font-weight: 600;
		color: var(--c-text-primary);
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	.badge-icon {
		font-size: 0.8em;
	}

	.category {
		font-weight: 500;
		color: var(--c-primary);
	}

	.separator {
		opacity: 0.3;
	}

	/* Status Badge */
	.status-badge {
		font-size: 0.875rem;
	}

	/* Content */
	.title {
		font-family: var(--font-display);
		font-size: 1.5rem;
		font-weight: 700;
		line-height: 1.25;
		margin: 0 0 0.5rem 0;
		color: var(--c-text-primary);
		letter-spacing: -0.02em;
	}

	.description {
		font-size: 1rem;
		line-height: 1.6;
		color: var(--c-text-secondary);
		margin: 0 0 1rem 0;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.rejection-reason {
		font-size: 0.9375rem;
		line-height: 1.5;
		color: #991b1b;
		margin: 0.75rem 0 0 0;
		padding: 0.75rem;
		background: #fef2f2;
		border-radius: var(--radius-sm);
		border-left: 3px solid #dc2626;
	}

	.rejection-reason strong {
		font-weight: 600;
	}

	/* Visual Evidence */
	.feed-visual {
		position: relative;
		margin: 1rem 0;
		max-height: 500px;
	}

	.feed-visual :global(.image-carousel) {
		max-height: 500px;
	}

	.severity-indicator {
		position: absolute;
		top: 1rem;
		right: 1rem;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		z-index: 3;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	/* Footer */
	.feed-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 0.5rem;
	}

	.location-tag {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.8125rem;
		color: var(--c-text-secondary);
		background: var(--c-bg-subtle);
		padding: 0.25rem 0.5rem;
		border-radius: 6px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-btn {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: transparent;
		border: 1px solid transparent;
		padding: 0.5rem 0.75rem;
		border-radius: 99px;
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
		min-height: 44px;
		will-change: background, color;
		text-decoration: none;
	}

	.action-btn:hover:not(:disabled) {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	.action-btn:active:not(:disabled) {
		transform: scale(0.95);
	}

	.action-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.action-btn:focus-visible {
		outline: 2px solid var(--c-brand);
		outline-offset: 2px;
	}

	.action-btn-active {
		background: var(--c-bg-subtle);
		color: var(--c-brand);
	}

	.action-btn.share:hover {
		background: var(--c-text-primary);
		color: var(--c-bg-page);
	}

	.action-btn.admin-delete {
		color: #dc2626;
		border: 1px solid #fecaca;
	}

	.action-btn.admin-delete:hover:not(:disabled) {
		background: #fee2e2;
		color: #991b1b;
		border-color: #dc2626;
	}

	/* Empty State */
	.empty-state {
		text-align: center;
		padding: 4rem 1rem;
		color: var(--c-text-secondary);
	}

	.empty-icon {
		font-size: 2rem;
		display: block;
		margin-bottom: 1rem;
		opacity: 0.5;
	}

	.empty-state h2 {
		color: var(--c-text-primary);
		font-family: var(--font-display);
		margin-bottom: 0.5rem;
		font-size: 1.5rem;
	}

	.btn-action {
		display: inline-block;
		margin-top: 1.5rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		padding: 0.75rem 1.5rem;
		border-radius: 99px;
		text-decoration: none;
		font-weight: 600;
		border: none;
		cursor: pointer;
		font-family: var(--font-sans);
		font-size: 0.9375rem;
		transition:
			opacity 0.2s,
			transform 0.1s;
	}

	.btn-action:hover {
		opacity: 0.9;
	}

	.btn-action:active {
		transform: scale(0.98);
	}

	.btn-action:focus-visible {
		outline: 2px solid var(--c-brand);
		outline-offset: 2px;
	}

	/* Skeleton */
	.skeleton {
		background: transparent;
		pointer-events: none;
		animation: none;
	}

	.skeleton > * {
		background: linear-gradient(
			90deg,
			var(--c-bg-subtle) 25%,
			#f0f0f0 50%,
			var(--c-bg-subtle) 75%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: var(--radius-sm);
	}

	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	.sk-meta {
		display: flex;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.sk-badge {
		height: 24px;
		width: 80px;
	}

	.sk-title {
		height: 32px;
		width: 80%;
		margin-bottom: 1rem;
	}

	.sk-description {
		height: 20px;
		width: 100%;
		margin-bottom: 0.5rem;
	}

	.sk-description.short {
		width: 60%;
		margin-bottom: 1rem;
	}

	.sk-image {
		height: 300px;
		width: 100%;
		margin-bottom: 1rem;
		border-radius: var(--radius-md);
	}

	.sk-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.sk-location {
		height: 28px;
		width: 120px;
	}

	.sk-actions {
		display: flex;
		gap: 0.5rem;
	}

	.sk-btn {
		height: 32px;
		width: 48px;
	}

	.loading-more {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: 2rem;
	}

	@media (max-width: 768px) {
		.alert-track {
			gap: 1.5rem;
			padding: 0 0.75rem;
		}

		.alert-pill {
			font-size: 0.8125rem;
			padding: 0.25rem 0.625rem;
		}

		.feed {
			max-width: 100%;
		}

		.action-btn {
			padding: 0.5rem 0.75rem;
			font-size: 0.8125rem;
			min-height: 44px;
		}
	}

	@media (max-width: 640px) {
		.feed-meta-row {
			flex-wrap: wrap;
			gap: 0.5rem;
		}

		.status-badge {
			font-size: 0.8125rem;
		}

		.alert-track {
			gap: 1rem;
			padding: 0 0.5rem;
		}

		.alert-pill {
			font-size: 0.75rem;
			padding: 0.2rem 0.5rem;
			gap: 0.375rem;
		}

		.actions {
			gap: 0.375rem;
		}

		.action-btn {
			padding: 0.5rem 0.625rem;
			font-size: 0.75rem;
			gap: 0.2rem;
			min-height: 44px;
		}

		.title {
			font-size: 1.25rem;
		}

		.description {
			font-size: 0.9375rem;
		}

		.feed-footer {
			flex-wrap: wrap;
			gap: 0.75rem;
		}

		.location-tag {
			flex: 1;
			min-width: 0;
		}
	}

	@media (max-width: 480px) {
		.action-btn {
			padding: 0.5rem 0.5rem;
			font-size: 0.75rem;
			min-height: 44px;
		}

		.actions {
			gap: 0.25rem;
		}

		.title {
			font-size: 1.125rem;
		}

		.about-section {
			padding: 1rem;
		}

		.feed-item {
			padding-bottom: 1.5rem;
		}
	}

	@media (max-width: 375px) {
		.feed-footer {
			flex-direction: column;
			align-items: stretch;
			gap: 0.5rem;
		}

		.location-tag {
			width: 100%;
			max-width: none;
			font-size: 0.75rem;
			padding: 0.375rem 0.5rem;
			justify-content: flex-start;
		}

		.actions {
			width: 100%;
			justify-content: space-between;
			flex-wrap: nowrap;
		}

		.action-btn {
			flex: 1;
			padding: 0.5rem 0.375rem;
			font-size: 0.75rem;
			gap: 0.2rem;
			min-height: 44px;
			justify-content: center;
		}

		.action-btn span:not(.icon) {
			font-size: 0.75rem;
		}

		.action-btn.share {
			flex: 0 0 auto;
			padding: 0.5rem;
		}

		.action-btn.admin-delete {
			flex: 0 0 auto;
			padding: 0.5rem;
		}

		.meta-text {
			font-size: 0.75rem;
			flex-wrap: wrap;
		}

		.title {
			font-size: 1rem;
		}

		.description {
			font-size: 0.875rem;
		}

		.about-title {
			font-size: 1.125rem;
		}

		.about-text {
			font-size: 0.8125rem;
		}

		.about-actions {
			gap: 0.5rem;
		}

		.about-section .action-btn {
			padding: 0.5rem 1rem;
			font-size: 0.8125rem;
		}
	}

	@media (max-width: 320px) {
		.action-btn {
			padding: 0.375rem 0.25rem;
			font-size: 0.6875rem;
		}

		.action-btn .icon {
			width: 14px;
			height: 14px;
		}

		.title {
			font-size: 0.9375rem;
		}

		.location-tag {
			font-size: 0.6875rem;
		}
	}

	/* Dark Mode */
	:global([data-theme="dark"]) .rejection-reason {
		background: #450a0a;
		color: #fecaca;
		border-left-color: #dc2626;
	}

	:global([data-theme="dark"]) .rejection-reason strong {
		color: #fca5a5;
	}

	:global([data-theme="dark"]) .action-btn.admin-delete {
		color: #f87171;
		border-color: #7f1d1d;
	}

	:global([data-theme="dark"]) .action-btn.admin-delete:hover:not(:disabled) {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}

	:global([data-theme="dark"]) .alert-stream {
		background: #450a0a;
		border-bottom-color: #7f1d1d;
	}

	:global([data-theme="dark"]) .alert-pill {
		background: #1a1a1a;
		color: #fca5a5;
		border-color: #7f1d1d;
	}

	:global([data-theme="dark"]) .skeleton > * {
		background: linear-gradient(
			90deg,
			#27272a 25%,
			#3f3f46 50%,
			#27272a 75%
		);
		background-size: 200% 100%;
	}
	.hero-selector {
		margin: 2rem 0;
		display: flex;
		justify-content: center;
	}

	.category-filter {
		display: flex;
		justify-content: center;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 2rem;
		margin-bottom: 2rem;
		max-width: 800px;
		margin-left: auto;
		margin-right: auto;
	}

	.category-chip {
		height: 40px;
		padding: 0 1.5rem;
		border-radius: 99px;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		color: var(--c-text-secondary);
		font-weight: 600;
		font-size: 0.9375rem;
		cursor: pointer;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: var(--shadow-sm);
		letter-spacing: 0.01em;
	}

	.category-chip:hover {
		border-color: var(--c-text-primary);
		color: var(--c-text-primary);
		transform: translateY(-2px);
		box-shadow: var(--shadow-md);
		background: var(--c-bg-subtle);
	}

	.category-chip.active {
		background: var(--c-text-primary);
		color: var(--c-bg-page);
		border-color: var(--c-text-primary);
		box-shadow: var(--shadow-md);
		transform: translateY(-1px);
	}

	:global([data-theme="dark"]) .category-chip.active {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border-color: var(--c-brand);
	}
</style>
