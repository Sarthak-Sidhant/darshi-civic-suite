<script lang="ts">
	import { onMount } from "svelte";
	import { user, isAuthenticated } from "$lib/stores";
	import { getMe, getToken, clearToken, clearCurrentUser } from "$lib/api";
	import Toast from "$lib/components/Toast.svelte";
	import NotificationBell from "$lib/components/NotificationBell.svelte";
	import DistrictSelector from "$lib/components/DistrictSelector.svelte";
	import {
		selectedDistrict,
		type SelectedDistrict,
	} from "$lib/stores/districtStore";
	import { notifications } from "$lib/stores/notifications";
	import { language, type Language } from "$lib/stores/i18n";
	import { theme, toggleTheme } from "$lib/stores/theme";
	import {
		Home,
		User,
		Settings,
		Lock,
		Sparkles,
		Plus,
		Moon,
		Sun,
		Languages,
	} from "lucide-svelte";
	import { goto } from "$app/navigation";
	import { page } from "$app/stores";

	let { children } = $props();

	// District selection state
	let currentDistrict: SelectedDistrict | null = $state(null);

	// Sync with store
	$effect(() => {
		currentDistrict = $selectedDistrict;
	});

	onMount(async () => {
		// Skip auth check on admin pages (they handle it themselves)
		if (window.location.pathname.startsWith("/admin")) {
			return;
		}

		// Check if user is authenticated (blocking to prevent race conditions)
		const token = getToken();
		if (token) {
			try {
				const userData = await getMe();
				$user = userData;
				$isAuthenticated = true;
			} catch {
				// Token invalid, clear it
				clearToken();
				clearCurrentUser();
				$isAuthenticated = false;
			}
		}

		// Defer non-critical tasks to improve initial load
		requestIdleCallback(() => {
			// Register service worker after idle
			if ("serviceWorker" in navigator) {
				navigator.serviceWorker.register("/sw.js").catch(() => {});
			}

			// Preload fonts after idle
			if ("fonts" in document) {
				document.fonts.load("400 1rem Inter");
				document.fonts.load("700 1.5rem Outfit");
			}
		});
	});

	function logout() {
		clearToken();
		clearCurrentUser();
		$user = null;
		$isAuthenticated = false;
		notifications.clear(); // Clear notifications on logout
		goto("/");
	}

	function handleDistrictChange(district: SelectedDistrict | null) {
		currentDistrict = district;

		// Trigger event to notify pages about district change
		if (typeof window !== "undefined") {
			window.dispatchEvent(
				new CustomEvent("districtChange", {
					detail: district,
				}),
			);
		}

		// If we're not on the feed page, navigate to it
		if ($page.url.pathname !== "/") {
			goto("/");
		}
	}

	function toggleLanguage() {
		language.update((current) => (current === "en" ? "hi" : "en"));
	}
</script>

<svelte:head>
	<link rel="icon" type="image/x-icon" href="/favicon.ico" />
	<meta name="referrer" content="strict-origin-when-cross-origin" />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link
		rel="preconnect"
		href="https://fonts.gstatic.com"
		crossorigin="anonymous"
	/>
	<link rel="stylesheet" href="/fonts.css" />
	<link rel="manifest" href="/manifest.json" />
	<meta name="theme-color" content="#000000" />
	<meta name="apple-mobile-web-app-capable" content="yes" />
	<meta name="apple-mobile-web-app-status-bar-style" content="black" />
	<meta name="apple-mobile-web-app-title" content="Darshi" />
</svelte:head>

<div class="app-shell">
	<header class="glass-header">
		<div class="container">
			<div class="header-left">
				<a href="/" class="brand-link">
					<span
						class="brand-logo"
						style="font-family: var(--font-hindi);">दर्शी</span
					>
				</a>
				<div class="header-filter">
					<DistrictSelector onDistrictChange={handleDistrictChange} />
				</div>
			</div>
			<nav class="desktop-nav">
				<a href="/" class="nav-link" data-sveltekit-preload-data="hover"
					>Feed</a
				>
				<a
					href="/map"
					class="nav-link"
					data-sveltekit-preload-data="hover">Map</a
				>
				<a
					href="/submit"
					class="nav-link"
					data-sveltekit-preload-data="hover">Submit</a
				>

				<!-- Theme Toggle -->
				<button
					onclick={toggleTheme}
					class="nav-icon-link"
					aria-label={$theme === "light"
						? "Switch to dark mode"
						: "Switch to light mode"}
					title={$theme === "light" ? "Dark mode" : "Light mode"}
				>
					{#if $theme === "light"}
						<Moon size={20} strokeWidth={2} />
					{:else}
						<Sun size={20} strokeWidth={2} />
					{/if}
				</button>

				<!-- Language Toggle -->
				<button
					onclick={toggleLanguage}
					class="nav-icon-link lang-toggle"
					aria-label={$language === "en"
						? "Switch to Hindi"
						: "Switch to English"}
					title={$language === "en" ? "हिन्दी" : "English"}
					style={$language === "hi"
						? "font-family: var(--font-hindi); font-size: 1rem;"
						: ""}
				>
					{$language === "en" ? "अ" : "A"}
				</button>

				{#if $isAuthenticated}
					{#if $user?.role === "super_admin" || $user?.role === "moderator"}
						<a
							href="/admin"
							class="nav-link"
							data-sveltekit-preload-data="hover">Admin</a
						>
					{/if}
					<NotificationBell />
					<a
						href="/profile"
						class="nav-icon-link"
						aria-label="Profile"
						data-sveltekit-preload-data="hover"
					>
						<User size={20} strokeWidth={2} />
					</a>
					<button onclick={logout} class="nav-btn">Logout</button>
				{:else}
					<a
						href="/signin"
						class="nav-btn primary"
						data-sveltekit-preload-data="hover">Sign in</a
					>
				{/if}
			</nav>
			<!-- Mobile Header Controls (Theme, Language, Sign in) -->
			<div class="mobile-header-controls mobile-only">
				<!-- Theme Toggle Mobile -->
				<button
					onclick={toggleTheme}
					class="nav-icon-link"
					aria-label={$theme === "light"
						? "Switch to dark mode"
						: "Switch to light mode"}
				>
					{#if $theme === "light"}
						<Moon size={18} strokeWidth={2} />
					{:else}
						<Sun size={18} strokeWidth={2} />
					{/if}
				</button>

				<!-- Language Toggle Mobile -->
				<button
					onclick={toggleLanguage}
					class="nav-icon-link lang-toggle"
					aria-label={$language === "en"
						? "Switch to Hindi"
						: "Switch to English"}
					style={$language === "hi"
						? "font-family: var(--font-hindi); font-size: 0.9rem;"
						: ""}
				>
					{$language === "en" ? "अ" : "A"}
				</button>

				{#if !$isAuthenticated}
					<a
						href="/signin"
						class="sign-in-btn"
						data-sveltekit-preload-data="hover">Sign in</a
					>
				{/if}
			</div>
		</div>
	</header>

	<main>
		<div class="container">
			{@render children()}
		</div>
	</main>

	<!-- Mobile Bottom Navigation -->
	<nav class="mobile-nav">
		<a href="/" class="mobile-nav-item" data-sveltekit-preload-data="hover">
			<span class="mobile-nav-icon"><Home size={20} /></span>
			<span class="mobile-nav-label">Feed</span>
		</a>
		<a
			href="/map"
			class="mobile-nav-item"
			data-sveltekit-preload-data="hover"
		>
			<span class="mobile-nav-icon"
				><svg
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					><path
						d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"
					/><circle cx="12" cy="10" r="3" /></svg
				></span
			>
			<span class="mobile-nav-label">Map</span>
		</a>

		{#if $isAuthenticated}
			<a
				href="/profile"
				class="mobile-nav-item"
				data-sveltekit-preload-data="hover"
			>
				<span class="mobile-nav-icon"><User size={20} /></span>
				<span class="mobile-nav-label">Profile</span>
			</a>
		{/if}
	</nav>

	<!-- Floating Submit Button (Mobile) -->
	{#if !$page.url.pathname.startsWith("/signin") && !$page.url.pathname.startsWith("/forgot-password") && !$page.url.pathname.startsWith("/verify-email")}
		<a
			href="/submit"
			class="floating-submit-btn"
			data-sveltekit-preload-data="hover"
			aria-label="Submit report"
		>
			<Plus size={20} strokeWidth={2.5} />
			<span class="submit-text">SUBMIT</span>
		</a>
	{/if}
</div>

<!-- Toast Notification System -->
<Toast />

<style>
	/* Component-specific styles only - global styles are in /static/global.css */
</style>
