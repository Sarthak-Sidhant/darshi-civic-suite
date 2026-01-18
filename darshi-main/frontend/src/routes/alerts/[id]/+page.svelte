<script lang="ts">
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import {
        MapPin,
        Clock,
        TrendingUp,
        MessageCircle,
        Send,
        Image as ImageIcon,
    } from "lucide-svelte";
    import { api, getCurrentUser } from "$lib/api";
    import { toast } from "$lib/stores/toast";

    const alertId = $derived($page.params.id);

    let alert = $state<any>(null);
    let comments = $state<any[]>([]);
    let updates = $state<any[]>([]);
    let loading = $state(true);
    let commentText = $state("");
    let currentUser = $state<any>(null);
    let hasUpvoted = $state(false);

    onMount(async () => {
        currentUser = getCurrentUser();
        await loadAlert();
        await loadComments();
        await loadUpdates();
    });

    async function loadAlert() {
        try {
            const res = await api.get(`/alerts/${alertId}`);
            alert = await res.json();
        } catch (e) {
            toast.show("Alert not found", "error");
            goto("/alerts");
        } finally {
            loading = false;
        }
    }

    async function loadComments() {
        try {
            const res = await api.get(`/alerts/${alertId}/comments`);
            comments = await res.json();
        } catch (e) {
            console.error("Failed to load comments", e);
        }
    }

    async function loadUpdates() {
        try {
            const res = await api.get(`/alerts/${alertId}/updates`);
            updates = await res.json();
        } catch (e) {
            console.error("Failed to load updates", e);
        }
    }

    async function handleUpvote() {
        if (!currentUser) {
            toast.show("Sign in to upvote", "info");
            goto("/signin");
            return;
        }

        try {
            const res = await api.post(`/alerts/${alertId}/upvote`, {});
            const data = await res.json();
            hasUpvoted = data.status === "upvoted";
            if (alert) alert.upvote_count = data.count;
            toast.show(hasUpvoted ? "Upvoted!" : "Upvote removed", "success");
        } catch (e: any) {
            toast.show("Failed to upvote", "error");
        }
    }

    async function handleComment() {
        if (!currentUser) {
            toast.show("Sign in to comment", "info");
            goto("/signin");
            return;
        }

        if (!commentText.trim()) return;

        try {
            const formData = new FormData();
            formData.append("text", commentText);

            // Use native fetch with FormData - api.post converts to JSON
            const token = localStorage.getItem("auth_token");
            const baseUrl =
                import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1";
            const res = await fetch(`${baseUrl}/alerts/${alertId}/comment`, {
                method: "POST",
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                body: formData,
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(
                    error.detail || error.message || "Failed to add comment",
                );
            }

            const newComment = await res.json();
            comments = [newComment, ...comments];
            commentText = "";
            toast.show("Comment added", "success");
        } catch (e: any) {
            toast.show(e.message || "Failed to add comment", "error");
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
</script>

<svelte:head>
    <title>{alert?.title || "Alert"} - Darshi</title>
</svelte:head>

<div class="min-h-screen bg-[var(--c-bg-primary)]">
    {#if loading}
        <div class="flex justify-center items-center min-h-screen">
            <div
                class="animate-spin w-8 h-8 border-2 border-[var(--c-primary)] border-t-transparent rounded-full"
            ></div>
        </div>
    {:else if alert}
        <div class="max-w-4xl mx-auto px-4 py-8">
            <!-- Back Button -->
            <a
                href="/alerts"
                class="inline-flex items-center gap-2 text-[var(--c-text-secondary)] hover:text-[var(--c-text-primary)] mb-6"
            >
                ← Back to Alerts
            </a>

            <!-- Alert Header -->
            <div
                class="bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg p-6 mb-6"
            >
                <div class="flex items-start justify-between gap-4 mb-4">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-2">
                            {#if alert.is_official}
                                <span
                                    class="px-3 py-1 bg-blue-500/10 text-blue-400 text-sm font-bold rounded"
                                >
                                    ✓ OFFICIAL
                                </span>
                            {:else if alert.verified_by}
                                <span
                                    class="px-3 py-1 bg-green-500/10 text-green-400 text-sm font-bold rounded"
                                >
                                    ✓ VERIFIED
                                </span>
                            {/if}
                            <span
                                class="px-3 py-1 {getSeverityColor(
                                    alert.severity,
                                )} text-sm font-bold rounded uppercase"
                            >
                                {alert.severity}
                            </span>
                            <span
                                class="px-3 py-1 bg-[var(--c-bg-subtle)] text-[var(--c-text-secondary)] text-sm rounded"
                            >
                                {alert.status}
                            </span>
                        </div>
                        <h1
                            class="text-3xl font-bold text-[var(--c-text-primary)] mb-2"
                        >
                            {alert.title}
                        </h1>
                        <p class="text-[var(--c-text-secondary)]">
                            {alert.description}
                        </p>
                    </div>

                    {#if !alert.is_official}
                        <button
                            onclick={handleUpvote}
                            class="flex flex-col items-center gap-1 px-4 py-2 bg-[var(--c-bg-subtle)] hover:bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg transition"
                        >
                            <TrendingUp
                                size={20}
                                class={hasUpvoted
                                    ? "text-[var(--c-primary)]"
                                    : "text-[var(--c-text-secondary)]"}
                            />
                            <span
                                class="text-sm font-bold text-[var(--c-text-primary)]"
                                >{alert.upvote_count || 0}</span
                            >
                        </button>
                    {/if}
                </div>

                <!-- Image -->
                {#if alert.image_url}
                    <img
                        src={alert.image_url}
                        alt={alert.title}
                        class="w-full h-96 object-cover rounded-lg mb-4"
                    />
                {/if}

                <!-- Meta Info -->
                <div
                    class="flex flex-wrap items-center gap-4 text-sm text-[var(--c-text-tertiary)]"
                >
                    <span class="flex items-center gap-1">
                        <Clock size={16} />
                        {getTimeRemaining(alert.expires_at)}
                    </span>
                    <span class="flex items-center gap-1">
                        <MapPin size={16} />
                        {alert.address ||
                            `${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}`}
                    </span>
                    <span>
                        Radius: {alert.radius_km}km
                    </span>
                    <span>
                        {alert.view_count || 0} views
                    </span>
                </div>
            </div>

            <!-- Updates Section -->
            {#if updates.length > 0}
                <div
                    class="bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg p-6 mb-6"
                >
                    <h2
                        class="text-xl font-bold text-[var(--c-text-primary)] mb-4"
                    >
                        Updates
                    </h2>
                    <div class="space-y-4">
                        {#each updates as update}
                            <div
                                class="border-l-2 border-[var(--c-primary)] pl-4"
                            >
                                <div class="flex items-center gap-2 mb-1">
                                    <span
                                        class="font-medium text-[var(--c-text-primary)]"
                                        >{update.author_username}</span
                                    >
                                    <span
                                        class="text-xs text-[var(--c-text-tertiary)]"
                                    >
                                        {new Date(
                                            update.created_at,
                                        ).toLocaleString()}
                                    </span>
                                </div>
                                <p class="text-[var(--c-text-secondary)]">
                                    {update.content}
                                </p>
                                {#if update.image_url}
                                    <img
                                        src={update.image_url}
                                        alt="Update"
                                        class="mt-2 w-full max-w-md rounded-lg"
                                    />
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            <!-- Comments Section -->
            <div
                class="bg-[var(--c-bg-surface)] border border-[var(--c-border)] rounded-lg p-6"
            >
                <h2
                    class="text-xl font-bold text-[var(--c-text-primary)] mb-4 flex items-center gap-2"
                >
                    <MessageCircle size={20} />
                    Comments ({comments.length})
                </h2>

                <!-- Add Comment -->
                {#if alert.status === "ACTIVE"}
                    <div class="mb-6">
                        <textarea
                            bind:value={commentText}
                            placeholder="Add a comment..."
                            class="w-full px-4 py-3 bg-[var(--c-bg-subtle)] border border-[var(--c-border)] rounded-lg text-[var(--c-text-primary)] placeholder-[var(--c-text-tertiary)] resize-none focus:outline-none focus:border-[var(--c-primary)]"
                            rows="3"
                        ></textarea>
                        <button
                            onclick={handleComment}
                            disabled={!commentText.trim()}
                            class="mt-2 flex items-center gap-2 px-4 py-2 bg-[var(--c-primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                            <Send size={16} />
                            Post Comment
                        </button>
                    </div>
                {/if}

                <!-- Comments List -->
                <div class="space-y-4">
                    {#if comments.length === 0}
                        <p
                            class="text-center text-[var(--c-text-tertiary)] py-8"
                        >
                            No comments yet. Be the first to comment!
                        </p>
                    {:else}
                        {#each comments as comment}
                            <div
                                class="border-b border-[var(--c-border)] pb-4 last:border-0"
                            >
                                <div class="flex items-center gap-2 mb-2">
                                    <span
                                        class="font-medium text-[var(--c-text-primary)]"
                                        >{comment.username}</span
                                    >
                                    <span
                                        class="text-xs text-[var(--c-text-tertiary)]"
                                    >
                                        {new Date(
                                            comment.created_at,
                                        ).toLocaleString()}
                                    </span>
                                </div>
                                <p class="text-[var(--c-text-secondary)]">
                                    {comment.text}
                                </p>
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>
