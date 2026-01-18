/**
 * Browser Push Notification Utilities
 *
 * Handles push notification subscription and management.
 */

import { api, getErrorMessage, type ApiError } from '$lib/api';
import { toast } from '$lib/stores/toast';

const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY;

/**
 * Check if browser supports push notifications
 */
export function isPushSupported(): boolean {
    return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

/**
 * Convert VAPID public key from base64 to Uint8Array
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

/**
 * Request notification permission from the user
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
        throw new Error('Notifications not supported');
    }

    return await Notification.requestPermission();
}

/**
 * Subscribe to push notifications
 */
export async function subscribeToPush(): Promise<boolean> {
    try {
        // Check support
        if (!isPushSupported()) {
            return false;
        }

        // Check VAPID key
        if (!VAPID_PUBLIC_KEY) {
            toast.show('Push notifications not configured', 'error');
            return false;
        }

        // Request permission
        const permission = await requestNotificationPermission();
        if (permission !== 'granted') {
            return false;
        }

        // Get service worker registration
        const registration = await navigator.serviceWorker.ready;

        // Check if already subscribed
        const existingSubscription = await registration.pushManager.getSubscription();
        if (existingSubscription) {
            // Send subscription to backend (in case it was lost)
            try {
                await api.post('/notifications/push/subscribe', existingSubscription.toJSON());
            } catch (error) {
                // Silently ignore sync errors
            }

            return true;
        }

        // Subscribe to push notifications
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY) as BufferSource
        });

        // Send subscription to backend
        const res = await api.post('/notifications/push/subscribe', subscription.toJSON());

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        toast.show('Push notifications enabled!', 'success');
        return true;

    } catch (error) {
        const errorMsg = getErrorMessage(error as ApiError);
        toast.show(`Failed to enable push notifications: ${errorMsg}`, 'error');
        return false;
    }
}

/**
 * Unsubscribe from push notifications
 */
export async function unsubscribeFromPush(): Promise<boolean> {
    try {
        if (!isPushSupported()) {
            return false;
        }

        // Get service worker registration
        const registration = await navigator.serviceWorker.ready;

        // Get existing subscription
        const subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
            return true;
        }

        // Unsubscribe
        const success = await subscription.unsubscribe();
        if (!success) {
            throw new Error('Failed to unsubscribe');
        }

        // Remove subscription from backend
        try {
            const params = new URLSearchParams({ endpoint: subscription.endpoint });
            const res = await api.delete(`/notifications/push/unsubscribe?${params.toString()}`);

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
        } catch (error) {
            // Silently ignore backend removal errors
        }

        toast.show('Push notifications disabled', 'info');
        return true;

    } catch (error) {
        const errorMsg = getErrorMessage(error as ApiError);
        toast.show(`Failed to disable push notifications: ${errorMsg}`, 'error');
        return false;
    }
}

/**
 * Check if user is currently subscribed to push notifications
 */
export async function isPushSubscribed(): Promise<boolean> {
    try {
        if (!isPushSupported()) {
            return false;
        }

        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();

        return subscription !== null;
    } catch (error) {
        return false;
    }
}

/**
 * Get current push subscription
 */
export async function getPushSubscription(): Promise<PushSubscription | null> {
    try {
        if (!isPushSupported()) {
            return null;
        }

        const registration = await navigator.serviceWorker.ready;
        return await registration.pushManager.getSubscription();
    } catch (error) {
        return null;
    }
}
