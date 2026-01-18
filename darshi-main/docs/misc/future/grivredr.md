# Grivredr - AI-Powered Web Scraper Factory

> Automated Government Portal Integration for Grievance Filing

**Part of: Darshi Civic Suite**

This document outlines the integration and architecture of Grivredr, an intelligent system that automatically generates web scrapers for government grievance portals.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture Overview](#architecture-overview)
5. [Key Components](#key-components)
6. [The Discovery Process](#the-discovery-process)
7. [The Validation & Self-Healing Loop](#the-validation--self-healing-loop)
8. [Pattern Learning System](#pattern-learning-system)
9. [Directory Structure](#directory-structure)
10. [CLI Commands](#cli-commands)
11. [Cost Tracking](#cost-tracking)
12. [Integration with Darshi](#integration-with-darshi)
13. [Migration Path](#migration-path)
14. [Challenges & Mitigations](#challenges--mitigations)

---

## Executive Summary

**Problem:** Indian government portals for grievance registration are diverse, complex, and frequently changing. Writing and maintaining scrapers manually is time-consuming and brittle.

**Solution:** Grivredr uses AI (Claude with computer use) to automatically:
1. **Discover** form structures
2. **Generate** working scraper code
3. **Validate** that scrapers work correctly
4. **Self-heal** when portals change
5. **Learn** from successful patterns

**Value Proposition:** Reduce portal integration time from 10-20 hours to ~5 minutes, with self-healing capabilities that adapt to portal changes and continuous learning that improves over time.

---

## Problem Statement

### The Challenge

Indian government portals for grievance registration have several challenges:

#### 1. Diverse Technologies
```
Portal Technologies:
├─ React-based (Ant-Design components)
├─ jQuery-based (Select2 dropdowns)
├─ ASP.NET WebForms
├─ Plain HTML forms
├─ Angular/Vue applications
└─ Custom JavaScript frameworks
```

#### 2. Complex Dropdowns
```
Cascading Dependencies:
State → District → Block → Village
Zone → Ward → Locality
Category → Subcategory → Issue Type
```

#### 3. Dynamic Content
- Fields appear/disappear based on selections
- Options loaded via AJAX
- Multi-step forms
- File uploads with specific requirements

#### 4. No APIs
- Most portals only have web forms
- No programmatic access
- Must interact through browser

#### 5. Frequent Changes
- Portal UI updated without notice
- Existing scrapers break
- Constant maintenance required

### Traditional Approach (Painful)

```
For each portal:
1. Manually inspect form (2-4 hours)
   - Identify all fields
   - Note all dropdown options
   - Understand cascading logic
   - Document required fields

2. Write Playwright/Selenium code (4-8 hours)
   - Handle each field type
   - Implement cascade logic
   - Add error handling
   - Handle file uploads

3. Handle edge cases (2-4 hours)
   - Timeout issues
   - Dynamic content loading
   - Validation errors
   - Popup dialogs

4. Test and debug (2-4 hours)
   - Test with various inputs
   - Fix discovered issues
   - Verify submission success

5. Maintain when portal changes (ongoing)
   - Monitor for breakage
   - Update selectors
   - Retest everything

Total: 10-20 hours per portal
```

### Grivredr Approach (Automated)

```
For each portal:
1. Run: grivredr discover --url <url> --portal <name>
2. AI discovers form structure (~2 minutes)
3. AI generates scraper code (~30 seconds)
4. Validate and auto-fix if needed (~2 minutes)

Total: ~5 minutes per portal, ~$0.30-0.70 in AI costs

Bonus: Each successful scraper teaches the system,
       making future portals faster and more accurate.
```

---

## Solution Overview

### Automated Scraper Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        GRIVREDR PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

     ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
     │          │      │          │      │          │      │          │
     │ DISCOVER │ ──── │ GENERATE │ ──── │ VALIDATE │ ──── │  IMPROVE │
     │          │      │          │      │          │      │          │
     └──────────┘      └──────────┘      └──────────┘      └──────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
    │  Form    │      │ Scraper  │      │  Test    │      │ Working  │
    │ Structure│      │   Code   │      │ Results  │      │ Scraper  │
    └──────────┘      └──────────┘      └──────────┘      └──────────┘
                                                                 │
                                                                 ▼
                                                           ┌──────────┐
                                                           │  LEARN   │
                                                           │ Pattern  │
                                                           └──────────┘
```

### Step-by-Step

1. **Discovery Phase**
   - Open portal URL in headless browser
   - AI analyzes form structure (uses Playwright tools)
   - Extract all fields, dropdowns, options
   - Identify cascading relationships
   - Detect UI framework

2. **Generation Phase**
   - Use discovered structure to generate Python code
   - Apply framework-specific patterns from library
   - Include all dropdown option values
   - Handle cascading dependencies

3. **Validation Phase**
   - Run generated scraper with test data
   - Take screenshots to verify correctness
   - Use AI vision to check for errors

4. **Self-Healing Phase** (if needed)
   - Capture runtime errors
   - AI analyzes error + screenshot
   - Generate targeted fix
   - Apply fix and retry

5. **Learning Phase**
   - Store successful patterns in library
   - Update framework-specific templates
   - Improve future code generation

---

## Architecture Overview

### System Components

```
grivredr/
│
├── agents/                      # AI Agents (the brains)
│   ├── hybrid_form_discovery.py # Main discovery agent
│   ├── scraper_validator.py     # Validation + self-healing
│   ├── continuous_improvement_agent.py  # Iterative improvement
│   ├── code_generator_agent.py  # Code generation
│   └── base_agent.py            # Base class with cost tracking
│
├── cli/                         # Command-line interfaces
│   ├── factory_cli.py           # Main CLI (discover, validate, etc.)
│   └── fill_cli.py              # Form filling CLI
│
├── knowledge/                   # Pattern library & templates
│   ├── pattern_library.py       # Store successful patterns
│   ├── code_templates.py        # Reusable code snippets
│   └── framework_detector.py    # Detect UI frameworks
│
├── utils/                       # Utilities
│   ├── portal_manager.py        # Manage portal data
│   ├── code_extraction.py       # Extract code from AI responses
│   ├── constants.py             # Configuration constants
│   └── tracking.py              # Extract tracking IDs
│
├── scrapers/                    # Generated scrapers (output)
│   ├── mcd_delhi/
│   └── ranchi_smart/
│
├── portals/                     # Unified portal data structure
│   └── {state}/{district}/{portal}/
│       ├── scraper.py           # Generated scraper
│       ├── structure.json       # Form structure
│       ├── context/             # Dropdown context
│       │   ├── dropdowns.json   # All dropdown options
│       │   ├── cascades.json    # Cascade relationships
│       │   └── field_mappings.json
│       └── metadata.json        # Training metadata
│
└── config/                      # Configuration
    └── ai_client.py             # AI client setup
```

---

## Key Components

### 1. Hybrid Form Discovery Agent

The main discovery engine that combines AI intelligence with browser automation.

```python
class HybridFormDiscovery:
    """
    AI orchestrates, Playwright executes.

    The AI calls tools like:
    - get_all_form_fields()      # Get field overview
    - get_dropdown_options()     # Extract dropdown values
    - select_dropdown_option()   # Test cascading
    - complete_discovery()       # Finish with full structure
    """

    async def discover_form(self, url: str) -> dict:
        """
        Main discovery method.
        Returns complete form structure with all dropdown options.
        """
        # 1. Navigate to URL
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        # 2. Let AI discover structure
        discovery_result = await self._run_ai_discovery()

        # 3. Parse and validate result
        form_structure = self._parse_discovery_result(discovery_result)

        return form_structure
```

**Key Features:**
- Handles both Ant-Design and Select2 dropdowns
- Automatically detects UI framework
- Captures ALL dropdown options
- Identifies cascade relationships

### 2. Scraper Validator

Self-healing validation loop that tests and fixes generated scrapers.

```python
class ScraperValidator:
    """
    Validates generated scrapers and fixes issues.
    """

    async def validate_scraper(
        self,
        scraper_path: str,
        max_attempts: int = 3
    ) -> dict:
        """
        Run scraper, check for errors, fix if needed.
        """
        for attempt in range(1, max_attempts + 1):
            # Run scraper
            result = await self._run_scraper(scraper_path)

            if result.success:
                # Store successful pattern
                await self._store_pattern(scraper_path)
                return {"status": "success", "attempt": attempt}

            # AI analyzes error
            fix = await self._generate_fix(result.error, result.screenshot)

            # Apply fix
            await self._apply_fix(scraper_path, fix)

        return {"status": "failed", "attempts": max_attempts}
```

### 3. Pattern Library

Stores successful patterns for reuse across similar portals.

```python
class PatternLibrary:
    """
    Store and retrieve successful scraper patterns.
    """

    def store_pattern(
        self,
        portal_url: str,
        form_schema: dict,
        generated_code: str,
        confidence: float
    ):
        """
        Store a successful pattern.

        Args:
            portal_url: Source portal URL
            form_schema: Discovered form structure
            generated_code: Working scraper code
            confidence: Success rate (0.0-1.0)
        """
        # Extract code snippets (dropdown handlers, cascade logic)
        snippets = self._extract_code_snippets(generated_code)

        # Store in SQLite + vector DB (optional)
        self.db.insert({
            'url': portal_url,
            'framework': form_schema['ui_framework'],
            'field_types': form_schema['field_types'],
            'code': generated_code,
            'snippets': snippets,
            'confidence': confidence,
            'created_at': datetime.now()
        })

    def get_similar_patterns(self, form_schema: dict) -> list:
        """
        Find patterns similar to given form schema.

        Returns: List of similar patterns, sorted by similarity score.
        """
        # Match by:
        # 1. UI framework (exact match)
        # 2. Field types (overlap)
        # 3. Cascade patterns (structural similarity)

        patterns = self.db.query(
            framework=form_schema['ui_framework']
        ).order_by('confidence DESC').limit(5)

        return patterns
```

### 4. Code Templates

Proven, tested code snippets for common patterns.

```python
# Ant-Design dropdown handler (tested on MCD Delhi)
ANT_DESIGN_SEARCHABLE_SELECT = """
async def _fill_searchable_select(self, selector, value, field_name):
    \"\"\"Fill Ant-Design searchable select dropdown.\"\"\"
    element = self.page.locator(selector)
    wrapper = element.locator("xpath=ancestor::div[contains(@class,'ant-select')]").first

    # Click to open dropdown
    await wrapper.click(force=True)
    await asyncio.sleep(0.8)

    # Type to search
    search_input = self.page.locator(".ant-select-selection-search-input").first
    await search_input.fill(value)
    await asyncio.sleep(0.5)

    # Click matching option
    option = self.page.locator(f".ant-select-item-option >> text={value}").first
    await option.click()
    await asyncio.sleep(0.5)

    self.logger.info(f"Selected '{value}' in {field_name}")
\"\"\"

# Select2 dropdown handler (tested on Smart Ranchi)
SELECT2_DROPDOWN = """
async def _fill_select2_dropdown(self, selector, value, field_name):
    \"\"\"Fill jQuery Select2 dropdown.\"\"\"
    # Open dropdown
    await self.page.click(f"{selector} + .select2-container")
    await asyncio.sleep(0.5)

    # Search for value
    search = self.page.locator(".select2-search__field").first
    await search.fill(value)
    await asyncio.sleep(0.5)

    # Select option
    option = self.page.locator(f".select2-results__option >> text={value}").first
    await option.click()
    await asyncio.sleep(0.3)

    self.logger.info(f"Selected '{value}' in {field_name}")
\"\"\"

# Cascade handler template
CASCADE_HANDLER = """
async def _handle_cascade(self, parent_selector, child_selector, parent_value, child_value):
    \"\"\"Handle cascading dropdown (parent triggers child options).\"\"\"
    # Fill parent
    await self._fill_dropdown(parent_selector, parent_value)

    # Wait for child to load
    await asyncio.sleep(1.0)

    # Verify child has options
    child_options = await self._get_dropdown_options(child_selector)
    if not child_options or child_value not in child_options:
        raise ValueError(f"Child value '{child_value}' not available after selecting parent")

    # Fill child
    await self._fill_dropdown(child_selector, child_value)
\"\"\"
```

---

## The Discovery Process

### What Happens During Discovery

```bash
grivredr discover \
    --url "https://smartranchi.in/Portal/View/ComplaintRegistration.aspx" \
    --portal ranchi_smart \
    --state jharkhand \
    --district ranchi
```

### Detailed Breakdown

#### Step 1: Page Load
```
[1] Loading page...
    - Open headless Chromium browser
    - Navigate to URL
    - Wait for network idle (all requests complete)
    - Wait 2 seconds for JS to initialize
```

#### Step 2: AI Analysis
```
[2] AI analyzing form with Playwright tools...

    AI Call 1: get_all_form_fields()
    → Returns: All form fields with types, selectors, labels

    AI Call 2: get_dropdown_options("#problem_dropdown")
    → Returns: ["Water Supply", "Drainage", "Road", ...]

    AI Call 3: get_dropdown_options("#ward_dropdown")
    → Returns: ["Ward 1", "Ward 2", ..., "Ward 55"]

    AI Call 4: select_dropdown_option("#zone", "Central Zone")
    → Selects option to test cascading

    AI Call 5: get_dropdown_options("#ward_dropdown")
    → Returns: Ward options for Central Zone (cascade loaded)

    ... continues until all dropdowns explored ...

    AI Call N: complete_discovery(full_structure)
    → AI provides complete form structure with all options
```

#### Step 3: Context Saved
```
[3] Saving context...

    portals/jharkhand/ranchi/ranchi_smart/
    ├── context/
    │   ├── dropdowns.json     # All dropdown options with values
    │   ├── cascades.json      # Cascade relationships
    │   └── field_mappings.json
    ├── structure.json         # Full form structure
    └── metadata.json          # Training cost, timestamp
```

#### Step 4: Code Generation (with Pattern Learning)
```
[4] Generating scraper code...

    - AI receives form structure + dropdown context
    - Detects UI framework: Select2
    - Queries pattern library for similar forms
    - Finds: 3 successful Select2 patterns
    - Uses proven Select2 template (95% confidence)
    - Generates complete Python class
    - Saves to scrapers/ranchi_smart/ranchi_smart_scraper.py
```

---

## The Validation & Self-Healing Loop

### Why Validation Matters

Generated code might have issues:
- Selector slightly wrong
- Need more wait time
- Framework-specific quirk not handled
- Cascade timing issue

### The Self-Healing Process

```bash
grivredr validate \
    --scraper scrapers/ranchi_smart/ranchi_smart_scraper.py \
    --state jharkhand --district ranchi --portal ranchi_smart \
    --max-attempts 3
```

### Validation Loop

```
┌─────────────────────────────────────────────────────────┐
│                  VALIDATION LOOP                         │
└─────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │   RUN    │────▶│  ERROR?  │────▶│   FIX    │
  │ SCRAPER  │     │          │     │   CODE   │
  └──────────┘     └──────────┘     └──────────┘
       ▲                │                │
       │                │ No             │
       │                ▼                │
       │           ┌──────────┐          │
       │           │ SUCCESS! │          │
       │           └────┬─────┘          │
       │                │                │
       │                ▼                │
       │           ┌──────────┐          │
       │           │  STORE   │          │
       │           │ PATTERN  │          │
       │           └──────────┘          │
       │                                 │
       └─────────────────────────────────┘
              (retry with fixed code)
```

---

## Pattern Learning System

Grivredr automatically learns from successful scrapers to improve future generations.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    PATTERN LEARNING LOOP                         │
└─────────────────────────────────────────────────────────────────┘

     ┌──────────┐      ┌──────────┐      ┌──────────┐
     │ DISCOVER │ ──── │ VALIDATE │ ──── │  STORE   │
     │  PORTAL  │      │ SCRAPER  │      │ PATTERN  │
     └──────────┘      └──────────┘      └──────────┘
          ▲                                    │
          │                                    ▼
     ┌──────────┐                        ┌──────────┐
     │   USE    │ ◄───────────────────── │ PATTERN  │
     │ PATTERNS │                        │ LIBRARY  │
     └──────────┘                        └──────────┘
```

### What Gets Learned

1. **Code Snippets**: Working dropdown handlers, cascade patterns, validation triggers
2. **UI Framework Detection**: Ant-Design, Select2, ASP.NET, Bootstrap patterns
3. **Timing Patterns**: How long to wait for cascading dropdowns
4. **Success Rates**: Which patterns work best for which form types

### Pattern Library Components

**`knowledge/pattern_library.py`**:
- SQLite storage for patterns
- Optional vector search for semantic similarity
- Code snippet extraction from working scrapers
- Confidence scoring based on validation success

**`knowledge/code_templates.py`**:
- Proven, tested code for each UI framework
- Ant-Design searchable select handler
- Select2 jQuery dropdown handler
- ASP.NET WebForms patterns
- Cascade handling templates

### Usage in Code Generation

When generating a new scraper:

1. **Detect UI Framework**: Is this Ant-Design? Select2? ASP.NET?
2. **Find Similar Patterns**: Search library for forms with similar field types
3. **Inject Proven Templates**: Use tested code instead of AI guessing
4. **Generate with Context**: AI knows what patterns work

**Example:**
```python
# Code generation with pattern learning
async def generate_scraper(form_structure: dict) -> str:
    # 1. Detect framework
    framework = detect_framework(form_structure)

    # 2. Find similar patterns
    similar = pattern_library.get_similar_patterns(form_structure)

    # 3. Build prompt with proven patterns
    prompt = f"""
    Generate scraper for {framework} form.

    Similar portals that worked:
    {format_patterns(similar)}

    Use these proven code snippets:
    {get_templates_for_framework(framework)}

    Form structure:
    {json.dumps(form_structure)}
    """

    # 4. AI generates with pattern context
    code = await gemini.generate(prompt)
    return code
```

### CLI Commands for Patterns

```bash
# Show pattern library statistics
grivredr patterns

# View patterns found similar to a new form
grivredr detect --url "https://portal.example.com"

# Manually add a pattern (after validation)
grivredr store-pattern \
    --scraper scrapers/portal/scraper.py \
    --confidence 0.95
```

### When Patterns Are Stored

Patterns are automatically stored when:
- **Validation passes** (`scraper_validator.py`)
- **Continuous improvement succeeds** (`continuous_improvement_agent.py`)
- **Discovery completes** (`hybrid_form_discovery.py`)

Confidence scores are calculated based on:
- Number of validation attempts (fewer = higher confidence)
- Success rate during improvement
- Cycles needed to reach target

### Pattern Storage Schema

```python
# SQLite table: patterns
{
    "id": "uuid",
    "portal_url": "https://smartranchi.in/...",
    "state": "jharkhand",
    "district": "ranchi",
    "portal_name": "ranchi_smart",

    # Form characteristics
    "ui_framework": "select2",
    "field_count": 12,
    "field_types": ["text", "searchable_select", "textarea", "file"],
    "has_cascades": true,
    "cascade_count": 2,

    # Code snippets
    "full_code": "...",  # Complete scraper
    "dropdown_handler": "...",  # Extracted snippet
    "cascade_handler": "...",  # Extracted snippet

    # Success metrics
    "confidence": 0.95,
    "validation_attempts": 1,
    "success_rate": 1.0,

    "created_at": timestamp,
    "last_used_at": timestamp,
    "usage_count": 5
}
```

### Benefits of Pattern Learning

1. **Faster Generation**: Reuse proven code, less guesswork
2. **Higher Success Rate**: Patterns have proven to work
3. **Reduced Costs**: Fewer AI calls for similar forms
4. **Better Reliability**: Tested patterns are more robust
5. **Continuous Improvement**: System gets smarter over time

---

## Directory Structure

### Portal Data Organization

```
portals/
└── {state}/                    # e.g., jharkhand, delhi
    └── {district}/             # e.g., ranchi, central_zone
        └── {portal_name}/      # e.g., ranchi_smart, mcd_delhi
            │
            ├── scraper.py      # Generated scraper code
            │
            ├── structure.json  # Discovered form structure
            │   {
            │     "form_url": "https://...",
            │     "form_title": "Complaint Registration",
            │     "ui_framework": "select2",
            │     "fields": [
            │       {
            │         "name": "Problem",
            │         "type": "searchable_select",
            │         "selector": "#problem_id",
            │         "required": true,
            │         "options": ["Water Supply", "Drainage", ...]
            │       },
            │       ...
            │     ]
            │   }
            │
            ├── context/        # Dropdown context (critical!)
            │   │
            │   ├── dropdowns.json
            │   │   {
            │   │     "Problem": {
            │   │       "selector": "#problem_id",
            │   │       "options": {
            │   │         "Water Supply": "1",
            │   │         "Drainage": "2"
            │   │       }
            │   │     }
            │   │   }
            │   │
            │   ├── cascades.json
            │   │   {
            │   │     "Zone_to_Ward": {
            │   │       "parent": "#zone_id",
            │   │       "child": "#ward_id"
            │   │     }
            │   │   }
            │   │
            │   └── field_mappings.json
            │
            └── metadata.json   # Training info
                {
                  "created_at": "2024-12-27T22:33:00",
                  "training_cost": 0.29,
                  "api_calls": 10,
                  "ui_framework": "select2",
                  "pattern_confidence": 0.95,
                  "patterns_used": ["pattern_uuid_1", "pattern_uuid_2"]
                }
```

---

## CLI Commands

### Main Commands

```bash
# 1. DISCOVER - Generate scraper for a new portal
grivredr discover \
    --url "https://portal.example.com/form" \
    --portal portal_name \
    --state state_name \
    --district district_name \
    [--visible]  # Show browser window

# 2. TEST - Dry-run test (fill form, don't submit)
grivredr test \
    --scraper scrapers/portal_name/scraper.py \
    --state state_name \
    --district district_name \
    --portal portal_name \
    [--visible]

# 3. VALIDATE - Self-healing validation loop
grivredr validate \
    --scraper scrapers/portal_name/scraper.py \
    --max-attempts 3 \
    [--submit]   # Actually submit form (not dry-run)

# 4. IMPROVE - Continuous improvement
grivredr improve \
    --scraper scrapers/portal_name/scraper.py \
    --target 90           # 90% success rate target
    --max-cycles 5

# 5. LIST - Show all portals
grivredr list \
    [--state state_name]

# 6. DETECT - Detect UI framework
grivredr detect \
    --url "https://portal.example.com"

# 7. PATTERNS - View pattern library
grivredr patterns \
    [--framework select2]  # Filter by framework
    [--top 10]             # Top N by confidence

# 8. STORE-PATTERN - Manually store pattern
grivredr store-pattern \
    --scraper scrapers/portal/scraper.py \
    --confidence 0.95
```

---

## Cost Tracking

### Typical Costs

| Operation | AI Calls | Typical Cost | With Pattern Learning |
|-----------|----------|--------------|----------------------|
| Discovery (simple form) | 8-12 | $0.15-0.25 | $0.10-0.20 (20% ↓) |
| Discovery (complex form) | 15-25 | $0.30-0.70 | $0.20-0.50 (30% ↓) |
| Code generation | 1 | $0.05-0.10 | $0.03-0.07 (40% ↓) |
| Validation (per attempt) | 1-2 | $0.01-0.05 | $0.01-0.03 (20% ↓) |
| Self-healing fix | 1 | $0.05-0.15 | $0.03-0.10 (30% ↓) |

**Cost Reduction from Pattern Learning:**
- **First portal** (no patterns): $0.50
- **10th similar portal** (with patterns): $0.30 (40% reduction)
- **100th portal**: $0.20 (60% reduction)

---

## Integration with Darshi

### Use Cases

#### 1. Unified Grievance Filing

**Scenario:** User reports pothole via Darshi

```
User fills Darshi form:
├─ Issue: Pothole
├─ Location: Koramangala, Bangalore
├─ Photo: [image]
└─ Description: "Large pothole near mall"

Darshi Backend:
1. Store in Darshi database (as usual)
2. Identify responsible portal: BBMP grievance portal
3. Check if Grivredr scraper exists
   → Yes: bbmp_bangalore scraper (95% confidence pattern)

4. Call Grivredr scraper:
   await bbmp_scraper.fill_and_submit({
     "category": "Road Maintenance",
     "ward": "98",
     "issue": "Pothole",
     "description": "...",
     "location": "...",
     "photo": image_file
   })

5. Capture tracking ID from portal
   → Store in Darshi: external_tracking_id = "BBMP/2024/12345"

6. Return to user:
   "✅ Report filed successfully!
    Darshi ID: #DR123456
    BBMP ID: BBMP/2024/12345"
```

#### 2. Multi-Portal Filing

**Scenario:** Issue requires filing to multiple agencies

```
User reports: "Construction site causing noise and dust pollution"

Darshi identifies multiple agencies:
├─ Municipal Corp (illegal construction check)
├─ Pollution Control Board (noise/dust)
└─ Traffic Police (road congestion)

For each agency:
1. Check if Grivredr scraper available
2. File complaint automatically (using learned patterns)
3. Track all IDs
4. Show consolidated view to user
```

#### 3. Status Tracking

**Scenario:** User wants to check status of filed complaint

```
Darshi stores:
├─ Internal report ID: DR123456
└─ External tracking ID: BBMP/2024/12345

User clicks "Check Status":

Darshi calls Grivredr status checker:
await bbmp_scraper.check_status("BBMP/2024/12345")

Returns:
{
  "status": "In Progress",
  "last_updated": "2024-12-20",
  "assigned_to": "Ward Engineer, Ward 98",
  "remarks": "Site inspection scheduled for Dec 25"
}

Darshi shows:
"📊 Status Update
 Your report (BBMP/2024/12345) is in progress.
 Inspection scheduled for Dec 25.
 Assigned to: Ward Engineer, Ward 98"
```

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DARSHI CORE                             │
├─────────────────────────────────────────────────────────────┤
│  User submits report → Darshi processes → Stores in DB      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Portal Router │  (Which portal to file to?)
                  └────────┬───────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      GRIVREDR SERVICE                        │
├─────────────────────────────────────────────────────────────┤
│  API Endpoints:                                              │
│  • POST /grivredr/file                                       │
│    - Parameters: portal_id, complaint_data                   │
│    - Returns: tracking_id, success                           │
│                                                              │
│  • GET /grivredr/status/{portal_id}/{tracking_id}            │
│    - Returns: status, updates, remarks                       │
│                                                              │
│  • GET /grivredr/portals                                     │
│    - Returns: list of available portal scrapers              │
│                                                              │
│  • GET /grivredr/patterns                                    │
│    - Returns: pattern library statistics                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                  ┌────────────────────┐
                  │  Scraper Registry  │
                  │  + Pattern Library │
                  └────────┬───────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐   ┌────────┐   ┌────────┐
         │  BBMP  │   │  PMC   │   │ Ranchi │
         │ Scraper│   │ Scraper│   │ Scraper│
         │ (95%)  │   │ (92%)  │   │ (98%)  │
         └────────┘   └────────┘   └────────┘
         % = pattern confidence
```

---

## Migration Path

### Phase 1: Standalone Development (6-8 weeks)

**Goals:** Build Grivredr as independent tool

**Tasks:**
- [x] Core discovery agent
- [x] Scraper generation
- [x] Validation & self-healing
- [x] Pattern library foundation
- [ ] CLI interface polishing
- [ ] Documentation
- [ ] Test on 20+ portals

**Deliverables:**
- Working Grivredr tool (CLI)
- 20+ portal scrapers generated
- Pattern library with initial patterns

### Phase 2: Pattern Learning Enhancement (3-4 weeks)

**Goals:** Enhance pattern learning capabilities

**Tasks:**
- [ ] Vector search for semantic similarity
- [ ] Automatic snippet extraction
- [ ] Confidence scoring improvements
- [ ] Pattern effectiveness tracking
- [ ] Pattern visualization dashboard

**Deliverables:**
- Advanced pattern matching
- Pattern library dashboard

### Phase 3: API Service (4-5 weeks)

**Goals:** Convert to API service

**Tasks:**
- [ ] Build FastAPI service wrapper
- [ ] Scraper registry system
- [ ] File complaint API endpoint
- [ ] Check status API endpoint
- [ ] Portal list API endpoint
- [ ] Pattern library API endpoint
- [ ] Authentication & rate limiting

**Deliverables:**
- Grivredr API service
- API documentation

### Phase 4: Darshi Integration (3-4 weeks)

**Goals:** Integrate with Darshi

**Tasks:**
- [ ] Portal identification logic (which portal for which location?)
- [ ] Complaint data mapping (Darshi → portal format)
- [ ] External tracking ID storage
- [ ] Status checking integration
- [ ] UI changes (show portal filing status)

**Deliverables:**
- Seamless Darshi → Grivredr → Portal flow
- Pattern-based portal suggestions

### Phase 5: Scale (Ongoing)

**Goals:** 100+ portals, continuous learning

**Tasks:**
- [ ] Generate scrapers for top 50 cities
- [ ] Monitor scraper health (detect breakage)
- [ ] Auto-healing when portals change
- [ ] Portal coverage dashboard
- [ ] Pattern effectiveness analytics
- [ ] Continuous pattern refinement

---

## Challenges & Mitigations

### 1. Portal Changes

**Challenge:** Portals change without notice, scrapers break.

**Mitigations:**
- Health monitoring (daily tests)
- Auto-detection of breakage
- Self-healing: Re-run discovery when scraper fails
- Pattern library: Quickly regenerate with proven patterns
- Graceful degradation: Fall back to manual filing instructions

### 2. CAPTCHA

**Challenge:** Many portals have CAPTCHA.

**Mitigations:**
- Human-in-the-loop for CAPTCHA solving
- CAPTCHA solving services (2Captcha, Anti-Captcha)
- Alternative: Generate direct link for user to complete

### 3. Authentication

**Challenge:** Some portals require login.

**Mitigations:**
- Support for credential storage (encrypted)
- OAuth integration where available
- User provides credentials once, stored securely

### 4. Complex Multi-Step Forms

**Challenge:** Forms with multiple pages.

**Mitigations:**
- Discovery agent handles multi-step
- Store intermediate state
- Validation at each step
- Pattern library includes multi-step patterns

### 5. File Upload Validation

**Challenge:** Strict file size/format requirements.

**Mitigations:**
- Parse requirements during discovery
- Pre-validate files before submission
- Auto-resize images if needed
- Pattern library includes upload patterns

### 6. Pattern Drift

**Challenge:** Patterns become outdated as portals evolve.

**Mitigations:**
- Track pattern age and usage
- Monitor pattern success rates
- Auto-deprecate low-performing patterns
- Periodic pattern review and refresh

---

## Success Metrics

### Coverage
- Number of portals with working scrapers (target: 100+)
- Geographic coverage (% of Indian cities)
- Pattern library size (target: 500+ patterns)

### Reliability
- Scraper success rate (target: >95%)
- Average time to detect + fix breakage (target: <24h)
- Pattern match rate (% of new portals matched to patterns)

### Efficiency
- Average discovery time (target: <5 min)
- Cost per portal (target: <$0.50)
- Cost reduction from patterns (target: >40%)

### Learning
- Pattern reuse rate (% of scrapers using patterns)
- Pattern confidence improvement over time
- Pattern library growth rate

### Integration
- % of Darshi reports auto-filed to portals (target: 50%+)
- User satisfaction with auto-filing
- Reduction in manual filing time

---

## Conclusion

Grivredr transforms portal integration from a manual, time-consuming process to an automated, self-healing, continuously learning system. By combining:

1. **AI-powered discovery** (understands any form)
2. **Automated code generation** (proven patterns)
3. **Self-healing validation** (fixes itself)
4. **Pattern learning** (gets smarter over time)
5. **Continuous improvement** (adapts to changes)

We enable Darshi to integrate with 100+ government portals at scale, providing citizens with truly unified grievance filing across all jurisdictions. The pattern learning system ensures that each successful scraper makes future integrations faster, more reliable, and more cost-effective.

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Part of: Darshi Civic Suite*
