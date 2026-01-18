<script lang="ts">
    import { onMount } from "svelte";
    import { MapPin, ChevronDown, X, Building2 } from "lucide-svelte";
    import {
        selectedDistrict,
        type SelectedDistrict,
    } from "$lib/stores/districtStore";
    import {
        getStates,
        getDistrictsForState,
        type State,
        type District,
    } from "$lib/lgdData";
    import LoadingSpinner from "./LoadingSpinner.svelte";

    type Props = {
        onDistrictChange?: (district: SelectedDistrict | null) => void;
        variant?: "default" | "hero";
    };

    let { onDistrictChange, variant = "default" }: Props = $props();

    let states: State[] = $state([]);
    let districts: District[] = $state([]);
    let loading = $state(true);
    let showModal = $state(false);

    // Selection state
    let selectedStateCode: number | null = $state(null);
    let selectedDistrictCode: number | null = $state(null);
    let loadingDistricts = $state(false);

    // Current selection display
    let currentDistrict = $derived($selectedDistrict);

    onMount(async () => {
        states = await getStates();
        loading = false;

        // If district already selected, pre-populate
        if ($selectedDistrict) {
            selectedStateCode = $selectedDistrict.stateCode;
            districts = await getDistrictsForState($selectedDistrict.stateCode);
            selectedDistrictCode = $selectedDistrict.districtCode;
        }
    });

    async function handleStateChange(e: Event) {
        const target = e.target as HTMLSelectElement;
        const stateCode = parseInt(target.value);

        if (isNaN(stateCode)) {
            selectedStateCode = null;
            districts = [];
            selectedDistrictCode = null;
            return;
        }

        selectedStateCode = stateCode;
        selectedDistrictCode = null;
        loadingDistricts = true;

        districts = await getDistrictsForState(stateCode);
        loadingDistricts = false;
    }

    function handleDistrictChange(e: Event) {
        const target = e.target as HTMLSelectElement;
        const districtCode = parseInt(target.value);

        if (isNaN(districtCode)) {
            selectedDistrictCode = null;
            return;
        }

        selectedDistrictCode = districtCode;
    }

    function confirmSelection() {
        if (!selectedStateCode || !selectedDistrictCode) return;

        const state = states.find((s) => s.code === selectedStateCode);
        const district = districts.find((d) => d.code === selectedDistrictCode);

        if (!state || !district) return;

        const selection: SelectedDistrict = {
            stateCode: state.code,
            stateName: state.name,
            districtCode: district.code,
            districtName: district.name,
        };

        selectedDistrict.select(selection);
        onDistrictChange?.(selection);
        closeModal();
    }

    function clearSelection() {
        selectedDistrict.clear();
        selectedStateCode = null;
        selectedDistrictCode = null;
        districts = [];
        onDistrictChange?.(null);
        closeModal();
    }

    function openModal() {
        showModal = true;
        if (typeof document !== "undefined") {
            document.body.style.overflow = "hidden";
        }
    }

    function closeModal() {
        showModal = false;
        if (typeof document !== "undefined") {
            document.body.style.overflow = "";
        }
    }
</script>

<div class="district-selector">
    <button
        class="selector-toggle"
        class:active={currentDistrict !== null}
        class:hero={variant === "hero"}
        onclick={openModal}
        aria-label="Select district"
        type="button"
    >
        <MapPin size={variant === "hero" ? 20 : 18} />
        <span class="toggle-text">
            {#if currentDistrict}
                {currentDistrict.districtName}
            {:else}
                {variant === "hero"
                    ? "Select Your District"
                    : "Select District"}
            {/if}
        </span>
        <ChevronDown size={variant === "hero" ? 20 : 16} />
    </button>
</div>

{#if showModal}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="modal-overlay" onclick={closeModal} role="presentation"></div>

    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
        class="modal-content"
        onclick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
    >
        <div class="modal-header">
            <div class="header-icon">
                <Building2 size={24} />
            </div>
            <div class="header-text">
                <h3>Select Your District</h3>
                <p>
                    Choose your state and district to see local civic
                    information
                </p>
            </div>
            <button
                type="button"
                class="close-btn"
                onclick={closeModal}
                aria-label="Close"
            >
                <X size={24} />
            </button>
        </div>

        <div class="modal-body">
            {#if loading}
                <div class="loading-state">
                    <LoadingSpinner size="md" />
                    <span>Loading states...</span>
                </div>
            {:else}
                <div class="form-group">
                    <label for="state-select" class="label"
                        >State / Union Territory</label
                    >
                    <select
                        id="state-select"
                        class="select-input"
                        value={selectedStateCode ?? ""}
                        onchange={handleStateChange}
                    >
                        <option value="">Choose a state...</option>
                        {#each states as state}
                            <option value={state.code}>{state.name}</option>
                        {/each}
                    </select>
                </div>

                <div class="form-group">
                    <label for="district-select" class="label">District</label>
                    <select
                        id="district-select"
                        class="select-input"
                        value={selectedDistrictCode ?? ""}
                        onchange={handleDistrictChange}
                        disabled={!selectedStateCode || loadingDistricts}
                    >
                        {#if !selectedStateCode}
                            <option value="">Select a state first...</option>
                        {:else if loadingDistricts}
                            <option value="">Loading districts...</option>
                        {:else}
                            <option value="">Choose a district...</option>
                            {#each districts as district}
                                <option value={district.code}
                                    >{district.name}</option
                                >
                            {/each}
                        {/if}
                    </select>
                </div>

                <div class="modal-actions">
                    <button
                        type="button"
                        class="confirm-btn"
                        onclick={confirmSelection}
                        disabled={!selectedStateCode || !selectedDistrictCode}
                    >
                        <MapPin size={16} />
                        Confirm Selection
                    </button>

                    {#if currentDistrict}
                        <button
                            type="button"
                            class="clear-btn"
                            onclick={clearSelection}
                        >
                            <X size={16} />
                            Clear Selection
                        </button>
                    {/if}
                </div>

                {#if currentDistrict}
                    <div class="current-selection">
                        <span class="selection-label">Currently selected:</span>
                        <span class="selection-value">
                            {currentDistrict.districtName}, {currentDistrict.stateName}
                        </span>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
{/if}

<style>
    .district-selector {
        position: relative;
    }

    .selector-toggle {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--c-bg-subtle);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-full);
        color: var(--c-text-secondary);
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.875rem;
        font-weight: 500;
        font-family: var(--font-sans);
    }

    .selector-toggle:hover {
        background: var(--c-bg-surface);
        border-color: var(--c-brand);
        color: var(--c-text-primary);
    }

    .selector-toggle.active {
        background: var(--c-brand);
        border-color: var(--c-brand);
        color: white;
    }

    .toggle-text {
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* Modal styles */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9998;
        animation: fadeIn 0.2s ease-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    .modal-content {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 420px;
        max-height: 90vh;
        overflow-y: auto;
        background: var(--c-bg-surface);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        z-index: 9999;
        box-shadow: var(--shadow-lg);
        animation: modalSlideIn 0.25s ease-out;
    }

    @keyframes modalSlideIn {
        from {
            opacity: 0;
            transform: translate(-50%, -48%);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%);
        }
    }

    .modal-header {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .header-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        background: var(--c-brand);
        color: white;
        border-radius: var(--radius-md);
        flex-shrink: 0;
    }

    .header-text {
        flex: 1;
    }

    .header-text h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 0.25rem 0;
    }

    .header-text p {
        font-size: 0.875rem;
        color: var(--c-text-secondary);
        margin: 0;
    }

    .close-btn {
        background: transparent;
        border: none;
        color: var(--c-text-tertiary);
        cursor: pointer;
        padding: 0.25rem;
        line-height: 1;
        transition: color 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .close-btn:hover {
        color: var(--c-text-primary);
    }

    .modal-body {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .loading-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        padding: 2rem;
        color: var(--c-text-secondary);
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .label {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--c-text-primary);
    }

    .select-input {
        width: 100%;
        padding: 0.875rem 1rem;
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        font-size: 1rem;
        font-family: var(--font-sans);
        background: var(--c-bg-surface);
        color: var(--c-text-primary);
        cursor: pointer;
        transition: border-color 0.2s;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 0.75rem center;
        padding-right: 2.5rem;
    }

    .select-input:focus {
        outline: none;
        border-color: var(--c-brand);
    }

    .select-input:disabled {
        background: var(--c-bg-subtle);
        cursor: not-allowed;
        opacity: 0.7;
    }

    .modal-actions {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .confirm-btn,
    .clear-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.875rem 1.25rem;
        border: none;
        border-radius: var(--radius-sm);
        font-size: 0.875rem;
        font-weight: 600;
        font-family: var(--font-sans);
        cursor: pointer;
        transition: all 0.2s;
    }

    .confirm-btn {
        background: var(--c-brand);
        color: white;
    }

    .confirm-btn:hover:not(:disabled) {
        opacity: 0.9;
        transform: translateY(-1px);
    }

    .confirm-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
    }

    .clear-btn {
        background: transparent;
        color: var(--c-error);
        border: 1px solid var(--c-error);
    }

    .clear-btn:hover {
        background: var(--c-error);
        color: white;
    }

    .current-selection {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        padding: 0.75rem;
        background: var(--c-success-bg);
        border: 1px solid var(--c-success-border);
        border-radius: var(--radius-sm);
    }

    .selection-label {
        font-size: 0.75rem;
        color: var(--c-success-dark);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .selection-value {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--c-success-dark);
    }

    /* Mobile adjustments */
    @media (max-width: 640px) {
        .toggle-text {
            display: none;
        }

        .selector-toggle {
            padding: 0.625rem;
            min-width: 44px;
            min-height: 44px;
            justify-content: center;
        }

        .selector-toggle.active .toggle-text {
            display: block;
            max-width: 80px;
        }

        .modal-content {
            width: 100%;
            max-width: none;
            max-height: calc(100vh - var(--header-height, 56px));
            top: var(--header-height, 56px);
            left: 0;
            transform: none;
            border-radius: 0 0 var(--radius-lg) var(--radius-lg);
            animation: slideDown 0.25s ease-out;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    }

    /* Dark mode */
    :global([data-theme="dark"]) .modal-content {
        background: var(--c-bg-surface);
    }

    :global([data-theme="dark"]) .select-input {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
        border-color: var(--c-border);
    }

    :global([data-theme="dark"]) .select-input option {
        background: var(--c-bg-surface);
        color: var(--c-text-primary);
    }

    :global([data-theme="dark"]) .select-input:disabled {
        background: var(--c-bg-page);
        color: var(--c-text-tertiary);
    }

    .selector-toggle.hero {
        padding: 0.75rem 1.25rem;
        background: var(--c-brand);
        color: white;
        border-color: var(--c-brand);
        font-size: 1rem;
        border-radius: var(--radius-md);
        min-width: 200px;
        justify-content: center;
    }

    :global([data-theme="dark"]) .confirm-btn {
        background: #2563eb; /* Hardcoded blue to adhere to brand color and ensure contrast */
        color: white;
    }

    :global([data-theme="dark"]) .confirm-btn:disabled {
        background: var(--c-bg-subtle);
        color: var(--c-text-tertiary);
        opacity: 0.5;
    }

    .selector-toggle.hero:hover {
        background: var(--c-brand-dark);
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
    }

    .selector-toggle.hero .toggle-text {
        max-width: none;
    }
</style>
