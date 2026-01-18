# MP/MLA Fund Tracking Platform

> Transparency and Accountability in Local Area Development Spending

**Part of: Darshi Civic Suite**

This document outlines the integration strategy for tracking Member of Parliament (MP) and Member of Legislative Assembly (MLA) fund utilization, project progress, and expenditure patterns.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture](#architecture)
5. [Data Model](#data-model)
6. [Data Sources](#data-sources)
7. [Analytics & Visualization](#analytics--visualization)
8. [User Interface](#user-interface)
9. [Integration with Darshi](#integration-with-darshi)
10. [Migration Path](#migration-path)
11. [Challenges & Mitigations](#challenges--mitigations)
12. [Tech Stack](#tech-stack)

---

## Executive Summary

**Background:**
- MPs receive ₹5 crores/year (MPLADS - Member of Parliament Local Area Development Scheme)
- MLAs receive ₹1-5 crores/year (varies by state - MLA LAD fund)
- Funds for local development: roads, schools, healthcare, sanitation

**Problem:** Citizens don't know:
- How their MP/MLA is spending these funds
- Which projects are funded in their area
- Project completion status
- Historical spending patterns
- Comparison with other MPs/MLAs

**Solution:** A transparent, visual platform that:
1. Tracks every project funded by MPLADS/MLA LAD funds
2. Shows project status (sanctioned → ongoing → completed)
3. Maps projects geographically
4. Analyzes spending patterns
5. Compares representatives' performance
6. Allows citizen feedback on project quality

**Value Proposition:** Hold elected representatives accountable by making their development spending visible and measurable.

---

## Problem Statement

### The Transparency Gap

#### 1. Information Asymmetry

**Current State:**
- MPLADS data published on government portal (mplads.gov.in)
- But: PDFs, hard to search/analyze
- But: No state-level aggregation for MLA funds
- But: No project status updates post-sanction
- But: No citizen feedback mechanism

**Citizen Questions (Currently Unanswered):**
- "Has my MP done anything in my area?"
- "Where did the ₹5 crores go?"
- "Why is my area's school still broken when funds exist?"
- "Is this MP better than the previous one?"

#### 2. Lack of Accountability

**Problems:**
- Funds sanctioned but projects not completed
- Poor quality construction (leaks, cracks within months)
- Nepotism in project selection (benefit MP's preferred areas)
- No consequences for non-utilization

**Example:**
```
MP X sanctioned ₹50 lakhs for community center in 2022
├─ Status on portal: "Sanctioned"
├─ Ground reality: Construction incomplete, abandoned
├─ Quality: Roof leaking, walls cracked
└─ Citizen recourse: None (don't know whom to complain to)
```

#### 3. No Comparative Analysis

Citizens can't answer:
- "How does my MP compare to MPs in neighboring constituencies?"
- "Which party's MPs deliver better infrastructure?"
- "Which categories (health, education, roads) get most funding?"

---

## Solution Overview

### Platform Capabilities

#### 1. Comprehensive Fund Tracking

```
For each MP/MLA:
├─ Annual allocation (₹5 crores for MPs)
├─ Projects sanctioned (itemized list)
│  ├─ Project name & description
│  ├─ Location (constituency, ward, geolocation)
│  ├─ Category (health, education, roads, etc.)
│  ├─ Sanctioned amount
│  ├─ Sanctioned date
│  ├─ Implementing agency
│  └─ Expected completion date
├─ Funds utilized (vs allocated)
├─ Projects completed (vs sanctioned)
└─ Year-over-year trends
```

#### 2. Real-Time Project Status

```
Project Lifecycle:
Sanctioned → Approval → Tendering → Work Order →
Construction Started → Ongoing → Inspection →
Completed → Citizen Feedback

Current government data: Only "Sanctioned"
Our platform: All stages + photos + citizen feedback
```

#### 3. Geographic Visualization

```
Interactive Map:
├─ Color-coded by project status
│  ├─ Green: Completed
│  ├─ Yellow: Ongoing
│  ├─ Red: Delayed/Stalled
│  └─ Gray: Sanctioned but not started
├─ Filter by category (schools, roads, healthcare)
├─ Filter by year (2020, 2021, 2022, 2023, 2024)
└─ Click project → See details, photos, status
```

#### 4. Citizen Feedback

```
For each project:
├─ "Is this project completed?" (Yes/No)
├─ "Quality rating" (1-5 stars)
├─ "Upload photo of current state"
├─ "Report issue" (incomplete, poor quality, not started)
└─ Comments section
```

#### 5. Comparative Analytics

```
Compare MPs/MLAs:
├─ Funds utilization rate (%)
├─ Projects completed (%)
├─ Average project completion time
├─ Citizen satisfaction score
├─ Category-wise spending distribution
└─ Timeline comparison (term 1 vs term 2)
```

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────┤
│  MPLADS     State MLA    RTI          Citizen      Government   │
│  Portal     Portals      Responses    Reports      Orders       │
└──────┬────────────┬──────────┬────────────┬────────────┬────────┘
       │            │          │            │            │
       ▼            ▼          ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  Web Scrapers  │  PDF Parsers  │  Manual Entry  │  API Clients │
│  (Grivredr)    │               │  (Admin)       │               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  • Geocoding (project addresses → coordinates)                   │
│  • Categorization (education, health, infrastructure)            │
│  • Deduplication (same project from multiple sources)            │
│  • Entity extraction (MP name, constituency, amounts)            │
│  • Status inference (from text descriptions)                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  Firestore (Real-time)           │  BigQuery (Analytics)        │
│  ├── MPs/MLAs                    │  ├── Spending patterns       │
│  ├── Projects                    │  ├── Completion rates        │
│  ├── Citizen feedback            │  ├── Constituency analysis   │
│  └── Status updates              │  └── Comparative metrics     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS ENGINE                              │
├─────────────────────────────────────────────────────────────────┤
│  • Utilization rate calculation                                  │
│  • Completion rate tracking                                      │
│  • Delay detection                                               │
│  • Citizen satisfaction scoring                                  │
│  • Constituency ranking                                          │
│  • Spending pattern analysis                                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  Web Portal    Mobile App    Public API     Data Export         │
│  (Dashboard)   (PWA)         (Developers)   (CSV/JSON)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### MP/MLA Schema

```python
# Collection: representatives
{
    "id": "uuid",

    # Personal Info
    "name": "Rajeev Chandrashekhar",
    "party": "BJP",
    "position": "mp|mla|former_mp|former_mla",

    # Constituency
    "constituency": {
        "name": "Bangalore South",
        "type": "lok_sabha|vidhan_sabha",
        "state": "Karnataka",
        "districts": ["Bengaluru Urban"],
        "geohashes": ["tdr1", "tdr2"]  # Coverage area
    },

    # Tenure
    "tenure": {
        "start_date": "2019-05-23",
        "end_date": null,  # null if current
        "term": "17th Lok Sabha",
        "previous_terms": ["16th Lok Sabha"]
    },

    # Contact
    "contact": {
        "email": "rajeevchandrashekhar@sansad.nic.in",
        "phone": "+91-11-2301-XXXX",
        "office_address": "...",
        "website": "https://...",
        "social_media": {
            "twitter": "@Rajeev_GoI",
            "facebook": "..."
        }
    },

    # Fund Allocation
    "fund_allocation": {
        "scheme": "MPLADS",
        "annual_amount": 50000000,  # ₹5 crores
        "currency": "INR"
    },

    # Performance Summary (calculated)
    "performance": {
        "total_allocated": 250000000,  # Over 5 years
        "total_utilized": 230000000,
        "utilization_rate": 0.92,  # 92%
        "projects_sanctioned": 142,
        "projects_completed": 118,
        "completion_rate": 0.83,  # 83%
        "avg_project_completion_days": 245,
        "citizen_satisfaction": 4.1  # out of 5
    },

    "created_at": timestamp,
    "updated_at": timestamp
}
```

### Project Schema

```python
# Collection: projects
{
    "id": "uuid",

    # Representative
    "representative_id": "uuid",
    "representative_name": "Rajeev Chandrashekhar",
    "representative_position": "MP",
    "constituency": "Bangalore South",

    # Project Details
    "title": "Construction of Community Health Center",
    "description": "Construction of a 50-bed community health center with...",
    "category": "healthcare",  # Standardized categories
    "subcategory": "hospital",

    # Financial
    "sanctioned_amount": 15000000,  # ₹1.5 crores
    "released_amount": 12000000,   # Amount actually released
    "spent_amount": 11500000,      # Amount spent so far
    "currency": "INR",

    # Timeline
    "sanctioned_date": "2022-04-15",
    "approval_date": "2022-05-20",
    "work_order_date": "2022-07-01",
    "construction_start_date": "2022-08-15",
    "expected_completion_date": "2024-02-15",
    "actual_completion_date": null,  # null if not completed

    # Status
    "status": "sanctioned|approved|tendering|ongoing|completed|stalled|cancelled",
    "status_updated_at": timestamp,
    "status_history": [
        {"status": "sanctioned", "date": "2022-04-15"},
        {"status": "approved", "date": "2022-05-20"},
        {"status": "ongoing", "date": "2022-08-15"}
    ],

    # Location
    "location": {
        "address": "Ward 98, Koramangala, Bangalore",
        "ward": "98",
        "zone": "South Zone",
        "city": "Bangalore",
        "state": "Karnataka",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "geohash": "tdr1hv"
    },

    # Implementing Agency
    "implementing_agency": {
        "name": "BBMP",
        "department": "Health Department",
        "contractor": "XYZ Constructions Pvt Ltd"
    },

    # Documents
    "documents": {
        "sanction_letter_url": "gs://...",
        "tender_document_url": "gs://...",
        "work_order_url": "gs://...",
        "completion_certificate_url": null
    },

    # Photos
    "photos": [
        {
            "url": "gs://...",
            "caption": "Foundation laying ceremony",
            "date": "2022-08-15",
            "source": "official|citizen"
        }
    ],

    # Citizen Feedback
    "feedback": {
        "completion_confirmations": 0,  # How many citizens confirmed completed
        "quality_ratings": [],  # [5, 4, 4, 5] - citizen ratings
        "avg_quality_rating": null,
        "issues_reported": [
            {
                "user_id": "uuid",
                "issue": "Construction quality poor, cracks visible",
                "reported_at": timestamp,
                "photos": ["gs://..."]
            }
        ]
    },

    # Metadata
    "data_source": "mplads_portal|state_portal|rti|citizen",
    "scraped_from_url": "https://...",
    "verified": true,
    "verified_by": "admin_user_id",
    "created_at": timestamp,
    "updated_at": timestamp
}
```

### Categories

```python
PROJECT_CATEGORIES = {
    "healthcare": ["hospital", "clinic", "pharmacy", "ambulance"],
    "education": ["school", "college", "library", "digital_classroom", "lab"],
    "infrastructure": ["road", "bridge", "footpath", "drainage", "streetlight"],
    "water": ["water_supply", "tank", "pipeline", "purification"],
    "sanitation": ["toilet", "waste_management", "sewage"],
    "sports": ["stadium", "playground", "gym"],
    "culture": ["community_center", "auditorium", "library", "park"],
    "electricity": ["power_supply", "transformer", "poles"],
    "other": ["miscellaneous"]
}
```

---

## Data Sources

### 1. MPLADS Portal (mplads.gov.in)

**What's Available:**
- All MP-sanctioned projects (since 2006)
- Constituency-wise data
- Category-wise data
- Sanctioned amounts

**Format:** PDF reports, Excel downloads, web pages

**Scraping Strategy:**
```python
class MPLADSScraper:
    """
    Scrape MPLADS portal for project data.
    """

    async def scrape_constituency(self, constituency: str, year: int) -> list:
        """
        Scrape all projects for a constituency in a year.
        """
        # 1. Navigate to constituency page
        # 2. Extract project list
        # 3. For each project, extract details
        # 4. Parse financial data
        # 5. Geocode project locations
        pass
```

### 2. State MLA Fund Portals

**Examples:**
- Maharashtra: https://mahades.maharashtra.gov.in
- Karnataka: (varies by district)
- Tamil Nadu: (district-level portals)

**Challenge:** Each state has different format, some don't publish online.

**Strategy:**
- Grivredr adaptive scrapers for each state
- RTI requests for data not published
- Manual entry for smaller states

### 3. RTI Responses

**Use Cases:**
- Request project status updates (not on portals)
- Request contractor details
- Request quality inspection reports

### 4. Government Orders & Gazettes

**Monitor for:**
- Fund release notifications
- Project completion announcements
- Transfer of funds to agencies

### 5. Citizen Reports (via Darshi)

**Integration:**
- Citizens upload photos of project sites
- Report project status ("construction started", "completed")
- Rate project quality

---

## Analytics & Visualization

### Key Metrics

#### 1. Utilization Rate

```sql
-- Calculate fund utilization rate for an MP
SELECT
  representative_name,
  SUM(sanctioned_amount) as total_sanctioned,
  SUM(spent_amount) as total_spent,
  (SUM(spent_amount) / SUM(sanctioned_amount)) as utilization_rate
FROM projects
WHERE representative_id = 'xyz'
GROUP BY representative_name
```

#### 2. Completion Rate

```sql
-- Calculate project completion rate
SELECT
  representative_name,
  COUNT(*) as total_projects,
  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_projects,
  (SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*)) as completion_rate
FROM projects
WHERE representative_id = 'xyz'
```

#### 3. Average Completion Time

```sql
-- Average days to complete projects
SELECT
  representative_name,
  AVG(DATE_DIFF(actual_completion_date, construction_start_date, DAY)) as avg_completion_days
FROM projects
WHERE status = 'completed'
  AND representative_id = 'xyz'
```

#### 4. Spending by Category

```sql
-- Category-wise spending distribution
SELECT
  category,
  SUM(sanctioned_amount) as total_amount,
  (SUM(sanctioned_amount) / (SELECT SUM(sanctioned_amount) FROM projects WHERE representative_id = 'xyz')) as percentage
FROM projects
WHERE representative_id = 'xyz'
GROUP BY category
ORDER BY total_amount DESC
```

#### 5. Citizen Satisfaction

```python
def calculate_citizen_satisfaction(representative_id: str) -> float:
    """
    Calculate average citizen satisfaction score.
    Based on project quality ratings and completion confirmations.
    """
    projects = get_projects(representative_id, status='completed')

    total_rating = 0
    count = 0

    for project in projects:
        if project.feedback.quality_ratings:
            avg_rating = sum(project.feedback.quality_ratings) / len(project.feedback.quality_ratings)
            total_rating += avg_rating
            count += 1

    if count == 0:
        return None

    return total_rating / count
```

### Visualization Examples

#### 1. Constituency Map

```
┌─────────────────────────────────────────────────────────────┐
│  Bangalore South - MP: Rajeev Chandrashekhar               │
│  Fund Utilization: 92% | Projects Completed: 118/142       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│        [Interactive Map of Constituency]                    │
│                                                             │
│  Legend:                                                    │
│  🟢 Completed (118)                                         │
│  🟡 Ongoing (18)                                            │
│  🔴 Stalled/Delayed (4)                                     │
│  ⚪ Sanctioned (not started) (2)                            │
│                                                             │
│  Filters:                                                   │
│  [All ▼] [2020 ▼] [2021 ▼] [2022 ▼] [2023 ▼] [2024 ▼]    │
│  [Healthcare] [Education] [Roads] [Water] [All Categories] │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Spending Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│  Spending by Category (2019-2024)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Healthcare       ████████████████ 32% (₹80 Cr)            │
│  Education        ████████████ 24% (₹60 Cr)                │
│  Infrastructure   ██████████ 20% (₹50 Cr)                  │
│  Water & Sanit.   ██████ 12% (₹30 Cr)                      │
│  Sports           ████ 8% (₹20 Cr)                          │
│  Other            ██ 4% (₹10 Cr)                            │
│                                                             │
│  Total: ₹250 Crores (5 years @ ₹5 Cr/year)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Timeline View

```
┌─────────────────────────────────────────────────────────────┐
│  Project Timeline: Community Health Center, Koramangala     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Sanctioned        Approved       Work Started    Expected  │
│  Apr 2022          May 2022       Aug 2022        Feb 2024  │
│      ●──────────────●──────────────●──────────────○        │
│                                    │                         │
│                               Current status:                │
│                               60% complete                   │
│                               (as of Dec 2024)               │
│                                                             │
│  ⚠️ Delayed by 45 days                                      │
│  New expected completion: Mar 2024                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4. Comparative Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Compare MPs: Bangalore Constituencies                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Metric              South    North    Central   Average   │
│  ─────────────────── ────────────────────────────────────  │
│  Utilization Rate    92%      87%      95%       91%       │
│  Completion Rate     83%      78%      88%       83%       │
│  Projects Completed  118      102      135       118       │
│  Avg Completion Time 245d     267d     228d      247d      │
│  Citizen Rating      4.1⭐    3.8⭐    4.3⭐      4.1⭐     │
│                                                             │
│  Best Performer: Bangalore Central (Overall Score: 9.2/10) │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## User Interface

### Web Portal

#### 1. Homepage

```
┌─────────────────────────────────────────────────────────────┐
│  💰 Track Your MP/MLA Development Funds                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔍 Search by:                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ MP/MLA Name, Constituency, or Your Location         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  OR                                                         │
│                                                             │
│  📍 Detect My Location                                      │
│     [Allow Location Access]                                 │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  📊 National Statistics                                     │
│  • ₹2,725 Crores allocated (545 MPs @ ₹5 Cr each)          │
│  • 89% utilization rate                                     │
│  • 15,234 projects completed this year                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Representative Profile

```
┌─────────────────────────────────────────────────────────────┐
│  👤 Rajeev Chandrashekhar                                   │
│     MP, Bangalore South (BJP) | 2019-2024                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Performance Overview                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Fund Utilization: 92% ████████████░░  (₹230/250 Cr) │   │
│  │ Projects Completed: 83% ████████████░░ (118/142)     │   │
│  │ Citizen Rating: 4.1⭐⭐⭐⭐☆                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [View Projects Map] [Spending Analysis] [Compare with...] │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  📋 Recent Projects (2024)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🏥 Community Health Center, Koramangala               │   │
│  │    ₹1.5 Cr | 🟡 60% complete | Healthcare             │   │
│  │    [View Details]                                     │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🏫 Digital Classroom, Govt School HSR                 │   │
│  │    ₹25 Lakhs | 🟢 Completed | Education               │   │
│  │    Citizen Rating: 4.5⭐ [View Details]               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [See All 142 Projects]                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Project Detail Page

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Rajeev Chandrashekhar's Projects                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🏥 Community Health Center, Koramangala                    │
│  Status: 🟡 Ongoing (60% complete)                          │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  💰 Financial Details                                       │
│  • Sanctioned: ₹1.5 Crores                                  │
│  • Released: ₹1.2 Crores                                    │
│  • Spent: ₹1.15 Crores                                      │
│                                                             │
│  📅 Timeline                                                │
│  • Sanctioned: Apr 15, 2022                                 │
│  • Construction Started: Aug 15, 2022                       │
│  • Expected Completion: Mar 2024 (delayed by 45 days)      │
│                                                             │
│  📍 Location                                                │
│  Ward 98, Koramangala, Bangalore South                      │
│  [View on Map]                                              │
│                                                             │
│  🏗️ Implementing Agency                                     │
│  BBMP Health Department                                     │
│  Contractor: XYZ Constructions Pvt Ltd                      │
│                                                             │
│  📸 Photos                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐                          │
│  │ Found- │ │ Under  │ │ Recent │                          │
│  │ ation  │ │ Const. │ │ (Dec)  │                          │
│  └────────┘ └────────┘ └────────┘                          │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  👥 Citizen Feedback                                        │
│  • 3 people confirmed construction ongoing                  │
│  • No quality issues reported                               │
│                                                             │
│  ❓ Have you visited this site?                             │
│  [✓ Confirm Status] [⭐ Rate Quality] [📷 Upload Photo]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Mobile App (PWA)

**Key Features:**
- Geolocation-based project discovery ("Show projects near me")
- Barcode/QR scanning (if projects have signboards with codes)
- Easy photo upload for citizen feedback
- Offline mode (cached data)
- Push notifications ("New project sanctioned in your area")

---

## Integration with Darshi

### Use Cases

#### 1. Link Reports to Funded Projects

**Scenario:** Citizen reports poor construction quality

```
Darshi Report: "Community center roof leaking"
Location: Koramangala

System automatically links to:
Fund Tracking Entry: "Community Center, Koramangala"
├─ Funded by: MP Rajeev Chandrashekhar
├─ Amount: ₹75 Lakhs
├─ Contractor: ABC Constructions
└─ Completion: 2023-02-15

Action:
- Tag report as "funded project quality issue"
- Notify MP office
- Update project feedback score
- Escalate if needed
```

#### 2. Track Report → Fund Allocation

**Scenario:** Multiple reports about missing school playground

```
Darshi Reports: 15 reports about "School needs playground"
Location: Govt School, HSR Layout

Fund Tracking System:
- Check: Has MP/MLA sanctioned funds for this school?
  Result: No recent projects
- Suggest: "Submit petition to MP for playground funding"
- Provide: MP contact details, MPLADS application process
```

#### 3. Monitor Fund-Backed Projects

**Scenario:** MP sanctions school renovation

```
Fund Tracking: "School building renovation sanctioned"
Location: Govt School, HSR Layout
Amount: ₹50 Lakhs
Expected Completion: 6 months

Darshi Integration:
- Create monitoring timeline
- Send notifications to nearby citizens
- Encourage progress photos
- Alert if project stalled
- Collect feedback post-completion
```

---

## Migration Path

### Phase 1: Data Foundation (6-8 weeks)

**Goals:** Build data model, scrape MPLADS data

**Tasks:**
- [ ] Design data models (representatives, projects)
- [ ] Build MPLADS scraper (all 545 MPs)
- [ ] Geocode project locations
- [ ] Categorize projects
- [ ] Calculate baseline metrics

**Deliverables:**
- Database with 50,000+ MPLADS projects
- All MP profiles with performance metrics

### Phase 2: State MLA Funds (8-10 weeks)

**Goals:** Add state-level data

**Tasks:**
- [ ] Identify state MLA fund portals (28 states)
- [ ] Build Grivredr scrapers for each state
- [ ] RTI requests for states without online data
- [ ] Integrate MLA data into database
- [ ] Calculate state-level metrics

**Deliverables:**
- MLA data for 5 major states (Maharashtra, Karnataka, Tamil Nadu, UP, MP)

### Phase 3: Web Portal (6-8 weeks)

**Goals:** Public-facing website

**Tasks:**
- [ ] Build representative profile pages
- [ ] Create project detail pages
- [ ] Interactive map visualization
- [ ] Search and filters
- [ ] Comparative analytics dashboard

**Deliverables:**
- Web portal live (view-only, no citizen feedback yet)

### Phase 4: Citizen Feedback (4-5 weeks)

**Goals:** Enable citizen participation

**Tasks:**
- [ ] Build project status confirmation feature
- [ ] Add quality rating system
- [ ] Photo upload for projects
- [ ] Issue reporting
- [ ] Feedback moderation system

**Deliverables:**
- Citizens can contribute project updates

### Phase 5: Darshi Integration (3-4 weeks)

**Goals:** Connect with existing Darshi platform

**Tasks:**
- [ ] Link Darshi reports to funded projects
- [ ] Add "Check if funded" feature to report submission
- [ ] Monitor funded projects via Darshi reports
- [ ] Shared user accounts

**Deliverables:**
- Seamless integration between platforms

### Phase 6: Advanced Analytics (Ongoing)

**Goals:** Deep insights, ML models

**Tasks:**
- [ ] Predictive models (which projects likely to stall?)
- [ ] Anomaly detection (unusual spending patterns)
- [ ] Sentiment analysis (citizen feedback text)
- [ ] Comparative ranking algorithms

---

## Challenges & Mitigations

### 1. Data Availability

**Challenge:** Many states don't publish MLA fund data online.

**Mitigations:**
- Focus on states that publish (start with 5-6 major states)
- RTI requests for remaining states
- Manual entry for high-priority constituencies
- Crowdsourcing: Allow users to submit project info

### 2. Data Staleness

**Challenge:** Government portals update infrequently.

**Mitigations:**
- Monthly scraping schedule
- Citizen feedback fills gaps (real-time status updates)
- Monitor government order websites for new sanctions

### 3. Geocoding Accuracy

**Challenge:** Project addresses vague ("Govt School, Ward 98")

**Mitigations:**
- Use Google Maps Geocoding API
- Fallback to ward centroid if address ambiguous
- Citizen-submitted photos with GPS coordinates
- Manual correction for high-value projects

### 4. Citizen Engagement

**Challenge:** Will citizens actually provide feedback?

**Mitigations:**
- Gamification (badges for contributions)
- Integration with Darshi (existing user base)
- WhatsApp notifications ("Rate this completed project")
- Make it easy (1-tap "Is this complete? Yes/No")

### 5. Political Sensitivity

**Challenge:** Platform exposes underperforming MPs/MLAs.

**Mitigations:**
- Data-driven, objective metrics (no editorial bias)
- Transparency: Data sources clearly cited
- Right to reply: MPs/MLAs can respond to feedback
- Legal review: Ensure compliance with defamation laws

### 6. Verification

**Challenge:** How to verify citizen-submitted updates?

**Mitigations:**
- Require multiple confirmations (3+ people)
- Photo evidence with GPS + timestamp
- Admin review for sensitive claims
- Community moderation (trusted users)

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Scraping | **Grivredr** | Adaptive scrapers for government portals |
| Geocoding | **Google Maps Geocoding API** | Convert addresses to coordinates |
| Database | **Firestore** | Projects, representatives, feedback |
| Analytics | **BigQuery** | Historical analysis, rankings |
| Backend | **FastAPI** | API server |
| Frontend | **SvelteKit** | Web portal |
| Maps | **Google Maps Platform** | Interactive maps |
| Storage | **Cloud Storage** | Photos, documents |

---

## Success Metrics

### Data Coverage
- Number of MPs covered (target: 545/545)
- Number of MLAs covered (target: 500+)
- Projects in database (target: 100,000+)

### User Engagement
- Monthly active users
- Citizen feedback submissions per month
- Photos uploaded per month

### Impact
- Media coverage / citations
- Downloads of data by researchers/journalists
- Requests for data access (API usage)

### Accountability
- Number of underperforming representatives exposed
- Projects marked as stalled → resumed
- Citizen satisfaction improvement (year-over-year)

---

## Conclusion

The MP/MLA Fund Tracking Platform brings transparency to development spending by making fund utilization data accessible, visual, and participatory. By combining:

1. **Comprehensive data** (scraped + RTI + citizen-contributed)
2. **Visual analytics** (maps, charts, comparisons)
3. **Citizen participation** (feedback, ratings, photos)
4. **Integration with Darshi** (link reports to funded projects)

We empower citizens to hold their elected representatives accountable for how they spend public development funds.

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Part of: Darshi Civic Suite*
