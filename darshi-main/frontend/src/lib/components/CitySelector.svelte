<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import { fade, scale } from "svelte/transition";
    import { getCities, type City, getNearestCity } from "$lib/api";
    import { currentCity, userLocation } from "$lib/stores";
    import { MapPin, Search, Check, Navigation, X } from "lucide-svelte";
    import LoadingSpinner from "./LoadingSpinner.svelte";
    import { toast } from "$lib/stores/toast";

    export let isOpen = false;
    export let dismissible = true;

    const dispatch = createEventDispatcher();

    let cities: City[] = [];
    let loading = true;
    let searchQuery = "";
    let locating = false;

    onMount(async () => {
        try {
            cities = await getCities();
        } catch (e) {
            console.error("Failed to load cities", e);
        } finally {
            loading = false;
        }
    });

    function selectCity(city: City) {
        currentCity.set(city);
        dispatch("select", city);
        isOpen = false;
    }

    function close() {
        if (dismissible) {
            isOpen = false;
            dispatch("close");
        }
    }

    async function detectLocation() {
        if (!navigator.geolocation) {
            toast.error("Geolocation is not supported by your browser");
            return;
        }

        locating = true;
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const { latitude, longitude } = position.coords;

                // Update generic location store
                userLocation.set({ lat: latitude, lng: longitude });

                try {
                    const result = await getNearestCity(latitude, longitude);
                    if (result.found && result.city) {
                        selectCity(result.city);
                        toast.success(`Located in ${result.city.name}`);
                    } else {
                        toast.warning(
                            "darshi is not available in your area yet",
                        );
                    }
                } catch (e) {
                    toast.error("Failed to find nearest city");
                } finally {
                    locating = false;
                }
            },
            (error) => {
                console.error(error);
                toast.error("Please enable location access");
                locating = false;
            },
        );
    }

    $: filteredCities = cities.filter(
        (c) =>
            c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            c.state.toLowerCase().includes(searchQuery.toLowerCase()),
    );
</script>

{#if isOpen}
    <div
        class="modal-overlay"
        transition:fade={{ duration: 200 }}
        onclick={close}
    >
        <div
            class="modal-content"
            transition:scale={{ duration: 200, start: 0.95 }}
            onclick={(e) => e.stopPropagation()}
        >
            <header class="modal-header">
                <h2>
                    <MapPin class="w-5 h-5 text-primary" />
                    Select City
                </h2>
                {#if dismissible}
                    <button class="btn-close" onclick={close}>
                        <X size={20} />
                    </button>
                {/if}
            </header>

            <div class="modal-body">
                <div class="search-box">
                    <Search size={18} class="search-icon" />
                    <input
                        type="text"
                        bind:value={searchQuery}
                        placeholder="Search for your city..."
                        autofocus
                    />
                </div>

                <button
                    class="detect-btn"
                    onclick={detectLocation}
                    disabled={locating}
                >
                    {#if locating}
                        <LoadingSpinner size="sm" />
                    {:else}
                        <Navigation size={18} />
                    {/if}
                    <span>Use my current location</span>
                </button>

                <div class="divider">or choose manually</div>

                <div class="cities-list">
                    {#if loading}
                        <div class="loading-state">
                            <LoadingSpinner size="md" />
                        </div>
                    {:else if filteredCities.length === 0}
                        <div class="empty-state">
                            <p>No cities found</p>
                        </div>
                    {:else}
                        {#each filteredCities as city}
                            <button
                                class="city-item"
                                class:active={$currentCity?.id === city.id}
                                onclick={() => selectCity(city)}
                            >
                                <div class="city-info">
                                    <span class="city-name">{city.name}</span>
                                    <span class="city-state">{city.state}</span>
                                </div>
                                {#if $currentCity?.id === city.id}
                                    <Check size={18} class="text-primary" />
                                {/if}
                            </button>
                        {/each}
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.75);
        backdrop-filter: blur(4px);
        display: flex;
        align-items: flex-start;
        justify-content: center;
        z-index: 2000;
        padding: 4rem 1rem 1rem 1rem;
    }

    .modal-content {
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-lg);
        width: 100%;
        max-width: 480px;
        display: flex;
        flex-direction: column;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        max-height: 80vh;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.25rem;
        border-bottom: 1px solid var(--c-border);
    }

    .modal-header h2 {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0;
    }

    .btn-close {
        color: var(--c-text-tertiary);
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 0.25rem;
        border-radius: var(--radius-sm);
        transition: all 0.2s;
    }

    .btn-close:hover {
        color: var(--c-text-primary);
        background: var(--c-bg-subtle);
    }

    .modal-body {
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        overflow-y: auto;
    }

    .search-box {
        position: relative;
    }

    .search-icon {
        position: absolute;
        left: 1rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--c-text-tertiary);
        pointer-events: none;
    }

    .search-box input {
        width: 100%;
        padding: 0.75rem 1rem 0.75rem 2.75rem;
        background: var(--c-bg-subtle);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        color: var(--c-text-primary);
        font-size: 1rem;
    }

    .search-box input:focus {
        outline: none;
        border-color: var(--c-primary);
        box-shadow: 0 0 0 2px var(--c-primary-light);
    }

    .detect-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.75rem;
        background: rgba(var(--rgb-primary), 0.1);
        color: var(--c-primary);
        border: 1px solid rgba(var(--rgb-primary), 0.2);
        border-radius: var(--radius-md);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }

    .detect-btn:hover:not(:disabled) {
        background: rgba(var(--rgb-primary), 0.2);
    }

    .detect-btn:disabled {
        opacity: 0.6;
        cursor: wait;
    }

    .divider {
        display: flex;
        align-items: center;
        color: var(--c-text-tertiary);
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    .divider::before,
    .divider::after {
        content: "";
        flex: 1;
        height: 1px;
        background: var(--c-border);
    }

    .divider::before {
        margin-right: 1rem;
    }
    .divider::after {
        margin-left: 1rem;
    }

    .cities-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .city-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.875rem 1rem;
        background: var(--c-bg-subtle);
        border: 1px solid transparent;
        border-radius: var(--radius-md);
        cursor: pointer;
        text-align: left;
        transition: all 0.2s;
    }

    .city-item:hover {
        background: var(--c-bg-surface);
        border-color: var(--c-border);
        transform: translateY(-1px);
    }

    .city-item.active {
        background: rgba(var(--rgb-primary), 0.05);
        border-color: var(--c-primary);
    }

    .city-info {
        display: flex;
        flex-direction: column;
    }

    .city-name {
        font-weight: 600;
        color: var(--c-text-primary);
    }

    .city-state {
        font-size: 0.8125rem;
        color: var(--c-text-tertiary);
    }

    .loading-state,
    .empty-state {
        padding: 2rem;
        text-align: center;
        color: var(--c-text-tertiary);
    }
</style>
