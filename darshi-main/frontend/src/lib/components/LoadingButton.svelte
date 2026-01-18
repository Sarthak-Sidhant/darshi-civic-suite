<script lang="ts">
	import LoadingSpinner from "./LoadingSpinner.svelte";

	interface Props {
		loading?: boolean;
		disabled?: boolean;
		type?: "button" | "submit" | "reset";
		variant?: "primary" | "secondary" | "danger" | "success";
		class?: string;
		onclick?: (e: MouseEvent) => void;
		children?: import("svelte").Snippet;
	}

	let {
		loading = false,
		disabled = false,
		type = "button",
		variant = "primary",
		class: customClass = "",
		onclick,
		children,
	}: Props = $props();

	const isDisabled = $derived(loading || disabled);
</script>

<button
	class="loading-button {customClass}"
	class:loading-button-primary={variant === "primary"}
	class:loading-button-secondary={variant === "secondary"}
	class:loading-button-danger={variant === "danger"}
	class:loading-button-success={variant === "success"}
	{type}
	disabled={isDisabled}
	{onclick}
	aria-busy={loading}
>
	{#if loading}
		<span class="loading-button-spinner">
			<LoadingSpinner size="sm" />
		</span>
	{/if}
	<span
		class="loading-button-content"
		class:loading-button-content-hidden={loading}
	>
		{@render children?.()}
	</span>
</button>

<style>
	.loading-button {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.75rem 1.5rem;
		border: none;
		border-radius: var(--radius-md, 8px);
		font-size: 0.9375rem;
		font-weight: 600;
		font-family: var(--font-sans, system-ui, sans-serif);
		cursor: pointer;
		transition: all 0.2s;
		min-height: 44px;
		gap: 0.5rem;
	}

	.loading-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.loading-button-primary {
		background: var(--c-brand, #000);
		color: var(--c-brand-contrast, #fff);
	}

	.loading-button-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.loading-button-secondary {
		background: var(--c-bg-surface, #fff);
		color: var(--c-text-primary, #1f2937);
		border: 1px solid var(--c-border, #d1d5db);
	}

	.loading-button-secondary:hover:not(:disabled) {
		background: var(--c-bg-subtle, #f3f4f6);
	}

	.loading-button-danger {
		background: #dc2626;
		color: white;
	}

	.loading-button-danger:hover:not(:disabled) {
		background: #b91c1c;
	}

	.loading-button-success {
		background: #10b981;
		color: white;
	}

	.loading-button-success:hover:not(:disabled) {
		background: #059669;
	}

	.loading-button-spinner {
		position: absolute;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.loading-button-content {
		transition: opacity 0.2s;
	}

	.loading-button-content-hidden {
		opacity: 0;
	}

	.loading-button:active:not(:disabled) {
		transform: scale(0.98);
	}

	.loading-button:focus-visible {
		outline: 2px solid var(--c-brand, #000);
		outline-offset: 2px;
	}
</style>
