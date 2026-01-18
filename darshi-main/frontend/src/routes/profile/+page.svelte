<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { user, isAuthenticated } from "$lib/stores";
	import { api, clearToken, clearCurrentUser } from "$lib/api";
	import {
		Settings,
		Check,
		X,
		ThumbsUp,
		MessageCircle,
		LogOut,
	} from "lucide-svelte";

	let profile = $state<any>(null);
	let reports = $state<any[]>([]);
	let stats = $state<any>(null);
	let loading = $state(true);
	let error = $state("");

	onMount(async () => {
		if (!$isAuthenticated) {
			goto("/signin");
			return;
		}

		// Load all data in parallel for speed
		Promise.all([loadProfile(), loadReports(), loadStats()]).finally(() => {
			loading = false;
		});
	});

	async function loadProfile() {
		try {
			const response = await api.get("/users/me/profile");
			if (response.ok) {
				profile = await response.json();
			} else {
				error = "Failed to load profile";
			}
		} catch (err: any) {
			error = "Failed to load profile";
		}
	}

	async function loadReports() {
		try {
			const response = await api.get("/users/me/reports");
			if (response.ok) {
				const data = await response.json();
				reports = data.reports || [];
			}
		} catch (err: any) {
			// Silently fail
		}
	}

	async function loadStats() {
		try {
			const response = await api.get("/users/me/stats");
			if (response.ok) {
				stats = await response.json();
			}
		} catch (err: any) {
			// Silently fail
		}
	}

	function getStatusColor(status: string): string {
		const colors: Record<string, string> = {
			VERIFIED: "#10b981",
			PENDING_VERIFICATION: "#f59e0b",
			IN_PROGRESS: "#3b82f6",
			RESOLVED: "#8b5cf6",
			REJECTED: "#ef4444",
			DUPLICATE: "#6b7280",
			FLAGGED: "#f97316",
		};
		return colors[status] || "#6b7280";
	}

	function formatDate(dateString: string): string {
		if (!dateString) return "N/A";
		return new Date(dateString).toLocaleDateString("en-US", {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	}

	function logout() {
		clearToken();
		clearCurrentUser();
		$user = null;
		$isAuthenticated = false;
		goto("/");
	}
</script>

<svelte:head>
	<title>My Profile - Darshi</title>
</svelte:head>

{#if loading}
	<div class="loading">Loading...</div>
{:else if error}
	<div class="error">{error}</div>
{:else if profile}
	<div class="profile-page">
		<!-- Profile Header Card -->
		<div class="profile-card">
			<div class="avatar">
				{#if profile.profile_picture}
					<img
						src={profile.profile_picture}
						alt={profile.full_name || profile.username}
					/>
				{:else}
					<div class="avatar-placeholder">
						{(
							profile.full_name ||
							profile.username ||
							profile.email
						)
							.charAt(0)
							.toUpperCase()}
					</div>
				{/if}
			</div>

			<div class="profile-info">
				<h1>{profile.full_name || `@${profile.username}`}</h1>
				<p class="username">{profile.email || profile.phone}</p>

				<div class="badges">
					{#if profile.email_verified}
						<span class="badge success"
							><Check size={12} /> Verified</span
						>
					{/if}
					{#if profile.oauth_provider}
						<span class="badge info">{profile.oauth_provider}</span>
					{/if}
					{#if profile.badges}
						{#each profile.badges as badge}
							<span
								class="badge info"
								class:gold={badge === "local_guide"}
								class:official={badge === "official"}
							>
								{#if badge === "local_guide"}
									⭐
								{:else if badge === "official"}
									🛡️
								{/if}
								{badge.replace(/_/g, " ")}
							</span>
						{/each}
					{/if}
					{#if profile.reputation > 0}
						<span class="badge reputation"
							>Points: {profile.reputation}</span
						>
					{/if}
				</div>
			</div>

			<a href="/settings" class="settings-btn">
				<Settings size={20} />
				<span>Settings</span>
			</a>
		</div>

		<!-- Stats -->
		{#if stats}
			<div class="stats">
				<div class="stat">
					<div class="stat-value">{stats.total_reports || 0}</div>
					<div class="stat-label">Reports</div>
				</div>
				<div class="stat">
					<div class="stat-value">{stats.verified_reports || 0}</div>
					<div class="stat-label">Verified</div>
				</div>
				<div class="stat">
					<div class="stat-value">{stats.resolved_reports || 0}</div>
					<div class="stat-label">Resolved</div>
				</div>
				<div class="stat">
					<div class="stat-value">{stats.total_upvotes || 0}</div>
					<div class="stat-label">Upvotes</div>
				</div>
			</div>
		{/if}

		<!-- Reports Section -->
		<div class="reports-section">
			<h2>My Reports</h2>

			{#if reports.length === 0}
				<div class="empty">
					<p>No reports yet</p>
					<a href="/submit" class="btn-primary">Submit Report</a>
				</div>
			{:else}
				<div class="reports-grid">
					{#each reports as report}
						<a href="/report/{report.id}" class="report-card">
							{#if report.image_data && report.image_data.length > 0}
								<img
									src={report.image_data[0].webp_url ||
										report.image_data[0].jpeg_url}
									alt={report.title}
									class="report-img"
								/>
							{:else if report.image_urls && report.image_urls.length > 0}
								<img
									src={report.image_urls[0]}
									alt={report.title}
									class="report-img"
								/>
							{/if}

							<div class="report-body">
								<h3>{report.title}</h3>
								<p>{report.description || "No description"}</p>

								<div class="report-meta">
									<span class="category"
										>{report.category}</span
									>
									<span
										class="status"
										style="background: {getStatusColor(
											report.status,
										)}"
									>
										{report.status.replace(/_/g, " ")}
									</span>
								</div>

								<div class="report-stats">
									<span
										><ThumbsUp size={14} />
										{report.upvote_count || 0}</span
									>
									<span
										><MessageCircle size={14} />
										{report.comment_count || 0}</span
									>
									<span class="date"
										>{formatDate(report.created_at)}</span
									>
								</div>
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Logout Button -->
		<button class="logout-btn" onclick={logout}>
			<LogOut size={18} />
			<span>Logout</span>
		</button>
	</div>
{/if}

<style>
	.loading,
	.error {
		text-align: center;
		padding: 4rem 2rem;
		font-size: 1.125rem;
		color: var(--c-text-secondary);
	}

	.error {
		color: var(--c-error);
	}

	.profile-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 1rem;
	}

	/* Profile Card */
	.profile-card {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
		margin-bottom: 1rem;
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: 1rem;
		align-items: center;
	}

	.avatar {
		width: 80px;
		height: 80px;
		flex-shrink: 0;
	}

	.avatar img,
	.avatar-placeholder {
		width: 100%;
		height: 100%;
		border-radius: 50%;
		object-fit: cover;
	}

	.avatar-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
		font-size: 2rem;
		font-weight: 600;
		border: 2px solid var(--c-border);
	}

	.profile-info h1 {
		margin: 0 0 0.25rem 0;
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--c-text-primary);
	}

	.username {
		color: var(--c-text-secondary);
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
	}

	.badges {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.5rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.badge.success {
		background: #d1fae5;
		color: #065f46;
	}

	.badge.info {
		background: #dbeafe;
		color: #1e40af;
		text-transform: capitalize;
	}

	.settings-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		text-decoration: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.875rem;
		transition: opacity 0.2s;
		white-space: nowrap;
	}

	.settings-btn:hover {
		opacity: 0.9;
	}

	/* Stats */
	.stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.stat {
		background: var(--c-bg-surface);
		padding: 1rem;
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
		text-align: center;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: 700;
		color: var(--c-brand);
		margin-bottom: 0.25rem;
	}

	.stat-label {
		color: var(--c-text-secondary);
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Reports Section */
	.reports-section {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border-radius: 12px;
		box-shadow: var(--shadow-sm);
	}

	.reports-section h2 {
		margin: 0 0 1rem 0;
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--c-text-primary);
	}

	.empty {
		text-align: center;
		padding: 3rem 1rem;
	}

	.empty p {
		color: var(--c-text-secondary);
		margin-bottom: 1rem;
	}

	.btn-primary {
		display: inline-block;
		padding: 0.625rem 1.25rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		text-decoration: none;
		border-radius: 8px;
		font-weight: 600;
		transition: opacity 0.2s;
	}

	.btn-primary:hover {
		opacity: 0.9;
	}

	/* Reports Grid */
	.reports-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}

	.report-card {
		background: var(--c-bg-subtle);
		border-radius: 8px;
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition:
			transform 0.2s,
			box-shadow 0.2s;
		display: flex;
		flex-direction: column;
	}

	.report-card:hover {
		transform: translateY(-2px);
		box-shadow: var(--shadow-md);
	}

	.report-img {
		width: 100%;
		height: 180px;
		object-fit: cover;
		background: var(--c-border);
	}

	.report-body {
		padding: 1rem;
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.report-body h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--c-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.report-body p {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		margin: 0 0 0.75rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		flex: 1;
	}

	.report-meta {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		flex-wrap: wrap;
	}

	.category,
	.status {
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-weight: 500;
	}

	.category {
		background: var(--c-border);
		color: var(--c-text-secondary);
	}

	.status {
		color: white;
		text-transform: capitalize;
	}

	.report-stats {
		display: flex;
		gap: 1rem;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
		align-items: center;
	}

	.report-stats span {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.date {
		margin-left: auto;
		font-size: 0.75rem;
	}

	/* Logout Button */
	.logout-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.875rem;
		background: var(--c-bg-surface);
		color: var(--c-error);
		border: 2px solid var(--c-error);
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.9375rem;
		cursor: pointer;
		transition: all 0.2s;
		margin-top: 1rem;
		font-family: inherit;
	}

	.logout-btn:hover {
		background: var(--c-error);
		color: var(--c-bg-surface);
	}

	/* Mobile Responsive */
	@media (max-width: 768px) {
		.profile-page {
			padding: 0.75rem;
		}

		.profile-card {
			grid-template-columns: auto 1fr;
			padding: 1rem;
		}

		.settings-btn {
			grid-column: 1 / -1;
			justify-content: center;
		}

		.avatar {
			width: 64px;
			height: 64px;
		}

		.avatar-placeholder {
			font-size: 1.5rem;
		}

		.profile-info h1 {
			font-size: 1.25rem;
		}

		.stats {
			grid-template-columns: repeat(2, 1fr);
			gap: 0.75rem;
		}

		.stat {
			padding: 0.75rem;
		}

		.stat-value {
			font-size: 1.5rem;
		}

		.reports-section {
			padding: 1rem;
		}

		.reports-grid {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 480px) {
		.profile-page {
			padding: 0.5rem;
		}

		.profile-card {
			padding: 0.75rem;
		}

		.avatar {
			width: 56px;
			height: 56px;
		}

		.avatar-placeholder {
			font-size: 1.25rem;
		}

		.profile-info h1 {
			font-size: 1.125rem;
		}

		.username {
			font-size: 0.8125rem;
		}

		.stat-value {
			font-size: 1.25rem;
		}

		.stat-label {
			font-size: 0.6875rem;
		}

		.reports-section {
			padding: 0.75rem;
		}
	}

	/* Dark Mode - only override elements that need special handling */
	:global([data-theme="dark"]) .badge.success {
		background: var(--c-success-badge-bg);
		color: var(--c-success-badge-text);
	}

	:global([data-theme="dark"]) .badge.info {
		background: var(--c-info-badge-bg);
		color: var(--c-info-badge-text);
	}
</style>
