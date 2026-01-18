<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import Chart from "chart.js/auto";
	import {
		getAdminReports,
		updateReportStatus,
		getAdminDashboard,
		getAuditLogs,
		listAdmins,
		createAdmin,
		updateAdminStatus,
		clearToken,
		clearCurrentUser,
		getToken,
		getCurrentUser,
		getMunicipalities,
		getDepartments,
		assignReportToMunicipality,
		type Report,
		type Municipality,
		type Department,
		getPendingFlags,
		reviewFlag,
		type Flag as FlagType,
	} from "$lib/api";
	import { user, isAuthenticated } from "$lib/stores";
	import { toast } from "$lib/stores/toast";
	import {
		Menu,
		X,
		LayoutDashboard,
		FileText,
		ClipboardList,
		Users,
		Lock,
		LockOpen,
		Check,
		Flag,
	} from "lucide-svelte";

	// State
	let currentTab = $state("dashboard");
	let reports: Report[] = $state([]);
	let dashboardData: any = $state(null);
	let auditLogs: any[] = $state([]);
	let admins: any[] = $state([]);
	let pendingFlags: FlagType[] = $state([]);
	let totalFlags = $state(0);
	let loadingFlags = $state(false);
	let loading = $state(true);
	let error = $state("");
	let mobileMenuOpen = $state(false);

	// Municipality assignment state
	let municipalities: Municipality[] = $state([]);
	let departments: Department[] = $state([]);
	let selectedMunicipality = $state("");
	let selectedDepartment = $state("");
	let showAssignModal = $state(false);
	let reportToAssign: Report | null = $state(null);
	let assigning = $state(false);

	// Chart Refs
	let chartCanvas = $state<HTMLCanvasElement>();
	let statusCanvas = $state<HTMLCanvasElement>();

	function renderCharts() {
		if (!dashboardData || !chartCanvas || !statusCanvas) return;

		const existingChart1 = Chart.getChart(chartCanvas);
		if (existingChart1) existingChart1.destroy();

		const existingChart2 = Chart.getChart(statusCanvas);
		if (existingChart2) existingChart2.destroy();

		// Calculate reports per day from actual reports data
		const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
		const reportsPerDay = [0, 0, 0, 0, 0, 0, 0]; // Index 0 = Sunday
		const now = new Date();
		const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

		reports.forEach((report) => {
			const createdAt = new Date(report.created_at);
			if (createdAt >= oneWeekAgo) {
				const dayOfWeek = createdAt.getDay();
				reportsPerDay[dayOfWeek]++;
			}
		});

		// Reorder to Mon-Sun format
		const orderedData = [...reportsPerDay.slice(1), reportsPerDay[0]];

		// Report Trends Chart
		new Chart(chartCanvas, {
			type: "bar",
			data: {
				labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
				datasets: [
					{
						label: "Reports Filed",
						data: orderedData,
						backgroundColor: "#60a5fa",
						borderRadius: 4,
					},
				],
			},
			options: {
				responsive: true,
				plugins: { legend: { display: false } },
				scales: {
					y: {
						grid: { color: "#374151" },
						ticks: { color: "#9ca3af" },
					},
					x: {
						grid: { display: false },
						ticks: { color: "#9ca3af" },
					},
				},
			},
		});

		// Status Distribution Chart
		const statusData = dashboardData.summary.status_distribution || {};
		new Chart(statusCanvas, {
			type: "doughnut",
			data: {
				labels: Object.keys(statusData),
				datasets: [
					{
						data: Object.values(statusData),
						backgroundColor: [
							"#f87171",
							"#34d399",
							"#60a5fa",
							"#fbbf24",
							"#9ca3af",
						],
						borderWidth: 0,
					},
				],
			},
			options: {
				responsive: true,
				plugins: {
					legend: { position: "right", labels: { color: "#d1d5db" } },
				},
			},
		});
	}

	// Report management
	let selectedReports: Set<string> = $state(new Set());
	let filterStatus = $state("all");
	let filterCategory = $state("all");
	let searchQuery = $state("");
	let sortBy = $state("created_at");

	// Modal state
	let showStatusModal = $state(false);
	let selectedReport: Report | null = $state(null);
	let newStatus = $state("");
	let statusNote = $state("");
	let updating = $state(false);

	// Report detail modal
	let showDetailModal = $state(false);
	let detailReport: Report | null = $state(null);

	// Staff management modal
	let showCreateAdminModal = $state(false);
	let newAdminEmail = $state("");
	let newAdminPassword = $state("");
	let newAdminRole = $state("moderator");
	let creatingAdmin = $state(false);
	let isSuperAdmin = $derived($user?.role === "super_admin");

	// Access control state
	let isAuthorized = $state(false);

	onMount(async () => {
		// Check localStorage directly for immediate auth check
		const token = getToken();
		const currentUser = getCurrentUser();

		if (!token || !currentUser) {
			goto("/signin");
			return;
		}

		// Check if user has admin role
		isAuthorized =
			currentUser.role === "super_admin" ||
			currentUser.role === "moderator" ||
			currentUser.role === "admin";

		if (!isAuthorized) {
			// Do not redirect, let the template show 403
			loading = false;
			return;
		}

		// Always set stores from localStorage to ensure consistency
		$user = currentUser;
		$isAuthenticated = true;

		await loadDashboard();

		// Load flags count initially
		loadFlags(true);
	});

	async function loadDashboard() {
		loading = true;
		try {
			const [reportsData, dashData, munData] = await Promise.all([
				getAdminReports({ limit: 100 }),
				getAdminDashboard(),
				getMunicipalities(),
			]);
			reports = reportsData;
			dashboardData = dashData;
			municipalities = munData.municipalities;

			// Also load departments
			const deptData = await getDepartments();
			departments = deptData.departments;

			// Trigger chart render after data load
			setTimeout(() => {
				if (currentTab === "dashboard") renderCharts();
			}, 100);
		} catch (e) {
			error = "Failed to load dashboard data";
		} finally {
			loading = false;
		}
	}

	function openAssignModal(report: Report) {
		reportToAssign = report;
		selectedMunicipality = (report as any).assigned_municipality || "";
		selectedDepartment = (report as any).assigned_department || "";
		showAssignModal = true;
	}

	async function handleAssignReport() {
		if (!reportToAssign || !selectedMunicipality) return;

		assigning = true;
		try {
			await assignReportToMunicipality(
				reportToAssign.id,
				selectedMunicipality,
				selectedDepartment || undefined,
			);
			toast.success("Report assigned successfully");
			showAssignModal = false;
			reportToAssign = null;
			await loadDashboard();
		} catch (e) {
			toast.error("Failed to assign report");
		} finally {
			assigning = false;
		}
	}

	async function loadAuditLogs() {
		try {
			const data = await getAuditLogs({ limit: 100 });
			auditLogs = data.logs;
		} catch (e) {
			error = "Failed to load audit logs";
		}
	}

	async function loadFlags(silent = false) {
		if (!silent) loadingFlags = true;
		try {
			const data = await getPendingFlags();
			pendingFlags = data.flags;
			totalFlags = data.total;
		} catch (e) {
			if (!silent) toast.error("Failed to load flags");
		} finally {
			loadingFlags = false;
		}
	}

	async function handleReviewFlag(flagId: string, status: string) {
		try {
			await reviewFlag(flagId, status);
			toast.success(`Flag marked as ${status}`);
			await loadFlags();
		} catch (e) {
			toast.error("Failed to review flag");
		}
	}

	async function loadAdmins() {
		try {
			const data = await listAdmins();
			admins = data.admins;
		} catch (e: any) {
			if (e.message.includes("403")) {
				error = "Only super admins can view staff list";
			} else {
				error = "Failed to load staff list";
			}
		}
	}

	async function switchTab(tab: string) {
		currentTab = tab;
		mobileMenuOpen = false; // Close mobile menu when tab is switched
		if (tab === "audit" && auditLogs.length === 0) {
			await loadAuditLogs();
		} else if (tab === "staff" && admins.length === 0) {
			await loadAdmins();
		} else if (tab === "flags") {
			await loadFlags();
		}
	}

	function toggleReportSelection(reportId: string) {
		if (selectedReports.has(reportId)) {
			selectedReports.delete(reportId);
		} else {
			selectedReports.add(reportId);
		}
		selectedReports = selectedReports; // Trigger reactivity
	}

	function selectAllReports() {
		if (selectedReports.size === filteredReports.length) {
			selectedReports.clear();
		} else {
			filteredReports.forEach((r) => selectedReports.add(r.id));
		}
		selectedReports = selectedReports;
	}

	async function bulkUpdateStatus(status: string) {
		if (selectedReports.size === 0) return;
		if (!confirm(`Update ${selectedReports.size} reports to ${status}?`))
			return;

		updating = true;
		try {
			await Promise.all(
				Array.from(selectedReports).map((id) =>
					updateReportStatus(id, status, `Bulk action: ${status}`),
				),
			);
			await loadDashboard();
			selectedReports.clear();
		} catch (e) {
			toast.error("Failed to update some reports");
		} finally {
			updating = false;
		}
	}

	function openDetailModal(report: Report) {
		detailReport = report;
		showDetailModal = true;
	}

	function openStatusModal(report: Report) {
		selectedReport = report;
		newStatus = report.status;
		statusNote = "";
		showStatusModal = true;
	}

	async function handleUpdateStatus() {
		if (!selectedReport) return;

		updating = true;
		try {
			await updateReportStatus(selectedReport.id, newStatus, statusNote);
			await loadDashboard();
			showStatusModal = false;
			selectedReport = null;
		} catch (e) {
			toast.error("Failed to update status");
		} finally {
			updating = false;
		}
	}

	function exportToCSV() {
		const csv = [
			["ID", "Title", "Status", "Category", "Severity", "Created At"],
			...filteredReports.map((r) => [
				r.id,
				r.title,
				r.status,
				r.category,
				r.severity,
				r.created_at,
			]),
		]
			.map((row) => row.join(","))
			.join("\n");

		const blob = new Blob([csv], { type: "text/csv" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `reports-${new Date().toISOString()}.csv`;
		a.click();
	}

	function handleLogout() {
		clearToken();
		clearCurrentUser();
		$user = null;
		$isAuthenticated = false;
		goto("/signin");
	}

	async function handleCreateAdmin() {
		if (!newAdminEmail || !newAdminPassword) {
			error = "Email and password are required";
			return;
		}

		creatingAdmin = true;
		error = "";
		try {
			await createAdmin(newAdminEmail, newAdminPassword, newAdminRole);
			showCreateAdminModal = false;
			newAdminEmail = "";
			newAdminPassword = "";
			newAdminRole = "moderator";
			await loadAdmins();
		} catch (e) {
			error = "Failed to create admin";
		} finally {
			creatingAdmin = false;
		}
	}

	async function handleToggleAdminStatus(
		adminEmail: string,
		currentStatus: boolean,
	) {
		if (
			!confirm(
				`${currentStatus ? "Deactivate" : "Activate"} ${adminEmail}?`,
			)
		)
			return;

		try {
			await updateAdminStatus(adminEmail, !currentStatus);
			await loadAdmins();
		} catch (e) {
			toast.error("Failed to update admin status");
		}
	}

	function getStatusColor(status: string): string {
		const colors: Record<string, string> = {
			PENDING_VERIFICATION: "#f39c12",
			VERIFIED: "#3498db",
			IN_PROGRESS: "#9b59b6",
			RESOLVED: "#27ae60",
			REJECTED: "#e74c3c",
			DUPLICATE: "#95a5a6",
			FLAGGED: "#e67e22",
		};
		return colors[status] || "#7f8c8d";
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString("en-US", {
			year: "numeric",
			month: "short",
			day: "numeric",
			hour: "2-digit",
			minute: "2-digit",
		});
	}

	// Computed
	const filteredReports = $derived.by(() => {
		let filtered = reports;

		if (filterStatus !== "all") {
			filtered = filtered.filter((r) => r.status === filterStatus);
		}

		if (filterCategory !== "all") {
			filtered = filtered.filter((r) => r.category === filterCategory);
		}

		if (searchQuery) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(
				(r) =>
					r.title.toLowerCase().includes(query) ||
					r.description?.toLowerCase().includes(query) ||
					r.id.toLowerCase().includes(query),
			);
		}

		return filtered;
	});

	const categories = $derived(
		[...new Set(reports.map((r) => r.category))].sort(),
	);
</script>

{#if !isAuthorized && !loading}
	<div class="unauthorized-container">
		<div class="unauthorized-card">
			<Lock size={48} class="lock-icon" />
			<h1>403 Forbidden</h1>
			<p>YOU ARE FORBIDDEN.</p>
			<p>You do not have permission to access the Admin Dashboard.</p>
			<button onclick={() => goto("/")} class="btn-primary"
				>Go Home</button
			>
		</div>
	</div>
{:else}
	<div class="admin-container">
		<!-- Mobile Header -->
		<header class="mobile-header">
			<div class="mobile-header-content">
				<div class="mobile-title">
					<h2>Darshi Admin</h2>
					<span class="admin-badge">{$user?.role}</span>
				</div>
				<button
					class="mobile-menu-btn"
					onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
				>
					{#if mobileMenuOpen}
						<X size={20} />
					{:else}
						<Menu size={20} />
					{/if}
				</button>
			</div>
		</header>

		<!-- Sidebar -->
		<aside class="sidebar" class:mobile-open={mobileMenuOpen}>
			<div class="sidebar-header">
				<h2>Darshi Admin</h2>
				<span class="admin-badge">{$user?.role}</span>
			</div>

			<nav class="sidebar-nav">
				<button
					class:active={currentTab === "dashboard"}
					onclick={() => switchTab("dashboard")}
				>
					<LayoutDashboard size={18} /> Dashboard
				</button>
				<button
					class:active={currentTab === "reports"}
					onclick={() => switchTab("reports")}
				>
					<FileText size={18} /> Reports
				</button>
				<button
					class:active={currentTab === "audit"}
					onclick={() => switchTab("audit")}
				>
					<ClipboardList size={18} /> Audit Logs
				</button>
				<button
					class:active={currentTab === "flags"}
					onclick={() => switchTab("flags")}
				>
					<div class="flex items-center justify-between w-full">
						<span class="flex items-center gap-2">
							<Flag size={18} /> Flags
						</span>
						{#if totalFlags > 0}
							<span
								class="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full"
								>{totalFlags}</span
							>
						{/if}
					</div>
				</button>
				<button
					class:active={currentTab === "staff"}
					onclick={() => switchTab("staff")}
				>
					<Users size={18} /> Staff
				</button>
			</nav>

			<div class="sidebar-footer">
				<div class="user-info">
					<span class="user-email">{$user?.email}</span>
				</div>
				<button class="logout-btn" onclick={handleLogout}>
					Logout
				</button>
			</div>
		</aside>

		<!-- Overlay for mobile menu -->
		{#if mobileMenuOpen}
			<div
				class="mobile-overlay"
				onclick={() => (mobileMenuOpen = false)}
			></div>
		{/if}

		<!-- Main Content -->
		<main class="main-content">
			{#if loading}
				<div class="loading">Loading...</div>
			{:else if error}
				<div class="error-banner">{error}</div>
			{:else}
				<!-- Dashboard Tab -->
				{#if currentTab === "dashboard"}
					<div class="dashboard-tab">
						<h1>Dashboard Overview</h1>

						{#if dashboardData}
							<div class="stats-grid">
								<div class="stat-card">
									<div class="stat-value">
										{dashboardData.summary.total_reports}
									</div>
									<div class="stat-label">Total Reports</div>
								</div>
								<div class="stat-card">
									<div class="stat-value">
										{dashboardData.summary
											.status_distribution?.VERIFIED || 0}
									</div>
									<div class="stat-label">Verified</div>
								</div>
								<div class="stat-card">
									<div class="stat-value">
										{dashboardData.summary
											.status_distribution
											?.PENDING_VERIFICATION || 0}
									</div>
									<div class="stat-label">Pending</div>
								</div>
								<div class="stat-card">
									<div class="stat-value">
										{dashboardData.summary.average_severity.toFixed(
											1,
										)}
									</div>
									<div class="stat-label">Avg Severity</div>
								</div>
							</div>

							<div class="dashboard-sections mb-8">
								<!-- Charts Section -->
								<div
									class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 w-full"
								>
									<div
										class="bg-gray-800 p-6 rounded-xl border border-gray-700"
									>
										<h3
											class="text-lg font-bold mb-4 text-white"
										>
											Report Trends
										</h3>
										<div class="h-64 w-full">
											<canvas bind:this={chartCanvas}
											></canvas>
										</div>
									</div>
									<div
										class="bg-gray-800 p-6 rounded-xl border border-gray-700"
									>
										<h3
											class="text-lg font-bold mb-4 text-white"
										>
											Status Distribution
										</h3>
										<div
											class="h-64 flex justify-center w-full"
										>
											<canvas bind:this={statusCanvas}
											></canvas>
										</div>
									</div>
								</div>

								<div class="section">
									<h3>Top Categories</h3>
									<div class="category-list">
										{#each dashboardData.top_categories as cat}
											<div class="category-item">
												<span class="category-name"
													>{cat.category}</span
												>
												<span class="category-count"
													>{cat.count}</span
												>
											</div>
										{/each}
									</div>
								</div>

								<div class="section">
									<h3>Status Distribution</h3>
									<div class="status-list">
										{#each Object.entries(dashboardData.summary.status_distribution) as [status, count]}
											<div class="status-item">
												<span
													class="status-badge"
													style="background: {getStatusColor(
														status,
													)}"
												>
													{status}
												</span>
												<span class="status-count"
													>{count}</span
												>
											</div>
										{/each}
									</div>
								</div>
							</div>

							<div class="section recent-actions">
								<h3>Recent Admin Actions</h3>
								<div class="actions-list">
									{#each dashboardData.recent_admin_actions.slice(0, 10) as action}
										<div class="action-item">
											<div class="action-info">
												<span class="action-type"
													>{action.action}</span
												>
												<span class="action-user"
													>{action.user_id}</span
												>
											</div>
											<span class="action-time"
												>{formatDate(
													action.timestamp,
												)}</span
											>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Reports Tab -->
				{#if currentTab === "reports"}
					<div class="reports-tab">
						<div class="reports-header">
							<h1>Report Management</h1>
							<button class="export-btn" onclick={exportToCSV}>
								Export CSV
							</button>
						</div>

						<!-- Filters -->
						<div class="filters">
							<input
								type="text"
								bind:value={searchQuery}
								placeholder="Search reports..."
								class="search-input"
							/>

							<select bind:value={filterStatus}>
								<option value="all">All Statuses</option>
								<option value="PENDING_VERIFICATION"
									>Pending</option
								>
								<option value="VERIFIED">Verified</option>
								<option value="IN_PROGRESS">In Progress</option>
								<option value="RESOLVED">Resolved</option>
								<option value="REJECTED">Rejected</option>
							</select>

							<select bind:value={filterCategory}>
								<option value="all">All Categories</option>
								{#each categories as cat}
									<option value={cat}>{cat}</option>
								{/each}
							</select>
						</div>

						<!-- Bulk Actions -->
						{#if selectedReports.size > 0}
							<div class="bulk-actions">
								<span>{selectedReports.size} selected</span>
								<button
									onclick={() => bulkUpdateStatus("VERIFIED")}
									>Verify</button
								>
								<button
									onclick={() =>
										bulkUpdateStatus("IN_PROGRESS")}
									>In Progress</button
								>
								<button
									onclick={() => bulkUpdateStatus("RESOLVED")}
									>Resolve</button
								>
								<button
									onclick={() => bulkUpdateStatus("REJECTED")}
									>Reject</button
								>
							</div>
						{/if}

						<!-- Reports Table -->
						<div class="table-container">
							<table>
								<thead>
									<tr>
										<th>
											<input
												type="checkbox"
												checked={selectedReports.size ===
													filteredReports.length &&
													filteredReports.length > 0}
												onchange={selectAllReports}
											/>
										</th>
										<th>ID</th>
										<th>Title</th>
										<th>Status</th>
										<th>Category</th>
										<th>Severity</th>
										<th>Created</th>
										<th>Actions</th>
									</tr>
								</thead>
								<tbody>
									{#each filteredReports as report}
										<tr>
											<td>
												<input
													type="checkbox"
													checked={selectedReports.has(
														report.id,
													)}
													onchange={() =>
														toggleReportSelection(
															report.id,
														)}
												/>
											</td>
											<td class="report-id"
												>{report.id.slice(0, 8)}</td
											>
											<td class="report-title"
												>{report.title}</td
											>
											<td>
												<span
													class="status-badge"
													style="background: {getStatusColor(
														report.status,
													)}"
												>
													{report.status}
												</span>
											</td>
											<td>{report.category}</td>
											<td>
												<span
													class="severity-badge"
													class:high={report.severity >=
														7}
												>
													{report.severity}
												</span>
											</td>
											<td class="date"
												>{formatDate(
													report.created_at,
												)}</td
											>
											<td>
												<div class="action-btns">
													<button
														class="action-btn view-btn"
														onclick={() =>
															openDetailModal(
																report,
															)}
													>
														View
													</button>
													<button
														class="action-btn"
														onclick={() =>
															openStatusModal(
																report,
															)}
													>
														Status
													</button>
													<button
														class="action-btn assign-btn"
														onclick={() =>
															openAssignModal(
																report,
															)}
													>
														Assign
													</button>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}

				<!-- Flags Tab -->
				{#if currentTab === "flags"}
					<div class="flags-tab">
						<h1>Report Flags</h1>

						{#if loadingFlags}
							<div class="loading">Loading flags...</div>
						{:else if pendingFlags.length === 0}
							<div class="empty-state">
								<Check size={48} class="text-green-500" />
								<h2>All Caught Up!</h2>
								<p>There are no pending flags to review.</p>
							</div>
						{:else}
							<div class="table-container">
								<table>
									<thead>
										<tr>
											<th>Type</th>
											<th>Report</th>
											<th>Reason</th>
											<th>Reporter</th>
											<th>Date</th>
											<th>Actions</th>
										</tr>
									</thead>
									<tbody>
										{#each pendingFlags as flag}
											<tr>
												<td>
													<span
														class="status-badge"
														style="background: #e74c3c"
													>
														{flag.flag_type.replace(
															"_",
															" ",
														)}
													</span>
												</td>
												<td>
													<a
														href="/report/{flag.report_id}"
														target="_blank"
														class="text-blue-400 hover:underline"
													>
														{flag.report_title ||
															"View Report"}
													</a>
													<div
														class="text-xs text-gray-400"
													>
														{flag.report_category}
													</div>
												</td>
												<td
													class="max-w-[200px] truncate"
													title={flag.reason}
													>{flag.reason || "-"}</td
												>
												<td>{flag.user_id}</td>
												<td
													>{new Date(
														flag.created_at,
													).toLocaleDateString()}</td
												>
												<td>
													<div class="flex gap-2">
														<button
															class="btn-sm btn-danger"
															onclick={() =>
																handleReviewFlag(
																	flag.id,
																	"actioned",
																)}
															title="Action Needed"
														>
															Valid
														</button>
														<button
															class="btn-sm btn-secondary"
															onclick={() =>
																handleReviewFlag(
																	flag.id,
																	"dismissed",
																)}
															title="Dismiss Flag"
														>
															Dismiss
														</button>
													</div>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Audit Logs Tab -->
				{#if currentTab === "audit"}
					<div class="audit-tab">
						<h1>Audit Logs</h1>

						<div class="audit-list">
							{#each auditLogs as log}
								<div class="audit-item">
									<div class="audit-header">
										<span class="audit-action"
											>{log.action}</span
										>
										<span class="audit-time"
											>{formatDate(log.timestamp)}</span
										>
									</div>
									<div class="audit-details">
										<span>User: {log.user_id}</span>
										<span
											>Resource: {log.resource_type}:{log.resource_id ||
												"N/A"}</span
										>
										{#if log.ip_address}
											<span>IP: {log.ip_address}</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Staff Tab -->
				{#if currentTab === "staff"}
					<div class="staff-tab">
						<div class="staff-header">
							<h1>Staff Management</h1>
							{#if isSuperAdmin}
								<button
									class="create-admin-btn"
									onclick={() =>
										(showCreateAdminModal = true)}
								>
									+ Create Admin
								</button>
							{/if}
						</div>

						{#if error}
							<div class="error-banner">{error}</div>
						{/if}

						<div class="staff-list">
							{#each admins as admin}
								<div
									class="staff-card"
									class:inactive={!admin.is_active}
								>
									<div class="staff-info">
										<div class="staff-header-row">
											<span class="staff-email"
												>{admin.email}</span
											>
											{#if $user?.email !== admin.email && isSuperAdmin}
												<button
													class="toggle-status-btn"
													onclick={() =>
														handleToggleAdminStatus(
															admin.email,
															admin.is_active,
														)}
													title={admin.is_active
														? "Deactivate"
														: "Activate"}
												>
													{#if admin.is_active}
														<Lock size={16} />
													{:else}
														<LockOpen size={16} />
													{/if}
												</button>
											{/if}
										</div>
										<span
											class="staff-role"
											class:super={admin.role ===
												"super_admin"}
										>
											{admin.role.replace("_", " ")}
										</span>
									</div>
									<div class="staff-meta">
										<span
											>Created: {admin.created_at
												? formatDate(admin.created_at)
												: "N/A"}</span
										>
										<span
											>Last login: {admin.last_login
												? formatDate(admin.last_login)
												: "Never"}</span
										>
										<span
											class:active={admin.is_active}
											class:inactive-text={!admin.is_active}
										>
											{#if admin.is_active}
												<Check size={14} /> Active
											{:else}
												<X size={14} /> Inactive
											{/if}
										</span>
									</div>
								</div>
							{/each}
							{#if admins.length === 0}
								<p class="empty-state">
									No staff members found.
								</p>
							{/if}
						</div>
					</div>
				{/if}
			{/if}
		</main>
	</div>

	<!-- Status Update Modal -->
	{#if showStatusModal && selectedReport}
		<div class="modal-overlay" onclick={() => (showStatusModal = false)}>
			<div class="modal" onclick={(e) => e.stopPropagation()}>
				<h2>Update Report Status</h2>
				<p class="report-info">Report: {selectedReport.title}</p>

				<div class="form-group">
					<label>New Status</label>
					<select bind:value={newStatus}>
						<option value="VERIFIED">Verified</option>
						<option value="IN_PROGRESS">In Progress</option>
						<option value="RESOLVED">Resolved</option>
						<option value="REJECTED">Rejected</option>
						<option value="FLAGGED">Flagged</option>
					</select>
				</div>

				<div class="form-group">
					<label>Note (optional)</label>
					<textarea
						bind:value={statusNote}
						rows="3"
						placeholder="Add a note..."
					></textarea>
				</div>

				<div class="modal-actions">
					<button
						class="btn-secondary"
						onclick={() => (showStatusModal = false)}>Cancel</button
					>
					<button
						class="btn-primary"
						onclick={handleUpdateStatus}
						disabled={updating}
					>
						{updating ? "Updating..." : "Update Status"}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Report Detail Modal -->
	{#if showDetailModal && detailReport}
		<div class="modal-overlay" onclick={() => (showDetailModal = false)}>
			<div class="modal modal-large" onclick={(e) => e.stopPropagation()}>
				<div class="detail-header">
					<h2>{detailReport.title}</h2>
					<button
						class="close-btn"
						onclick={() => (showDetailModal = false)}>×</button
					>
				</div>

				<div class="detail-content">
					<!-- Left column: Images and Description -->
					<div class="detail-main">
						{#if detailReport.image_urls && detailReport.image_urls.length > 0}
							<div class="image-gallery">
								{#each detailReport.image_urls as url}
									<img src={url} alt="Report image" />
								{/each}
							</div>
						{:else}
							<div class="no-images">No images attached</div>
						{/if}

						<div class="description-section">
							<h3>Description</h3>
							<p>
								{detailReport.description ||
									"No description provided"}
							</p>
						</div>

						{#if (detailReport as any).ai_analysis}
							<div class="ai-section">
								<h3>AI Analysis</h3>
								<pre>{JSON.stringify(
										(detailReport as any).ai_analysis,
										null,
										2,
									)}</pre>
							</div>
						{/if}
					</div>

					<!-- Right column: Meta info -->
					<div class="detail-sidebar">
						<div class="meta-card">
							<h4>Status</h4>
							<span
								class="status-badge status-{detailReport.status.toLowerCase()}"
								>{detailReport.status}</span
							>
						</div>

						<div class="meta-card">
							<h4>Category</h4>
							<span>{detailReport.category}</span>
						</div>

						<div class="meta-card">
							<h4>Severity</h4>
							<span class="severity-{detailReport.severity}"
								>{detailReport.severity}</span
							>
						</div>

						<div class="meta-card">
							<h4>Submitted By</h4>
							<span
								>{detailReport.submitted_by ||
									"Anonymous"}</span
							>
						</div>

						<div class="meta-card">
							<h4>Location</h4>
							<span
								>{detailReport.address ||
									`${detailReport.latitude?.toFixed(4)}, ${detailReport.longitude?.toFixed(4)}`}</span
							>
						</div>

						<div class="meta-card">
							<h4>Created</h4>
							<span>{formatDate(detailReport.created_at)}</span>
						</div>

						{#if (detailReport as any).assigned_municipality}
							<div class="meta-card">
								<h4>Assigned To</h4>
								<span
									>{(detailReport as any)
										.assigned_municipality}</span
								>
							</div>
						{/if}

						<div class="meta-card">
							<h4>Engagement</h4>
							<span
								>👍 {detailReport.upvote_count} upvotes • 💬 {detailReport.comments_count}
								comments</span
							>
						</div>
					</div>
				</div>

				<div class="modal-actions">
					<button
						class="btn-secondary"
						onclick={() => (showDetailModal = false)}>Close</button
					>
					<button
						class="btn-primary"
						onclick={() => {
							showDetailModal = false;
							openStatusModal(detailReport!);
						}}>Update Status</button
					>
					<button
						class="btn-primary"
						onclick={() => {
							showDetailModal = false;
							openAssignModal(detailReport!);
						}}>Assign</button
					>
				</div>
			</div>
		</div>
	{/if}
	{#if showAssignModal && reportToAssign}
		<div class="modal-overlay" onclick={() => (showAssignModal = false)}>
			<div class="modal" onclick={(e) => e.stopPropagation()}>
				<h2>Assign Report</h2>
				<p class="report-info">Report: {reportToAssign.title}</p>

				<div class="form-group">
					<label>Municipality</label>
					<select bind:value={selectedMunicipality}>
						<option value="">Select Municipality...</option>
						{#each municipalities as mun}
							<option value={mun.id}
								>{mun.name} ({mun.short_code ||
									mun.state})</option
							>
						{/each}
					</select>
				</div>

				<div class="form-group">
					<label>Department (optional)</label>
					<select bind:value={selectedDepartment}>
						<option value="">Select Department...</option>
						{#each departments as dept}
							<option value={dept.id}>{dept.name}</option>
						{/each}
					</select>
				</div>

				<div class="modal-actions">
					<button
						class="btn-secondary"
						onclick={() => (showAssignModal = false)}>Cancel</button
					>
					<button
						class="btn-primary"
						onclick={handleAssignReport}
						disabled={assigning || !selectedMunicipality}
					>
						{assigning ? "Assigning..." : "Assign Report"}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Create Admin Modal -->
	{#if showCreateAdminModal}
		<div
			class="modal-overlay"
			onclick={() => (showCreateAdminModal = false)}
		>
			<div class="modal" onclick={(e) => e.stopPropagation()}>
				<h2>Create New Admin</h2>

				<div class="form-group">
					<label>Email</label>
					<input
						type="email"
						bind:value={newAdminEmail}
						placeholder="admin@example.com"
						required
					/>
				</div>

				<div class="form-group">
					<label>Password</label>
					<input
						type="password"
						bind:value={newAdminPassword}
						placeholder="Enter a secure password"
						required
						minlength="8"
					/>
				</div>

				<div class="form-group">
					<label>Role</label>
					<select bind:value={newAdminRole}>
						<option value="moderator">Moderator</option>
						<option value="super_admin">Super Admin</option>
					</select>
				</div>

				<div class="modal-actions">
					<button
						class="btn-secondary"
						onclick={() => (showCreateAdminModal = false)}
						>Cancel</button
					>
					<button
						class="btn-primary"
						onclick={handleCreateAdmin}
						disabled={creatingAdmin}
					>
						{creatingAdmin ? "Creating..." : "Create Admin"}
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow-x: hidden;
	}

	.admin-container {
		display: flex;
		min-height: 100vh;
		width: 100%;
		max-width: 100vw;
		background: var(--c-bg-subtle);
		margin: 0;
		padding: 0;
		gap: 1px;
	}

	.admin-container * {
		box-sizing: border-box;
	}

	/* Mobile Header */
	.mobile-header {
		display: none;
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		background: var(--c-bg-surface);
		border-bottom: 1px solid var(--c-border);
		z-index: 100;
		padding: 1rem;
	}

	.mobile-header-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.mobile-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.mobile-title h2 {
		margin: 0;
		font-size: 1.125rem;
	}

	.mobile-menu-btn {
		background: transparent;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		padding: 0.5rem 0.75rem;
		font-size: 1.25rem;
		cursor: pointer;
		color: var(--c-text-primary);
	}

	.mobile-overlay {
		display: none;
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 99;
	}

	/* Sidebar */
	.sidebar {
		width: 260px;
		flex-shrink: 0;
		background: var(--c-bg-surface);
		border-right: 1px solid var(--c-border);
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow-y: auto;
		position: sticky;
		top: 0;
		z-index: 50;
	}

	.sidebar-header {
		padding: 1.5rem;
		border-bottom: 1px solid var(--c-border);
	}

	.sidebar-header h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.25rem;
		color: var(--c-text-primary);
	}

	.admin-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border-radius: var(--radius-full);
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.sidebar-nav {
		flex: 1;
		padding: 1rem;
	}

	.sidebar-nav button {
		width: 100%;
		padding: 0.75rem 1rem;
		text-align: left;
		background: transparent;
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all 0.2s;
		font-size: 0.9375rem;
		color: var(--c-text-secondary);
		margin-bottom: 0.5rem;
	}

	.sidebar-nav button:hover {
		background: var(--c-bg-subtle);
		color: var(--c-text-primary);
	}

	.sidebar-nav button.active {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		font-weight: 600;
	}

	.sidebar-footer {
		padding: 1rem;
		border-top: 1px solid var(--c-border);
	}

	.user-info {
		margin-bottom: 1rem;
	}

	.user-email {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
		display: block;
		padding: 0.5rem;
		word-break: break-all;
	}

	.logout-btn {
		width: 100%;
		padding: 0.75rem;
		background: transparent;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		font-weight: 600;
		color: var(--c-text-primary);
		transition: all 0.2s;
	}

	.logout-btn:hover {
		background: var(--c-bg-subtle);
	}

	/* Main Content */
	.main-content {
		flex: 1;
		padding: 2rem;
		min-width: 0;
		overflow-x: hidden;
		background: var(--c-bg-subtle);
	}

	h1 {
		font-size: 2rem;
		margin: 0 0 1.5rem 0;
		color: var(--c-text-primary);
	}

	.loading {
		text-align: center;
		padding: 3rem;
		color: var(--c-text-secondary);
	}

	.error-banner {
		padding: 1rem;
		background: var(--c-error-bg);
		color: var(--c-error-dark);
		border: 1px solid var(--c-error-border);
		border-radius: var(--radius-md);
		margin-bottom: 1.5rem;
	}

	/* Dashboard */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	@media (min-width: 1400px) {
		.stats-grid {
			grid-template-columns: repeat(4, 1fr);
		}

		.dashboard-sections {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	.stat-card {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border-radius: var(--radius-lg);
		border: 1px solid var(--c-border);
	}

	.stat-value {
		font-size: 2.5rem;
		font-weight: 700;
		color: var(--c-brand);
		margin-bottom: 0.5rem;
	}

	.stat-label {
		color: var(--c-text-secondary);
		font-size: 0.875rem;
	}

	.dashboard-sections {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.section {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border-radius: var(--radius-lg);
		border: 1px solid var(--c-border);
	}

	.section h3 {
		margin: 0 0 1rem 0;
		font-size: 1.125rem;
		color: var(--c-text-primary);
	}

	.category-list,
	.status-list,
	.actions-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.category-item,
	.status-item,
	.action-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
	}

	.status-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		color: white;
		border-radius: var(--radius-md);
		font-size: 0.8125rem;
		font-weight: 600;
	}

	/* Reports */
	.reports-tab,
	.dashboard-tab,
	.audit-tab,
	.staff-tab {
		width: 100%;
		max-width: 100%;
		overflow-x: hidden;
	}

	.reports-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.export-btn {
		padding: 0.75rem 1.5rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-md);
		font-weight: 600;
		cursor: pointer;
	}

	.filters {
		display: flex;
		gap: 1rem;
		margin-bottom: 1.5rem;
		width: 100%;
		max-width: 100%;
	}

	.search-input {
		flex: 1;
		padding: 0.75rem 1rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		background: var(--c-bg-surface);
	}

	.filters select {
		padding: 0.75rem 1rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		background: var(--c-bg-surface);
	}

	.bulk-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
		padding: 1rem;
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		margin-bottom: 1.5rem;
	}

	.bulk-actions button {
		padding: 0.5rem 1rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-md);
		font-weight: 600;
		cursor: pointer;
		font-size: 0.875rem;
	}

	.table-container {
		background: var(--c-bg-surface);
		border: 1px solid var(--c-border);
		border-radius: var(--radius-lg);
		overflow-x: auto;
		width: 100%;
		max-width: 100%;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		min-width: 800px;
	}

	th,
	td {
		padding: 1rem;
		text-align: left;
		border-bottom: 1px solid var(--c-border);
	}

	th {
		background: var(--c-bg-subtle);
		font-weight: 600;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.report-id {
		font-family: monospace;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.report-title {
		font-weight: 500;
	}

	.severity-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		background: var(--c-bg-subtle);
		border-radius: var(--radius-md);
		font-weight: 600;
		font-size: 0.875rem;
	}

	.severity-badge.high {
		background: var(--c-error-light);
		color: var(--c-error-dark);
	}

	.date {
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.action-btn {
		padding: 0.5rem 1rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		font-weight: 600;
		font-size: 0.875rem;
	}

	.action-btns {
		display: flex;
		gap: 0.5rem;
	}

	.assign-btn {
		background: var(--c-bg-tertiary);
		color: var(--c-text-primary);
		border: 1px solid var(--c-border);
	}

	.assign-btn:hover {
		background: var(--c-bg-hover);
	}

	.view-btn {
		background: transparent;
		color: var(--c-brand);
		border: 1px solid var(--c-brand);
	}

	.view-btn:hover {
		background: var(--c-brand);
		color: var(--c-brand-contrast);
	}

	/* Report Detail Modal */
	.modal-large {
		max-width: 900px;
		width: 95%;
		max-height: 90vh;
		overflow-y: auto;
	}

	.detail-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--c-border);
	}

	.detail-header h2 {
		margin: 0;
		font-size: 1.25rem;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		color: var(--c-text-secondary);
		cursor: pointer;
	}

	.detail-content {
		display: grid;
		grid-template-columns: 1fr 280px;
		gap: 1.5rem;
	}

	@media (max-width: 768px) {
		.detail-content {
			grid-template-columns: 1fr;
		}
	}

	.detail-main {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.image-gallery {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.image-gallery img {
		max-width: 200px;
		max-height: 150px;
		object-fit: cover;
		border-radius: var(--radius-md);
		border: 1px solid var(--c-border);
	}

	.no-images {
		padding: 2rem;
		text-align: center;
		color: var(--c-text-tertiary);
		background: var(--c-bg-tertiary);
		border-radius: var(--radius-md);
	}

	.description-section h3,
	.ai-section h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1rem;
		color: var(--c-text-secondary);
	}

	.ai-section pre {
		background: var(--c-bg-tertiary);
		padding: 1rem;
		border-radius: var(--radius-md);
		overflow-x: auto;
		font-size: 0.75rem;
		max-height: 200px;
	}

	.detail-sidebar {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.meta-card {
		background: var(--c-bg-tertiary);
		padding: 0.75rem;
		border-radius: var(--radius-md);
	}

	.meta-card h4 {
		margin: 0 0 0.25rem 0;
		font-size: 0.75rem;
		color: var(--c-text-tertiary);
		text-transform: uppercase;
	}

	.meta-card span {
		font-size: 0.875rem;
	}

	/* Audit Logs */
	.audit-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.audit-item {
		background: var(--c-bg-surface);
		padding: 1rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
	}

	.audit-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.audit-action {
		font-weight: 600;
		color: var(--c-brand);
	}

	.audit-details {
		display: flex;
		gap: 1rem;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	/* Staff */
	.staff-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.create-admin-btn {
		padding: 0.75rem 1.5rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-md);
		font-weight: 600;
		cursor: pointer;
		font-size: 0.9375rem;
		transition: opacity 0.2s;
	}

	.create-admin-btn:hover {
		opacity: 0.9;
	}

	.staff-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1rem;
	}

	.staff-card {
		background: var(--c-bg-surface);
		padding: 1.5rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-lg);
		transition: all 0.2s;
	}

	.staff-card.inactive {
		opacity: 0.6;
		background: var(--c-bg-subtle);
	}

	.staff-info {
		margin-bottom: 1rem;
	}

	.staff-header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.staff-email {
		font-weight: 600;
		font-size: 0.9375rem;
		word-break: break-word;
	}

	.toggle-status-btn {
		background: transparent;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-sm);
		padding: 0.25rem 0.5rem;
		cursor: pointer;
		font-size: 1rem;
		transition: all 0.2s;
		flex-shrink: 0;
	}

	.toggle-status-btn:hover {
		background: var(--c-bg-subtle);
		border-color: var(--c-brand);
	}

	.staff-role {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border-radius: var(--radius-full);
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: capitalize;
	}

	.staff-role.super {
		background: var(--c-accent);
	}

	.staff-meta {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--c-text-secondary);
	}

	.staff-meta .active {
		color: var(--c-success);
		font-weight: 600;
	}

	.staff-meta .inactive-text {
		color: var(--c-error);
		font-weight: 600;
	}

	.form-group input {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		background: var(--c-bg-subtle);
		font-family: var(--font-sans);
		font-size: 1rem;
	}

	.form-group input:focus {
		outline: none;
		border-color: var(--c-brand);
		background: var(--c-bg-surface);
	}

	/* Modal */
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal {
		background: var(--c-bg-surface);
		padding: 2rem;
		border-radius: var(--radius-lg);
		max-width: 500px;
		width: 90%;
		box-shadow: var(--shadow-xl);
	}

	.modal h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.5rem;
	}

	.report-info {
		color: var(--c-text-secondary);
		margin-bottom: 1.5rem;
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	.form-group label {
		display: block;
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.form-group select,
	.form-group textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		background: var(--c-bg-subtle);
		font-family: var(--font-sans);
	}

	.modal-actions {
		display: flex;
		gap: 1rem;
		justify-content: flex-end;
	}

	.btn-secondary {
		padding: 0.75rem 1.5rem;
		background: transparent;
		border: 1px solid var(--c-border);
		border-radius: var(--radius-md);
		font-weight: 600;
		cursor: pointer;
	}

	.btn-primary {
		padding: 0.75rem 1.5rem;
		background: var(--c-brand);
		color: var(--c-brand-contrast);
		border: none;
		border-radius: var(--radius-md);
		font-weight: 600;
		cursor: pointer;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Responsive Design */
	@media (max-width: 1200px) {
		.dashboard-sections {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 1024px) {
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.table-container {
			overflow-x: auto;
		}

		table {
			min-width: 800px;
		}
	}

	@media (max-width: 768px) {
		.mobile-header {
			display: block;
		}

		.mobile-overlay {
			display: block;
		}

		.sidebar {
			transform: translateX(-100%);
			transition: transform 0.3s ease;
			z-index: 100;
		}

		.sidebar.mobile-open {
			transform: translateX(0);
		}

		.main-content {
			margin-left: 0;
			margin-top: 72px;
			max-width: 100%;
			padding: 1rem;
		}

		.filters {
			flex-direction: column;
		}

		.stats-grid {
			grid-template-columns: 1fr;
		}

		.dashboard-sections {
			grid-template-columns: 1fr;
		}

		.reports-header {
			flex-direction: column;
			align-items: stretch;
		}

		.export-btn {
			width: 100%;
		}

		.bulk-actions {
			flex-direction: column;
			align-items: stretch;
		}

		.bulk-actions button {
			width: 100%;
		}

		h1 {
			font-size: 1.5rem;
		}

		.section h3 {
			font-size: 1rem;
		}

		.staff-list {
			grid-template-columns: 1fr;
		}

		.table-container {
			margin: 0 -1rem;
			border-radius: 0;
			border-left: none;
			border-right: none;
		}
	}

	@media (max-width: 480px) {
		.mobile-title h2 {
			font-size: 1rem;
		}

		.admin-badge {
			font-size: 0.625rem;
			padding: 0.2rem 0.5rem;
		}

		.stat-value {
			font-size: 2rem;
		}

		.main-content {
			padding: 0.75rem;
		}

		h1 {
			font-size: 1.25rem;
			margin-bottom: 1rem;
		}

		.modal {
			width: 95%;
			padding: 1.5rem;
		}

		.modal h2 {
			font-size: 1.25rem;
		}
	}

	.unauthorized-container {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100vh;
		background: var(--c-bg-subtle);
	}

	.unauthorized-card {
		background: var(--c-bg-surface);
		padding: 3rem;
		border-radius: var(--radius-lg);
		text-align: center;
		box-shadow: var(--shadow-xl);
		border: 1px solid var(--c-border);
		color: var(--c-text-primary);
	}

	.unauthorized-card h1 {
		color: #ef4444;
		margin: 1rem 0;
	}

	.lock-icon {
		color: #ef4444;
	}
</style>
