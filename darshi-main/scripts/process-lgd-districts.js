const fs = require('fs');
const data = JSON.parse(fs.readFileSync('lgd-districts.json', 'utf8'));

// Extract unique states and all districts
const states = new Map();
const districts = [];

data.records.forEach(r => {
    // Add state if not exists
    if (!states.has(r.state_code)) {
        states.set(r.state_code, {
            code: r.state_code,
            name: r.state_name_english.trim(),
            nameLocal: r.state_name_local ? r.state_name_local.trim() : ''
        });
    }

    // Add district
    districts.push({
        stateCode: r.state_code,
        code: r.district_code,
        name: r.district_name_english.trim(),
        nameLocal: r.district_name_local ? r.district_name_local.trim() : ''
    });
});

// Sort states alphabetically
const statesArray = Array.from(states.values()).sort((a, b) => a.name.localeCompare(b.name));

// Sort districts alphabetically within each state
districts.sort((a, b) => {
    if (a.stateCode !== b.stateCode) return a.stateCode - b.stateCode;
    return a.name.localeCompare(b.name);
});

const output = {
    states: statesArray,
    districts: districts
};

// Ensure directory exists
fs.mkdirSync('frontend/static/data', { recursive: true });
fs.writeFileSync('frontend/static/data/districts.json', JSON.stringify(output));

console.log('Created districts.json with', statesArray.length, 'states and', districts.length, 'districts');
