/**
 * Unit tests for validation utilities
 */

import { describe, it, expect } from 'vitest';
import {
	validationRules,
	validateField,
	getCharacterCount,
	getPasswordStrength,
	debounce
} from './validation';

describe('Validation Rules', () => {
	describe('required', () => {
		it('should fail for empty string', () => {
			const rule = validationRules.required();
			expect(rule.validate('')).toBe(false);
		});

		it('should fail for whitespace only', () => {
			const rule = validationRules.required();
			expect(rule.validate('   ')).toBe(false);
		});

		it('should pass for non-empty string', () => {
			const rule = validationRules.required();
			expect(rule.validate('hello')).toBe(true);
		});

		it('should use custom message', () => {
			const rule = validationRules.required('Custom message');
			expect(rule.message).toBe('Custom message');
		});
	});

	describe('minLength', () => {
		it('should fail for string shorter than minimum', () => {
			const rule = validationRules.minLength(5);
			expect(rule.validate('abc')).toBe(false);
		});

		it('should pass for string at minimum length', () => {
			const rule = validationRules.minLength(5);
			expect(rule.validate('abcde')).toBe(true);
		});

		it('should pass for string longer than minimum', () => {
			const rule = validationRules.minLength(5);
			expect(rule.validate('abcdefgh')).toBe(true);
		});
	});

	describe('maxLength', () => {
		it('should fail for string longer than maximum', () => {
			const rule = validationRules.maxLength(5);
			expect(rule.validate('abcdefgh')).toBe(false);
		});

		it('should pass for string at maximum length', () => {
			const rule = validationRules.maxLength(5);
			expect(rule.validate('abcde')).toBe(true);
		});

		it('should pass for string shorter than maximum', () => {
			const rule = validationRules.maxLength(5);
			expect(rule.validate('abc')).toBe(true);
		});
	});

	describe('email', () => {
		it('should pass for valid email', () => {
			const rule = validationRules.email();
			expect(rule.validate('test@example.com')).toBe(true);
			expect(rule.validate('user.name@domain.co.in')).toBe(true);
			expect(rule.validate('user+tag@example.org')).toBe(true);
		});

		it('should fail for invalid email', () => {
			const rule = validationRules.email();
			expect(rule.validate('')).toBe(false);
			expect(rule.validate('invalid-email')).toBe(false);
			expect(rule.validate('@nodomain.com')).toBe(false);
			expect(rule.validate('noemail@')).toBe(false);
			expect(rule.validate('spaces in@email.com')).toBe(false);
		});
	});

	describe('phone', () => {
		it('should pass for valid 10-digit phone', () => {
			const rule = validationRules.phone();
			expect(rule.validate('9876543210')).toBe(true);
			expect(rule.validate('987-654-3210')).toBe(true);
			expect(rule.validate('(987) 654-3210')).toBe(true);
		});

		it('should fail for invalid phone', () => {
			const rule = validationRules.phone();
			expect(rule.validate('123')).toBe(false);
			expect(rule.validate('12345678901234')).toBe(false);
		});
	});

	describe('username', () => {
		it('should pass for valid username', () => {
			const rule = validationRules.username();
			expect(rule.validate('abc')).toBe(true);
			expect(rule.validate('user123')).toBe(true);
			expect(rule.validate('test_user')).toBe(true);
			expect(rule.validate('a'.repeat(30))).toBe(true);
		});

		it('should fail for invalid username', () => {
			const rule = validationRules.username();
			expect(rule.validate('')).toBe(false);
			expect(rule.validate('ab')).toBe(false); // Too short
			expect(rule.validate('a'.repeat(31))).toBe(false); // Too long
			expect(rule.validate('user@name')).toBe(false); // Invalid character
			expect(rule.validate('user name')).toBe(false); // Space
		});
	});

	describe('password', () => {
		it('should pass for valid password', () => {
			const rule = validationRules.password();
			expect(rule.validate('Password1')).toBe(true);
			expect(rule.validate('SecurePass123')).toBe(true);
			expect(rule.validate('MyP@ssw0rd!')).toBe(true);
		});

		it('should fail for password without uppercase', () => {
			const rule = validationRules.password();
			expect(rule.validate('password1')).toBe(false);
		});

		it('should fail for password without lowercase', () => {
			const rule = validationRules.password();
			expect(rule.validate('PASSWORD1')).toBe(false);
		});

		it('should fail for password without number', () => {
			const rule = validationRules.password();
			expect(rule.validate('PasswordABC')).toBe(false);
		});

		it('should fail for password too short', () => {
			const rule = validationRules.password();
			expect(rule.validate('Pass1')).toBe(false);
		});
	});

	describe('alphanumeric', () => {
		it('should pass for alphanumeric string', () => {
			const rule = validationRules.alphanumeric();
			expect(rule.validate('abc123')).toBe(true);
			expect(rule.validate('ABC')).toBe(true);
			expect(rule.validate('123')).toBe(true);
		});

		it('should fail for non-alphanumeric string', () => {
			const rule = validationRules.alphanumeric();
			expect(rule.validate('abc_123')).toBe(false);
			expect(rule.validate('abc 123')).toBe(false);
			expect(rule.validate('abc@123')).toBe(false);
		});
	});
});

describe('validateField', () => {
	it('should return valid for passing all rules', () => {
		const result = validateField('test@example.com', [
			validationRules.required(),
			validationRules.email()
		]);
		expect(result.valid).toBe(true);
		expect(result.errors).toHaveLength(0);
	});

	it('should return invalid with errors for failing rules', () => {
		const result = validateField('', [
			validationRules.required('Required'),
			validationRules.email('Invalid email')
		]);
		expect(result.valid).toBe(false);
		expect(result.errors).toContain('Required');
	});

	it('should collect all errors', () => {
		const result = validateField('ab', [
			validationRules.minLength(5, 'Too short'),
			validationRules.email('Invalid email')
		]);
		expect(result.valid).toBe(false);
		expect(result.errors).toHaveLength(2);
	});
});

describe('getCharacterCount', () => {
	it('should return count with max', () => {
		expect(getCharacterCount('hello', 10)).toBe('5/10');
	});

	it('should return count without max', () => {
		expect(getCharacterCount('hello')).toBe('5 characters');
	});

	it('should handle empty string', () => {
		expect(getCharacterCount('', 100)).toBe('0/100');
	});
});

describe('getPasswordStrength', () => {
	it('should return Very Weak for empty password', () => {
		const result = getPasswordStrength('');
		expect(result.strength).toBe(0);
		expect(result.label).toBe('Very Weak');
	});

	it('should increase strength for length', () => {
		const short = getPasswordStrength('abc');
		const medium = getPasswordStrength('abcdefgh');
		const long = getPasswordStrength('abcdefghijkl');
		expect(medium.strength).toBeGreaterThan(short.strength);
		expect(long.strength).toBeGreaterThan(medium.strength);
	});

	it('should increase strength for character variety', () => {
		const lowercase = getPasswordStrength('abcdefgh');
		const mixed = getPasswordStrength('Abcdefgh');
		const withNumber = getPasswordStrength('Abcdefg1');
		const withSpecial = getPasswordStrength('Abcdefg1!');

		expect(mixed.strength).toBeGreaterThan(lowercase.strength);
		expect(withNumber.strength).toBeGreaterThan(mixed.strength);
		expect(withSpecial.strength).toBeGreaterThan(withNumber.strength);
	});

	it('should return appropriate labels', () => {
		const veryStrong = getPasswordStrength('MyP@ssw0rd123!');
		expect(['Strong', 'Very Strong']).toContain(veryStrong.label);
	});

	it('should return color codes', () => {
		const result = getPasswordStrength('Password1');
		expect(result.color).toMatch(/^#[0-9a-f]{6}$/i);
	});
});

describe('debounce', () => {
	it('should delay function execution', async () => {
		let counter = 0;
		const increment = () => {
			counter++;
		};
		const debouncedIncrement = debounce(increment, 100);

		debouncedIncrement();
		debouncedIncrement();
		debouncedIncrement();

		expect(counter).toBe(0);

		await new Promise((resolve) => setTimeout(resolve, 150));

		expect(counter).toBe(1);
	});

	it('should reset timer on subsequent calls', async () => {
		let counter = 0;
		const increment = () => {
			counter++;
		};
		const debouncedIncrement = debounce(increment, 100);

		debouncedIncrement();
		await new Promise((resolve) => setTimeout(resolve, 50));
		debouncedIncrement();
		await new Promise((resolve) => setTimeout(resolve, 50));
		debouncedIncrement();

		expect(counter).toBe(0);

		await new Promise((resolve) => setTimeout(resolve, 150));

		expect(counter).toBe(1);
	});
});
