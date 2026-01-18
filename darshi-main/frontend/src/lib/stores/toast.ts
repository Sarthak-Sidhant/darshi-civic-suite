import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	duration?: number;
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	function show(message: string, type: ToastType = 'info', duration: number = 5000) {
		const id = Math.random().toString(36).substring(2, 9);
		const toast: Toast = { id, type, message, duration };

		update((toasts) => [...toasts, toast]);

		if (duration > 0) {
			setTimeout(() => {
				update((toasts) => toasts.filter((t) => t.id !== id));
			}, duration);
		}

		return id;
	}

	return {
		subscribe,
		show,
		dismiss: (id: string) => {
			update((toasts) => toasts.filter((t) => t.id !== id));
		},
		clear: () => {
			update(() => []);
		},
		// Helper methods use the same store's show function
		success: (message: string, duration?: number) => show(message, 'success', duration),
		error: (message: string, duration?: number) => show(message, 'error', duration),
		warning: (message: string, duration?: number) => show(message, 'warning', duration),
		info: (message: string, duration?: number) => show(message, 'info', duration)
	};
}

export const toast = createToastStore();
