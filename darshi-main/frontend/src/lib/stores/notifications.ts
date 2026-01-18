/**
 * Notification Store
 *
 * Manages in-app notifications with polling for updates.
 * Provides reactive state for notification list and unread count.
 */

import { writable } from 'svelte/store';
import { api, getErrorMessage, type ApiError } from '$lib/api';
import { toast } from './toast';

export interface Notification {
    id: string;
    user_id: string;
    type: 'report_status_change' | 'new_comment' | 'admin_action' | 'upvote_milestone';
    title: string;
    message: string;
    read: boolean;
    created_at: string;
    report_id?: string;
    comment_id?: string;
    actor?: string;
    push_sent: boolean;
    push_sent_at?: string;
}

interface NotificationResponse {
    notifications: Notification[];
    unread_count: number;
}

function createNotificationStore() {
    const { subscribe, set, update } = writable<Notification[]>([]);
    const unreadCount = writable<number>(0);
    let pollInterval: number | null = null;

    return {
        subscribe,
        unreadCount: { subscribe: unreadCount.subscribe },

        /**
         * Fetch notifications from the API
         */
        async fetch(unreadOnly: boolean = false): Promise<void> {
            try {
                const params = new URLSearchParams();
                if (unreadOnly) {
                    params.append('unread_only', 'true');
                }
                params.append('limit', '50');

                const res = await api.get(`/notifications?${params.toString()}`);
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }

                const response: NotificationResponse = await res.json();

                set(response.notifications);
                unreadCount.set(response.unread_count);
            } catch (error) {
                // Don't show toast for polling errors to avoid spam
            }
        },

        /**
         * Mark a single notification as read
         */
        async markAsRead(notificationId: string): Promise<void> {
            // Optimistic update
            update(notifications =>
                notifications.map(n =>
                    n.id === notificationId ? { ...n, read: true } : n
                )
            );
            unreadCount.update(count => Math.max(0, count - 1));

            try {
                const res = await api.put(`/notifications/${notificationId}/read`, {});
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }
            } catch (error) {
                toast.show('Failed to mark notification as read', 'error');

                // Revert optimistic update
                await this.fetch();
            }
        },

        /**
         * Mark all notifications as read
         */
        async markAllAsRead(): Promise<void> {
            // Optimistic update
            update(notifications =>
                notifications.map(n => ({ ...n, read: true }))
            );
            unreadCount.set(0);

            try {
                const res = await api.put('/notifications/read-all', {});
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }
                const response: { marked_read: number } = await res.json();
                toast.show(`${response.marked_read} notifications marked as read`, 'success');
            } catch (error) {
                toast.show('Failed to mark all as read', 'error');

                // Revert optimistic update
                await this.fetch();
            }
        },

        /**
         * Delete a notification
         */
        async delete(notificationId: string): Promise<void> {
            // Optimistic update
            update(notifications =>
                notifications.filter(n => n.id !== notificationId)
            );

            try {
                const res = await api.delete(`/notifications/${notificationId}`);
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                }
            } catch (error) {
                toast.show('Failed to delete notification', 'error');

                // Revert optimistic update
                await this.fetch();
            }
        },

        /**
         * Start polling for new notifications
         * @param intervalMs - Polling interval in milliseconds (default: 30000 = 30s)
         */
        startPolling(intervalMs: number = 30000): void {
            if (pollInterval !== null) {
                return; // Already polling
            }

            // Initial fetch
            this.fetch();

            // Poll every N seconds
            pollInterval = window.setInterval(() => {
                this.fetch();
            }, intervalMs);
        },

        /**
         * Stop polling for notifications
         */
        stopPolling(): void {
            if (pollInterval !== null) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        },

        /**
         * Clear all notifications from store (on logout)
         */
        clear(): void {
            set([]);
            unreadCount.set(0);
            this.stopPolling();
        }
    };
}

export const notifications = createNotificationStore();
