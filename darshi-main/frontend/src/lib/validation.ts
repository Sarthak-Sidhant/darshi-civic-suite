export interface ValidationRule {
	validate: (value: string) => boolean;
	message: string;
}

export interface ValidationResult {
	valid: boolean;
	errors: string[];
}

export interface FieldValidation {
	value: string;
	errors: string[];
	touched: boolean;
}

// Validation rules
export const validationRules = {
	required: (message: string = 'This field is required'): ValidationRule => ({
		validate: (value: string) => value.trim().length > 0,
		message
	}),

	minLength: (min: number, message?: string): ValidationRule => ({
		validate: (value: string) => value.length >= min,
		message: message || `Minimum ${min} characters required`
	}),

	maxLength: (max: number, message?: string): ValidationRule => ({
		validate: (value: string) => value.length <= max,
		message: message || `Maximum ${max} characters allowed`
	}),

	email: (message: string = 'Invalid email format'): ValidationRule => ({
		validate: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
		message
	}),

	phone: (message: string = 'Invalid phone number'): ValidationRule => ({
		validate: (value: string) => /^\d{10}$/.test(value.replace(/\D/g, '')),
		message
	}),

	username: (message: string = 'Username must be 3-30 characters, alphanumeric and underscore only'): ValidationRule => ({
		validate: (value: string) => /^[a-zA-Z0-9_]{3,30}$/.test(value),
		message
	}),

	password: (message: string = 'Password must be at least 8 characters with uppercase, lowercase, and number'): ValidationRule => ({
		validate: (value: string) => {
			if (value.length < 8) return false;
			if (!/[A-Z]/.test(value)) return false;
			if (!/[a-z]/.test(value)) return false;
			if (!/[0-9]/.test(value)) return false;
			return true;
		},
		message
	}),

	alphanumeric: (message: string = 'Only letters and numbers allowed'): ValidationRule => ({
		validate: (value: string) => /^[a-zA-Z0-9]+$/.test(value),
		message
	})
};

// Validate a field against multiple rules
export function validateField(value: string, rules: ValidationRule[]): ValidationResult {
	const errors: string[] = [];

	for (const rule of rules) {
		if (!rule.validate(value)) {
			errors.push(rule.message);
		}
	}

	return {
		valid: errors.length === 0,
		errors
	};
}

// Character counter helper
export function getCharacterCount(value: string, max?: number): string {
	if (max) {
		return `${value.length}/${max}`;
	}
	return `${value.length} characters`;
}

// Password strength calculator
export function getPasswordStrength(password: string): { strength: number; label: string; color: string } {
	let strength = 0;

	if (password.length >= 8) strength++;
	if (password.length >= 12) strength++;
	if (/[a-z]/.test(password)) strength++;
	if (/[A-Z]/.test(password)) strength++;
	if (/[0-9]/.test(password)) strength++;
	if (/[^a-zA-Z0-9]/.test(password)) strength++;

	const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
	const colors = ['#dc2626', '#ea580c', '#f59e0b', '#84cc16', '#22c55e', '#10b981'];

	return {
		strength,
		label: labels[Math.min(strength, labels.length - 1)],
		color: colors[Math.min(strength, colors.length - 1)]
	};
}

// Debounce utility
export function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout> | null = null;

	return function executedFunction(...args: Parameters<T>) {
		const later = () => {
			timeout = null;
			func(...args);
		};

		if (timeout !== null) {
			clearTimeout(timeout);
		}
		timeout = setTimeout(later, wait);
	};
}
