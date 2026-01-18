<script lang="ts">
	import { notifications } from '$lib/stores/notifications';
	import { user } from '$lib/stores';
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';

	const { unreadCount } = notifications;

	let loading = $state(false);

	onMount(async () => {
		if ($user) {
			loading = true;
			try {
				await notifications.fetch();
				notifications.startPolling(30000); // Poll every 30s
			} finally {
				loading = false;
			}
		}
	});

	onDestroy(() => {
		notifications.stopPolling();
	});

	function handleClick() {
		goto('/notifications');
	}
</script>

<div class="notification-bell">
	<button
		onclick={handleClick}
		aria-label="Notifications"
		class="bell-button"
		class:loading
	>
		{#if loading}
			<span class="spinner" aria-label="Loading notifications"></span>
		{:else}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
				<path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
			</svg>

			{#if $unreadCount > 0}
				<span class="badge" aria-label="{$unreadCount} unread notifications">
					{$unreadCount > 99 ? '99+' : $unreadCount}
				</span>
			{/if}
		{/if}
	</button>
</div>

<style>
	.notification-bell {
		position: relative;
	}

	.bell-button {
		position: relative;
		min-width: 44px;
		min-height: 44px;
		padding: 0.5rem;
		background: transparent;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.375rem;
		transition: background 0.2s, color 0.2s;
		color: var(--c-text-primary);
	}

	.bell-button:hover {
		background: var(--c-bg-subtle, rgba(0, 0, 0, 0.05));
		color: var(--c-text-primary);
	}

	.bell-button:focus-visible {
		outline: 2px solid var(--c-primary, #3b82f6);
		outline-offset: 2px;
	}

	.bell-button.loading {
		cursor: not-allowed;
	}

	.badge {
		position: absolute;
		top: 4px;
		right: 4px;
		background: #dc2626;
		color: white;
		border-radius: 99px;
		min-width: 18px;
		height: 18px;
		padding: 0 4px;
		font-size: 0.625rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		line-height: 1;
	}

	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid rgba(0, 0, 0, 0.1);
		border-top-color: var(--c-primary, #3b82f6);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Dark mode support */
	:global([data-theme="dark"]) .spinner {
		border-color: rgba(255, 255, 255, 0.2);
		border-top-color: var(--c-primary, #60a5fa);
	}
</style>
