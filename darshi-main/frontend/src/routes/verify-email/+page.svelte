<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { Check, X } from "lucide-svelte";
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";

	let loading = $state(true);
	let success = $state(false);
	let error = $state("");
	let email = $state("");

	onMount(async () => {
		const token = $page.url.searchParams.get("token");

		if (!token) {
			error = "Invalid verification link. No token provided.";
			loading = false;
			return;
		}

		await verifyEmail(token);
	});

	async function verifyEmail(token: string) {
		try {
			const response = await api.post("/auth/verify-email", { token });

			if (response.ok) {
				const data = await response.json();
				email = data.email;
				success = true;

				// Redirect to signin after 3 seconds
				setTimeout(() => {
					goto("/signin");
				}, 3000);
			} else {
				const data = await response.json();
				error =
					data.detail ||
					"Failed to verify email. The link may be expired or invalid.";
			}
		} catch (err: any) {
			error =
				"An error occurred while verifying your email. Please try again.";
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Verify Email - Darshi</title>
</svelte:head>

<div class="container">
	<div class="card">
		{#if loading}
			<div class="loading-spinner"></div>
			<h1>Verifying Your Email...</h1>
			<p>Please wait while we verify your email address.</p>
		{:else if success}
			<div class="success-icon"><Check size={40} strokeWidth={3} /></div>
			<h1>Email Verified Successfully!</h1>
			<p>
				Your email address <strong>{email}</strong> has been verified.
			</p>
			<p class="redirect-text">
				Redirecting you to sign in page in 3 seconds...
			</p>
			<a href="/signin" class="btn-primary">Go to Sign In Now</a>
		{:else if error}
			<div class="error-icon"><X size={40} strokeWidth={3} /></div>
			<h1>Verification Failed</h1>
			<p class="error-message">{error}</p>
			<div class="actions">
				<a href="/signin" class="btn-secondary">Go to Sign In</a>
				<a href="/settings" class="btn-primary"
					>Resend Verification Email</a
				>
			</div>
		{/if}
	</div>
</div>

<style>
	.container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 1rem;
		background: var(--c-bg-subtle);
	}

	.card {
		background: var(--c-bg-surface);
		padding: 3rem 2rem;
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		border: 1px solid var(--c-border);
		max-width: 500px;
		width: 100%;
		text-align: center;
	}

	.loading-spinner {
		width: 60px;
		height: 60px;
		border: 4px solid var(--c-border);
		border-top-color: var(--c-accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 2rem;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.success-icon {
		width: 80px;
		height: 80px;
		background: var(--c-success);
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 3rem;
		margin: 0 auto 1.5rem;
		animation: scaleIn 0.3s ease-out;
	}

	.error-icon {
		width: 80px;
		height: 80px;
		background: var(--c-error);
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 3rem;
		margin: 0 auto 1.5rem;
	}

	@keyframes scaleIn {
		from {
			transform: scale(0);
		}
		to {
			transform: scale(1);
		}
	}

	h1 {
		font-size: 1.875rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0 0 1rem 0;
	}

	p {
		color: var(--c-text-secondary);
		line-height: 1.6;
		margin-bottom: 1rem;
	}

	p strong {
		color: var(--c-text-primary);
		font-weight: 600;
	}

	.error-message {
		color: var(--c-error-dark);
		background: var(--c-error-bg);
		padding: 1rem;
		border-radius: var(--radius-sm);
		margin: 1.5rem 0;
	}

	.redirect-text {
		color: var(--c-accent);
		font-weight: 500;
		margin-top: 1.5rem;
	}

	.actions {
		display: flex;
		gap: 1rem;
		margin-top: 2rem;
		flex-wrap: wrap;
	}

	.btn-primary,
	.btn-secondary {
		flex: 1;
		min-width: 150px;
		padding: 0.875rem 1.5rem;
		border-radius: var(--radius-sm);
		font-weight: 600;
		text-decoration: none;
		text-align: center;
		cursor: pointer;
		transition: all 0.2s;
		display: inline-block;
	}

	.btn-primary {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
	}

	.btn-primary:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.btn-secondary {
		background: var(--c-bg-surface);
		color: var(--c-accent);
		border: 2px solid var(--c-accent);
	}

	.btn-secondary:hover {
		background: var(--c-bg-subtle);
	}

	@media (max-width: 640px) {
		.card {
			padding: 2rem 1.5rem;
		}

		h1 {
			font-size: 1.5rem;
		}

		.actions {
			flex-direction: column;
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
		}
	}
</style>
