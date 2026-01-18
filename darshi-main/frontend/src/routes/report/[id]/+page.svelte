<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import {
		getReport,
		getComments,
		upvoteReport,
		addComment,
		deleteComment,
		getErrorMessage,
		deleteReportAdmin,
		updateReportCategory,
		// updateReportStatus removed (imported later)
		getNearbyLandmarks,
		type Report,
		type Comment,
		type Landmark,
		getReportUpdates,
		createReportUpdate,
		type ReportUpdate,
	} from "$lib/api";
	import { user, isAuthenticated } from "$lib/stores";
	import { toast } from "$lib/stores/toast";
	import LoadingButton from "$lib/components/LoadingButton.svelte";
	import ImageCarousel from "$lib/components/ImageCarousel.svelte";
	import ReportMap from "$lib/components/ReportMap.svelte";
	import FlagModal from "$lib/components/FlagModal.svelte";
	import ResolutionModal from "$lib/components/ResolutionModal.svelte";
	import { updateReportStatus } from "$lib/api";
	import {
		AlertTriangle,
		MapPin,
		ThumbsUp,
		Share2,
		Clock,
		CheckCircle,
		Wrench,
		XCircle,
		Trash2,
		Edit,
		Shield,
		Navigation,
		Brain,
		Flag,
	} from "lucide-svelte";

	let report = $state<Report | null>(null);
	let comments: Comment[] = $state([]);
	let landmarks: Landmark[] = $state([]);
	let loading = $state(true);
	let loadingLandmarks = $state(false);
	let error = $state("");
	let commentText = $state("");
	let submittingComment = $state(false);
	let deletingCommentId: string | null = $state(null);
	let upvoting = $state(false);

	let reportId = $derived($page.params.id);
	let isAdmin = $derived(
		$user?.role === "super_admin" || $user?.role === "moderator",
	);
	let isAuthor = $derived(
		$user && report?.submitted_by && $user.username === report.submitted_by,
	);

	const MAX_COMMENT_LENGTH = 500;
	let commentLength = $derived(commentText.length);

	// Admin controls state
	let showEditCategory = $state(false);
	let newCategory = $state("");
	let updatingCategory = $state(false);
	let deletingReport = $state(false);
	let showFlagModal = $state(false);

	// Updates & Tabs
	let activeTab = $state("comments"); // 'comments' | 'updates'
	let updates: ReportUpdate[] = $state([]);
	let loadingUpdates = $state(false);
	let newUpdateContent = $state("");
	let submittingUpdate = $state(false);
	let isOfficialUpdate = $state(false);

	// Status Management
	let selectedStatus = $state("");
	let showResolutionModal = $state(false);
	let resolving = $state(false);

	let autoRefreshInterval: ReturnType<typeof setInterval> | null = null;

	onMount(() => {
		// Load report on mount
		if (reportId) {
			loadReport().then(() => {
				// Auto-refresh if report is pending verification (images still processing)
				if (report && report.status === "PENDING_VERIFICATION") {
					autoRefreshInterval = setInterval(async () => {
						if (!reportId) return;

						try {
							const updatedReport = await getReport(reportId);
							if (
								updatedReport.status !== "PENDING_VERIFICATION"
							) {
								// Status changed - reload full report and stop refreshing
								await loadReport();
								if (autoRefreshInterval) {
									clearInterval(autoRefreshInterval);
									autoRefreshInterval = null;
								}
							}
						} catch (e) {
							// Silently fail - user can manually refresh
						}
					}, 5000); // Check every 5 seconds
				}
			});
		}

		// Cleanup on unmount
		return () => {
			if (autoRefreshInterval) {
				clearInterval(autoRefreshInterval);
			}
		};
	});

	async function loadReport() {
		if (!reportId) return;

		try {
			const [reportData, commentsData, updatesData] = await Promise.all([
				getReport(reportId),
				getComments(reportId),
				getReportUpdates(reportId),
			]);
			report = reportData;
			updates = updatesData;

			// Compatibility: If older reports use 'location' field for address, use it.
			// Note: Backend now excludes raw geometry 'location' column.
			if (report && !report.address && report.location) {
				// If 'location' comes back as string (e.g. from older API), use it as address
				report.address = report.location;
			}

			comments = commentsData;

			// Load nearby landmarks after report is loaded
			if (report && report.latitude && report.longitude) {
				loadLandmarks();
			}
		} catch (e) {
			error = getErrorMessage(e);
		} finally {
			loading = false;
		}
	}

	async function loadLandmarks() {
		if (!reportId) return;

		loadingLandmarks = true;
		try {
			const data = await getNearbyLandmarks(reportId);
			landmarks = data.landmarks;
		} catch (e) {
			// Landmarks are optional, don't fail if they can't be loaded
			// Silent failure is intentional - landmarks are supplementary data
		} finally {
			loadingLandmarks = false;
		}
	}

	async function handleUpvote() {
		if (!$user || !reportId) {
			toast.show("Please sign in to upvote", "warning");
			// Redirect to signin
			goto("/signin");
			return;
		}

		upvoting = true;
		try {
			// SECURITY FIX: No username parameter - extracted from JWT token by backend
			await upvoteReport(reportId);
			await loadReport();
			toast.show("Upvoted successfully!", "success");
		} catch (e) {
			const errorMsg = getErrorMessage(e);
			if (errorMsg.includes("Authentication required")) {
				goto("/signin");
			}
			toast.show(errorMsg || "Failed to upvote", "error");
		} finally {
			upvoting = false;
		}
	}

	async function handleAddComment(e: Event) {
		e.preventDefault();
		if (!$user || !reportId) {
			toast.show("Please sign in to comment", "warning");
			goto("/signin");
			return;
		}

		if (!commentText.trim()) return;

		if (commentText.length > MAX_COMMENT_LENGTH) {
			toast.show(
				`Comment must be less than ${MAX_COMMENT_LENGTH} characters`,
				"error",
			);
			return;
		}

		submittingComment = true;
		try {
			// SECURITY FIX: No username parameter - extracted from JWT token by backend
			await addComment(reportId, commentText);
			commentText = "";
			comments = await getComments(reportId);
			if (report) report.comments_count += 1;
			toast.show("Comment added successfully!", "success");
		} catch (e) {
			const errorMsg = getErrorMessage(e);
			if (errorMsg.includes("Authentication required")) {
				goto("/signin");
			}
			toast.show(errorMsg || "Failed to add comment", "error");
		} finally {
			submittingComment = false;
		}
	}

	async function handleDeleteComment(commentId: string) {
		if (
			!reportId ||
			!confirm("Delete this comment? This action cannot be undone.")
		)
			return;

		deletingCommentId = commentId;
		try {
			await deleteComment(reportId, commentId);
			comments = await getComments(reportId);
			if (report) report.comments_count -= 1;
			toast.show("Comment deleted successfully", "success");
		} catch (e) {
			toast.show(
				getErrorMessage(e) || "Failed to delete comment",
				"error",
			);
		} finally {
			deletingCommentId = null;
		}
	}

	async function handleSubmitUpdate() {
		if (!newUpdateContent.trim() || submittingUpdate) return;

		submittingUpdate = true;
		try {
			const newUpdate = await createReportUpdate(
				reportId!,
				newUpdateContent,
				"public",
				isOfficialUpdate,
			);
			updates = [newUpdate, ...updates];
			newUpdateContent = "";
			toast.show("Update posted successfully", "success");
		} catch (e) {
			toast.show(getErrorMessage(e) || "Failed to post update", "error");
		} finally {
			submittingUpdate = false;
		}
	}

	async function handleStatusChange() {
		if (!selectedStatus) return; // or default to current status
		if (selectedStatus === "RESOLVED") {
			showResolutionModal = true;
			return;
		}
		await updateStatus(selectedStatus);
	}

	async function handleResolve(event: CustomEvent) {
		const { summary, imageUrl } = event.detail;
		resolving = true;
		await updateStatus("RESOLVED", { summary, imageUrl });
		resolving = false;
	}

	async function updateStatus(
		status: string,
		resolutionDetails?: { summary: string; imageUrl?: string },
	) {
		if (!reportId) return;
		try {
			await updateReportStatus(
				reportId,
				status,
				undefined,
				resolutionDetails?.summary,
				resolutionDetails?.imageUrl,
			);
			if (report) report.status = status;
			toast.show(`Status updated to ${status}`, "success");
			showResolutionModal = false;
			// Add timeline event manually if not re-fetching?
			// Better to re-fetch report to get updated timeline
			await loadReport();
		} catch (e) {
			toast.show(
				getErrorMessage(e) || "Failed to update status",
				"error",
			);
		}
	}

	function getUrgencyColor(severity: number): string {
		if (severity >= 8) return "#dc2626";
		if (severity >= 6) return "#ea580c";
		if (severity >= 4) return "#ca8a04";
		return "#16a34a";
	}

	function getUrgencyLabel(severity: number): string {
		if (severity >= 8) return "CRITICAL";
		if (severity >= 6) return "HIGH";
		if (severity >= 4) return "MEDIUM";
		return "LOW";
	}

	function shareReport() {
		if (!report) return;

		const url = `${window.location.origin}/report/${report.id}`;
		const text = `${report.title}\n\n${report.category} | ${getUrgencyLabel(report.severity)}\n\nHelp hold authorities accountable:`;

		if (navigator.share) {
			navigator
				.share({ title: report.title, text: text, url: url })
				.catch(() => {
					// User cancelled or share failed - copy to clipboard as fallback
					navigator.clipboard.writeText(`${text}\n${url}`);
					toast.show("Link copied to clipboard!", "success");
				});
		} else {
			navigator.clipboard.writeText(`${text}\n${url}`);
			toast.show("Link copied to clipboard!", "success");
		}
	}

	// Admin functions
	async function handleDeleteReport() {
		if (
			!reportId ||
			!confirm("Delete this report? This action cannot be undone.")
		)
			return;

		deletingReport = true;
		try {
			await deleteReportAdmin(reportId);
			toast.show("Report deleted successfully", "success");
			goto("/");
		} catch (e) {
			toast.show(
				getErrorMessage(e) || "Failed to delete report",
				"error",
			);
		} finally {
			deletingReport = false;
		}
	}

	async function handleUpdateCategory() {
		if (!reportId || !newCategory.trim()) return;

		updatingCategory = true;
		try {
			await updateReportCategory(reportId, newCategory);
			if (report) report.category = newCategory;
			showEditCategory = false;
			newCategory = "";
			toast.show("Category updated successfully", "success");
			await loadReport(); // Reload to get timeline update
		} catch (e) {
			toast.show(
				getErrorMessage(e) || "Failed to update category",
				"error",
			);
		} finally {
			updatingCategory = false;
		}
	}

	function startEditCategory() {
		if (report) {
			newCategory = report.category;
			showEditCategory = true;
		}
	}
</script>

<svelte:head>
	<title>{report?.title || "Report"} - Darshi</title>
</svelte:head>

{#if loading}
	<div class="loading-state">
		<div class="spinner" role="status" aria-label="Loading report"></div>
	</div>
{:else if error}
	<div class="error-state" role="alert">
		<span class="icon" aria-hidden="true"><AlertTriangle size={32} /></span>
		<p>{error}</p>
	</div>
{:else if report}
	<article class="report-detail">
		<!-- Header -->
		<header class="report-header">
			<div class="header-meta">
				<span class="category">{report.category}</span>
				<span class="separator" aria-hidden="true">·</span>
				<span class="status">{report.status.replace(/_/g, " ")}</span>
			</div>
			{#if report.severity > 0}
				<div
					class="urgency-badge"
					style="background: {getUrgencyColor(report.severity)}"
					role="status"
					aria-label="Urgency: {getUrgencyLabel(report.severity)}"
				>
					{getUrgencyLabel(report.severity)}
				</div>
			{/if}
		</header>

		<h1 class="report-title">{report.title}</h1>

		<!-- Images -->
		{#if report.image_data && report.image_data.length > 0}
			<div class="image-section">
				<ImageCarousel imageData={report.image_data} />
			</div>
		{:else if report.image_urls && report.image_urls.length > 0}
			<div class="image-section">
				<ImageCarousel images={report.image_urls} />
			</div>
		{:else if report.status === "PENDING_VERIFICATION"}
			<!-- Show placeholder while images are being processed -->
			<div class="image-section">
				<div class="image-processing-placeholder">
					<div class="processing-spinner"></div>
					<h3>Processing Images...</h3>
					<p>
						Your images are being optimized and verified. This
						usually takes 5-10 seconds.
					</p>
					<p class="processing-hint">
						Refresh the page in a moment to see your images and AI
						verification results.
					</p>
				</div>
			</div>
		{/if}

		<!-- Description -->
		<section class="content-section">
			<h2 class="section-title">Description</h2>
			<p class="description">
				{report.description || "No description provided"}
			</p>
		</section>

		<!-- AI Analysis -->
		{#if report.ai_analysis || report.flag_reason}
			<section class="content-section">
				<div
					class="ai-analysis-card"
					class:rejected={!report.ai_analysis?.is_valid}
				>
					<div class="ai-header-row">
						<div
							class="ai-icon-wrapper"
							class:rejected={!report.ai_analysis?.is_valid}
						>
							<Brain size={20} />
						</div>
						<div class="ai-header-content">
							<h3 class="section-title ai-title-new">
								AI Analysis
							</h3>
							{#if report.ai_analysis?.is_valid}
								<span class="ai-status-badge verified">
									<CheckCircle size={14} />
									Verified Issue
								</span>
							{:else}
								<span class="ai-status-badge rejected">
									<XCircle size={14} />
									Invalid Report
								</span>
							{/if}
						</div>
					</div>

					{#if report.ai_analysis?.is_valid}
						<!-- Valid report - show category and severity -->
						<div class="ai-details">
							{#if report.ai_analysis.category && report.ai_analysis.category !== "None"}
								<div class="ai-detail-row">
									<span class="ai-label"
										>Detected Category</span
									>
									<span class="ai-value category-badge"
										>{report.ai_analysis.category}</span
									>
								</div>
							{/if}
							{#if typeof report.ai_analysis.severity === "number" && report.ai_analysis.severity > 0}
								<div class="ai-detail-row">
									<span class="ai-label"
										>Severity Assessment</span
									>
									<div class="severity-indicator">
										<span class="severity-score"
											>{report.ai_analysis
												.severity}/10</span
										>
										<div class="severity-bar-container">
											<div
												class="severity-bar-fill"
												style="width: {report
													.ai_analysis.severity *
													10}%; background: {getUrgencyColor(
													report.ai_analysis.severity,
												)}"
											></div>
										</div>
									</div>
								</div>
							{/if}
						</div>
						{#if report.ai_analysis.description}
							<div class="ai-summary">
								<p>{report.ai_analysis.description}</p>
							</div>
						{/if}
					{:else}
						<!-- Invalid/Rejected report - show rejection reason prominently -->
						<div class="ai-rejection-box">
							<div class="rejection-header">
								<AlertTriangle size={16} />
								<span>Rejection Reason</span>
							</div>
							<p class="rejection-text">
								{report.flag_reason ||
									report.ai_analysis?.description ||
									"This image was flagged as not containing a valid civic issue."}
							</p>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Location -->
		<section class="content-section">
			<h3 class="section-title">Location</h3>
			<div class="location-card">
				<span class="icon" aria-hidden="true"><MapPin size={16} /></span
				>
				<div class="location-info">
					<span class="location-address"
						>{report.address ||
							report.location ||
							"Location not found"}</span
					>
					{#if report.latitude && report.longitude}
						<span class="location-coords"
							>{report.latitude.toFixed(6)}, {report.longitude.toFixed(
								6,
							)}</span
						>
					{/if}
				</div>
			</div>
			{#if report.latitude && report.longitude}
				<ReportMap
					latitude={report.latitude}
					longitude={report.longitude}
					markerText={report.title}
				/>
			{/if}
		</section>

		<!-- Nearby Landmarks -->
		{#if report.latitude && report.longitude}
			<section class="content-section">
				<h3 class="section-title">Nearby Landmarks</h3>
				{#if loadingLandmarks}
					<div class="landmarks-loading">
						<div class="spinner"></div>
						<p>Finding nearby landmarks...</p>
					</div>
				{:else if landmarks.length > 0}
					<div class="landmarks-list">
						{#each landmarks as landmark}
							<div class="landmark-item">
								<div class="landmark-icon">
									<Navigation size={16} />
								</div>
								<div class="landmark-info">
									<span class="landmark-name"
										>{landmark.name}</span
									>
									<span class="landmark-meta">
										<span class="landmark-type"
											>{landmark.type}</span
										>
										<span class="landmark-separator">•</span
										>
										<span class="landmark-distance"
											>{landmark.distance_text}</span
										>
									</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="landmarks-empty">
						<Navigation size={24} />
						<p>No landmarks found nearby</p>
					</div>
				{/if}
			</section>
		{/if}

		<!-- Actions -->
		<div class="actions-bar">
			<LoadingButton
				variant="primary"
				loading={upvoting}
				onclick={handleUpvote}
			>
				<span class="icon" aria-hidden="true"
					><ThumbsUp size={16} /></span
				>
				<span>Upvote ({report.upvote_count})</span>
			</LoadingButton>
			<LoadingButton variant="secondary" onclick={shareReport}>
				<span class="icon" aria-hidden="true"><Share2 size={16} /></span
				>
				<span>Share</span>
			</LoadingButton>
			<LoadingButton
				variant="secondary"
				onclick={() => (showFlagModal = true)}
			>
				<span class="icon" aria-hidden="true"><Flag size={16} /></span>
				<span>Flag</span>
			</LoadingButton>
		</div>

		<!-- User Controls for Resolution -->
		{#if isAuthor && report.status === "RESOLVED"}
			<div class="user-resolution-check">
				<h3>Is this issue resolved?</h3>
				<p>
					Please confirm if the work has been completed
					satisfactorily.
				</p>
				<div class="actions">
					<LoadingButton
						variant="success"
						onclick={() =>
							updateStatus("CLOSED", {
								summary: "User confirmed resolution",
							})}
					>
						Yes, Close Report
					</LoadingButton>
					<LoadingButton
						variant="danger"
						onclick={() =>
							updateStatus("IN_PROGRESS", {
								summary:
									"User rejected resolution: Issue persists",
							})}
					>
						No, Reopen
					</LoadingButton>
				</div>
			</div>
		{/if}

		<!-- Admin Controls -->
		{#if isAdmin}
			<div class="admin-controls">
				<div class="admin-header">
					<Shield size={16} />
					<span>Admin Controls</span>
				</div>
				<div class="admin-actions">
					<div class="status-manager">
						<select
							bind:value={selectedStatus}
							class="status-select"
						>
							<option value="" disabled selected
								>Change Status...</option
							>
							<option value="PENDING_VERIFICATION"
								>Pending Verification</option
							>
							<option value="VERIFIED">Verified</option>
							<option value="IN_PROGRESS">In Progress</option>
							<option value="RESOLVED">Resolved</option>
							<option value="REJECTED">Rejected</option>
						</select>
						<button
							class="btn-primary-sm"
							onclick={handleStatusChange}
							disabled={!selectedStatus}>Update</button
						>
					</div>

					<button
						class="admin-btn edit-category"
						onclick={startEditCategory}
					>
						<Edit size={16} />
						Edit Category
					</button>
					<LoadingButton
						variant="danger"
						loading={deletingReport}
						onclick={handleDeleteReport}
					>
						<Trash2 size={16} />
						Delete Report
					</LoadingButton>
				</div>

				{#if showEditCategory}
					<div class="edit-category-form">
						<input
							type="text"
							bind:value={newCategory}
							placeholder="Enter new category"
							class="category-input"
						/>
						<div class="form-actions">
							<LoadingButton
								variant="primary"
								loading={updatingCategory}
								onclick={handleUpdateCategory}
							>
								Save
							</LoadingButton>
							<button
								class="btn-secondary"
								onclick={() => (showEditCategory = false)}
							>
								Cancel
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Timeline -->
		<section class="content-section">
			<h2 class="section-title">Status Timeline</h2>
			{#if report.timeline && report.timeline.length > 0}
				<div class="timeline" role="list">
					{#each report.timeline as event}
						<div class="timeline-item" role="listitem">
							<div class="timeline-dot" aria-hidden="true"></div>
							<div class="timeline-content">
								<strong>{event.event.replace(/_/g, " ")}</strong
								>
								<p>{event.details}</p>
								<time datetime={event.timestamp}
									>{new Date(
										event.timestamp,
									).toLocaleString()}</time
								>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="empty-timeline">
					<span class="icon" aria-hidden="true"
						><Clock size={32} /></span
					>
					<p>Waiting for resolution</p>
				</div>
			{/if}
		</section>

		<!-- Resolution Status -->
		<section class="content-section">
			<h2 class="section-title">Resolution Status</h2>
			{#if report.status === "RESOLVED"}
				<div class="resolution-card resolved" role="status">
					<span class="icon" aria-hidden="true"
						><CheckCircle size={48} /></span
					>
					<h3>Issue Resolved</h3>
					<p>
						This issue has been marked as resolved by authorities.
					</p>
					{#if report.admin_note}
						<div class="admin-note">
							<strong>Admin Note:</strong>
							<p>{report.admin_note}</p>
						</div>
					{/if}
				</div>
			{:else if report.status === "IN_PROGRESS"}
				<div class="resolution-card in-progress" role="status">
					<span class="icon" aria-hidden="true"
						><Wrench size={48} /></span
					>
					<h3>Work in Progress</h3>
					<p>
						Authorities are currently working on resolving this
						issue.
					</p>
				</div>
			{:else if report.status === "REJECTED" || report.status === "FLAGGED"}
				<div class="resolution-card rejected" role="status">
					<span class="icon" aria-hidden="true"
						><XCircle size={48} /></span
					>
					<h3>
						Report {report.status === "REJECTED"
							? "Rejected"
							: "Flagged"}
					</h3>
					<p>
						This report was {report.status === "REJECTED"
							? "rejected by AI verification"
							: "flagged for review"}.
					</p>
					{#if report.flag_reason}
						<p class="rejection-reason">
							<strong>Reason:</strong>
							{report.flag_reason}
						</p>
					{/if}
				</div>
			{:else}
				<div class="resolution-card pending" role="status">
					<span class="icon" aria-hidden="true"
						><Clock size={48} /></span
					>
					<h3>Awaiting Action</h3>
					<p>
						This report is pending review or action from
						authorities.
					</p>
				</div>
			{/if}
		</section>

		<!-- Comments Section -->
		<section class="comments-section">
			<h2 class="section-title">Comments ({report.comments_count})</h2>

			{#if $isAuthenticated}
				<form class="comment-form" onsubmit={handleAddComment}>
					<div class="form-group">
						<label for="comment" class="sr-only"
							>Add your comment</label
						>
						<textarea
							id="comment"
							bind:value={commentText}
							placeholder="Add your thoughts..."
							rows="3"
							maxlength={MAX_COMMENT_LENGTH}
							aria-label="Comment text"
						></textarea>
						<div class="comment-meta">
							<span
								class="character-count"
								class:error={commentLength > MAX_COMMENT_LENGTH}
							>
								{commentLength}/{MAX_COMMENT_LENGTH}
							</span>
						</div>
					</div>
					<LoadingButton
						type="submit"
						loading={submittingComment}
						disabled={!commentText.trim() ||
							commentLength > MAX_COMMENT_LENGTH}
					>
						Post Comment
					</LoadingButton>
				</form>
			{:else}
				<div class="login-prompt" role="status">
					<a href="/signin">Sign in</a> to join the discussion
				</div>
			{/if}

			<div class="comments-list" role="list">
				{#each comments as comment}
					<div class="comment" role="listitem">
						<div class="comment-header">
							<div class="comment-meta">
								<strong
									>{comment.username ||
										comment.user_id}</strong
								>
								<time datetime={comment.created_at}
									>{new Date(
										comment.created_at,
									).toLocaleString()}</time
								>
							</div>
							{#if isAdmin}
								<LoadingButton
									variant="danger"
									loading={deletingCommentId === comment.id}
									onclick={() =>
										handleDeleteComment(comment.id)}
								>
									{#if deletingCommentId === comment.id}
										...
									{:else}
										<Trash2 size={16} />
									{/if}
								</LoadingButton>
							{/if}
						</div>
						<p>{comment.text}</p>
					</div>
				{/each}
				{#if comments.length === 0}
					<p class="empty-state">
						No comments yet. Be the first to comment!
					</p>
				{/if}
			</div>
		</section>
	</article>
{/if}

<style>
	.user-resolution-check {
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-lg);
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		border-left: 4px solid var(--c-brand);
	}

	.user-resolution-check h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1.125rem;
	}

	.user-resolution-check .actions {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
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

	.loading-state,
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 1rem;
		min-height: 400px;
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--c-bg-subtle);
		border-top-color: var(--c-brand);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.report-detail {
		max-width: 680px;
		margin: 0 auto;
		padding: 0 1rem;
	}

	/* Header */
	.report-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.header-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		color: var(--c-text-secondary);
	}

	.category {
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--c-text-primary);
	}

	.urgency-badge {
		padding: 0.375rem 0.75rem;
		border-radius: 99px;
		font-size: 0.75rem;
		font-weight: 700;
		color: white;
		letter-spacing: 0.05em;
	}

	.report-title {
		font-family: var(--font-display);
		font-size: 2rem;
		font-weight: 700;
		line-height: 1.25;
		margin: 0 0 1.5rem 0;
		letter-spacing: -0.02em;
	}

	/* Images */
	.image-section {
		margin-bottom: 2rem;
	}

	/* Content Sections */
	.content-section {
		margin-bottom: 2rem;
	}

	.section-title {
		font-family: var(--font-display);
		font-size: 1.25rem;
		font-weight: 700;
		margin: 0 0 1rem 0;
		color: var(--c-text-primary);
	}

	.description {
		font-size: 1rem;
		line-height: 1.6;
		color: var(--c-text-secondary);
		margin: 0;
	}

	.location-card {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		overflow-wrap: break-word;
		word-wrap: break-word;
		word-break: break-word;
	}

	.location-card .icon {
		margin-top: 0.125rem;
		flex-shrink: 0;
	}

	.location-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		min-width: 0;
		flex: 1;
	}

	.location-address {
		font-weight: 500;
		color: var(--c-text-primary);
		overflow-wrap: break-word;
		word-wrap: break-word;
	}

	.location-coords {
		font-size: 0.8125rem;
		color: var(--c-text-tertiary);
		font-family: ui-monospace, "Cascadia Code", "Source Code Pro", Menlo,
			Consolas, "DejaVu Sans Mono", monospace;
	}

	.actions-bar {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 2rem;
		flex-wrap: wrap;
	}

	.actions-bar :global(button) {
		flex: 1;
		min-width: 120px;
		justify-content: center;
	}

	/* Admin Controls */
	.admin-controls {
		background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
		border: 2px solid #f59e0b;
		border-radius: var(--radius-md);
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.admin-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #92400e;
		font-weight: 600;
		margin-bottom: 1rem;
		font-size: 0.875rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.admin-actions {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.admin-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1rem;
		background: var(--c-bg-surface);
		border: 1px solid #d97706;
		border-radius: var(--radius-sm);
		color: #92400e;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.admin-btn:hover {
		background: #fffbeb;
		border-color: #b45309;
	}

	.edit-category-form {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #f59e0b;
	}

	.category-input {
		width: 100%;
		padding: 0.625rem;
		border: 1px solid #d97706;
		border-radius: var(--radius-sm);
		font-size: 0.9375rem;
		margin-bottom: 0.75rem;
	}

	.category-input:focus {
		outline: none;
		border-color: #b45309;
		box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
	}

	.form-actions {
		display: flex;
		gap: 0.5rem;
	}

	.btn-secondary {
		padding: 0.625rem 1rem;
		background: var(--c-bg-surface);
		border: 1px solid #d97706;
		border-radius: var(--radius-sm);
		color: #92400e;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.btn-secondary:hover {
		background: #fffbeb;
	}

	/* Timeline */
	.timeline {
		position: relative;
		padding-left: 2rem;
	}

	.timeline::before {
		content: "";
		position: absolute;
		left: 0.5rem;
		top: 0.5rem;
		bottom: 0.5rem;
		width: 2px;
		background: var(--c-border);
	}

	.timeline-item {
		position: relative;
		padding-bottom: 1.5rem;
		padding-right: 0.5rem;
	}

	.timeline-dot {
		position: absolute;
		left: -1.625rem;
		top: 0.375rem;
		width: 12px;
		height: 12px;
		background: var(--c-brand);
		border: 2px solid var(--c-bg-page);
		border-radius: 50%;
	}

	.timeline-content strong {
		display: block;
		font-weight: 600;
		margin-bottom: 0.25rem;
		text-transform: capitalize;
	}

	.timeline-content p {
		color: var(--c-text-secondary);
		margin: 0.25rem 0;
		font-size: 0.9375rem;
	}

	.timeline-content time {
		font-size: 0.8125rem;
		color: var(--c-text-tertiary);
	}

	.empty-timeline {
		text-align: center;
		padding: 2rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
	}

	.empty-timeline .icon {
		font-size: 2rem;
		display: block;
		margin-bottom: 0.5rem;
	}

	.empty-timeline p {
		color: var(--c-text-secondary);
		margin: 0;
	}

	/* Resolution */
	.resolution-card {
		padding: 2rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		text-align: center;
	}

	.resolution-card .icon {
		font-size: 3rem;
		display: block;
		margin-bottom: 1rem;
	}

	.resolution-card h3 {
		font-family: var(--font-display);
		font-size: 1.5rem;
		margin: 0 0 0.5rem 0;
	}

	.resolution-card p {
		margin: 0;
		color: var(--c-text-secondary);
	}

	.resolution-card.rejected {
		background: #fef2f2;
		border: 1px solid #fee2e2;
	}

	.resolution-card.rejected h3 {
		color: #991b1b;
	}

	.rejection-reason {
		margin-top: 1rem;
		padding: 1rem;
		background: var(--c-bg-surface);
		border-radius: var(--radius-sm);
		text-align: left;
		color: var(--c-text-primary);
		font-size: 0.9375rem;
	}

	.rejection-reason strong {
		color: #991b1b;
	}

	.admin-note {
		margin-top: 1.5rem;
		padding: 1rem;
		background: var(--c-bg-surface);
		border-radius: var(--radius-sm);
		text-align: left;
	}

	/* Comments */
	.comments-section {
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 1px solid var(--c-border);
	}

	/* Tabs */
	.section-tabs {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 1.5rem;
		border-bottom: 1px solid var(--c-border);
	}

	.tab-btn {
		padding: 0.75rem 0;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--c-text-secondary);
		font-weight: 500;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.tab-btn:hover {
		color: var(--c-text-primary);
	}

	.tab-btn.active {
		color: var(--c-primary);
		border-bottom-color: var(--c-primary);
	}

	.update-card {
		padding: 1.5rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: 0.5rem;
		margin-bottom: 1rem;
		border-left: 4px solid var(--c-primary);
	}

	.update-card.official {
		border-left-color: var(--c-brand);
		background: var(--c-bg-subtle);
	}

	.update-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.author-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-weight: 600;
		color: var(--c-text-primary);
	}

	.official-badge {
		background: var(--c-brand);
		color: white;
		font-size: 0.7rem;
		padding: 0.1rem 0.3rem;
		border-radius: 0.25rem;
		margin-left: 0.5rem;
	}

	.update-form {
		margin-bottom: 2rem;
		background: var(--c-bg-subtle);
		padding: 1.5rem;
		border-radius: 0.5rem;
	}

	.comment-form {
		margin-bottom: 1.5rem;
	}

	.form-group {
		margin-bottom: 0.75rem;
	}

	.comment-form textarea {
		width: 100%;
		padding: 0.75rem 1rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		font-family: var(--font-sans);
		font-size: 1rem;
		resize: vertical;
		transition: border-color 0.2s;
	}

	.comment-form textarea:focus {
		outline: none;
		border-color: var(--c-brand);
	}

	.comment-meta {
		display: flex;
		justify-content: flex-end;
		margin-top: 0.25rem;
	}

	.character-count {
		font-size: 0.8125rem;
		color: var(--c-text-tertiary);
	}

	.character-count.error {
		color: #dc2626;
		font-weight: 600;
	}

	.comment {
		padding: 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		margin-bottom: 0.75rem;
	}

	.comment-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		gap: 0.5rem;
	}

	.comment-header .comment-meta {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
		min-width: 0;
		justify-content: flex-start;
		margin: 0;
	}

	.comment-header .comment-meta time {
		color: var(--c-text-tertiary);
		font-size: 0.8125rem;
	}

	.comment-header :global(button) {
		min-width: auto;
		padding: 0.25rem 0.5rem;
		min-height: auto;
		font-size: 1rem;
	}

	.comment p {
		margin: 0;
		word-wrap: break-word;
		overflow-wrap: break-word;
		word-break: break-word;
		min-width: 0;
	}

	.comment-header strong {
		overflow-wrap: break-word;
		word-wrap: break-word;
		word-break: break-all;
		min-width: 0;
	}

	.empty-state {
		text-align: center;
		color: var(--c-text-secondary);
		padding: 2rem;
	}

	.login-prompt {
		text-align: center;
		padding: 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		margin-bottom: 1.5rem;
		color: var(--c-text-secondary);
	}

	.login-prompt a {
		color: var(--c-brand);
		font-weight: 600;
		text-decoration: none;
	}

	.login-prompt a:hover {
		text-decoration: underline;
	}

	.comments-list {
		display: flex;
		flex-direction: column;
	}

	/* Landmarks */
	.landmarks-loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 2rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
	}

	.landmarks-loading p {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.landmarks-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.landmark-item {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		transition: background 0.2s;
	}

	.landmark-item:hover {
		background: var(--c-border);
	}

	.landmark-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border-radius: var(--radius-sm);
		flex-shrink: 0;
	}

	.landmark-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
		min-width: 0;
	}

	.landmark-name {
		font-weight: 600;
		color: var(--c-text-primary);
		font-size: 0.9375rem;
	}

	.landmark-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		color: var(--c-text-secondary);
	}

	.landmark-type {
		text-transform: capitalize;
	}

	.landmark-separator {
		color: var(--c-text-tertiary);
	}

	.landmark-distance {
		font-weight: 500;
		color: var(--c-text-secondary);
	}

	.landmarks-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 2rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		color: var(--c-text-secondary);
	}

	.landmarks-empty p {
		margin: 0;
		font-size: 0.875rem;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.timeline {
			padding-left: 1.5rem;
		}

		.timeline::before {
			left: 0.375rem;
		}

		.timeline-dot {
			left: -1.25rem;
			width: 10px;
			height: 10px;
		}

		.actions-bar :global(button) {
			min-width: 100px;
		}
	}

	@media (max-width: 640px) {
		.report-title {
			font-size: 1.5rem;
		}

		.actions-bar :global(button) {
			font-size: 0.875rem;
			padding: 0.625rem;
			min-width: 90px;
		}

		.resolution-card {
			padding: 1.5rem 1rem;
		}

		.resolution-card .icon {
			font-size: 2rem;
		}

		.resolution-card h3 {
			font-size: 1.25rem;
		}

		.timeline {
			padding-left: 1rem;
		}

		.timeline::before {
			left: 0.25rem;
		}

		.timeline-dot {
			left: -0.875rem;
			width: 8px;
			height: 8px;
		}
	}

	@media (max-width: 480px) {
		.actions-bar :global(button) {
			min-width: auto;
			flex: 1 1 0;
			font-size: 0.8rem;
		}

		.actions-bar {
			gap: 0.5rem;
		}
	}

	/* AI Analysis - Redesigned */
	.ai-analysis-card {
		background: var(--c-bg-subtle);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		padding: 1.25rem;
		transition: all 0.2s ease;
	}

	.ai-analysis-card.rejected {
		background: var(--c-error-bg);
		border-color: var(--c-error-border);
	}

	:global([data-theme="dark"]) .ai-analysis-card {
		background: rgba(30, 41, 59, 0.6);
		border-color: rgba(51, 65, 85, 0.6);
	}

	:global([data-theme="dark"]) .ai-analysis-card.rejected {
		background: rgba(127, 29, 29, 0.2);
		border-color: rgba(185, 28, 28, 0.3);
	}

	.ai-header-row {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.ai-icon-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border-radius: var(--radius-sm);
		flex-shrink: 0;
	}

	.ai-icon-wrapper.rejected {
		background: var(--c-error);
	}

	.ai-header-content {
		flex: 1;
		min-width: 0;
	}

	.ai-title-new {
		margin: 0 0 0.25rem 0 !important;
		font-size: 1rem !important;
		font-weight: 600;
		color: var(--c-text-primary);
	}

	.ai-status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.25rem 0.625rem;
		border-radius: 99px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.ai-status-badge.verified {
		background: var(--c-success-light);
		color: var(--c-success-dark);
	}

	.ai-status-badge.rejected {
		background: var(--c-error-light);
		color: var(--c-error-dark);
	}

	:global([data-theme="dark"]) .ai-status-badge.verified {
		background: var(--c-success-badge-bg, #065f46);
		color: var(--c-success-badge-text, #d1fae5);
	}

	:global([data-theme="dark"]) .ai-status-badge.rejected {
		background: var(--c-error-badge-bg, #991b1b);
		color: var(--c-error-badge-text, #fee2e2);
	}

	.ai-details {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.ai-detail-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0;
		border-bottom: 1px solid rgba(0, 0, 0, 0.05);
	}

	:global([data-theme="dark"]) .ai-detail-row {
		border-bottom-color: rgba(255, 255, 255, 0.05);
	}

	.ai-detail-row:last-child {
		border-bottom: none;
	}

	.ai-label {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.ai-value {
		font-size: 0.9375rem;
		font-weight: 500;
		color: var(--c-text-primary);
	}

	.category-badge {
		background: var(--c-info-bg);
		color: var(--c-info-dark);
		padding: 0.25rem 0.75rem;
		border-radius: var(--radius-sm);
		font-size: 0.8125rem;
	}

	:global([data-theme="dark"]) .category-badge {
		background: var(--c-info-badge-bg, #1e40af);
		color: var(--c-info-badge-text, #dbeafe);
	}

	.severity-indicator {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.severity-score {
		font-weight: 600;
		font-size: 0.9375rem;
		color: var(--c-text-primary);
		min-width: 40px;
	}

	.severity-bar-container {
		width: 80px;
		height: 8px;
		background: rgba(0, 0, 0, 0.1);
		border-radius: 4px;
		overflow: hidden;
	}

	:global([data-theme="dark"]) .severity-bar-container {
		background: rgba(255, 255, 255, 0.1);
	}

	.severity-bar-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.3s ease;
	}

	.ai-summary {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px dashed var(--c-border);
	}

	.ai-summary p {
		margin: 0;
		font-size: 0.875rem;
		line-height: 1.6;
		color: var(--c-text-secondary);
	}

	/* AI Rejection Box */
	.ai-rejection-box {
		background: rgba(239, 68, 68, 0.08);
		border: 1px solid var(--c-error-border);
		border-radius: var(--radius-sm);
		padding: 1rem;
		margin-top: 0.5rem;
	}

	:global([data-theme="dark"]) .ai-rejection-box {
		background: rgba(239, 68, 68, 0.15);
		border-color: rgba(185, 28, 28, 0.4);
	}

	.rejection-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--c-error-dark);
		margin-bottom: 0.5rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	:global([data-theme="dark"]) .rejection-header {
		color: #fca5a5;
	}

	.rejection-text {
		margin: 0;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--c-text-primary);
	}

	/* Image Processing Placeholder */
	.image-processing-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
		background: var(--c-bg-subtle);
		border: 2px dashed var(--c-border);
		border-radius: var(--radius-lg);
		text-align: center;
		gap: 1rem;
	}

	.processing-spinner {
		width: 48px;
		height: 48px;
		border: 4px solid var(--c-bg-surface);
		border-top-color: var(--c-brand);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.image-processing-placeholder h3 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--c-text-primary);
	}

	.image-processing-placeholder p {
		margin: 0;
		font-size: 0.9375rem;
		color: var(--c-text-secondary);
		max-width: 400px;
	}

	.processing-hint {
		font-size: 0.8125rem !important;
		color: var(--c-text-tertiary) !important;
		font-style: italic;
	}

	:global([data-theme="dark"]) .image-processing-placeholder {
		background: rgba(255, 255, 255, 0.03);
	}
</style>
