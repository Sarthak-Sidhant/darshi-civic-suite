<script lang="ts">
	import {
		notifications,
		type Notification,
	} from "$lib/stores/notifications";
	import { goto } from "$app/navigation";
	import {
		subscribeToPush,
		unsubscribeFromPush,
		isPushSubscribed,
		isPushSupported,
	} from "$lib/push";
	import { onMount } from "svelte";

	const { unreadCount } = notifications;

	type Props = { onclose: () => void };
	let { onclose }: Props = $props();

	let pushEnabled = $state(false);
	let pushSupported = $state(false);
	let pushLoading = $state(false);

	onMount(async () => {
		pushSupported = isPushSupported();
		if (pushSupported) {
			pushEnabled = await isPushSubscribed();
		}
	});

	function getIcon(type: string): string {
		switch (type) {
			case "report_status_change":
				return "✓"; // Check mark
			case "new_comment":
				return "💬"; // Speech bubble
			case "admin_action":
				return "🛡️"; // Shield
			case "upvote_milestone":
				return "📈"; // Trending up
			default:
				return "📄"; // Document
		}
	}

	function getIconColor(type: string): string {
		switch (type) {
			case "report_status_change":
				return "#10b981"; // green
			case "new_comment":
				return "#3b82f6"; // blue
			case "admin_action":
				return "#f59e0b"; // amber
			case "upvote_milestone":
				return "#8b5cf6"; // purple
			default:
				return "#6b7280"; // gray
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
		return date.toLocaleDateString();
	}

	async function handleClick(notification: Notification) {
		if (!notification.read) {
			await notifications.markAsRead(notification.id);
		}
		if (notification.report_id) {
			goto(`/report/${notification.report_id}`);
		}
		onclose();
	}

	async function handleMarkAllRead() {
		await notifications.markAllAsRead();
	}

	async function handleDelete(notificationId: string, event: MouseEvent) {
		event.stopPropagation();
		await notifications.delete(notificationId);
	}

	async function togglePushNotifications() {
		if (pushLoading) return;

		pushLoading = true;
		try {
			if (pushEnabled) {
				const success = await unsubscribeFromPush();
				if (success) {
					pushEnabled = false;
				}
			} else {
				const success = await subscribeToPush();
				if (success) {
					pushEnabled = true;
				}
			}
		} finally {
			pushLoading = false;
		}
	}
</script>

<div class="dropdown" role="menu">
	<div class="dropdown-header">
		<h3>Notifications</h3>
		{#if $unreadCount > 0}
			<button
				class="mark-all-read"
				onclick={handleMarkAllRead}
				type="button"
			>
				Mark all read
			</button>
		{/if}
	</div>

	{#if pushSupported}
		<div class="push-toggle">
			<label>
				<span class="push-label">
					<svg
						width="16"
						height="16"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
						></path>
						<path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
					</svg>
					Push notifications
				</span>
				<input
					type="checkbox"
					checked={pushEnabled}
					disabled={pushLoading}
					onchange={togglePushNotifications}
					class="push-checkbox"
				/>
				<span class="toggle-switch" class:loading={pushLoading}></span>
			</label>
		</div>
	{/if}

	<div class="notification-list">
		{#each $notifications as notification}
			<div
				class="notification-item"
				class:unread={!notification.read}
				onclick={() => handleClick(notification)}
				role="button"
				tabindex="0"
				onkeydown={(e) => {
					if (e.key === "Enter" || e.key === " ") {
						e.preventDefault();
						handleClick(notification);
					}
				}}
			>
				<div
					class="icon"
					style="color: {getIconColor(notification.type)}"
				>
					<span aria-hidden="true">{getIcon(notification.type)}</span>
				</div>
				<div class="content">
					<h4>{notification.title}</h4>
					<p>{notification.message}</p>
					<time datetime={notification.created_at}
						>{formatDate(notification.created_at)}</time
					>
				</div>
				{#if !notification.read}
					<span class="unread-dot" aria-label="Unread"></span>
				{/if}
				<button
					class="delete-btn"
					onclick={(e) => handleDelete(notification.id, e)}
					aria-label="Delete notification"
					type="button"
				>
					×
				</button>
			</div>
		{/each}

		{#if $notifications.length === 0}
			<div class="empty-state">
				<p>No notifications yet</p>
				<span class="empty-icon">🔔</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.dropdown {
		position: absolute;
		top: calc(100% + 0.5rem);
		right: 0;
		width: 360px;
		max-width: 90vw;
		max-height: 480px;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border, #e5e7eb);
		border-radius: 0.5rem;
		box-shadow:
			0 10px 15px -3px rgba(0, 0, 0, 0.1),
			0 4px 6px -2px rgba(0, 0, 0, 0.05);
		z-index: 1000;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.dropdown-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--c-border, #e5e7eb);
		background: var(--c-bg-surface);
		flex-shrink: 0;
	}

	.dropdown-header h3 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--c-text, #111827);
	}

	.mark-all-read {
		background: none;
		border: none;
		color: var(--c-primary, #3b82f6);
		font-size: 0.875rem;
		cursor: pointer;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		transition: background 0.2s;
	}

	.mark-all-read:hover {
		background: var(--c-bg-subtle, rgba(59, 130, 246, 0.1));
	}

	.notification-list {
		flex: 1;
		overflow-y: auto;
		min-height: 0;
	}

	.notification-item {
		display: flex;
		gap: 0.75rem;
		padding: 1rem;
		border: none;
		background: var(--c-bg-surface);
		width: 100%;
		text-align: left;
		cursor: pointer;
		border-bottom: 1px solid var(--c-border, #e5e7eb);
		transition: background 0.2s;
		position: relative;
	}

	.notification-item:hover {
		background: var(--c-bg-subtle, #f9fafb);
	}

	.notification-item.unread {
		background: var(--c-info-bg);
	}

	.notification-item.unread:hover {
		background: var(--c-info-light);
	}

	.icon {
		flex-shrink: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
		background: var(--c-bg-subtle, #f3f4f6);
		border-radius: 50%;
	}

	.content {
		flex: 1;
		min-width: 0;
	}

	.content h4 {
		margin: 0 0 0.25rem 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--c-text, #111827);
	}

	.content p {
		margin: 0 0 0.25rem 0;
		font-size: 0.8125rem;
		color: var(--c-text-subtle, #6b7280);
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.content time {
		font-size: 0.75rem;
		color: var(--c-text-muted, #9ca3af);
	}

	.unread-dot {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		right: 2.5rem;
		width: 8px;
		height: 8px;
		background: #3b82f6;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.delete-btn {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		right: 0.5rem;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--c-text-muted, #9ca3af);
		font-size: 1.5rem;
		line-height: 1;
		cursor: pointer;
		border-radius: 0.25rem;
		transition: all 0.2s;
		opacity: 0;
	}

	.notification-item:hover .delete-btn {
		opacity: 1;
	}

	.delete-btn:hover {
		background: rgba(239, 68, 68, 0.1);
		color: #dc2626;
	}

	.empty-state {
		padding: 3rem 1rem;
		text-align: center;
		color: var(--c-text-muted, #9ca3af);
	}

	.empty-state p {
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
	}

	.empty-icon {
		font-size: 2rem;
		opacity: 0.5;
	}

	.push-toggle {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--c-border, #e5e7eb);
	}

	.push-toggle label {
		display: flex;
		justify-content: space-between;
		align-items: center;
		cursor: pointer;
		gap: 0.5rem;
	}

	.push-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-text, #111827);
	}

	.push-checkbox {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}

	.toggle-switch {
		position: relative;
		width: 44px;
		height: 24px;
		background: #d1d5db;
		border-radius: 12px;
		transition: background 0.2s;
		flex-shrink: 0;
	}

	.toggle-switch::after {
		content: "";
		position: absolute;
		top: 2px;
		left: 2px;
		width: 20px;
		height: 20px;
		background: var(--c-bg-surface);
		border-radius: 50%;
		transition: transform 0.2s;
	}

	.push-checkbox:checked + .toggle-switch {
		background: #3b82f6;
	}

	.push-checkbox:checked + .toggle-switch::after {
		transform: translateX(20px);
	}

	.push-checkbox:disabled + .toggle-switch {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.toggle-switch.loading::after {
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Dark mode is handled via CSS variables */

	/* Mobile responsive */
	@media (max-width: 640px) {
		.dropdown {
			right: -0.5rem;
			width: calc(100vw - 1rem);
		}

		.notification-item {
			padding: 0.875rem;
		}

		.content h4 {
			font-size: 0.8125rem;
		}

		.content p {
			font-size: 0.75rem;
		}
	}
</style>
