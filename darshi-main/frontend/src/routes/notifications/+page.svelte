<script lang="ts">
	import {
		notifications,
		type Notification,
	} from "$lib/stores/notifications";
	import { isAuthenticated } from "$lib/stores";
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";

	const { unreadCount } = notifications;

	let loading = $state(true);
	let error = $state("");
	let filter = $state<"all" | "unread">("unread");

	onMount(() => {
		if (!$isAuthenticated) {
			goto("/signin?redirect=/notifications");
			return;
		}

		(async () => {
			try {
				// Fetch unread first (default view)
				await notifications.fetch(true);
				// Mark all unread as read when user opens notifications page
				if ($unreadCount > 0) {
					await notifications.markAllAsRead();
				}
				notifications.startPolling(30000);
			} catch (err) {
				error = "Failed to load notifications";
			} finally {
				loading = false;
			}
		})();

		return () => {
			notifications.stopPolling();
		};
	});

	async function handleFilterChange(newFilter: "all" | "unread") {
		filter = newFilter;
		loading = true;
		error = "";
		try {
			await notifications.fetch(newFilter === "unread");
		} catch (err) {
			error = "Failed to load notifications";
		} finally {
			loading = false;
		}
	}

	async function handleNotificationClick(notification: Notification) {
		// Navigate to report if available
		if (notification.report_id) {
			goto(`/report/${notification.report_id}`);
		}
	}

	function getIcon(type: string): string {
		switch (type) {
			case "report_status_change":
				return "✓";
			case "new_comment":
				return "💬";
			case "admin_action":
				return "🛡️";
			case "upvote_milestone":
				return "📈";
			default:
				return "📄";
		}
	}

	function getIconColor(type: string): string {
		switch (type) {
			case "report_status_change":
				return "#10b981";
			case "new_comment":
				return "#3b82f6";
			case "admin_action":
				return "#f59e0b";
			case "upvote_milestone":
				return "#8b5cf6";
			default:
				return "#6b7280";
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return "Just now";
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString("en-US", {
			month: "short",
			day: "numeric",
		});
	}
</script>

<svelte:head>
	<title>Notifications - Darshi</title>
	<meta name="description" content="View your notifications" />
</svelte:head>

<div class="page-container">
	<header class="page-header">
		<h1>Notifications</h1>
	</header>

	{#if error}
		<div class="error-banner" role="alert">
			<span>{error}</span>
			<button onclick={() => (error = "")} aria-label="Dismiss error"
				>×</button
			>
		</div>
	{/if}

	<div class="filter-tabs" role="tablist">
		<button
			role="tab"
			aria-selected={filter === "unread"}
			class="tab"
			class:active={filter === "unread"}
			onclick={() => handleFilterChange("unread")}
		>
			Unread
		</button>
		<button
			role="tab"
			aria-selected={filter === "all"}
			class="tab"
			class:active={filter === "all"}
			onclick={() => handleFilterChange("all")}
		>
			All
		</button>
	</div>

	{#if loading}
		<div class="loading-container">
			<LoadingSpinner size="lg" />
			<p>Loading notifications...</p>
		</div>
	{:else if $notifications.length === 0}
		<div class="empty-state">
			<div class="empty-icon">🔔</div>
			<h2>No notifications</h2>
			<p>
				{filter === "unread"
					? "You're all caught up!"
					: "Notifications will appear here when you have updates"}
			</p>
		</div>
	{:else}
		<div class="notifications-list">
			{#each $notifications as notification (notification.id)}
				<button
					class="notification-card"
					onclick={() => handleNotificationClick(notification)}
				>
					<div
						class="notification-icon"
						style="background-color: {getIconColor(
							notification.type,
						)}"
					>
						<span>{getIcon(notification.type)}</span>
					</div>

					<div class="notification-content">
						<h3>{notification.title}</h3>
						<p>{notification.message}</p>
						<div class="notification-meta">
							<time datetime={notification.created_at}>
								{formatDate(notification.created_at)}
							</time>
							{#if notification.actor}
								<span class="actor"
									>by {notification.actor}</span
								>
							{/if}
						</div>
					</div>

					<div class="notification-arrow">
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
							<polyline points="9 18 15 12 9 6"></polyline>
						</svg>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.page-container {
		width: 100%;
		max-width: 680px;
		margin: 0 auto;
		padding: 0;
		min-height: calc(100vh - var(--header-height));
	}

	.page-header {
		padding: 1.5rem 1rem 1rem;
		border-bottom: 1px solid var(--c-border);
		background: var(--c-bg-surface);
		position: sticky;
		top: var(--header-height);
		z-index: 10;
	}

	.page-header h1 {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0;
	}

	.error-banner {
		background: var(--c-error-bg);
		border: 1px solid var(--c-error-border);
		color: var(--c-error-dark);
		padding: 0.875rem 1rem;
		margin: 1rem;
		border-radius: var(--radius-md);
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
	}

	.error-banner button {
		background: transparent;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--c-error-dark);
		padding: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		line-height: 1;
		flex-shrink: 0;
	}

	.error-banner button:hover {
		background: var(--c-error-light);
	}

	.filter-tabs {
		display: flex;
		gap: 0;
		border-bottom: 2px solid var(--c-border);
		background: var(--c-bg-surface);
		padding: 0 1rem;
		position: sticky;
		top: calc(var(--header-height) + 64px);
		z-index: 9;
	}

	.tab {
		flex: 1;
		background: transparent;
		border: none;
		padding: 0.875rem 1rem;
		font-family: inherit;
		font-size: 0.9375rem;
		font-weight: 600;
		color: var(--c-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		position: relative;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
	}

	.tab.active {
		color: var(--c-brand);
		border-bottom-color: var(--c-brand);
	}

	.tab:hover:not(.active) {
		color: var(--c-text-primary);
		background: var(--c-bg-subtle);
	}

	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 1rem;
		gap: 1rem;
		color: var(--c-text-secondary);
	}

	.empty-state {
		text-align: center;
		padding: 4rem 1.5rem;
	}

	.empty-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
		opacity: 0.4;
	}

	.empty-state h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--c-text-primary);
		margin: 0 0 0.5rem 0;
	}

	.empty-state p {
		color: var(--c-text-secondary);
		font-size: 0.9375rem;
		margin: 0;
		line-height: 1.5;
	}

	.notifications-list {
		display: flex;
		flex-direction: column;
	}

	.notification-card {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		padding: 1rem;
		background: var(--c-bg-surface);
		border: none;
		border-bottom: 1px solid var(--c-border);
		cursor: pointer;
		transition: background 0.2s;
		text-align: left;
		width: 100%;
		font-family: inherit;
	}

	.notification-card:hover {
		background: var(--c-bg-subtle);
	}

	.notification-card:active {
		background: var(--c-bg-subtle);
	}

	.notification-icon {
		flex-shrink: 0;
		width: 44px;
		height: 44px;
		border-radius: var(--radius-md);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
	}

	.notification-content {
		flex: 1;
		min-width: 0;
	}

	.notification-content h3 {
		font-size: 0.9375rem;
		font-weight: 600;
		color: var(--c-text-primary);
		margin: 0 0 0.25rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.notification-content p {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
		margin: 0 0 0.375rem 0;
		line-height: 1.4;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.notification-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.8125rem;
		color: var(--c-text-tertiary);
	}

	.actor {
		font-weight: 500;
	}

	.notification-arrow {
		flex-shrink: 0;
		color: var(--c-text-tertiary);
		display: flex;
		align-items: center;
	}

	/* Tablet */
	@media (min-width: 768px) {
		.page-container {
			max-width: 800px;
		}

		.page-header {
			padding: 2rem 1.5rem 1.5rem;
		}

		.page-header h1 {
			font-size: 1.875rem;
		}

		.filter-tabs {
			padding: 0 1.5rem;
			top: calc(var(--header-height) + 84px);
		}

		.tab {
			padding: 1rem 1.5rem;
			font-size: 1rem;
		}

		.notification-card {
			padding: 1.25rem 1.5rem;
			gap: 1rem;
			border-radius: var(--radius-md);
			border: 1px solid var(--c-border);
			border-bottom: 1px solid var(--c-border);
			margin: 0 1rem 0.75rem;
		}

		.notification-card:hover {
			border-color: var(--c-brand);
			box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
		}

		.notification-icon {
			width: 48px;
			height: 48px;
			font-size: 1.5rem;
		}

		.notification-content h3 {
			font-size: 1rem;
		}

		.notification-content p {
			font-size: 0.9375rem;
		}

		.empty-state {
			padding: 5rem 2rem;
		}
	}

	/* Desktop */
	@media (min-width: 1024px) {
		.page-container {
			max-width: 900px;
		}
	}

	/* Mobile refinements */
	@media (max-width: 640px) {
		.page-header {
			top: 56px;
		}

		.filter-tabs {
			top: calc(56px + 58px);
		}

		.notification-card {
			gap: 0.75rem;
			padding: 0.875rem 1rem;
		}

		.notification-icon {
			width: 40px;
			height: 40px;
			font-size: 1.125rem;
		}

		.notification-content h3 {
			font-size: 0.875rem;
		}

		.notification-content p {
			font-size: 0.8125rem;
			-webkit-line-clamp: 1;
		}

		.notification-meta {
			font-size: 0.75rem;
		}

		.empty-state {
			padding: 3rem 1.5rem;
		}

		.empty-icon {
			font-size: 3rem;
		}
	}

	/* Small mobile */
	@media (max-width: 360px) {
		.page-header {
			padding: 1rem 0.75rem 0.75rem;
		}

		.filter-tabs {
			padding: 0 0.75rem;
		}

		.notification-card {
			padding: 0.75rem;
		}
	}
</style>
