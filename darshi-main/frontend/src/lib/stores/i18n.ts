import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type Language = 'en' | 'hi';

// Translation keys with English and Hindi
export const translations = {
	en: {
		// Navigation
		home: 'Home',
		submit: 'Submit Report',
		map: 'Map View',
		profile: 'Profile',
		signin: 'Sign In',
		signout: 'Sign Out',
		register: 'Register',

		// Home page
		holdCityAccountable: 'Hold Your City Accountable',
		reportCivicIssues: 'Report civic issues. potholes, broken streetlights, waste management, whatever you want. and track their resolution.',
		learnMore: 'Learn more about Darshi',
		submitReport: 'Submit Report',
		noReportsYet: 'No Reports Yet',
		beFirstToReport: 'Be the first to report a civic issue in your area',
		reportIssue: 'Report Issue',

		// Report statuses
		pendingVerification: 'Pending Verification',
		verified: 'Verified',
		inProgress: 'In Progress',
		resolved: 'Resolved',
		rejected: 'Rejected',
		duplicate: 'Duplicate',
		flagged: 'Flagged',

		// Report categories
		pothole: 'Pothole',
		streetlight: 'Streetlight',
		garbage: 'Garbage',
		drainage: 'Drainage',
		water: 'Water Supply',
		electricity: 'Electricity',
		road: 'Road Damage',
		other: 'Other',

		// Actions
		upvote: 'Upvote',
		comment: 'Comment',
		share: 'Share',
		edit: 'Edit',
		delete: 'Delete',
		save: 'Save',
		cancel: 'Cancel',
		loading: 'Loading',

		// Forms
		title: 'Title',
		description: 'Description',
		location: 'Location',
		uploadImages: 'Upload Images',
		required: 'Required',

		// Messages
		signInToUpvote: 'Please sign in to upvote',
		signInToComment: 'Please sign in to comment',
		reportCreated: 'Report created successfully!',
		reportUpdated: 'Report updated successfully',
		reportDeleted: 'Report deleted successfully',
		copiedToClipboard: 'Link copied to clipboard!',
		errorOccurred: 'An error occurred',

		// Auth
		username: 'Username',
		email: 'Email',
		password: 'Password',
		confirmPassword: 'Confirm Password',
		forgotPassword: 'Forgot Password?',
		dontHaveAccount: "Don't have an account?",
		alreadyHaveAccount: 'Already have an account?',
		createAccount: 'Create Account',
		welcomeBack: 'Welcome Back',
		createYourAccount: 'Create Your Account',
	},
	hi: {
		// Navigation
		home: 'होम',
		submit: 'रिपोर्ट सबमिट करें',
		map: 'मैप व्यू',
		profile: 'प्रोफ़ाइल',
		signin: 'साइन इन',
		signout: 'साइन आउट',
		register: 'रजिस्टर',

		// Home page
		holdCityAccountable: 'अपने शहर को जवाबदेह बनाएं',
		reportCivicIssues: 'नागरिक समस्याओं की रिपोर्ट करें। गड्ढे, टूटी हुई स्ट्रीट लाइट, कचरा प्रबंधन, जो चाहें। और उनके समाधान को ट्रैक करें।',
		learnMore: 'दर्शी के बारे में और जानें',
		submitReport: 'रिपोर्ट सबमिट करें',
		noReportsYet: 'अभी तक कोई रिपोर्ट नहीं',
		beFirstToReport: 'अपने क्षेत्र में नागरिक समस्या की रिपोर्ट करने वाले पहले व्यक्ति बनें',
		reportIssue: 'समस्या रिपोर्ट करें',

		// Report statuses
		pendingVerification: 'सत्यापन लंबित',
		verified: 'सत्यापित',
		inProgress: 'प्रगति में',
		resolved: 'हल हो गया',
		rejected: 'अस्वीकृत',
		duplicate: 'डुप्लीकेट',
		flagged: 'फ्लैग किया गया',

		// Report categories
		pothole: 'गड्ढा',
		streetlight: 'स्ट्रीट लाइट',
		garbage: 'कचरा',
		drainage: 'नाली',
		water: 'पानी की आपूर्ति',
		electricity: 'बिजली',
		road: 'सड़क क्षति',
		other: 'अन्य',

		// Actions
		upvote: 'अपवोट',
		comment: 'टिप्पणी',
		share: 'शेयर',
		edit: 'संपादित करें',
		delete: 'हटाएं',
		save: 'सेव करें',
		cancel: 'रद्द करें',
		loading: 'लोड हो रहा है',

		// Forms
		title: 'शीर्षक',
		description: 'विवरण',
		location: 'स्थान',
		uploadImages: 'फ़ोटो अपलोड करें',
		required: 'आवश्यक',

		// Messages
		signInToUpvote: 'अपवोट करने के लिए कृपया साइन इन करें',
		signInToComment: 'टिप्पणी करने के लिए कृपया साइन इन करें',
		reportCreated: 'रिपोर्ट सफलतापूर्वक बनाई गई!',
		reportUpdated: 'रिपोर्ट सफलतापूर्वक अपडेट की गई',
		reportDeleted: 'रिपोर्ट सफलतापूर्वक हटाई गई',
		copiedToClipboard: 'लिंक क्लिपबोर्ड पर कॉपी किया गया!',
		errorOccurred: 'एक त्रुटि हुई',

		// Auth
		username: 'यूज़रनेम',
		email: 'ईमेल',
		password: 'पासवर्ड',
		confirmPassword: 'पासवर्ड की पुष्टि करें',
		forgotPassword: 'पासवर्ड भूल गए?',
		dontHaveAccount: 'खाता नहीं है?',
		alreadyHaveAccount: 'पहले से खाता है?',
		createAccount: 'खाता बनाएं',
		welcomeBack: 'वापसी पर स्वागत है',
		createYourAccount: 'अपना खाता बनाएं',
	}
};

// Get initial language from localStorage or default to English
function getInitialLanguage(): Language {
	if (!browser) return 'en';
	const stored = localStorage.getItem('language');
	return (stored === 'hi' ? 'hi' : 'en') as Language;
}

// Create language store
const initialLanguage = getInitialLanguage();
export const language = writable<Language>(initialLanguage);

// Subscribe to changes and persist to localStorage (client-side only)
if (browser) {
	// Apply initial language immediately
	document.documentElement.lang = initialLanguage;

	// Subscribe to future changes
	language.subscribe(lang => {
		localStorage.setItem('language', lang);
		document.documentElement.lang = lang;
	});
}

// Helper function to get translation
export function t(key: keyof typeof translations.en, lang: Language): string {
	return translations[lang][key] || translations.en[key] || key;
}

// Create derived store for current translations
export const currentTranslations = {
	subscribe: (callback: (value: Record<string, string>) => void) => {
		return language.subscribe(lang => {
			callback(translations[lang]);
		});
	}
};
