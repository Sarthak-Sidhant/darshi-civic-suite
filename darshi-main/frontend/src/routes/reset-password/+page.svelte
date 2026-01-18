<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";
	import { Check, X } from "lucide-svelte";

	let token = $state("");
	let newPassword = $state("");
	let confirmPassword = $state("");
	let loading = $state(false);
	let success = $state(false);
	let error = $state("");
	let tokenError = $state(false);

	onMount(() => {
		const urlToken = $page.url.searchParams.get("token");

		if (!urlToken) {
			tokenError = true;
			error = "Invalid password reset link. No token provided.";
			return;
		}

		token = urlToken;
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();

		// Validation
		if (!newPassword || !confirmPassword) {
			error = "Please fill in all fields";
			return;
		}

		if (newPassword.length < 8) {
			error = "Password must be at least 8 characters";
			return;
		}

		if (newPassword !== confirmPassword) {
			error = "Passwords do not match";
			return;
		}

		loading = true;
		error = "";

		try {
			const response = await api.post("/auth/reset-password", {
				token,
				new_password: newPassword,
			});

			if (response.ok) {
				success = true;

				// Redirect to signin after 3 seconds
				setTimeout(() => {
					goto("/signin");
				}, 3000);
			} else {
				const data = await response.json();
				error =
					data.detail ||
					"Failed to reset password. The link may be expired or invalid.";
			}
		} catch (err: any) {
			error = "An error occurred. Please try again.";
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Reset Password - Darshi</title>
</svelte:head>

<div class="container">
	<div class="card">
		{#if tokenError}
			<div class="error-icon"><X size={40} strokeWidth={3} /></div>
			<h1>Invalid Reset Link</h1>
			<p class="error-message">{error}</p>
			<a href="/forgot-password" class="btn-primary">Request New Link</a>
		{:else if success}
			<div class="success-icon"><Check size={40} strokeWidth={3} /></div>
			<h1>Password Reset Successful!</h1>
			<p>Your password has been reset successfully.</p>
			<p class="redirect-text">
				Redirecting you to sign in page in 3 seconds...
			</p>
			<a href="/signin" class="btn-primary">Go to Sign In Now</a>
		{:else}
			<h1>Reset Your Password</h1>
			<p class="subtitle">Enter your new password below.</p>

			{#if error}
				<div class="alert alert-error">{error}</div>
			{/if}

			<form onsubmit={handleSubmit}>
				<div class="form-group">
					<label for="newPassword">New Password</label>
					<input
						id="newPassword"
						type="password"
						bind:value={newPassword}
						placeholder="Enter new password (min 8 characters)"
						required
						disabled={loading}
					/>
				</div>

				<div class="form-group">
					<label for="confirmPassword">Confirm Password</label>
					<input
						id="confirmPassword"
						type="password"
						bind:value={confirmPassword}
						placeholder="Confirm new password"
						required
						disabled={loading}
					/>
				</div>

				<div class="password-requirements">
					<p>Password must:</p>
					<ul>
						<li class:valid={newPassword.length >= 8}>
							Be at least 8 characters long
						</li>
						<li
							class:valid={newPassword === confirmPassword &&
								newPassword.length > 0}
						>
							Match the confirmation
						</li>
					</ul>
				</div>

				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? "Resetting..." : "Reset Password"}
				</button>
			</form>

			<div class="links">
				<a href="/signin">Back to Sign In</a>
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

	.password-requirements {
		background: var(--c-bg-subtle);
		padding: 1rem;
		border-radius: var(--radius-sm);
		margin-bottom: 1.5rem;
	}

	.password-requirements p {
		margin: 0 0 0.5rem 0;
		font-weight: 500;
		color: var(--c-text-secondary);
		font-size: 0.875rem;
	}

	.password-requirements ul {
		margin: 0;
		padding-left: 1.5rem;
		list-style: none;
	}

	.password-requirements li {
		color: var(--c-text-tertiary);
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
		position: relative;
	}

	.password-requirements li::before {
		content: "○";
		position: absolute;
		left: -1.5rem;
	}

	.password-requirements li.valid {
		color: #10b981;
	}

	.password-requirements li.valid::before {
		content: "●";
		font-weight: bold;
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

	.success-icon,
	.error-icon {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 3rem;
		margin: 0 auto 1.5rem;
		color: white;
	}

	.success-icon {
		background: #10b981;
		animation: scaleIn 0.3s ease-out;
	}

	.error-icon {
		background: #ef4444;
	}

	@keyframes scaleIn {
		from {
			transform: scale(0);
		}
		to {
			transform: scale(1);
		}
	}

	.error-message {
		color: var(--c-error-dark, #991b1b);
		text-align: center;
		margin-bottom: 2rem;
	}

	.redirect-text {
		color: var(--c-accent);
		font-weight: 500;
		text-align: center;
		margin: 1.5rem 0;
	}

	p {
		text-align: center;
		color: var(--c-text-secondary);
		margin-bottom: 1rem;
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
