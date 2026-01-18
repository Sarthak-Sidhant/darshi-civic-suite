<script lang="ts">
	import { toast, type Toast } from "$lib/stores/toast";
	import { fly, fade } from "svelte/transition";
	import { Check, X, AlertTriangle, Info } from "lucide-svelte";

	let toasts: Toast[] = $state([]);

	$effect(() => {
		const unsubscribe = toast.subscribe((value) => {
			toasts = value;
		});
		return unsubscribe;
	});

	function getAriaLabel(type: Toast["type"]): string {
		switch (type) {
			case "success":
				return "Success notification";
			case "error":
				return "Error notification";
			case "warning":
				return "Warning notification";
			case "info":
				return "Information notification";
			default:
				return "Notification";
		}
	}
</script>

<div class="toast-container" aria-live="polite" aria-atomic="true">
	{#each toasts as t (t.id)}
		<div
			class="toast toast-{t.type}"
			role="alert"
			aria-label={getAriaLabel(t.type)}
			transition:fly={{ y: -20, duration: 300 }}
		>
			<div class="toast-icon" aria-hidden="true">
				{#if t.type === "success"}
					<Check size={14} strokeWidth={3} />
				{:else if t.type === "error"}
					<X size={14} strokeWidth={3} />
				{:else if t.type === "warning"}
					<AlertTriangle size={14} strokeWidth={2.5} />
				{:else}
					<Info size={14} strokeWidth={2.5} />
				{/if}
			</div>
			<div class="toast-message">{t.message}</div>
			<button
				class="toast-close"
				onclick={() => toast.dismiss(t.id)}
				aria-label="Close notification"
				type="button"
			>
				<X size={16} strokeWidth={2} />
			</button>
		</div>
	{/each}
</div>

<style>
	.toast-container {
		position: fixed;
		top: 5rem;
		right: 1rem;
		z-index: 9999;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		max-width: 400px;
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		background: var(--c-bg-surface);
		border-radius: var(--radius-md, 8px);
		box-shadow:
			0 4px 12px rgba(0, 0, 0, 0.15),
			0 0 0 1px rgba(0, 0, 0, 0.1);
		pointer-events: auto;
		min-width: 300px;
		animation: slideIn 0.3s ease-out;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.toast-icon {
		flex-shrink: 0;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		font-weight: 700;
		font-size: 14px;
	}

	.toast-success .toast-icon {
		background: var(--c-success-light, #d1fae5);
		color: var(--c-success-dark, #065f46);
	}

	.toast-error .toast-icon {
		background: var(--c-error-light, #fee2e2);
		color: var(--c-error-dark, #991b1b);
	}

	.toast-warning .toast-icon {
		background: var(--c-warning-light, #fef3c7);
		color: var(--c-warning-dark, #92400e);
	}

	.toast-info .toast-icon {
		background: var(--c-info-light, #dbeafe);
		color: var(--c-info-dark, #1e40af);
	}

	.toast-message {
		flex: 1;
		font-size: 0.9375rem;
		line-height: 1.5;
		color: var(--c-text-primary, #1f2937);
	}

	.toast-close {
		flex-shrink: 0;
		min-width: 44px;
		min-height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: none;
		border-radius: 4px;
		color: var(--c-text-secondary, #6b7280);
		font-size: 20px;
		line-height: 1;
		cursor: pointer;
		transition: all 0.2s;
		padding: 0;
		margin: -0.5rem -0.5rem -0.5rem 0;
	}

	.toast-close:hover {
		background: var(--c-bg-subtle, #f3f4f6);
		color: var(--c-text-primary, #1f2937);
	}

	.toast-close:focus-visible {
		outline: 2px solid var(--c-brand, #000);
		outline-offset: 2px;
	}

	@media (max-width: 640px) {
		.toast-container {
			top: 4rem;
			right: 0.75rem;
			left: 0.75rem;
			max-width: none;
		}

		.toast {
			min-width: 0;
		}
	}

	/* Dark Mode */
	:global([data-theme="dark"]) .toast {
		background: var(--c-bg-surface);
		box-shadow:
			0 4px 12px rgba(0, 0, 0, 0.5),
			0 0 0 1px rgba(255, 255, 255, 0.1);
	}
</style>
