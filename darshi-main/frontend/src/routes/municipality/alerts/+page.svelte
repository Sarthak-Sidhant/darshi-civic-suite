<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { goto } from "$app/navigation";
    import {
        Zap,
        AlertTriangle,
        Radio,
        Send,
        Clock,
        MapPin,
        Users,
        X,
        Plus,
        RefreshCw,
        Trash2,
    } from "lucide-svelte";
    import {
        getMunicipalityAlerts,
        createBroadcast,
        endBroadcast,
        getToken,
        getCurrentUser,
        type BroadcastAlert,
        type AlertCreate,
    } from "$lib/api";
    import { toast } from "$lib/stores/toast";

    // State
    let alerts = $state<BroadcastAlert[]>([]);
    let loading = $state(true);
    let error = $state("");
    let refreshInterval: ReturnType<typeof setInterval> | undefined;
    let statusFilter = $state("ACTIVE");

    // Modal state
    let showBroadcastModal = $state(false);
    let sending = $state(false);
    let newAlert = $state<AlertCreate>({
        title: "",
        description: "",
        category: "traffic",
        severity: "medium",
        radius_meters: 5000,
        expires_in_hours: 24,
    });

    const categories = [
        { value: "traffic", label: "Traffic", icon: "🚗" },
        { value: "power", label: "Power Outage", icon: "⚡" },
        { value: "water", label: "Water Supply", icon: "💧" },
        { value: "safety", label: "Safety Alert", icon: "🚨" },
        { value: "community", label: "Community", icon: "👥" },
    ];

    const severities = [
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
    ];

    let isAuthorized = $state(false);

    onMount(async () => {
        const token = getToken();
        const currentUser = getCurrentUser();

        if (!token || !currentUser) {
            goto("/signin");
            return;
        }

        isAuthorized = [
            "super_admin",
            "admin",
            "moderator",
            "municipality_admin",
            "municipality_staff",
        ].includes(currentUser.role || "");

        if (!isAuthorized) {
            loading = false;
            return;
        }

        await loadAlerts();
        refreshInterval = setInterval(loadAlerts, 30000);
    });

    onDestroy(() => {
        if (refreshInterval) clearInterval(refreshInterval);
    });

    async function loadAlerts() {
        try {
            const data = await getMunicipalityAlerts(statusFilter);
            alerts = data.alerts;
            error = "";
        } catch (e: any) {
            error = e.message || "Failed to load alerts";
        } finally {
            loading = false;
        }
    }

    function openBroadcastModal() {
        newAlert = {
            title: "",
            description: "",
            category: "traffic",
            severity: "medium",
            radius_meters: 5000,
            expires_in_hours: 24,
        };
        showBroadcastModal = true;
    }

    async function handleBroadcast() {
        if (!newAlert.title.trim()) {
            toast.error("Please enter an alert title");
            return;
        }

        sending = true;
        try {
            await createBroadcast(newAlert);
            toast.success("Alert broadcast sent!");
            showBroadcastModal = false;
            await loadAlerts();
        } catch (e: any) {
            toast.error(e.message || "Failed to send broadcast");
        } finally {
            sending = false;
        }
    }

    async function handleEndAlert(alertId: string) {
        if (!confirm("Are you sure you want to end this alert?")) return;

        try {
            await endBroadcast(alertId);
            toast.success("Alert ended");
            await loadAlerts();
        } catch (e: any) {
            toast.error(e.message || "Failed to end alert");
        }
    }

    $effect(() => {
        if (statusFilter) {
            loadAlerts();
        }
    });

    function getSeverityClass(severity: string): string {
        switch (severity) {
            case "critical":
                return "severity-critical";
            case "high":
                return "severity-high";
            case "medium":
                return "severity-medium";
            default:
                return "severity-low";
        }
    }

    function getTimeAgo(dateStr: string): string {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);

        if (diffMins < 1) return "just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${Math.floor(diffHours / 24)}d ago`;
    }

    function getCategoryIcon(category: string): string {
        const cat = categories.find((c) => c.value === category);
        return cat?.icon || "📢";
    }
</script>

{#if !isAuthorized && !loading}
    <div class="unauthorized">
        <div class="unauthorized-content">
            <AlertTriangle size={48} />
            <h2>Access Denied</h2>
            <p>You don't have permission to access the Alert Hub.</p>
            <button class="btn-primary" onclick={() => goto("/")}
                >Go Home</button
            >
        </div>
    </div>
{:else}
    <div class="alerts-page">
        <!-- Header -->
        <header class="page-header">
            <div class="header-left">
                <div class="header-indicator"></div>
                <div>
                    <h1>Alert Hub</h1>
                    <p class="header-subtitle">Broadcast alerts to citizens</p>
                </div>
            </div>
            <div class="header-actions">
                <button
                    class="btn-icon"
                    onclick={loadAlerts}
                    disabled={loading}
                >
                    <RefreshCw size={18} class={loading ? "spin" : ""} />
                </button>
                <button class="btn-broadcast" onclick={openBroadcastModal}>
                    <Plus size={18} />
                    New Broadcast
                </button>
            </div>
        </header>

        <!-- Filter Tabs -->
        <div class="filter-tabs">
            <button
                class="tab"
                class:active={statusFilter === "ACTIVE"}
                onclick={() => (statusFilter = "ACTIVE")}
            >
                <Radio size={16} />
                Active
            </button>
            <button
                class="tab"
                class:active={statusFilter === "EXPIRED"}
                onclick={() => (statusFilter = "EXPIRED")}
            >
                <Clock size={16} />
                Expired
            </button>
            <button
                class="tab"
                class:active={statusFilter === "all"}
                onclick={() => (statusFilter = "all")}
            >
                All
            </button>
        </div>

        <!-- Content -->
        <main class="alerts-content">
            {#if loading && alerts.length === 0}
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Loading alerts...</p>
                </div>
            {:else if error}
                <div class="error-state">
                    <AlertTriangle size={24} />
                    <p>{error}</p>
                    <button class="btn-secondary" onclick={loadAlerts}
                        >Retry</button
                    >
                </div>
            {:else if alerts.length === 0}
                <div class="empty-state">
                    <Radio size={48} />
                    <h3>No alerts</h3>
                    <p>Create a new broadcast to alert citizens</p>
                    <button class="btn-primary" onclick={openBroadcastModal}>
                        <Plus size={18} />
                        Create Broadcast
                    </button>
                </div>
            {:else}
                <div class="alerts-grid">
                    {#each alerts as alert}
                        <div
                            class="alert-card {getSeverityClass(
                                alert.severity,
                            )}"
                        >
                            <div class="alert-header">
                                <span class="alert-category">
                                    {getCategoryIcon(alert.category)}
                                    {alert.category}
                                </span>
                                <span class="alert-time"
                                    >{getTimeAgo(alert.created_at)}</span
                                >
                            </div>

                            <h3 class="alert-title">{alert.title}</h3>

                            {#if alert.description}
                                <p class="alert-description">
                                    {alert.description}
                                </p>
                            {/if}

                            <div class="alert-meta">
                                <span
                                    class="severity-badge {getSeverityClass(
                                        alert.severity,
                                    )}"
                                >
                                    {alert.severity}
                                </span>
                                <span
                                    class="status-badge"
                                    class:active={alert.status === "ACTIVE"}
                                >
                                    {alert.status}
                                </span>
                            </div>

                            {#if alert.status === "ACTIVE"}
                                <button
                                    class="btn-end-alert"
                                    onclick={() => handleEndAlert(alert.id)}
                                >
                                    <Trash2 size={16} />
                                    End Alert
                                </button>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}
        </main>
    </div>

    <!-- Broadcast Modal -->
    {#if showBroadcastModal}
        <div class="modal-overlay" onclick={() => (showBroadcastModal = false)}>
            <div class="modal-content" onclick={(e) => e.stopPropagation()}>
                <header class="modal-header">
                    <h2><Zap size={20} /> Create Broadcast</h2>
                    <button
                        class="btn-close"
                        onclick={() => (showBroadcastModal = false)}
                    >
                        <X size={20} />
                    </button>
                </header>

                <div class="modal-body">
                    <div class="form-group">
                        <label for="alert-title">Title *</label>
                        <input
                            id="alert-title"
                            type="text"
                            placeholder="Brief alert title..."
                            bind:value={newAlert.title}
                        />
                    </div>

                    <div class="form-group">
                        <label for="alert-description">Description</label>
                        <textarea
                            id="alert-description"
                            placeholder="Detailed information..."
                            rows="3"
                            bind:value={newAlert.description}
                        ></textarea>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="alert-category">Category</label>
                            <select
                                id="alert-category"
                                bind:value={newAlert.category}
                            >
                                {#each categories as cat}
                                    <option value={cat.value}
                                        >{cat.icon} {cat.label}</option
                                    >
                                {/each}
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="alert-severity">Severity</label>
                            <select
                                id="alert-severity"
                                bind:value={newAlert.severity}
                            >
                                {#each severities as sev}
                                    <option value={sev.value}
                                        >{sev.label}</option
                                    >
                                {/each}
                            </select>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="alert-radius">Radius (km)</label>
                            <input
                                id="alert-radius"
                                type="number"
                                min="1"
                                max="50"
                                bind:value={newAlert.radius_meters}
                            />
                        </div>

                        <div class="form-group">
                            <label for="alert-expiry">Expires in (hours)</label>
                            <input
                                id="alert-expiry"
                                type="number"
                                min="1"
                                max="168"
                                bind:value={newAlert.expires_in_hours}
                            />
                        </div>
                    </div>
                </div>

                <footer class="modal-footer">
                    <button
                        class="btn-secondary"
                        onclick={() => (showBroadcastModal = false)}
                    >
                        Cancel
                    </button>
                    <button
                        class="btn-broadcast"
                        onclick={handleBroadcast}
                        disabled={sending || !newAlert.title.trim()}
                    >
                        <Send size={16} />
                        {sending ? "Sending..." : "Send Broadcast"}
                    </button>
                </footer>
            </div>
        </div>
    {/if}
{/if}

<style>
    .alerts-page {
        padding: 1.5rem;
    }

    /* Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .header-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--c-error);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }

    .page-header h1 {
        font-family: var(--font-display);
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--c-text-primary);
        margin: 0;
    }

    .header-subtitle {
        font-size: 0.875rem;
        color: var(--c-text-secondary);
        margin: 0;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .btn-icon {
        padding: 0.625rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-secondary);
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-icon:hover:not(:disabled) {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
    }

    .btn-icon :global(.spin) {
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

    .btn-broadcast {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.25rem;
        background: var(--c-error);
        color: white;
        border: none;
        border-radius: var(--radius-sm);
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-broadcast:hover:not(:disabled) {
        opacity: 0.9;
    }

    .btn-broadcast:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    /* Filter Tabs */
    .filter-tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid var(--c-border);
        padding-bottom: 1rem;
    }

    .tab {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: transparent;
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-secondary);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }

    .tab:hover {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
    }

    .tab.active {
        background: var(--c-brand);
        border-color: var(--c-brand);
        color: var(--c-brand-contrast);
    }

    /* States */
    .loading-state,
    .error-state,
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        gap: 1rem;
        color: var(--c-text-secondary);
        text-align: center;
    }

    .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid var(--c-border);
        border-top-color: var(--c-brand);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    .error-state {
        color: var(--c-error);
    }

    .empty-state h3 {
        margin: 0;
        color: var(--c-text-primary);
    }

    .empty-state p {
        margin: 0;
    }

    /* Alerts Grid */
    .alerts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 1rem;
    }

    .alert-card {
        padding: 1.25rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        border-left: 4px solid var(--c-border);
    }

    .alert-card.severity-critical {
        border-left-color: var(--c-error);
    }
    .alert-card.severity-high {
        border-left-color: var(--c-orange);
    }
    .alert-card.severity-medium {
        border-left-color: var(--c-warning);
    }
    .alert-card.severity-low {
        border-left-color: var(--c-success);
    }

    .alert-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }

    .alert-category {
        font-size: 0.8125rem;
        color: var(--c-text-secondary);
        text-transform: capitalize;
    }

    .alert-time {
        font-size: 0.75rem;
        color: var(--c-text-tertiary);
    }

    .alert-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 0.5rem 0;
    }

    .alert-description {
        font-size: 0.875rem;
        color: var(--c-text-secondary);
        margin: 0 0 1rem 0;
        line-height: 1.5;
    }

    .alert-meta {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .severity-badge,
    .status-badge {
        padding: 0.25rem 0.625rem;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .severity-badge.severity-critical {
        background: var(--c-error-light);
        color: var(--c-error-dark);
    }
    .severity-badge.severity-high {
        background: var(--c-orange-bg);
        color: var(--c-orange-dark);
    }
    .severity-badge.severity-medium {
        background: var(--c-warning-light);
        color: var(--c-warning-dark);
    }
    .severity-badge.severity-low {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }

    .status-badge {
        background: var(--c-bg-subtle);
        color: var(--c-text-secondary);
    }

    .status-badge.active {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }

    .btn-end-alert {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: transparent;
        border: 1px solid var(--c-error);
        border-radius: var(--radius-sm);
        color: var(--c-error);
        font-size: 0.8125rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-end-alert:hover {
        background: var(--c-error-light);
    }

    /* Unauthorized */
    .unauthorized {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        padding: 2rem;
    }

    .unauthorized-content {
        text-align: center;
        color: var(--c-text-secondary);
    }

    .unauthorized-content h2 {
        margin: 1rem 0 0.5rem;
        color: var(--c-text-primary);
    }

    /* Modal */
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 200;
        padding: 1rem;
    }

    .modal-content {
        background: var(--c-bg-surface);
        border-radius: var(--radius-lg);
        max-width: 500px;
        width: 100%;
        max-height: 90vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
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
        gap: 0.5rem;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0;
    }

    .btn-close {
        padding: 0.5rem;
        background: transparent;
        border: none;
        color: var(--c-text-secondary);
        cursor: pointer;
        border-radius: var(--radius-sm);
    }

    .btn-close:hover {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
    }

    .modal-body {
        padding: 1.25rem;
        overflow-y: auto;
        flex: 1;
    }

    .form-group {
        margin-bottom: 1rem;
    }

    .form-group label {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--c-text-secondary);
        margin-bottom: 0.5rem;
    }

    .form-group input,
    .form-group textarea,
    .form-group select {
        width: 100%;
        padding: 0.75rem;
        background: var(--c-bg-subtle);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-primary);
        font-size: 0.9375rem;
    }

    .form-group input:focus,
    .form-group textarea:focus,
    .form-group select:focus {
        outline: none;
        border-color: var(--c-brand);
    }

    .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--c-border);
    }

    .btn-primary,
    .btn-secondary {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.25rem;
        border-radius: var(--radius-sm);
        font-weight: 600;
        font-size: 0.9375rem;
        cursor: pointer;
        transition: all 0.2s;
        border: none;
    }

    .btn-primary {
        background: var(--c-brand);
        color: var(--c-brand-contrast);
    }

    .btn-secondary {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
        border: 1px solid var(--c-border);
    }

    /* Responsive */
    @media (max-width: 768px) {
        .alerts-page {
            padding: 1rem;
        }

        .alerts-grid {
            grid-template-columns: 1fr;
        }

        .form-row {
            grid-template-columns: 1fr;
        }

        .filter-tabs {
            flex-wrap: wrap;
        }
    }
</style>
