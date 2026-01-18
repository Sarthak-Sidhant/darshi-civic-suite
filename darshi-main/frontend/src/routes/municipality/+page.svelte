<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import {
        CheckCircle,
        Clock,
        AlertTriangle,
        MapPin,
        Activity,
        BarChart3,
        RefreshCw,
        Eye,
        ChevronRight,
        Filter,
        Search,
    } from "lucide-svelte";
    import { getToken, getCurrentUser, getReports, api } from "$lib/api";
    import { toast } from "$lib/stores/toast";
    import type { Report } from "$lib/api";

    // State
    let loading = $state(true);
    let error = $state("");
    let reports = $state<Report[]>([]);
    let stats = $state<any>(null);
    let searchQuery = $state("");
    let statusFilter = $state("all");
    let categoryFilter = $state("all");
    let isAuthorized = $state(false);

    // Modal state
    let selectedReport = $state<Report | null>(null);
    let showReportModal = $state(false);

    onMount(async () => {
        const token = getToken();
        const currentUser = getCurrentUser();

        if (!token || !currentUser) {
            goto("/signin");
            return;
        }

        // Check for admin/municipality role
        const role = currentUser.role;
        if (
            !role ||
            !["super_admin", "admin", "moderator", "municipality_admin", "municipality_staff"].includes(
                role,
            )
        ) {
            isAuthorized = false;
            loading = false;
            return;
        }

        isAuthorized = true;
        await loadDashboard();
    });

    async function loadDashboard() {
        try {
            loading = true;

            // Load reports
            reports = await getReports(undefined, undefined, 100);

            // Calculate stats
            const pending = reports.filter(
                (r) =>
                    r.status === "PENDING_VERIFICATION" ||
                    r.status === "VERIFIED",
            ).length;
            const inProgress = reports.filter(
                (r) => r.status === "IN_PROGRESS",
            ).length;
            const resolved = reports.filter(
                (r) => r.status === "RESOLVED",
            ).length;

            stats = {
                total: reports.length,
                pending,
                inProgress,
                resolved,
                criticalCount: reports.filter((r) => r.severity >= 8).length,
            };

            error = "";
        } catch (e: any) {
            error = e.message || "Failed to load dashboard";
            console.error("Dashboard load error:", e);
        } finally {
            loading = false;
        }
    }

    async function handleRefresh() {
        await loadDashboard();
        toast.success("Dashboard refreshed");
    }

    function openReportModal(report: Report) {
        selectedReport = report;
        showReportModal = true;
    }

    function closeReportModal() {
        selectedReport = null;
        showReportModal = false;
    }

    // Filtered reports
    const filteredReports = $derived(() => {
        return reports.filter((r) => {
            if (
                searchQuery &&
                !r.title.toLowerCase().includes(searchQuery.toLowerCase())
            )
                return false;
            if (statusFilter !== "all" && r.status !== statusFilter)
                return false;
            if (categoryFilter !== "all" && r.category !== categoryFilter)
                return false;
            return true;
        });
    });

    const categories = $derived(
        [...new Set(reports.map((r) => r.category))].sort(),
    );

    function getStatusBadgeClass(status: string): string {
        switch (status) {
            case "VERIFIED":
                return "status-verified";
            case "IN_PROGRESS":
                return "status-progress";
            case "RESOLVED":
                return "status-resolved";
            case "PENDING_VERIFICATION":
                return "status-pending";
            case "REJECTED":
                return "status-rejected";
            default:
                return "status-default";
        }
    }

    function getSeverityClass(severity: number): string {
        if (severity >= 8) return "severity-critical";
        if (severity >= 5) return "severity-high";
        if (severity >= 3) return "severity-medium";
        return "severity-low";
    }

    function formatTime(dateStr: string): string {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return "just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
</script>

{#if !isAuthorized && !loading}
    <div class="unauthorized">
        <div class="unauthorized-content">
            <AlertTriangle size={48} />
            <h2>Access Denied</h2>
            <p>
                You don't have permission to access the Municipality Dashboard.
            </p>
            <button class="btn-primary" onclick={() => goto("/")}
                >Go Home</button
            >
        </div>
    </div>
{:else}
    <div class="operations-page">
        <!-- Header -->
        <header class="page-header">
            <div class="header-left">
                <h1>Operations Center</h1>
                <p class="header-subtitle">
                    Real-time municipal issue tracking
                </p>
            </div>
            <div class="header-right">
                <button
                    class="btn-icon"
                    onclick={handleRefresh}
                    disabled={loading}
                >
                    <RefreshCw size={18} class={loading ? "spin" : ""} />
                </button>
                <span class="status-indicator" class:loading>
                    {loading ? "Syncing..." : "Live"}
                </span>
            </div>
        </header>

        {#if loading && !stats}
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading dashboard...</p>
            </div>
        {:else if error}
            <div class="error-state">
                <AlertTriangle size={24} />
                <p>{error}</p>
                <button class="btn-secondary" onclick={handleRefresh}
                    >Retry</button
                >
            </div>
        {:else if stats}
            <!-- Stats Grid -->
            <section class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon total">
                        <Activity size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.total}</span>
                        <span class="stat-label">Total Reports</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon pending">
                        <Clock size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.pending}</span>
                        <span class="stat-label">Pending</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon progress">
                        <BarChart3 size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.inProgress}</span>
                        <span class="stat-label">In Progress</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon resolved">
                        <CheckCircle size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.resolved}</span>
                        <span class="stat-label">Resolved</span>
                    </div>
                </div>
            </section>

            <!-- Filters -->
            <section class="filters-bar">
                <div class="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Search reports..."
                        bind:value={searchQuery}
                    />
                </div>

                <div class="filter-group">
                    <Filter size={16} />
                    <select bind:value={statusFilter}>
                        <option value="all">All Status</option>
                        <option value="PENDING_VERIFICATION">Pending</option>
                        <option value="VERIFIED">Verified</option>
                        <option value="IN_PROGRESS">In Progress</option>
                        <option value="RESOLVED">Resolved</option>
                        <option value="REJECTED">Rejected</option>
                    </select>

                    <select bind:value={categoryFilter}>
                        <option value="all">All Categories</option>
                        {#each categories as cat}
                            <option value={cat}>{cat}</option>
                        {/each}
                    </select>
                </div>
            </section>

            <!-- Reports List -->
            <section class="reports-section">
                <h2 class="section-title">
                    Active Reports ({filteredReports().length})
                </h2>

                {#if filteredReports().length === 0}
                    <div class="empty-state">
                        <MapPin size={32} />
                        <p>No reports match your filters</p>
                    </div>
                {:else}
                    <div class="reports-list">
                        {#each filteredReports() as report}
                            <div
                                class="report-card"
                                onclick={() => openReportModal(report)}
                            >
                                <div class="report-main">
                                    <div class="report-header">
                                        <span class="report-category"
                                            >{report.category}</span
                                        >
                                        <span class="report-time"
                                            >{formatTime(
                                                report.created_at,
                                            )}</span
                                        >
                                    </div>
                                    <h3 class="report-title">{report.title}</h3>
                                    <div class="report-location">
                                        <MapPin size={14} />
                                        <span
                                            >{report.location ||
                                                report.address ||
                                                "Location unavailable"}</span
                                        >
                                    </div>
                                </div>
                                <div class="report-meta">
                                    <span
                                        class="severity-badge {getSeverityClass(
                                            report.severity,
                                        )}"
                                    >
                                        {report.severity}/10
                                    </span>
                                    <span
                                        class="status-badge {getStatusBadgeClass(
                                            report.status,
                                        )}"
                                    >
                                        {report.status.replace(/_/g, " ")}
                                    </span>
                                    <ChevronRight
                                        size={18}
                                        class="report-arrow"
                                    />
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </section>
        {/if}
    </div>

    <!-- Report Detail Modal -->
    {#if showReportModal && selectedReport}
        <div class="modal-overlay" onclick={closeReportModal}>
            <div class="modal-content" onclick={(e) => e.stopPropagation()}>
                <header class="modal-header">
                    <h2>{selectedReport.title}</h2>
                    <button class="btn-close" onclick={closeReportModal}
                        >×</button
                    >
                </header>

                <div class="modal-body">
                    <div class="detail-row">
                        <span class="detail-label">Category</span>
                        <span class="detail-value"
                            >{selectedReport.category}</span
                        >
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status</span>
                        <span
                            class="status-badge {getStatusBadgeClass(
                                selectedReport.status,
                            )}"
                        >
                            {selectedReport.status.replace(/_/g, " ")}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Severity</span>
                        <span
                            class="severity-badge {getSeverityClass(
                                selectedReport.severity,
                            )}"
                        >
                            {selectedReport.severity}/10
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Location</span>
                        <span class="detail-value"
                            >{selectedReport.location ||
                                selectedReport.address}</span
                        >
                    </div>
                    {#if selectedReport.description}
                        <div class="detail-row full">
                            <span class="detail-label">Description</span>
                            <p class="detail-value">
                                {selectedReport.description}
                            </p>
                        </div>
                    {/if}
                </div>

                <footer class="modal-footer">
                    <button class="btn-secondary" onclick={closeReportModal}
                        >Close</button
                    >
                    <a href="/report/{selectedReport.id}" class="btn-primary">
                        <Eye size={16} /> View Full Report
                    </a>
                </footer>
            </div>
        </div>
    {/if}
{/if}

<style>
    .operations-page {
        padding: 1.5rem;
    }

    /* Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        flex-wrap: wrap;
        gap: 1rem;
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
        margin: 0.25rem 0 0 0;
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .btn-icon {
        padding: 0.5rem;
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

    .btn-icon:disabled {
        opacity: 0.5;
        cursor: not-allowed;
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

    .status-indicator {
        padding: 0.375rem 0.75rem;
        background: var(--c-success-light);
        color: var(--c-success-dark);
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .status-indicator.loading {
        background: var(--c-warning-light);
        color: var(--c-warning-dark);
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

    /* Loading & Error States */
    .loading-state,
    .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        gap: 1rem;
        color: var(--c-text-secondary);
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

    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }

    .stat-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.25rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
    }

    .stat-icon {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-sm);
    }

    .stat-icon.total {
        background: var(--c-info-light);
        color: var(--c-info-dark);
    }
    .stat-icon.pending {
        background: var(--c-warning-light);
        color: var(--c-warning-dark);
    }
    .stat-icon.progress {
        background: var(--c-brand);
        color: var(--c-brand-contrast);
    }
    .stat-icon.resolved {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }

    .stat-info {
        display: flex;
        flex-direction: column;
    }

    .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--c-text-primary);
        line-height: 1;
    }

    .stat-label {
        font-size: 0.8125rem;
        color: var(--c-text-secondary);
        margin-top: 0.25rem;
    }

    /* Filters */
    .filters-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.5rem;
        align-items: center;
    }

    .search-box {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        flex: 1;
        min-width: 200px;
        max-width: 400px;
    }

    .search-box input {
        flex: 1;
        border: none;
        background: transparent;
        color: var(--c-text-primary);
        font-size: 0.9375rem;
        outline: none;
    }

    .search-box input::placeholder {
        color: var(--c-text-tertiary);
    }

    .filter-group {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--c-text-secondary);
    }

    .filter-group select {
        padding: 0.5rem 0.75rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-primary);
        font-size: 0.875rem;
        cursor: pointer;
    }

    /* Reports */
    .section-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 1rem 0;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
        padding: 3rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        color: var(--c-text-secondary);
    }

    .reports-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .report-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.25rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .report-card:hover {
        border-color: var(--c-brand);
        box-shadow: var(--shadow-sm);
    }

    .report-main {
        flex: 1;
        min-width: 0;
    }

    .report-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.375rem;
    }

    .report-category {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--c-brand);
        text-transform: uppercase;
    }

    .report-time {
        font-size: 0.75rem;
        color: var(--c-text-tertiary);
    }

    .report-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 0.375rem 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .report-location {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.8125rem;
        color: var(--c-text-secondary);
    }

    .report-meta {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
    }

    .report-arrow {
        color: var(--c-text-tertiary);
    }

    /* Badges */
    .severity-badge,
    .status-badge {
        padding: 0.25rem 0.625rem;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .severity-critical {
        background: var(--c-error-light);
        color: var(--c-error-dark);
    }
    .severity-high {
        background: var(--c-warning-light);
        color: var(--c-warning-dark);
    }
    .severity-medium {
        background: var(--c-info-light);
        color: var(--c-info-dark);
    }
    .severity-low {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }

    .status-verified {
        background: var(--c-info-light);
        color: var(--c-info-dark);
    }
    .status-progress {
        background: var(--c-warning-light);
        color: var(--c-warning-dark);
    }
    .status-resolved {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }
    .status-pending {
        background: var(--c-bg-subtle);
        color: var(--c-text-secondary);
    }
    .status-rejected {
        background: var(--c-error-light);
        color: var(--c-error-dark);
    }
    .status-default {
        background: var(--c-bg-subtle);
        color: var(--c-text-secondary);
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
        max-height: 80vh;
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
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0;
    }

    .btn-close {
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: none;
        font-size: 1.5rem;
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

    .detail-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 0;
        border-bottom: 1px solid var(--c-border);
    }

    .detail-row.full {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }

    .detail-row:last-child {
        border-bottom: none;
    }

    .detail-label {
        font-size: 0.875rem;
        color: var(--c-text-secondary);
    }

    .detail-value {
        font-size: 0.9375rem;
        color: var(--c-text-primary);
        margin: 0;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--c-border);
    }

    /* Buttons */
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
        text-decoration: none;
        border: none;
    }

    .btn-primary {
        background: var(--c-brand);
        color: var(--c-brand-contrast);
    }

    .btn-primary:hover {
        opacity: 0.9;
    }

    .btn-secondary {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
        border: 1px solid var(--c-border);
    }

    .btn-secondary:hover {
        background: var(--c-border);
    }

    /* Responsive */
    @media (max-width: 768px) {
        .operations-page {
            padding: 1rem;
        }

        .page-header h1 {
            font-size: 1.5rem;
        }

        .stats-grid {
            grid-template-columns: repeat(2, 1fr);
        }

        .filters-bar {
            flex-direction: column;
            align-items: stretch;
        }

        .search-box {
            max-width: none;
        }

        .filter-group {
            flex-wrap: wrap;
        }

        .report-card {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
        }

        .report-meta {
            width: 100%;
            justify-content: flex-start;
        }

        .report-arrow {
            display: none;
        }
    }

    @media (max-width: 480px) {
        .stats-grid {
            grid-template-columns: 1fr;
        }

        .stat-card {
            padding: 1rem;
        }

        .stat-value {
            font-size: 1.5rem;
        }
    }
</style>
