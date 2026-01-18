<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { user, isAuthenticated } from "$lib/stores";
	import {
		api,
		deleteAccount,
		clearToken,
		clearCurrentUser,
		getErrorMessage,
	} from "$lib/api";
	import { toast } from "$lib/stores/toast";
	import { notifications } from "$lib/stores/notifications";
	import { Check, X, Loader2 } from "lucide-svelte";

	let profile = $state<any>(null);
	let loading = $state(true);
	let saving = $state(false);
	let deletingAccount = $state(false);

	// Form fields
	let username = $state("");
	let originalUsername = $state("");
	let fullName = $state("");
	let oldPassword = $state("");
	let newPassword = $state("");
	let confirmPassword = $state("");

	// Username validation
	let checkingUsername = $state(false);
	let usernameError = $state("");
	let usernameAvailable = $state(true);

	onMount(async () => {
		if (!$isAuthenticated) {
			goto("/signin");
			return;
		}

		// Load states for dropdown
		loadStates();

		try {
			const response = await api.get("/users/me/profile");
			if (response.ok) {
				profile = await response.json();
				fullName = profile.full_name || "";
				username = profile.username || "";
				originalUsername = profile.username || "";
				// Initialize location
				city = profile.city || "";
				userState = profile.state || "";
				country = profile.country || "India";
			} else {
				toast.show("Failed to load profile", "error");
			}
		} catch (err) {
			toast.show("Failed to load profile", "error");
		} finally {
			loading = false;
		}
	});

	async function checkUsername() {
		if (!username || username.length < 3) {
			usernameError = "Username must be at least 3 characters";
			usernameAvailable = false;
			return false;
		}

		// If username hasn't changed, it's valid
		if (username === originalUsername) {
			usernameError = "";
			usernameAvailable = true;
			return true;
		}

		// Validate format
		if (!/^[a-z0-9_]+$/.test(username)) {
			usernameError = "Only lowercase letters, numbers, and underscores";
			usernameAvailable = false;
			return false;
		}

		checkingUsername = true;
		usernameError = "";

		try {
			const res = await api.get(
				`/auth/check-username?username=${encodeURIComponent(username)}`,
			);
			const response = await res.json();
			if (!response.available) {
				usernameError = "Username already taken";
				usernameAvailable = false;
				return false;
			}
			usernameError = "";
			usernameAvailable = true;
			return true;
		} catch (error) {
			usernameError = "Unable to verify";
			return true; // Allow submission, backend will validate
		} finally {
			checkingUsername = false;
		}
	}

	// Location state
	let city = $state("");
	let userState = $state("");
	let country = $state("India");
	let availableStates = $state<string[]>([]);
	let availableCities = $state<string[]>([]);
	let loadingCities = $state(false);

	// Load states on mount
	async function loadStates() {
		try {
			const res = await api.get("/location/states");
			if (res.ok) {
				availableStates = await res.json();
			}
		} catch {
			// Silently fail
		}
	}

	// Load cities when state changes
	async function loadCities(stateName: string) {
		if (!stateName) {
			availableCities = [];
			return;
		}
		loadingCities = true;
		try {
			const res = await api.get(
				`/location/cities?state=${encodeURIComponent(stateName)}`,
			);
			if (res.ok) {
				availableCities = await res.json();
			}
		} catch {
			// Silently fail
		} finally {
			loadingCities = false;
		}
	}

	// Watch for state changes
	$effect(() => {
		if (userState) {
			loadCities(userState);
		}
	});

	async function updateProfile() {
		// Check username availability first if changed
		if (username !== originalUsername) {
			const isValid = await checkUsername();
			if (!isValid) {
				return;
			}
		}

		saving = true;
		try {
			const updateData: any = { full_name: fullName };

			// Only include username if changed
			if (username !== originalUsername) {
				updateData.username = username;
			}

			// Include location if set
			if (city) updateData.city = city;
			if (userState) updateData.state = userState;
			if (country) updateData.country = country;

			const response = await api.put("/users/me/profile", updateData);

			if (response.ok) {
				toast.show("Profile updated!", "success");
				profile = await response.json();
				originalUsername = profile.username; // Update original
				// Update global user state
				$user = profile;
			} else {
				const data = await response.json();
				toast.show(data.detail || "Update failed", "error");
			}
		} catch (err) {
			toast.show("Update failed", "error");
		} finally {
			saving = false;
		}
	}

	async function changePassword() {
		if (newPassword !== confirmPassword) {
			toast.show("Passwords do not match", "error");
			return;
		}

		if (newPassword.length < 8) {
			toast.show("Password must be at least 8 characters", "error");
			return;
		}

		saving = true;
		try {
			const response = await api.put("/auth/change-password", {
				old_password: oldPassword,
				new_password: newPassword,
			});

			if (response.ok) {
				toast.show("Password changed!", "success");
				oldPassword = "";
				newPassword = "";
				confirmPassword = "";
			} else {
				const data = await response.json();
				toast.show(data.detail || "Failed to change password", "error");
			}
		} catch (err) {
			toast.show("Failed to change password", "error");
		} finally {
			saving = false;
		}
	}

	async function handleDeleteAccount() {
		// Double confirmation for irreversible action
		const firstConfirm = confirm(
			"Are you absolutely sure you want to delete your account?\n\n" +
				"This will permanently delete:\n" +
				"• Your profile and settings\n" +
				"• All your reports\n" +
				"• All your comments\n\n" +
				"This action CANNOT be undone.",
		);

		if (!firstConfirm) return;

		const secondConfirm = confirm(
			"This is your final warning.\n\n" +
				"Type your username to confirm: " +
				(profile?.username || "") +
				"\n\n" +
				"Click OK to permanently delete your account.",
		);

		if (!secondConfirm) return;

		deletingAccount = true;
		try {
			await deleteAccount();

			// Clear all local state
			clearToken();
			clearCurrentUser();
			notifications.clear();
			$user = null;
			$isAuthenticated = false;

			toast.show("Your account has been deleted. Goodbye!", "success");

			// Redirect to home
			goto("/");
		} catch (err) {
			toast.show(
				getErrorMessage(err) || "Failed to delete account",
				"error",
			);
		} finally {
			deletingAccount = false;
		}
	}
</script>

<svelte:head>
	<title>Settings - Darshi</title>
</svelte:head>

{#if loading}
	<div class="loading">Loading...</div>
{:else if profile}
	<div class="settings-page">
		<h1>Settings</h1>

		<!-- Profile Info -->
		<div class="card">
			<h2>Profile Information</h2>
			<form
				onsubmit={(e) => {
					e.preventDefault();
					updateProfile();
				}}
			>
				<div class="form-group">
					<label for="username">Username</label>
					<div class="input-with-status">
						<input
							id="username"
							type="text"
							bind:value={username}
							onblur={checkUsername}
							placeholder="your_username"
							pattern="[a-z0-9_]+"
						/>
						{#if checkingUsername}
							<span class="status-icon checking"
								><Loader2 size={16} class="spin" /></span
							>
						{:else if username && username === originalUsername}
							<span class="status-icon current">Current</span>
						{:else if usernameAvailable && username.length >= 3 && !usernameError}
							<span class="status-icon available"
								><Check size={16} /></span
							>
						{:else if usernameError}
							<span class="status-icon error"
								><X size={16} /></span
							>
						{/if}
					</div>
					{#if usernameError}
						<small class="error-text">{usernameError}</small>
					{:else}
						<small
							>Lowercase letters, numbers, and underscores only</small
						>
					{/if}
				</div>

				<div class="form-group">
					<label for="fullName">Full Name</label>
					<input
						id="fullName"
						type="text"
						bind:value={fullName}
						placeholder="Enter your name"
					/>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label for="state">State</label>
						<select id="state" bind:value={userState}>
							<option value="">Select state</option>
							{#each availableStates as state}
								<option value={state}>{state}</option>
							{/each}
						</select>
					</div>

					<div class="form-group">
						<label for="city">City</label>
						<select
							id="city"
							bind:value={city}
							disabled={!userState || loadingCities}
						>
							<option value=""
								>{loadingCities
									? "Loading..."
									: "Select city"}</option
							>
							{#each availableCities as c}
								<option value={c}>{c}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class="form-group">
					<label for="email">Email</label>
					<input
						id="email"
						type="email"
						value={profile.email}
						disabled
						class="disabled-input"
					/>
					<small>Email cannot be changed</small>
				</div>

				<button
					type="submit"
					class="btn-primary"
					disabled={saving ||
						(!!usernameError && username !== originalUsername)}
				>
					{saving ? "Saving..." : "Save Changes"}
				</button>
			</form>
		</div>

		<!-- Verification Status -->
		<div class="card">
			<h2>Account Verification</h2>

			<div class="verification-row">
				<div class="verification-info">
					<strong>Email</strong>
					{#if profile.email_verified}
						<span class="badge success"
							><Check size={12} /> Verified</span
						>
					{:else}
						<span class="badge error"
							><X size={12} /> Not Verified</span
						>
					{/if}
				</div>
			</div>

			{#if profile.phone}
				<div class="verification-row">
					<div class="verification-info">
						<strong>Phone</strong>
						{#if profile.phone_verified}
							<span class="badge success"
								><Check size={12} /> Verified</span
							>
						{:else}
							<span class="badge error"
								><X size={12} /> Not Verified</span
							>
						{/if}
					</div>
				</div>
			{/if}

			{#if profile.oauth_provider}
				<div class="verification-row">
					<div class="verification-info">
						<strong>Connected Account</strong>
						<span class="badge info">{profile.oauth_provider}</span>
					</div>
				</div>
			{/if}
		</div>

		<!-- Change Password -->
		{#if !profile.oauth_provider}
			<div class="card">
				<h2>Change Password</h2>
				<form
					onsubmit={(e) => {
						e.preventDefault();
						changePassword();
					}}
				>
					<div class="form-group">
						<label for="oldPassword">Current Password</label>
						<input
							id="oldPassword"
							type="password"
							bind:value={oldPassword}
							placeholder="Enter current password"
						/>
					</div>

					<div class="form-group">
						<label for="newPassword">New Password</label>
						<input
							id="newPassword"
							type="password"
							bind:value={newPassword}
							placeholder="Min 8 characters"
						/>
					</div>

					<div class="form-group">
						<label for="confirmPassword">Confirm New Password</label
						>
						<input
							id="confirmPassword"
							type="password"
							bind:value={confirmPassword}
							placeholder="Confirm new password"
						/>
					</div>

					<button type="submit" class="btn-primary" disabled={saving}>
						{saving ? "Changing..." : "Change Password"}
					</button>
				</form>
			</div>
		{:else}
			<div class="card info-card">
				<strong>Password Management</strong>
				<p>
					You signed in with {profile.oauth_provider}. Your password
					is managed by {profile.oauth_provider}.
				</p>
			</div>
		{/if}

		<!-- Notification Preferences -->
		<div class="card">
			<h2>Notification Preferences</h2>

			<div class="preference-row">
				<div class="preference-info">
					<strong>In-App Notifications</strong>
					<p>
						Receive notifications within the app for updates on your
						reports
					</p>
				</div>
				<label class="toggle-switch">
					<input type="checkbox" checked />
					<span class="toggle-slider"></span>
				</label>
			</div>

			<div class="preference-row">
				<div class="preference-info">
					<strong>Email Notifications</strong>
					<p>Receive email updates about report status changes</p>
				</div>
				<label class="toggle-switch">
					<input type="checkbox" />
					<span class="toggle-slider"></span>
				</label>
			</div>

			<div class="preference-row">
				<div class="preference-info">
					<strong>Alert Broadcasts</strong>
					<p>Get notified about emergency alerts in your area</p>
				</div>
				<label class="toggle-switch">
					<input type="checkbox" checked />
					<span class="toggle-slider"></span>
				</label>
			</div>

			<div class="preference-row">
				<div class="preference-info">
					<strong>Community Updates</strong>
					<p>Receive updates on reports near your location</p>
				</div>
				<label class="toggle-switch">
					<input type="checkbox" />
					<span class="toggle-slider"></span>
				</label>
			</div>
		</div>

		<!-- Danger Zone -->
		<div class="card danger-card">
			<h2>Danger Zone</h2>
			<div class="danger-content">
				<div>
					<strong>Delete Account</strong>
					<p>
						Permanently delete your account and all data. This
						cannot be undone.
					</p>
				</div>
				<button
					class="btn-danger"
					onclick={handleDeleteAccount}
					disabled={deletingAccount}
				>
					{deletingAccount ? "Deleting..." : "Delete Account"}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.loading {
		text-align: center;
		padding: 4rem 2rem;
		font-size: 1.125rem;
		color: var(--c-text-secondary);
	}

	.settings-page {
		max-width: 800px;
		margin: 0 auto;
		padding: 1rem;
	}

	h1 {
		font-size: 2rem;
		font-weight: 700;
		color: var(--c-text-primary);
		margin: 0 0 1.5rem 0;
	}

	.card {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-sm);
		border: 1px solid var(--c-border);
		margin-bottom: 1rem;
	}

	.card h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--c-text-primary);
		margin: 0 0 1rem 0;
	}

	/* Form Styles */
	.form-group {
		margin-bottom: 1.25rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-row .form-group {
		margin-bottom: 1.25rem;
	}

	.form-group select {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		font-size: 1rem;
		background: var(--c-bg-surface);
		color: var(--c-text-primary);
		cursor: pointer;
		transition: border-color 0.2s;
	}

	.form-group select:focus {
		outline: none;
		border-color: var(--c-accent);
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.form-group select:disabled {
		background: var(--c-bg-subtle);
		color: var(--c-text-secondary);
		cursor: not-allowed;
	}

	.form-group label {
		display: block;
		font-weight: 500;
		color: var(--c-text-secondary);
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
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

	.disabled-input {
		background: var(--c-bg-subtle);
		color: var(--c-text-secondary);
		cursor: not-allowed;
	}

	.form-group small {
		display: block;
		color: var(--c-text-tertiary);
		font-size: 0.8125rem;
		margin-top: 0.25rem;
	}

	.form-group small.error-text {
		color: var(--c-error);
	}

	/* Username input with status */
	.input-with-status {
		position: relative;
		display: flex;
		align-items: center;
	}

	.input-with-status input {
		flex: 1;
		padding-right: 3rem;
	}

	.status-icon {
		position: absolute;
		right: 0.75rem;
		display: flex;
		align-items: center;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.status-icon.available {
		color: var(--c-success);
	}

	.status-icon.error {
		color: var(--c-error);
	}

	.status-icon.current {
		color: var(--c-text-secondary);
	}

	.status-icon.checking {
		color: var(--c-accent);
	}

	.status-icon :global(.spin) {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	/* Verification */
	.verification-row {
		padding: 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-sm);
		margin-bottom: 0.75rem;
	}

	.verification-row:last-child {
		margin-bottom: 0;
	}

	.verification-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.verification-info strong {
		color: var(--c-text-primary);
		font-size: 0.9375rem;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.5rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.badge.success {
		background: var(--c-success-light);
		color: var(--c-success-dark);
	}

	.badge.error {
		background: var(--c-error-light);
		color: var(--c-error-dark);
	}

	.badge.info {
		background: var(--c-info-light);
		color: var(--c-info-dark);
		text-transform: capitalize;
	}

	/* Info Card */
	.info-card {
		background: var(--c-info-bg);
		border: 1px solid var(--c-info-border);
	}

	.info-card strong {
		display: block;
		color: var(--c-info-dark);
		margin-bottom: 0.5rem;
		font-size: 1rem;
	}

	.info-card p {
		color: var(--c-info-dark);
		margin: 0;
		font-size: 0.9375rem;
	}

	/* Danger Card */
	.danger-card {
		background: var(--c-error-bg);
		border: 1px solid var(--c-error-border);
	}

	.danger-card h2 {
		color: var(--c-error-dark);
	}

	.danger-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1.5rem;
	}

	.danger-content strong {
		display: block;
		color: var(--c-error-dark);
		margin-bottom: 0.25rem;
		font-size: 1rem;
	}

	.danger-content p {
		color: var(--c-error-dark);
		margin: 0;
		font-size: 0.875rem;
	}

	/* Buttons */
	.btn-primary,
	.btn-danger {
		padding: 0.75rem 1.5rem;
		border-radius: var(--radius-sm);
		font-weight: 600;
		cursor: pointer;
		border: none;
		transition: opacity 0.2s;
		font-size: 0.9375rem;
		font-family: inherit;
	}

	.btn-primary {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		width: 100%;
	}

	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-danger {
		background: var(--c-error);
		color: white;
		flex-shrink: 0;
	}

	.btn-danger:hover {
		opacity: 0.9;
	}

	/* Mobile Responsive */
	@media (max-width: 768px) {
		.settings-page {
			padding: 0.75rem;
		}

		h1 {
			font-size: 1.5rem;
		}

		.card {
			padding: 1rem;
		}

		.card h2 {
			font-size: 1.125rem;
		}

		.form-group input {
			font-size: 16px; /* Prevent iOS zoom */
		}

		.danger-content {
			flex-direction: column;
			align-items: stretch;
			gap: 1rem;
		}

		.btn-danger {
			width: 100%;
		}
	}

	@media (max-width: 480px) {
		.settings-page {
			padding: 0.5rem;
		}

		h1 {
			font-size: 1.25rem;
			margin-bottom: 1rem;
		}

		.card {
			padding: 0.75rem;
			margin-bottom: 0.75rem;
		}

		.card h2 {
			font-size: 1rem;
			margin-bottom: 0.75rem;
		}

		.form-group {
			margin-bottom: 1rem;
		}

		.form-group input {
			padding: 0.625rem;
		}

		.verification-row {
			padding: 0.75rem;
		}

		.verification-info {
			gap: 0.5rem;
		}

		.badge {
			font-size: 0.6875rem;
		}
	}

	/* Notification Preferences */
	.preference-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-sm);
		margin-bottom: 0.75rem;
	}

	.preference-row:last-child {
		margin-bottom: 0;
	}

	.preference-info {
		flex: 1;
	}

	.preference-info strong {
		display: block;
		color: var(--c-text-primary);
		font-size: 0.9375rem;
		margin-bottom: 0.25rem;
	}

	.preference-info p {
		color: var(--c-text-secondary);
		font-size: 0.8125rem;
		margin: 0;
	}

	.toggle-switch {
		position: relative;
		display: inline-block;
		width: 48px;
		height: 28px;
		flex-shrink: 0;
		margin-left: 1rem;
	}

	.toggle-switch input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	.toggle-slider {
		position: absolute;
		cursor: pointer;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: var(--c-border);
		transition: 0.3s;
		border-radius: 28px;
	}

	.toggle-slider:before {
		position: absolute;
		content: "";
		height: 22px;
		width: 22px;
		left: 3px;
		bottom: 3px;
		background-color: white;
		transition: 0.3s;
		border-radius: 50%;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.toggle-switch input:checked + .toggle-slider {
		background-color: var(--c-brand);
	}

	.toggle-switch input:checked + .toggle-slider:before {
		transform: translateX(20px);
	}

	/* Dark mode is handled automatically via CSS variables */
</style>
