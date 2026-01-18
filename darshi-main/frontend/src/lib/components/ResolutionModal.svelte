<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import LoadingButton from "$lib/components/LoadingButton.svelte";
    import { X } from "lucide-svelte";

    export let open = false;
    export let submitting = false;

    let summary = "";
    let imageUrl = ""; // Future: Upload

    const dispatch = createEventDispatcher();

    function close() {
        dispatch("close");
        summary = "";
    }

    function submit() {
        if (!summary.trim()) return;
        dispatch("submit", { summary, imageUrl });
    }
</script>

{#if open}
    <div class="modal-backdrop" onclick={close} role="dialog" aria-modal="true">
        <div class="modal" onclick={(e) => e.stopPropagation()}>
            <div class="modal-header">
                <h2>Resolve Report</h2>
                <button class="close-btn" onclick={close} aria-label="Close">
                    <X size={24} />
                </button>
            </div>

            <p class="description">
                Please provide details about how this issue was resolved. This
                information will be visible to the public.
            </p>

            <div class="form-group">
                <label for="resolution-summary">Resolution Details</label>
                <textarea
                    id="resolution-summary"
                    bind:value={summary}
                    placeholder="E.g. The pothole was filled and resurfaced..."
                    rows="4"
                ></textarea>
            </div>

            <!-- Placeholder for Image Upload -->
            <!-- 
            <div class="form-group">
                <label>Proof Image (Optional)</label>
                <input type="text" bind:value={imageUrl} placeholder="https://..." />
            </div>
            -->

            <div class="modal-actions">
                <button class="btn-secondary" onclick={close}>Cancel</button>
                <LoadingButton
                    loading={submitting}
                    onclick={submit}
                    disabled={!summary.trim()}
                    variant="primary"
                >
                    Mark as Resolved
                </LoadingButton>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 50;
        padding: 1rem;
        backdrop-filter: blur(4px);
    }

    .modal {
        background: var(--c-bg-surface);
        border-radius: var(--radius-lg);
        width: 100%;
        max-width: 500px;
        padding: 1.5rem;
        box-shadow: var(--shadow-xl);
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .modal-header h2 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
    }

    .close-btn {
        background: none;
        border: none;
        padding: 0.25rem;
        cursor: pointer;
        color: var(--c-text-secondary);
        border-radius: var(--radius-sm);
    }

    .close-btn:hover {
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
    }

    .description {
        color: var(--c-text-secondary);
        margin-bottom: 1.5rem;
        font-size: 0.9375rem;
    }

    .form-group {
        margin-bottom: 1.5rem;
    }

    .form-group label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 0.875rem;
    }

    textarea {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        background: var(--c-bg-surface);
        color: var(--c-text-primary);
        font-family: inherit;
        resize: vertical;
    }

    textarea:focus {
        outline: none;
        border-color: var(--c-brand);
        box-shadow: 0 0 0 2px var(--c-brand-light);
    }

    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-secondary {
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        font-weight: 600;
        background: var(--c-bg-subtle);
        color: var(--c-text-primary);
        border: 1px solid var(--c-border);
        cursor: pointer;
    }

    .btn-secondary:hover {
        background: var(--c-border);
    }
</style>
