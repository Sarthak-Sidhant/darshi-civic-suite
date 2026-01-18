<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { page } from "$app/stores";
	import { setToken, getMe, setCurrentUser } from "$lib/api";
	import { toast } from "$lib/stores/toast";
	import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";

	let status = $state<"loading" | "success" | "error">("loading");
	let errorMessage = $state("");
	let redirecting = $state(false);

	onMount(async () => {
		try {
			// Extract token, username, and error from query params
			const token = $page.url.searchParams.get("token");
			const username = $page.url.searchParams.get("username");
			const suggestedUsername =
				$page.url.searchParams.get("suggested_username");
			const error = $page.url.searchParams.get("error");

			if (error) {
				throw new Error(`OAuth failed: ${error}`);
			}

			if (!token) {
				throw new Error("No authentication token received");
			}

			// Save token to localStorage
			setToken(token);

			// Fetch user data
			const user = await getMe();
			setCurrentUser(user);

			// Store suggested username for onboarding if provided
			if (suggestedUsername) {
				localStorage.setItem("suggested_username", suggestedUsername);
			}

			status = "success";
			redirecting = true;

			// Always redirect to home - onboarding is now optional
			toast.show(`Welcome, ${user.username}!`, "success");
			setTimeout(() => goto("/"), 1500);
		} catch (error: any) {
			status = "error";
			errorMessage = error.message || "Authentication failed";
			toast.show("Authentication failed", "error");
			setTimeout(() => goto("/signin"), 3000);
		}
	});
</script>

<svelte:head>
	<title>Completing Sign In - Darshi</title>
</svelte:head>

<div class="callback-container">
	{#if status === "loading"}
		<div class="status loading">
			<LoadingSpinner />
			<h2>Completing sign in...</h2>
			<p>Please wait while we authenticate you</p>
		</div>
	{:else if status === "success"}
		<div class="status success">
			<div class="icon">✅</div>
			<h2>Signed in successfully!</h2>
			{#if redirecting}
				<p>Redirecting you now...</p>
				<LoadingSpinner />
			{/if}
		</div>
	{:else}
		<div class="status error">
			<div class="icon">❌</div>
			<h2>Authentication failed</h2>
			<p class="error-message">{errorMessage}</p>
			<p class="redirect-notice">Redirecting to sign in...</p>
		</div>
	{/if}
</div>

<style>
	.callback-container {
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
		color: var(--c-error-dark);
		font-weight: 500;
		margin: 1rem 0;
	}

	.redirect-notice {
		color: var(--c-text-tertiary);
		font-size: 0.875rem;
		margin-top: 1rem;
	}

	.loading {
		padding: 4rem 3rem;
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
