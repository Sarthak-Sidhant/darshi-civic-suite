<script lang="ts">
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";
	import { Check } from "lucide-svelte";

	let email = $state("");
	let loading = $state(false);
	let success = $state(false);
	let error = $state("");

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!email) {
			error = "Please enter your email address";
			return;
		}

		loading = true;
		error = "";

		try {
			const response = await api.post("/auth/forgot-password", { email });

			if (response.ok) {
				success = true;
			} else {
				// Even if email doesn't exist, we show success for security
				success = true;
			}
		} catch (err: any) {
			error = "An error occurred. Please try again.";
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Forgot Password - Darshi</title>
</svelte:head>

<div class="container">
	<div class="card">
		<h1>Forgot Password?</h1>

		{#if !success}
			<p class="subtitle">
				Enter your email address and we'll send you a link to reset your
				password.
			</p>

			{#if error}
				<div class="alert alert-error">{error}</div>
			{/if}

			<form onsubmit={handleSubmit}>
				<div class="form-group">
					<label for="email">Email Address</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						placeholder="your-email@example.com"
						required
						disabled={loading}
					/>
				</div>

				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? "Sending..." : "Send Reset Link"}
				</button>
			</form>

			<div class="links">
				<a href="/signin">Back to Sign In</a>
			</div>
		{:else}
			<div class="success-message">
				<div class="success-icon">
					<Check size={40} strokeWidth={3} />
				</div>
				<h2>Check Your Email</h2>
				<p>
					If an account exists with <strong>{email}</strong>, you will
					receive a password reset link shortly.
				</p>
				<p class="note">
					The link will expire in 1 hour. If you don't receive an
					email, check your spam folder.
				</p>
				<a href="/signin" class="btn-primary">Back to Sign In</a>
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
		max-width: 450px;
		width: 100%;
	}

	h1 {
		font-size: 2rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0 0 1rem 0;
		text-align: center;
	}

	.subtitle {
		color: var(--c-text-secondary);
		text-align: center;
		margin-bottom: 2rem;
		line-height: 1.6;
	}

	.alert {
		padding: 1rem;
		border-radius: var(--radius-sm);
		margin-bottom: 1.5rem;
	}

	.alert-error {
		background: var(--c-error-bg, #fee2e2);
		color: var(--c-error-dark, #991b1b);
		border: 1px solid var(--c-error-border, #ef4444);
	}

	form {
		margin-bottom: 1.5rem;
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	.form-group label {
		display: block;
		font-weight: 500;
		color: var(--c-text-secondary);
		margin-bottom: 0.5rem;
	}

	.form-group input {
		width: 100%;
		padding: 0.875rem 1rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 1rem;
		transition: border-color 0.2s;
		background: var(--c-bg-surface);
		color: var(--c-text-primary);
	}

	.form-group input::placeholder {
		color: var(--c-text-tertiary);
	}

	.form-group input:focus {
		outline: none;
		border-color: var(--c-accent);
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.form-group input:disabled {
		background: var(--c-bg-subtle);
		cursor: not-allowed;
	}

	.btn-primary {
		width: 100%;
		padding: 0.875rem 1.5rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-sm);
		font-weight: 600;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.2s;
		text-decoration: none;
		display: block;
		text-align: center;
	}

	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.links {
		text-align: center;
		padding-top: 1rem;
	}

	.links a {
		color: var(--c-accent);
		text-decoration: none;
		font-weight: 500;
	}

	.links a:hover {
		text-decoration: underline;
	}

	.success-message {
		text-align: center;
	}

	.success-icon {
		width: 80px;
		height: 80px;
		background: #10b981;
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 3rem;
		margin: 0 auto 1.5rem;
		animation: scaleIn 0.3s ease-out;
	}

	@keyframes scaleIn {
		from {
			transform: scale(0);
		}
		to {
			transform: scale(1);
		}
	}

	.success-message h2 {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0 0 1rem 0;
	}

	.success-message p {
		color: var(--c-text-secondary);
		line-height: 1.6;
		margin-bottom: 1rem;
	}

	.success-message p strong {
		color: var(--c-text-primary);
		font-weight: 600;
	}

	.success-message .note {
		font-size: 0.875rem;
		color: var(--c-text-tertiary);
		margin-bottom: 2rem;
	}

	.success-message .btn-primary {
		margin-top: 1.5rem;
	}

	@media (max-width: 640px) {
		.card {
			padding: 2rem 1.5rem;
		}

		h1 {
			font-size: 1.5rem;
		}
	}
</style>
