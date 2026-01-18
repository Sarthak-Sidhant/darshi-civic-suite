<script lang="ts">
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";
    import { Upload, MapPin, Clock, AlertTriangle } from "lucide-svelte";
    import { api, getCurrentUser } from "$lib/api";
    import { toast } from "$lib/stores/toast";

    let currentUser = $state<any>(null);
    let loading = $state(false);

    // Form fields
    let title = $state("");
    let description = $state("");
    let category = $state("traffic_jam");
    let severity = $state("medium");
    let image: File | null = $state(null);
    let imagePreview = $state("");
    let latitude = $state(0);
    let longitude = $state(0);
    let radiusKm = $state(5);
    let expiresInHours = $state(24);

    const ALERT_CATEGORIES = {
        traffic_jam: "🚗 Traffic Jam",
        road_closure: "🚧 Road Closure",
        accident: "💥 Accident",
        power_outage: "⚡ Power Outage",
        water_supply: "💧 Water Supply",
        safety_alert: "🚨 Safety Alert",
        weather_warning: "🌧️ Weather Warning",
        fire: "🔥 Fire",
        festival: "🎉 Festival",
        school: "🏫 School Notice",
        announcement: "📢 Announcement",
    };

    onMount(() => {
        currentUser = getCurrentUser();
        if (!currentUser) {
            toast.show("Please sign in to create alerts", "info");
            goto("/signin");
            return;
        }

        // Get user location
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    latitude = pos.coords.latitude;
                    longitude = pos.coords.longitude;
                },
                (err) => {
                    console.error("Location error:", err);
                    toast.show("Please enable location access", "warning");
                },
            );
        }
    });

    function handleImageChange(e: Event) {
        const target = e.target as HTMLInputElement;
        const file = target.files?.[0];
        if (file) {
            image = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview = e.target?.result as string;
            };
            reader.readAsDataURL(file);
        }
    }

    async function handleSubmit(e: Event) {
        e.preventDefault();

        if (!title.trim() || !description.trim()) {
            toast.show("Please fill all required fields", "error");
            return;
        }

        if (!latitude || !longitude) {
            toast.show("Please enable location access", "error");
            return;
        }

        try {
            loading = true;

            const formData = new FormData();
            formData.append("title", title);
            formData.append("description", description);
            formData.append("category", category);
            formData.append("severity", severity);
            if (image) {
                formData.append("image", image);
            }
            formData.append("latitude", latitude.toString());
            formData.append("longitude", longitude.toString());
            formData.append("radius_km", radiusKm.toString());
            formData.append("expires_in_hours", expiresInHours.toString());

            // Use native fetch with FormData - api.post converts to JSON
            const token = localStorage.getItem("auth_token");
            const res = await fetch(
                `${import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1"}/alerts/create`,
                {
                    method: "POST",
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                    body: formData,
                },
            );

            if (!res.ok) {
                const error = await res.json();
                throw new Error(
                    error.detail || error.message || "Failed to create alert",
                );
            }

            const data = await res.json();

            toast.show("Alert created successfully!", "success");
            goto(`/alerts/${data.id}`);
        } catch (e: any) {
            toast.show(e.message || "Failed to create alert", "error");
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Create Alert - Darshi</title>
</svelte:head>

<div class="min-h-screen bg-[var(--c-bg-primary)] py-8">
    <div class="max-w-2xl mx-auto px-4">
        <div class="mb-6">
            <a
                href="/alerts"
                class="text-[var(--c-text-secondary)] hover:text-[var(--c-text-primary)]"
            >
                ← Back to Alerts
            </a>
        </div>

        <div
            class="bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg p-6"
        >
            <h1 class="text-2xl font-bold text-[var(--c-text-primary)] mb-2">
                Create Alert
            </h1>
            <p class="text-[var(--c-text-secondary)] mb-6">
                Report what's happening in your area right now
            </p>

            <form onsubmit={handleSubmit} class="space-y-6">
                <!-- Image Upload -->
                <div>
                    <label
                        class="block text-sm font-medium text-[var(--c-text-primary)] mb-2"
                    >
                        Photo <span
                            class="text-[var(--c-text-tertiary)] font-normal"
                            >(Optional)</span
                        >
                    </label>
                    <div
                        class="border-2 border-dashed border-[var(--c-border)] rounded-lg p-6 text-center hover:border-[var(--c-primary)] transition"
                    >
                        {#if imagePreview}
                            <img
                                src={imagePreview}
                                alt="Preview"
                                class="max-h-64 mx-auto rounded-lg mb-4"
                            />
                        {:else}
                            <Upload
                                size={48}
                                class="mx-auto mb-4 text-[var(--c-text-tertiary)]"
                            />
                            <p class="text-[var(--c-text-secondary)] mb-2">
                                Click to upload or drag and drop
                            </p>
                            <p class="text-xs text-[var(--c-text-tertiary)]">
                                PNG, JPG up to 5MB
                            </p>
                        {/if}
                        <input
                            type="file"
                            accept="image/*"
                            onchange={handleImageChange}
                            class="hidden"
                            id="image-upload"
                        />
                        <label
                            for="image-upload"
                            class="inline-block mt-4 px-4 py-2 bg-[var(--c-bg-subtle)] hover:bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg cursor-pointer transition"
                        >
                            {imagePreview ? "Change Photo" : "Add Photo"}
                        </label>
                    </div>
                </div>

                <!-- Title -->
                <div>
                    <label
                        class="block text-sm font-medium text-[var(--c-text-primary)] mb-2"
                    >
                        Title <span class="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        bind:value={title}
                        placeholder="e.g., Heavy traffic on MG Road"
                        class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] placeholder-[var(--c-text-tertiary)] focus:outline-none focus:border-[var(--c-primary)]"
                        required
                    />
                </div>

                <!-- Description -->
                <div>
                    <label
                        class="block text-sm font-medium text-[var(--c-text-primary)] mb-2"
                    >
                        Description <span class="text-red-500">*</span>
                    </label>
                    <textarea
                        bind:value={description}
                        placeholder="Describe what's happening..."
                        rows="4"
                        class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] placeholder-[var(--c-text-tertiary)] resize-none focus:outline-none focus:border-[var(--c-primary)]"
                        required
                    ></textarea>
                </div>

                <!-- Category & Severity -->
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label
                            class="block text-sm font-medium text-[var(--c-text-primary)] mb-2"
                        >
                            Category
                        </label>
                        <select
                            bind:value={category}
                            class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] focus:outline-none focus:border-[var(--c-primary)]"
                        >
                            {#each Object.entries(ALERT_CATEGORIES) as [key, label]}
                                <option value={key}>{label}</option>
                            {/each}
                        </select>
                    </div>

                    <div>
                        <label
                            class="block text-sm font-medium text-[var(--c-text-primary)] mb-2"
                        >
                            Severity
                        </label>
                        <select
                            bind:value={severity}
                            class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] focus:outline-none focus:border-[var(--c-primary)]"
                        >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>

                <!-- Radius & Expiry -->
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label
                            class="block text-sm font-medium text-[var(--c-text-primary)] mb-2 flex items-center gap-2"
                        >
                            <MapPin size={16} />
                            Radius (km)
                        </label>
                        <input
                            type="number"
                            bind:value={radiusKm}
                            min="1"
                            max="30"
                            class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] focus:outline-none focus:border-[var(--c-primary)]"
                        />
                        <p class="text-xs text-[var(--c-text-tertiary)] mt-1">
                            Max 30km
                        </p>
                    </div>

                    <div>
                        <label
                            class="block text-sm font-medium text-[var(--c-text-primary)] mb-2 flex items-center gap-2"
                        >
                            <Clock size={16} />
                            Expires in (hours)
                        </label>
                        <input
                            type="number"
                            bind:value={expiresInHours}
                            min="1"
                            max="168"
                            class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] focus:outline-none focus:border-[var(--c-primary)]"
                        />
                        <p class="text-xs text-[var(--c-text-tertiary)] mt-1">
                            Max 7 days
                        </p>
                    </div>
                </div>

                <!-- Location Info -->
                {#if latitude && longitude}
                    <div
                        class="p-4 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg"
                    >
                        <p class="text-sm text-[var(--c-text-secondary)]">
                            <MapPin size={16} class="inline" />
                            Location: {latitude.toFixed(4)}, {longitude.toFixed(
                                4,
                            )}
                        </p>
                    </div>
                {/if}

                <!-- Submit -->
                <button
                    type="submit"
                    disabled={loading}
                    class="w-full px-6 py-3 bg-[var(--c-primary)] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                >
                    {#if loading}
                        <div
                            class="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                        ></div>
                        Creating...
                    {:else}
                        <AlertTriangle size={20} />
                        Create Alert
                    {/if}
                </button>
            </form>
        </div>
    </div>
</div>
