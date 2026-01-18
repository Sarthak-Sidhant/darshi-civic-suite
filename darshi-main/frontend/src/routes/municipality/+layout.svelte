<script lang="ts">
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import {
        LayoutDashboard,
        Radio,
        BarChart2,
        LogOut,
        Menu,
        X,
    } from "lucide-svelte";
    import { user } from "$lib/stores";
    import { goto } from "$app/navigation";

    let { children } = $props();

    let currentPath = $state("");
    let mobileMenuOpen = $state(false);

    $effect(() => {
        currentPath = $page.url.pathname;
    });

    const navItems = [
        { name: "Operations", path: "/municipality", icon: LayoutDashboard },
        { name: "Alert Hub", path: "/municipality/alerts", icon: Radio },
        { name: "Analytics", path: "/municipality/analytics", icon: BarChart2 },
    ];

    function handleLogout() {
        goto("/");
    }
</script>

<div class="municipality-layout">
    <!-- Sidebar -->
    <aside class="sidebar" class:mobile-open={mobileMenuOpen}>
        <div class="sidebar-header">
            <h1 class="logo">MuniCommand</h1>
            <p class="logo-subtitle">Municipality Dashboard</p>
        </div>

        <nav class="sidebar-nav">
            {#each navItems as item}
                {@const Icon = item.icon}
                <a
                    href={item.path}
                    class="nav-item"
                    class:active={currentPath === item.path}
                    onclick={() => (mobileMenuOpen = false)}
                >
                    <Icon size={20} />
                    <span>{item.name}</span>
                </a>
            {/each}
        </nav>

        <div class="sidebar-footer">
            <div class="user-info">
                <div class="user-avatar">
                    {$user?.username?.charAt(0).toUpperCase() || "M"}
                </div>
                <div class="user-details">
                    <p class="user-name">
                        {$user?.username || "Municipality Officer"}
                    </p>
                    <p class="user-role">{$user?.role || "Admin"}</p>
                </div>
            </div>
            <button class="logout-btn" onclick={handleLogout}>
                <LogOut size={18} />
            </button>
        </div>
    </aside>

    <!-- Mobile Header -->
    <header class="mobile-header">
        <button
            class="menu-toggle"
            onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
        >
            {#if mobileMenuOpen}
                <X size={24} />
            {:else}
                <Menu size={24} />
            {/if}
        </button>
        <h1 class="mobile-title">MuniCommand</h1>
    </header>

    <!-- Mobile Overlay -->
    {#if mobileMenuOpen}
        <div
            class="mobile-overlay"
            onclick={() => (mobileMenuOpen = false)}
        ></div>
    {/if}

    <!-- Main Content -->
    <main class="main-content">
        {@render children()}
    </main>
</div>

<style>
    .municipality-layout {
        display: flex;
        min-height: 100vh;
        background: var(--c-bg-page);
    }

    /* Sidebar */
    .sidebar {
        width: 260px;
        background: var(--c-bg-surface);
        border-right: 1px solid var(--c-border);
        display: flex;
        flex-direction: column;
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        z-index: 100;
    }

    .sidebar-header {
        padding: 1.5rem;
        border-bottom: 1px solid var(--c-border);
    }

    .logo {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--c-brand);
        margin: 0;
    }

    .logo-subtitle {
        font-size: 0.75rem;
        color: var(--c-text-secondary);
        margin: 0.25rem 0 0 0;
    }

    .sidebar-nav {
        flex: 1;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .nav-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        border-radius: var(--radius-md);
        color: var(--c-text-secondary);
        text-decoration: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .nav-item:hover {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
    }

    .nav-item.active {
        background: var(--c-brand);
        color: var(--c-brand-contrast);
    }

    .sidebar-footer {
        padding: 1rem;
        border-top: 1px solid var(--c-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 1;
        min-width: 0;
    }

    .user-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: var(--c-brand);
        color: var(--c-brand-contrast);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        flex-shrink: 0;
    }

    .user-details {
        min-width: 0;
    }

    .user-name {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--c-text-primary);
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .user-role {
        font-size: 0.75rem;
        color: var(--c-text-secondary);
        margin: 0;
        text-transform: capitalize;
    }

    .logout-btn {
        padding: 0.5rem;
        background: transparent;
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-secondary);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .logout-btn:hover {
        background: var(--c-error-bg);
        border-color: var(--c-error);
        color: var(--c-error);
    }

    /* Mobile Header */
    .mobile-header {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background: var(--c-bg-surface);
        border-bottom: 1px solid var(--c-border);
        padding: 0 1rem;
        align-items: center;
        gap: 1rem;
        z-index: 90;
    }

    .menu-toggle {
        padding: 0.5rem;
        background: transparent;
        border: none;
        color: var(--c-text-primary);
        cursor: pointer;
    }

    .mobile-title {
        font-family: var(--font-display);
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--c-brand);
        margin: 0;
    }

    .mobile-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 99;
    }

    /* Main Content */
    .main-content {
        flex: 1;
        margin-left: 260px;
        min-height: 100vh;
    }

    /* Responsive */
    @media (max-width: 1024px) {
        .sidebar {
            transform: translateX(-100%);
            transition: transform 0.3s ease;
        }

        .sidebar.mobile-open {
            transform: translateX(0);
        }

        .mobile-header {
            display: flex;
        }

        .mobile-overlay {
            display: block;
        }

        .main-content {
            margin-left: 0;
            padding-top: 60px;
        }
    }
</style>
