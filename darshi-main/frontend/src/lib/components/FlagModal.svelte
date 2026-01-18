<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { fade, scale } from "svelte/transition";
    import {
        Flag,
        X,
        Send,
        AlertTriangle,
        Image as ImageIcon,
    } from "lucide-svelte";
    import { api } from "$lib/api";
    import { toast } from "$lib/stores/toast";

    export let reportId: string;
    export let updateId: string | null = null;
    export let isOpen = false;

    const dispatch = createEventDispatcher();

    let reason = "";
    let flagType = "fake_report";
    let submitting = false;
    let imageUrl = ""; // Future: Implement image upload if needed

    const flagTypes = [
        { value: "fake_report", label: "Fake Report" },
        { value: "inappropriate", label: "Inappropriate Content" },
        { value: "spam", label: "Spam / Duplicate" },
        { value: "request_update", label: "Request Update" },
        { value: "other", label: "Other" },
    ];

    async function handleSubmit() {
        if (!reason && flagType === "other") {
            toast.error("Please provide a reason");
            return;
        }

        submitting = true;
        try {
            if (updateId) {
                await api.post(`/updates/${updateId}/flag`, { reason });
            } else {
                await api.post(`/reports/${reportId}/flag`, {
                    flag_type: flagType,
                    reason,
                    image_url: imageUrl || null,
                });
            }

            toast.success("Flag submitted for review");
            dispatch("success");
            close();
        } catch (e: any) {
            toast.error(e.message || "Failed to submit flag");
        } finally {
            submitting = false;
        }
    }

    function close() {
        isOpen = false;
        reason = "";
        flagType = "fake_report";
        dispatch("close");
    }
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
                    <Flag class="w-5 h-5 text-red-500" />
                    Flag {updateId ? "Update" : "Report"}
                </h2>
                <button class="btn-close" onclick={close}>
                    <X size={20} />
                </button>
            </header>

            <div class="modal-body">
                <div class="info-box">
                    <AlertTriangle size={16} />
                    <p>
                        Flags are reviewed by moderators. False flagging may
                        lead to account restrictions.
                    </p>
                </div>

                {#if !updateId}
                    <div class="form-group">
                        <label for="flag-type">Reason</label>
                        <div class="radio-group">
                            {#each flagTypes as type}
                                <label
                                    class="radio-item"
                                    class:selected={flagType === type.value}
                                >
                                    <input
                                        type="radio"
                                        name="flagType"
                                        value={type.value}
                                        bind:group={flagType}
                                    />
                                    <span>{type.label}</span>
                                </label>
                            {/each}
                        </div>
                    </div>
                {/if}

                <div class="form-group">
                    <label for="reason">Additional Details</label>
                    <textarea
                        id="reason"
                        bind:value={reason}
                        placeholder="Please provide more context..."
                        rows="3"
                    ></textarea>
                </div>
            </div>

            <footer class="modal-footer">
                <button class="btn-cancel" onclick={close}>Cancel</button>
                <button
                    class="btn-submit"
                    onclick={handleSubmit}
                    disabled={submitting}
                >
                    {#if submitting}
                        Sending...
                    {:else}
                        <Flag size={16} />
                        Submit Flag
                    {/if}
                </button>
            </footer>
        </div>
    </div>
{/if}

<style>
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(4px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 1rem;
    }

    .modal-content {
        background: var(--c-bg-surface);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-lg);
        width: 100%;
        max-width: 450px;
        display: flex;
        flex-direction: column;
        box-shadow:
            0 20px 25px -5px rgba(0, 0, 0, 0.1),
            0 10px 10px -5px rgba(0, 0, 0, 0.04);
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
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .info-box {
        display: flex;
        gap: 0.75rem;
        padding: 0.75rem;
        background: var(--c-bg-subtle);
        border-radius: var(--radius-sm);
        color: var(--c-text-secondary);
        font-size: 0.8125rem;
        line-height: 1.5;
    }

    .form-group label {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--c-text-secondary);
        margin-bottom: 0.5rem;
    }

    .radio-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .radio-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.625rem;
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        cursor: pointer;
        transition: all 0.2s;
    }

    .radio-item:hover {
        background: var(--c-bg-subtle);
    }

    .radio-item.selected {
        border-color: var(--c-error);
        background: var(--c-error-light);
        color: var(--c-error-dark);
    }

    .radio-item input {
        accent-color: var(--c-error);
    }

    textarea {
        width: 100%;
        padding: 0.75rem;
        background: var(--c-bg-subtle);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-sm);
        color: var(--c-text-primary);
        font-size: 0.9375rem;
        resize: vertical;
    }

    textarea:focus {
        outline: none;
        border-color: var(--c-error);
    }

    .modal-footer {
        padding: 1.25rem;
        border-top: 1px solid var(--c-border);
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-cancel {
        padding: 0.625rem 1rem;
        background: transparent;
        border: 1px solid var(--c-border);
        color: var(--c-text-secondary);
        border-radius: var(--radius-sm);
        font-weight: 500;
        cursor: pointer;
    }

    .btn-submit {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1rem;
        background: var(--c-error);
        color: white;
        border: none;
        border-radius: var(--radius-sm);
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-submit:hover:not(:disabled) {
        opacity: 0.9;
    }

    .btn-submit:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    /* Colors needed if not defined globally yet */
    :global(:root) {
        --c-error-light: rgba(239, 68, 68, 0.1);
        --c-error-dark: #b91c1c;
    }
</style>
