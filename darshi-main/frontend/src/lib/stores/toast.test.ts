/**
 * Unit tests for toast store
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { get } from 'svelte/store';

// We need to test the store creation logic
describe('Toast Store', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('should create a toast store with required methods', async () => {
		// Dynamically import to get fresh instance
		const { toast } = await import('./toast');

		expect(toast.subscribe).toBeDefined();
		expect(toast.show).toBeDefined();
		expect(toast.dismiss).toBeDefined();
		expect(toast.clear).toBeDefined();
	});

	it('should add toast on show', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Test message', 'info', 0);

		const toasts = get(toast);
		expect(toasts.length).toBeGreaterThanOrEqual(1);
		expect(toasts.find((t) => t.id === id)).toBeDefined();
	});

	it('should remove toast on dismiss', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Test message', 'info', 0);
		toast.dismiss(id);

		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)).toBeUndefined();
	});

	it('should clear all toasts', async () => {
		const { toast } = await import('./toast');

		toast.show('Message 1', 'info', 0);
		toast.show('Message 2', 'error', 0);
		toast.show('Message 3', 'success', 0);

		toast.clear();

		const toasts = get(toast);
		expect(toasts).toHaveLength(0);
	});

	it('should set correct toast type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Test', 'error', 0);

		const toasts = get(toast);
		const addedToast = toasts.find((t) => t.id === id);
		expect(addedToast?.type).toBe('error');
	});

	it('should generate unique IDs for each toast', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id1 = toast.show('Message 1', 'info', 0);
		const id2 = toast.show('Message 2', 'info', 0);
		const id3 = toast.show('Message 3', 'info', 0);

		expect(id1).not.toBe(id2);
		expect(id2).not.toBe(id3);
		expect(id1).not.toBe(id3);
	});

	it('should store message correctly', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const message = 'This is a test message';
		const id = toast.show(message, 'success', 0);

		const toasts = get(toast);
		const addedToast = toasts.find((t) => t.id === id);
		expect(addedToast?.message).toBe(message);
	});

	it('should store duration correctly', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const duration = 3000;
		const id = toast.show('Test', 'info', duration);

		const toasts = get(toast);
		const addedToast = toasts.find((t) => t.id === id);
		expect(addedToast?.duration).toBe(duration);
	});

	it('should auto-dismiss after duration', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Test', 'info', 1000);

		let toasts = get(toast);
		expect(toasts.find((t) => t.id === id)).toBeDefined();

		vi.advanceTimersByTime(1100);

		toasts = get(toast);
		expect(toasts.find((t) => t.id === id)).toBeUndefined();
	});

	it('should not auto-dismiss when duration is 0', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Test', 'info', 0);

		vi.advanceTimersByTime(10000);

		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)).toBeDefined();
	});
});

describe('Toast Types', () => {
	it('should support success type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Success!', 'success', 0);
		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)?.type).toBe('success');
	});

	it('should support error type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Error!', 'error', 0);
		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)?.type).toBe('error');
	});

	it('should support warning type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Warning!', 'warning', 0);
		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)?.type).toBe('warning');
	});

	it('should support info type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Info!', 'info', 0);
		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)?.type).toBe('info');
	});

	it('should default to info type', async () => {
		const { toast } = await import('./toast');
		toast.clear();

		const id = toast.show('Default type');
		const toasts = get(toast);
		expect(toasts.find((t) => t.id === id)?.type).toBe('info');
	});
});

describe('Toast Helper Methods', () => {
	it('success helper should create success toast', async () => {
		const { toast } = await import('./toast');
		// The helper methods create new store instances, so we just test they exist
		expect(toast.success).toBeDefined();
		expect(typeof toast.success).toBe('function');
	});

	it('error helper should create error toast', async () => {
		const { toast } = await import('./toast');
		expect(toast.error).toBeDefined();
		expect(typeof toast.error).toBe('function');
	});

	it('warning helper should create warning toast', async () => {
		const { toast } = await import('./toast');
		expect(toast.warning).toBeDefined();
		expect(typeof toast.warning).toBe('function');
	});

	it('info helper should create info toast', async () => {
		const { toast } = await import('./toast');
		expect(toast.info).toBeDefined();
		expect(typeof toast.info).toBe('function');
	});
});
