<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { page } from "$app/stores";
	import { login, api, getErrorMessage, setCurrentUser } from "$lib/api";
	import { isAuthenticated } from "$lib/stores";
	import { toast } from "$lib/stores/toast";
	import LoadingButton from "$lib/components/LoadingButton.svelte";
	import Turnstile from "$lib/components/Turnstile.svelte";

	// API base URL without /api/v1 suffix for OAuth
	const API_BASE_URL =
		import.meta.env.VITE_API_URL?.replace("/api/v1", "") ||
		"http://localhost:8080";

	// Auth method state: 'initial' | 'email-password' | 'email-magic-link'
	let authMethod = $state<"initial" | "email-password" | "email-magic-link">(
		"initial",
	);
	let loading = $state(false);

	// Email/Password form
	let email = $state("");
	let password = $state("");

	// Turnstile verification
	let turnstileToken = $state("");
	let turnstileComponent = $state<Turnstile>();

	// Magic link form
	let magicLinkEmail = $state("");
	let magicLinkSent = $state(false);

	// Redirect if already logged in
	onMount(() => {
		if ($isAuthenticated) {
			goto("/");
		}

		// Handle OAuth errors
		const errorParam = $page.url.searchParams.get("error");
		const errorMessage = $page.url.searchParams.get("message");

		if (errorParam) {
			if (errorParam === "oauth_init_failed") {
				toast.show("Failed to start OAuth login", "error");
			} else if (errorParam === "oauth_callback_failed") {
				toast.show("OAuth authentication failed", "error");
			} else if (errorParam === "user_creation_failed") {
				toast.show("Failed to create user account", "error");
			} else if (errorParam === "oauth_error") {
				toast.show(errorMessage || "OAuth error occurred", "error");
			} else if (errorParam === "expired") {
				toast.show("Session expired. Please sign in again.", "info");
			}
		}
	});

	// OAuth handlers - redirect to backend
	function handleGoogleAuth() {
		window.location.href = `${API_BASE_URL}/api/v1/auth/google/login`;
	}

	function handleGitHubAuth() {
		window.location.href = `${API_BASE_URL}/api/v1/auth/github/login`;
	}

	function handleFacebookAuth() {
		window.location.href = `${API_BASE_URL}/api/v1/auth/facebook/login`;
	}

	// Show email/password form
	function showEmailPassword() {
		authMethod = "email-password";
		email = "";
		password = "";
	}

	// Show magic link form
	function showMagicLink() {
		authMethod = "email-magic-link";
		magicLinkEmail = "";
		magicLinkSent = false;
	}

	// Back to initial state
	function backToInitial() {
		authMethod = "initial";
		email = "";
		password = "";
		magicLinkEmail = "";
		magicLinkSent = false;
	}

	// Email + password login
	async function handleEmailPasswordLogin(e: Event) {
		e.preventDefault();
		loading = true;

		try {
			const result = await login(email, password);

			// Token is automatically saved by login()
			// Check if user needs onboarding by fetching their profile
			const res = await api.get("/auth/me");
			const userData = await res.json();
		// CRITICAL: Save user data to localStorage so getCurrentUser() works
		setCurrentUser(userData);


			const isValidCity =
				userData.city?.trim() &&
				userData.city.toLowerCase() !== "unspecified";
			if (!isValidCity) {
				toast.show("Welcome! Please complete your profile", "info");
				goto("/onboarding");
			} else {
				toast.show(`Welcome back, ${userData.username}!`, "success");
				goto("/");
			}
		} catch (err: any) {
			toast.show(getErrorMessage(err), "error");
		} finally {
			loading = false;
		}
	}

	// Send magic link
	async function handleSendMagicLink(e: Event) {
		e.preventDefault();

		// Verify Turnstile token
		if (!turnstileToken) {
			toast.show("Please complete the verification challenge", "error");
			return;
		}

		loading = true;

		try {
			await api.post("/auth/send-magic-link", {
				email: magicLinkEmail,
				turnstile_token: turnstileToken,
			});
			magicLinkSent = true;
			toast.show("Check your email for the login link!", "success");
		} catch (err: any) {
			toast.show(getErrorMessage(err), "error");
			// Reset Turnstile on error
			if (turnstileComponent) {
				turnstileComponent.reset();
				turnstileToken = "";
			}
		} finally {
			loading = false;
		}
	}

	// Turnstile handlers
	function handleTurnstileVerify(token: string) {
		turnstileToken = token;
	}

	function handleTurnstileError() {
		turnstileToken = "";
		toast.show("Verification failed. Please try again.", "error");
	}

	function handleTurnstileExpire() {
		turnstileToken = "";
		toast.show("Verification expired. Please verify again.", "warning");
	}
</script>

<svelte:head>
	<title>Sign In - Darshi</title>
</svelte:head>

<div class="signin-container">
	<div class="signin-card">
		<!-- Logo/Header -->
		<div class="header">
			<h1>दर्शी</h1>
			<p class="tagline">Civic Grievance Platform</p>
		</div>

		{#if authMethod === "initial"}
			<!-- Initial State: OAuth + Email Options -->
			<div class="auth-options">
				<h2>Sign In to Darshi</h2>
				<p class="subtitle">Choose your preferred sign-in method</p>

				<!-- OAuth Buttons -->
				<div class="oauth-buttons">
					<button class="oauth-btn google" onclick={handleGoogleAuth}>
						<svg width="18" height="18" viewBox="0 0 18 18">
							<path
								fill="#4285F4"
								d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"
							/>
							<path
								fill="#34A853"
								d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"
							/>
							<path
								fill="#FBBC05"
								d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"
							/>
							<path
								fill="#EA4335"
								d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"
							/>
						</svg>
						Continue with Google
					</button>

					<button class="oauth-btn github" onclick={handleGitHubAuth}>
						<svg
							width="18"
							height="18"
							viewBox="0 0 16 16"
							fill="currentColor"
						>
							<path
								d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
							/>
						</svg>
						Continue with GitHub
					</button>

					<button
						class="oauth-btn facebook"
						onclick={handleFacebookAuth}
					>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<path
								d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"
							/>
						</svg>
						Continue with Facebook
					</button>
				</div>

				<!-- Divider -->
				<div class="divider">
					<span>OR</span>
				</div>

				<!-- Email Options -->
				<div class="email-options">
					<button class="email-btn" onclick={showEmailPassword}>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path
								d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
							/>
							<polyline points="22,6 12,13 2,6" />
						</svg>
						Continue with Email & Password
					</button>

					<button class="email-btn magic" onclick={showMagicLink}>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path
								d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"
							/>
							<circle cx="12" cy="10" r="3" />
						</svg>
						Send Login Link to Email
					</button>
				</div>

				<p class="help-text">
					Don't have an account? You'll create one automatically after
					signing in.
				</p>
			</div>
		{:else if authMethod === "email-password"}
			<!-- Email + Password Form -->
			<div class="email-form">
				<button class="back-btn" onclick={backToInitial}>
					← Back
				</button>

				<h2>Sign in with Email</h2>
				<p class="subtitle">Enter your email and password</p>

				<form onsubmit={handleEmailPasswordLogin}>
					<div class="form-group">
						<label for="email">Email</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							placeholder="your@email.com"
							required
							autocomplete="email"
						/>
					</div>

					<div class="form-group">
						<label for="password">Password</label>
						<input
							id="password"
							type="password"
							bind:value={password}
							placeholder="Enter your password"
							required
							autocomplete="current-password"
							minlength="6"
						/>
					</div>

					<LoadingButton type="submit" {loading} class="submit-btn">
						Sign In
					</LoadingButton>
				</form>

				<div class="form-footer">
					<a href="/forgot-password" class="forgot-link"
						>Forgot password?</a
					>
					<p class="help-text">
						Don't have an account? No worries! If this email isn't
						registered, we'll create an account for you after you
						sign in.
					</p>
				</div>
			</div>
		{:else if authMethod === "email-magic-link"}
			<!-- Magic Link Form -->
			<div class="email-form">
				<button class="back-btn" onclick={backToInitial}>
					← Back
				</button>

				{#if !magicLinkSent}
					<h2>Passwordless Sign In</h2>
					<p class="subtitle">
						We'll send a magic link to your email
					</p>

					<form onsubmit={handleSendMagicLink}>
						<div class="form-group">
							<label for="magic-email">Email Address</label>
							<input
								id="magic-email"
								type="email"
								bind:value={magicLinkEmail}
								placeholder="your@email.com"
								required
								autocomplete="email"
							/>
						</div>

						<!-- Cloudflare Turnstile -->
						<Turnstile
							bind:this={turnstileComponent}
							onVerify={handleTurnstileVerify}
							onError={handleTurnstileError}
							onExpire={handleTurnstileExpire}
						/>

						<LoadingButton
							type="submit"
							{loading}
							class="submit-btn"
						>
							Send Login Link
						</LoadingButton>
					</form>

					<p class="help-text">
						Click the link in your email to sign in instantly. No
						password needed!
					</p>
				{:else}
					<div class="success-message">
						<div class="icon">✉️</div>
						<h2>Check your email!</h2>
						<p>We've sent a login link to:</p>
						<p class="email-sent">{magicLinkEmail}</p>
						<p class="help-text">
							The link will expire in 15 minutes. Didn't receive
							it?
						</p>
						<button
							class="resend-btn"
							onclick={() => {
								magicLinkSent = false;
							}}
						>
							Send another link
						</button>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.signin-container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		background: var(--c-bg-subtle);
	}

	.signin-card {
		background: var(--c-bg-surface);
		border-radius: var(--radius-lg);
		padding: 2.5rem;
		max-width: 480px;
		width: 100%;
		box-shadow: var(--shadow-lg);
		border: 1px solid var(--c-border);
	}

	.header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.header h1 {
		font-size: 2.5rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0;
	}

	.tagline {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		margin-top: 0.5rem;
	}

	h2 {
		font-size: 1.5rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		color: var(--c-text-primary);
	}

	.subtitle {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		margin-bottom: 1.5rem;
	}

	.oauth-buttons {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.oauth-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 0.875rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		background: var(--c-bg-surface);
		font-size: 0.9375rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
		color: var(--c-text-primary);
	}

	.oauth-btn:hover {
		border-color: var(--c-border-hover);
		background: var(--c-bg-subtle);
		transform: translateY(-1px);
	}

	.oauth-btn.google {
		color: var(--c-text-primary);
	}
	.oauth-btn.github {
		color: var(--c-text-primary);
	}
	.oauth-btn.facebook {
		color: #1877f2;
	}

	.divider {
		display: flex;
		align-items: center;
		margin: 1.5rem 0;
		color: var(--c-text-tertiary);
		font-size: 0.875rem;
	}

	.divider::before,
	.divider::after {
		content: "";
		flex: 1;
		height: 1px;
		background: var(--c-border);
	}

	.divider span {
		padding: 0 1rem;
	}

	.email-options {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.email-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 0.875rem;
		border: 2px solid var(--c-accent);
		border-radius: var(--radius-sm);
		background: var(--c-bg-surface);
		color: var(--c-accent);
		font-size: 0.9375rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.email-btn:hover {
		background: var(--c-accent);
		color: white;
		transform: translateY(-1px);
	}

	.email-btn.magic {
		border-color: var(--c-brand);
		color: var(--c-brand);
	}

	.email-btn.magic:hover {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
	}

	.help-text {
		text-align: center;
		color: var(--c-text-tertiary);
		font-size: 0.8125rem;
		margin-top: 1rem;
		line-height: 1.5;
	}

	.back-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0;
		background: none;
		border: none;
		color: var(--c-accent);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		margin-bottom: 1.5rem;
	}

	.back-btn:hover {
		text-decoration: underline;
	}

	.form-group {
		margin-bottom: 1.25rem;
	}

	.form-group label {
		display: block;
		margin-bottom: 0.5rem;
		color: var(--c-text-secondary);
		font-size: 0.875rem;
		font-weight: 500;
	}

	.form-group input {
		width: 100%;
		padding: 0.75rem;
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

	:global(.submit-btn) {
		width: 100%;
		padding: 0.875rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-sm);
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition:
			opacity 0.2s,
			transform 0.2s;
	}

	:global(.submit-btn:hover:not(:disabled)) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	:global(.submit-btn:disabled) {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.form-footer {
		margin-top: 1.5rem;
		text-align: center;
	}

	.forgot-link {
		display: inline-block;
		color: var(--c-accent);
		font-size: 0.875rem;
		font-weight: 500;
		text-decoration: none;
		margin-bottom: 1rem;
	}

	.forgot-link:hover {
		text-decoration: underline;
	}

	.success-message {
		text-align: center;
		padding: 2rem 0;
	}

	.success-message .icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	.email-sent {
		font-weight: 600;
		color: var(--c-accent);
		margin: 0.5rem 0;
	}

	.resend-btn {
		margin-top: 1rem;
		padding: 0.625rem 1.5rem;
		background: var(--c-bg-surface);
		border: 2px solid var(--c-accent);
		border-radius: var(--radius-sm);
		color: var(--c-accent);
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.resend-btn:hover {
		background: var(--c-accent);
		color: white;
	}

	@media (max-width: 640px) {
		.signin-card {
			padding: 2rem 1.5rem;
		}
	}
</style>
