<script lang="ts">
	interface Props {
		size?: 'sm' | 'md' | 'lg';
		color?: string;
	}

	let { size = 'md', color }: Props = $props();

	const sizeMap = {
		sm: '20px',
		md: '32px',
		lg: '48px'
	};
</script>

<div
	class="spinner"
	class:spinner-sm={size === 'sm'}
	class:spinner-md={size === 'md'}
	class:spinner-lg={size === 'lg'}
	style:border-top-color={color}
	role="status"
	aria-label="Loading"
>
	<span class="sr-only">Loading...</span>
</div>

<style>
	.spinner {
		border: 2px solid var(--c-bg-subtle, #e5e7eb);
		border-top-color: var(--c-brand, #000);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.spinner-sm {
		width: 20px;
		height: 20px;
		border-width: 2px;
	}

	.spinner-md {
		width: 32px;
		height: 32px;
		border-width: 3px;
	}

	.spinner-lg {
		width: 48px;
		height: 48px;
		border-width: 4px;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
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
</style>
