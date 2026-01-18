<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { page } from "$app/stores";
	import { api, setToken, getMe, setCurrentUser } from "$lib/api";
	import { toast } from "$lib/stores/toast";
	import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";

	let status = $state<"verifying" | "success" | "error">("verifying");
	let errorMessage = $state("");

	onMount(async () => {
		const token = $page.url.searchParams.get("token");

		if (!token) {
			status = "error";
			errorMessage = "Invalid link - no token provided";
			return;
		}

		try {
			// Verify magic link with backend
			const res = await api.get(`/auth/verify-magic-link?token=${token}`);
			const response = await res.json();

			// Save token
			setToken(response.access_token);

			// Fetch and save user data
			const user = response.user;
			setCurrentUser(user);

			status = "success";
			toast.show("Signed in successfully!", "success");

			// Check if user needs onboarding
			const isValidCity =
				user.city?.trim() && user.city.toLowerCase() !== "unspecified";
			if (!isValidCity) {
				setTimeout(() => goto("/onboarding"), 1500);
			} else {
				setTimeout(() => goto("/"), 1500);
			}
		} catch (error: any) {
			status = "error";
			errorMessage = error.message || "Invalid or expired link";
		}
	});
</script>

<svelte:head>
	<title>Magic Link Sign In - Darshi</title>
</svelte:head>

<div class="magic-link-container">
	{#if status === "verifying"}
		<div class="status verifying">
			<LoadingSpinner />
			<h2>Verifying your login link...</h2>
			<p>Please wait a moment</p>
		</div>
	{:else if status === "success"}
		<div class="status success">
			<div class="icon">✅</div>
			<h2>Signed in successfully!</h2>
			<p>Redirecting you now...</p>
		</div>
	{:else}
		<div class="status error">
			<div class="icon">❌</div>
			<h2>Link Invalid or Expired</h2>
			<p class="error-message">{errorMessage}</p>
			<p class="help-text">
				Magic links expire after 15 minutes and can only be used once.
			</p>
			<a href="/signin" class="back-button">Back to Sign In</a>
		</div>
	{/if}
</div>

<style>
	.magic-link-container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		background: var(--c-bg-subtle);
	}

	.status {
		background: var(--c-bg-surface);
		padding: 3rem;
		border-radius: var(--radius-lg);
		text-align: center;
		max-width: 500px;
		width: 100%;
		box-shadow: var(--shadow-lg);
		border: 1px solid var(--c-border);
	}

	.icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	h2 {
		font-size: 1.75rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		color: var(--c-text-primary);
	}

	p {
		color: var(--c-text-secondary);
		font-size: 1rem;
		margin: 0.5rem 0;
	}

	.error-message {
		color: var(--c-error-dark, #dc2626);
		font-weight: 500;
		margin: 1rem 0;
	}

	.help-text {
		color: var(--c-text-tertiary);
		font-size: 0.875rem;
		margin: 1rem 0;
	}

	.back-button {
		display: inline-block;
		margin-top: 1.5rem;
		padding: 0.75rem 2rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		text-decoration: none;
		border-radius: var(--radius-sm);
		font-weight: 500;
		transition:
			opacity 0.2s,
			transform 0.2s;
	}

	.back-button:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.success,
	.error {
		animation: slideIn 0.3s ease-out;
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
