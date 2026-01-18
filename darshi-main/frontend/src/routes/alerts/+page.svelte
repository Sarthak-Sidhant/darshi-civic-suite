<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import {
        AlertTriangle,
        Clock,
        MapPin,
        Plus,
        TrendingUp,
        CheckCircle,
        Loader,
    } from "lucide-svelte";
    import { api, getCurrentUser } from "$lib/api";
    import { toast } from "$lib/stores/toast";

    let alerts = $state<any[]>([]);
    let loading = $state(true);
    let userDistrict = $state("");
    let userState = $state("");
    let selectedCategory = $state<string | null>(null);
    let currentUser = $state<any>(null);
    let detectingLocation = $state(true);

    const ALERT_CATEGORIES = {
        traffic_jam: "🚗 Traffic Jam",
        road_closure: "🚧 Road Closure",
        accident: "💥 Accident",
        power_outage: "⚡ Power Outage",
        water_supply: "💧 Water Supply",
        safety_alert: "🚨 Safety Alert",
        weather_warning: "🌧️ Weather",
        fire: "🔥 Fire",
        festival: "🎉 Festival",
        school: "🏫 School",
        announcement: "📢 Announcement",
    };

    onMount(async () => {
        currentUser = getCurrentUser();
        await detectCity();
    });

    async function detectCity() {
        try {
            detectingLocation = true;

            const position = await new Promise<GeolocationPosition>(
                (resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject);
                },
            );

            const { latitude, longitude } = position.coords;

            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&addressdetails=1`,
                { headers: { "User-Agent": "Darshi/1.0" } },
            );

            const data = await response.json();
            const address = data.address;

            // Extract district from Nominatim
            userDistrict =
                address.state_district ||
                address.county ||
                address.district ||
                address.city ||
                address.town ||
                "";
            userState = address.state || "";

            if (userDistrict && userState) {
                await fetchAlerts();
            } else {
                toast.show("Could not detect your district", "warning");
                loading = false;
            }
        } catch (e) {
            console.error("Location detection failed:", e);
            userDistrict = "Ranchi";
            userState = "Jharkhand";
            await fetchAlerts();
        } finally {
            detectingLocation = false;
        }
    }

    async function fetchAlerts() {
        loading = true;
        try {
            let url = `/alerts/in-district?district=${encodeURIComponent(userDistrict)}&state=${encodeURIComponent(userState)}`;

            if (selectedCategory) {
                url += `&categories=${selectedCategory}`;
            }

            const res = await api.get(url);
            const data = await res.json();
            alerts = data;
        } catch (e: any) {
            toast.show(e.message || "Failed to load alerts", "error");
        } finally {
            loading = false;
        }
    }

    function getTimeRemaining(expiresAt: string): string {
        const now = new Date();
        const expires = new Date(expiresAt);
        const diff = expires.getTime() - now.getTime();

        if (diff < 0) return "Expired";

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 24) {
            const days = Math.floor(hours / 24);
            return `${days}d remaining`;
        }
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    function getSeverityColor(severity: string): string {
        switch (severity) {
            case "critical":
                return "bg-red-500/10 border-red-500/30 text-red-400";
            case "high":
                return "bg-orange-500/10 border-orange-500/30 text-orange-400";
            case "medium":
                return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
            default:
                return "bg-green-500/10 border-green-500/30 text-green-400";
        }
    }

    $effect(() => {
        if (selectedCategory !== null && userDistrict && userState) {
            fetchAlerts();
        }
    });
</script>

<svelte:head>
    <title>Alerts - Darshi</title>
</svelte:head>

<div class="min-h-screen bg-[var(--c-bg-primary)]">
    <div
        class="sticky top-0 z-10 bg-[var(--c-bg-surface)] border-b border-[var(--c-border)]"
    >
        <div class="max-w-4xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-2xl font-bold text-[var(--c-text-primary)]">
                        🚨 Active Alerts
                    </h1>
                    {#if detectingLocation}
                        <p
                            class="text-sm text-[var(--c-text-secondary)] flex items-center gap-2"
                        >
                            <Loader size={14} class="animate-spin" />
                            Detecting your district...
                        </p>
                    {:else if userDistrict && userState}
                        <p class="text-sm text-[var(--c-text-secondary)]">
                            <MapPin size={16} class="inline" />
                            Alerts in {userDistrict} District, {userState}
                        </p>
                    {/if}
                </div>

                {#if currentUser}
                    <a
                        href="/alerts/create"
                        class="flex items-center gap-2 px-4 py-2 bg-[var(--c-primary)] text-white rounded-lg hover:opacity-90 transition"
                    >
                        <Plus size={20} />
                        <span class="hidden sm:inline">Create Alert</span>
                    </a>
                {/if}
            </div>
        </div>
    </div>

    <div class="max-w-4xl mx-auto px-4 py-4">
        <div class="flex gap-2 overflow-x-auto pb-2">
            <button
                onclick={() => {
                    selectedCategory = null;
                }}
                class="px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition {selectedCategory ===
                null
                    ? 'bg-[var(--c-primary)] text-white'
                    : 'bg-[var(--c-bg-surface)] text-[var(--c-text-secondary)] hover:bg-[var(--c-bg-subtle)]'}"
            >
                All
            </button>
            {#each Object.entries(ALERT_CATEGORIES) as [key, label]}
                <button
                    onclick={() => {
                        selectedCategory = key;
                    }}
                    class="px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition {selectedCategory ===
                    key
                        ? 'bg-[var(--c-primary)] text-white'
                        : 'bg-[var(--c-bg-surface)] text-[var(--c-text-secondary)] hover:bg-[var(--c-bg-subtle)]'}"
                >
                    {label}
                </button>
            {/each}
        </div>
    </div>

    <div class="max-w-4xl mx-auto px-4 pb-20">
        {#if loading || detectingLocation}
            <div class="flex justify-center py-20">
                <div
                    class="animate-spin w-8 h-8 border-2 border-[var(--c-primary)] border-t-transparent rounded-full"
                ></div>
            </div>
        {:else if alerts.length === 0}
            <div class="text-center py-20">
                <CheckCircle
                    size={48}
                    class="mx-auto mb-4 text-[var(--c-text-tertiary)]"
                />
                <h3 class="text-xl font-bold text-[var(--c-text-primary)] mb-2">
                    No Active Alerts
                </h3>
                <p class="text-[var(--c-text-secondary)]">
                    There are no alerts in {userDistrict} District right now.
                </p>
            </div>
        {:else}
            <div class="space-y-4">
                {#each alerts as alert}
                    <a
                        href="/alerts/{alert.id}"
                        class="block p-4 bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg hover:border-[var(--c-primary)] transition"
                    >
                        <div class="flex items-start gap-4">
                            {#if alert.image_url}
                                <img
                                    src={alert.image_url}
                                    alt={alert.title}
                                    class="w-24 h-24 object-cover rounded-lg"
                                />
                            {/if}

                            <div class="flex-1 min-w-0">
                                <div
                                    class="flex items-start justify-between gap-2 mb-2"
                                >
                                    <div class="flex-1">
                                        <div
                                            class="flex items-center gap-2 mb-1"
                                        >
                                            {#if alert.is_official}
                                                <span
                                                    class="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs font-bold rounded"
                                                    >✓ OFFICIAL</span
                                                >
                                            {:else if alert.verified_by}
                                                <span
                                                    class="px-2 py-0.5 bg-green-500/10 text-green-400 text-xs font-bold rounded"
                                                    >✓ VERIFIED</span
                                                >
                                            {/if}
                                            <span
                                                class="px-2 py-0.5 {getSeverityColor(
                                                    alert.severity,
                                                )} text-xs font-bold rounded uppercase"
                                                >{alert.severity}</span
                                            >
                                        </div>
                                        <h3
                                            class="text-lg font-bold text-[var(--c-text-primary)] mb-1"
                                        >
                                            {alert.title}
                                        </h3>
                                        <p
                                            class="text-sm text-[var(--c-text-secondary)] line-clamp-2"
                                        >
                                            {alert.description}
                                        </p>
                                    </div>
                                </div>

                                <div
                                    class="flex items-center gap-4 text-xs text-[var(--c-text-tertiary)]"
                                >
                                    <span class="flex items-center gap-1">
                                        <Clock size={14} />
                                        {getTimeRemaining(alert.expires_at)}
                                    </span>
                                    <span class="flex items-center gap-1">
                                        <MapPin size={14} />
                                        {alert.city}
                                    </span>
                                    {#if !alert.is_official}
                                        <span class="flex items-center gap-1">
                                            <TrendingUp size={14} />
                                            {alert.upvote_count || 0} upvotes
                                        </span>
                                    {/if}
                                </div>
                            </div>
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    </div>
</div>
