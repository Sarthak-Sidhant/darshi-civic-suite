// LGD Data utilities for working with districts and urban bodies

export interface State {
    code: number;
    name: string;
    nameLocal: string;
}

export interface District {
    stateCode: number;
    code: number;
    name: string;
    nameLocal: string;
}

export interface UrbanBody {
    code: number;
    name: string;
    type: string;
}

export interface LGDData {
    states: State[];
    districts: District[];
}

// Cache for loaded data
let lgdDataCache: LGDData | null = null;
let urbanBodiesCache: Record<number, UrbanBody[]> | null = null;

/**
 * Load and cache districts data
 */
export async function loadLGDData(): Promise<LGDData> {
    if (lgdDataCache) return lgdDataCache;

    try {
        const response = await fetch('/data/districts.json');
        lgdDataCache = await response.json();
        return lgdDataCache!;
    } catch (e) {
        console.error('Failed to load LGD data:', e);
        return { states: [], districts: [] };
    }
}

/**
 * Load and cache urban bodies data
 */
export async function loadUrbanBodies(): Promise<Record<number, UrbanBody[]>> {
    if (urbanBodiesCache) return urbanBodiesCache;

    try {
        const response = await fetch('/data/urban-bodies.json');
        urbanBodiesCache = await response.json();
        return urbanBodiesCache!;
    } catch (e) {
        console.error('Failed to load urban bodies data:', e);
        return {};
    }
}

/**
 * Get all states sorted alphabetically
 */
export async function getStates(): Promise<State[]> {
    const data = await loadLGDData();
    return data.states;
}

/**
 * Get districts for a specific state
 */
export async function getDistrictsForState(stateCode: number): Promise<District[]> {
    const data = await loadLGDData();
    return data.districts.filter(d => d.stateCode === stateCode);
}

/**
 * Get urban bodies for a specific state
 */
export async function getUrbanBodiesForState(stateCode: number): Promise<UrbanBody[]> {
    const data = await loadUrbanBodies();
    return data[stateCode] || [];
}

/**
 * Find urban bodies that match a district name (fuzzy match)
 * Since urban bodies don't have district codes, we match by name
 */
export async function getUrbanBodiesForDistrict(
    districtName: string,
    stateCode: number
): Promise<UrbanBody[]> {
    const urbanBodies = await getUrbanBodiesForState(stateCode);
    const normalizedDistrict = districtName.toLowerCase().trim();

    // Filter urban bodies whose name contains the district name
    // or whose district-like name matches
    return urbanBodies.filter(ub => {
        const normalizedName = ub.name.toLowerCase();

        // Direct match
        if (normalizedName.includes(normalizedDistrict)) return true;

        // Check if district name is part of urban body name
        // e.g., "Ranchi" should match "Ranchi Municipal Corporation"
        const nameParts = normalizedName.split(/[\s-]+/);
        if (nameParts.some(part => part === normalizedDistrict)) return true;

        // Check if urban body name is part of district
        // e.g., "Ranchi" urban body matches "Ranchi" district
        const districtParts = normalizedDistrict.split(/[\s-]+/);
        if (districtParts.some(part => normalizedName.startsWith(part))) return true;

        return false;
    });
}

/**
 * Get the primary urban body for a district (highest tier)
 * Priority: Municipal Corporation > Municipality > City Municipal Council > Others
 */
export async function getPrimaryUrbanBody(
    districtName: string,
    stateCode: number
): Promise<UrbanBody | null> {
    const urbanBodies = await getUrbanBodiesForDistrict(districtName, stateCode);

    if (urbanBodies.length === 0) return null;

    // Sort by priority (Municipal Corporation first)
    const priorityOrder = [
        'Municipal Corporations',
        'Municipality',
        'City Municipal Council',
        'Notified Area Council',
        'Town Panchayat'
    ];

    urbanBodies.sort((a, b) => {
        const aIndex = priorityOrder.findIndex(p => a.type.includes(p));
        const bIndex = priorityOrder.findIndex(p => b.type.includes(p));

        // -1 means not found, put at end
        const aPriority = aIndex === -1 ? 999 : aIndex;
        const bPriority = bIndex === -1 ? 999 : bIndex;

        return aPriority - bPriority;
    });

    return urbanBodies[0];
}

/**
 * Find a state by name (case-insensitive)
 */
export async function findStateByName(name: string): Promise<State | null> {
    const data = await loadLGDData();
    const normalizedName = name.toLowerCase().trim();

    return data.states.find(s =>
        s.name.toLowerCase() === normalizedName ||
        s.nameLocal.toLowerCase() === normalizedName
    ) || null;
}

/**
 * Find a district by name within a state (case-insensitive)
 */
export async function findDistrictByName(
    name: string,
    stateCode: number
): Promise<District | null> {
    const districts = await getDistrictsForState(stateCode);
    const normalizedName = name.toLowerCase().trim();

    return districts.find(d =>
        d.name.toLowerCase() === normalizedName ||
        d.nameLocal.toLowerCase() === normalizedName
    ) || null;
}
