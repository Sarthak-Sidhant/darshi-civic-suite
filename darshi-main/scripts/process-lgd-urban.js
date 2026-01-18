const fs = require('fs');
const data = JSON.parse(fs.readFileSync('lgd-urban.json', 'utf8'));

// Extract unique urban bodies (dedupe by localBodyCode)
const urbanBodies = new Map();

data.records.forEach(r => {
    // Use localBodyCode as unique key (same body can have multiple pincodes)
    if (!urbanBodies.has(r.localBodyCode)) {
        urbanBodies.set(r.localBodyCode, {
            stateCode: r.stateCode,
            stateName: r.stateNameEnglish,
            code: r.localBodyCode,
            name: r.localBodyNameEnglish,
            type: r.localBodyTypeName,
            pincodes: [r.pincode]
        });
    } else {
        // Add pincode if new
        const existing = urbanBodies.get(r.localBodyCode);
        if (!existing.pincodes.includes(r.pincode)) {
            existing.pincodes.push(r.pincode);
        }
    }
});

// Convert to array and sort by state then name
const urbanArray = Array.from(urbanBodies.values()).sort((a, b) => {
    if (a.stateCode !== b.stateCode) return a.stateCode - b.stateCode;
    return a.name.localeCompare(b.name);
});

// Group by state for easier lookup
const byState = {};
urbanArray.forEach(ub => {
    if (!byState[ub.stateCode]) {
        byState[ub.stateCode] = [];
    }
    byState[ub.stateCode].push({
        code: ub.code,
        name: ub.name,
        type: ub.type
    });
});

// Ensure directory exists
fs.mkdirSync('frontend/static/data', { recursive: true });
fs.writeFileSync('frontend/static/data/urban-bodies.json', JSON.stringify(byState));

console.log('Created urban-bodies.json with', urbanArray.length, 'unique urban bodies across', Object.keys(byState).length, 'states');
