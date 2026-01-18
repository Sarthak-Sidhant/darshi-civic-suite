<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { goto } from "$app/navigation";
    import Chart from "chart.js/auto";
    import {
        getMunicipalityDashboard,
        getMunicipalityReports,
        getToken,
        getCurrentUser,
        type MunicipalityStats,
        type Report,
    } from "$lib/api";
    import {
        TrendingUp,
        BarChart3,
        MapPin,
        AlertTriangle,
        RefreshCw,
        CheckCircle,
        Clock,
        Activity,
    } from "lucide-svelte";

    // State
    let stats = $state<MunicipalityStats | null>(null);
    let reports = $state<Report[]>([]);
    let loading = $state(true);
    let error = $state("");
    let isAuthorized = $state(false);
    let refreshInterval: ReturnType<typeof setInterval> | undefined;

    // Chart refs
    let trendCanvas = $state<HTMLCanvasElement>();
    let categoryCanvas = $state<HTMLCanvasElement>();
    let trendChart: Chart | null = null;
    let categoryChart: Chart | null = null;

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
            "municipality_admin", "municipality_staff",
        ].includes(currentUser.role || "");

        if (!isAuthorized) {
            loading = false;
            return;
        }

        await loadAnalytics();
        refreshInterval = setInterval(loadAnalytics, 60000);
    });

    onDestroy(() => {
        if (refreshInterval) clearInterval(refreshInterval);
        if (trendChart) trendChart.destroy();
        if (categoryChart) categoryChart.destroy();
    });

    async function loadAnalytics() {
        try {
            const [dashData, reportsData] = await Promise.all([
                getMunicipalityDashboard(),
                getMunicipalityReports({ limit: 200 }),
            ]);

            stats = dashData;
            reports = reportsData.reports;
            error = "";

            setTimeout(renderCharts, 100);
        } catch (e: any) {
            error = e.message || "Failed to load analytics";
        } finally {
            loading = false;
        }
    }

    async function handleRefresh() {
        loading = true;
        await loadAnalytics();
    }

    function renderCharts() {
        if (!trendCanvas || !categoryCanvas || !reports.length) return;

        if (trendChart) trendChart.destroy();
        if (categoryChart) categoryChart.destroy();

        const weeklyData = calculateWeeklyTrend(reports);

        // Trend Chart
        trendChart = new Chart(trendCanvas, {
            type: "line",
            data: {
                labels: weeklyData.labels,
                datasets: [
                    {
                        label: "Reports",
                        data: weeklyData.counts,
                        borderColor: "#3b82f6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.1)" },
                        ticks: { color: "var(--c-text-secondary)" },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "var(--c-text-secondary)" },
                    },
                },
            },
        });

        // Category Chart
        if (stats?.reports_by_category) {
            const categories = Object.keys(stats.reports_by_category);
            const counts = Object.values(stats.reports_by_category);
            const colors = [
                "#3b82f6",
                "#10b981",
                "#f59e0b",
                "#ef4444",
                "#8b5cf6",
                "#ec4899",
            ];

            categoryChart = new Chart(categoryCanvas, {
                type: "doughnut",
                data: {
                    labels: categories,
                    datasets: [
                        {
                            data: counts,
                            backgroundColor: colors.slice(0, categories.length),
                            borderWidth: 0,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "right",
                            labels: { color: "var(--c-text-primary)" },
                        },
                    },
                },
            });
        }
    }

    function calculateWeeklyTrend(reports: Report[]) {
        const last7Days: Record<string, number> = {};
        const labels: string[] = [];
        const now = new Date();

        for (let i = 6; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            const key = date.toLocaleDateString("en-US", { weekday: "short" });
            const dateKey = date.toISOString().split("T")[0];
            labels.push(key);
            last7Days[dateKey] = 0;
        }

        reports.forEach((report) => {
            const reportDate = new Date(report.created_at)
                .toISOString()
                .split("T")[0];
            if (reportDate in last7Days) {
                last7Days[reportDate]++;
            }
        });

        return { labels, counts: Object.values(last7Days) };
    }

    // Derived values
    const topCategory = $derived.by(() => {
        if (!stats?.reports_by_category) return null;
        const entries = Object.entries(stats.reports_by_category);
        if (!entries.length) return null;
        entries.sort((a, b) => b[1] - a[1]);
        return { name: entries[0][0], count: entries[0][1] };
    });

    const resolutionRate = $derived.by(() => {
        if (!stats || stats.total_reports === 0) return 0;
        return Math.round((stats.resolved_reports / stats.total_reports) * 100);
    });
</script>

{#if !isAuthorized && !loading}
    <div class="unauthorized">
        <div class="unauthorized-content">
            <AlertTriangle size={48} />
            <h2>Access Denied</h2>
            <p>You don't have permission to view analytics.</p>
            <button class="btn-primary" onclick={() => goto("/")}
                >Go Home</button
            >
        </div>
    </div>
{:else}
    <div class="analytics-page">
        <!-- Header -->
        <header class="page-header">
            <div class="header-left">
                <h1>Analytics</h1>
                <p class="header-subtitle">Performance insights and trends</p>
            </div>
            <button class="btn-icon" onclick={handleRefresh} disabled={loading}>
                <RefreshCw size={18} class={loading ? "spin" : ""} />
            </button>
        </header>

        {#if loading && !stats}
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading analytics...</p>
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
            <!-- Stats Cards -->
            <section class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon total">
                        <Activity size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.total_reports}</span>
                        <span class="stat-label">Total Reports</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon pending">
                        <Clock size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.pending_reports}</span>
                        <span class="stat-label">Pending</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon resolved">
                        <CheckCircle size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{stats.resolved_reports}</span>
                        <span class="stat-label">Resolved</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon rate">
                        <TrendingUp size={24} />
                    </div>
                    <div class="stat-info">
                        <span class="stat-value">{resolutionRate}%</span>
                        <span class="stat-label">Resolution Rate</span>
                    </div>
                </div>
            </section>

            <!-- Charts -->
            <section class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">Weekly Trend</h3>
                    <div class="chart-container">
                        <canvas bind:this={trendCanvas}></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h3 class="chart-title">By Category</h3>
                    <div class="chart-container">
                        <canvas bind:this={categoryCanvas}></canvas>
                    </div>
                </div>
            </section>

            <!-- Insights -->
            {#if topCategory}
                <section class="insights-section">
                    <h3 class="section-title">Insights</h3>
                    <div class="insight-card">
                        <MapPin size={20} />
                        <div>
                            <span class="insight-label">Top Category</span>
                            <span class="insight-value"
                                >{topCategory.name} ({topCategory.count} reports)</span
                            >
                        </div>
                    </div>
                </section>
            {/if}
        {/if}
    </div>
{/if}

<style>
    .analytics-page {
        padding: 1.5rem;
    }

    /* Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
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

    /* States */
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
    .stat-icon.resolved {
        background: var(--c-success-light);
        color: var(--c-success-dark);
    }
    .stat-icon.rate {
        background: var(--c-brand);
        color: var(--c-brand-contrast);
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

    /* Charts */
    .charts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    .chart-card {
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        padding: 1.5rem;
    }

    .chart-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 1rem 0;
    }

    .chart-container {
        height: 250px;
        position: relative;
    }

    /* Insights */
    .section-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0 0 1rem 0;
    }

    .insight-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        color: var(--c-text-secondary);
    }

    .insight-label {
        display: block;
        font-size: 0.75rem;
        color: var(--c-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .insight-value {
        display: block;
        font-size: 1rem;
        font-weight: 600;
        color: var(--c-text-primary);
        text-transform: capitalize;
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
        .analytics-page {
            padding: 1rem;
        }

        .charts-grid {
            grid-template-columns: 1fr;
        }

        .chart-container {
            height: 200px;
        }
    }
</style>
