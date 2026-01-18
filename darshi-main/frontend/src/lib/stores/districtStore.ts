// District selection store with localStorage persistence
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export interface SelectedDistrict {
    stateCode: number;
    stateName: string;
    districtCode: number;
    districtName: string;
}

const STORAGE_KEY = 'selected_district';

function createDistrictStore() {
    // Load from localStorage if available
    let initial: SelectedDistrict | null = null;

    if (browser) {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                initial = JSON.parse(stored);
            }
        } catch (e) {
            console.error('Failed to load district from localStorage:', e);
        }
    }

    const { subscribe, set, update } = writable<SelectedDistrict | null>(initial);

    return {
        subscribe,

        select: (district: SelectedDistrict) => {
            set(district);
            if (browser) {
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(district));
                } catch (e) {
                    console.error('Failed to save district to localStorage:', e);
                }
            }
        },

        clear: () => {
            set(null);
            if (browser) {
                try {
                    localStorage.removeItem(STORAGE_KEY);
                } catch (e) {
                    console.error('Failed to clear district from localStorage:', e);
                }
            }
        },

        // Check if a district is selected
        isSelected: (): boolean => {
            if (!browser) return false;
            return localStorage.getItem(STORAGE_KEY) !== null;
        }
    };
}

export const selectedDistrict = createDistrictStore();
