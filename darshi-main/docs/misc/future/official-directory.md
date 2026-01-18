# Official Directory & Contact Platform

> AI-Powered Navigation of India's Complex Governance Structure

**Part of: Darshi Civic Suite**

This document outlines the integration strategy for helping citizens identify and contact the right government officials for any civic issue.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture](#architecture)
5. [Data Model](#data-model)
6. [AI Query Resolution](#ai-query-resolution)
7. [Multi-Language Support](#multi-language-support)
8. [User Interface](#user-interface)
9. [Data Sources & Scraping](#data-sources--scraping)
10. [Migration Path](#migration-path)
11. [Challenges & Mitigations](#challenges--mitigations)
12. [Tech Stack](#tech-stack)

---

## Executive Summary

**Problem:** India's governance structure is complex and opaque. Citizens don't know which official or agency is responsible for specific problems, creating barriers to effective grievance redressal.

**Solution:** An AI-powered directory that:
1. Understands natural language queries ("Who handles potholes in Koramangala?")
2. Navigates the complex governance hierarchy (Municipal → Ward → Department → Official)
3. Provides direct contact information with multilingual support
4. Suggests escalation paths when initial contact fails

**Value Proposition:** Every citizen can reach the right official in under 30 seconds, regardless of their knowledge of bureaucratic structure or language proficiency.

---

## Problem Statement

### The Navigation Challenge

#### 1. Complexity of Indian Governance

**Example: A pothole in Bangalore**

```
Who's responsible?
├─ BBMP (Bruhat Bengaluru Mahanagara Palike)
│  ├─ Roads & Infrastructure Department
│  │  ├─ Ward 98 (Koramangala)
│  │  │  ├─ Ward Engineer
│  │  │  ├─ Assistant Executive Engineer (AEE)
│  │  │  └─ Executive Engineer (EE)
│  │  └─ Zonal Engineer (South Zone)
│  └─ OR Bangalore Development Authority (BDA)?
│     └─ (If it's a BDA-laid road)
└─ OR Karnataka PWD?
   └─ (If it's a state highway)
```

**Most citizens have no idea where to even start.**

#### 2. Ward/Zone Confusion

- Most cities have 50-200 wards
- Citizens don't know their ward number
- Ward boundaries change periodically
- Different agencies use different ward systems
  - Municipal wards ≠ Police station jurisdictions ≠ Assembly constituencies

#### 3. Department Maze

**Example: Construction site violations in Mumbai**

Possible agencies:
- **Municipal Corporation:** Building permissions, illegal construction
- **Pollution Control Board:** Noise, dust, air pollution
- **Traffic Police:** Vehicle congestion, illegal parking
- **Labor Department:** Safety violations
- **Fire Department:** Safety compliance

**Which one do you call?** Most citizens don't know.

#### 4. Language Barriers

- Governance happens in regional languages
- Officials' names, designations often only in local script
- Migrant workers can't read Kannada/Marathi/Tamil
- Even Google Translate doesn't help if you can't find the information

#### 5. Information Staleness

- Officials transfer every 1-2 years
- Contact numbers change
- Websites rarely updated (2-year-old information common)
- No centralized directory

### Current Gaps in Darshi

Darshi users face these challenges:
- "I want to report a pothole, but who should I address it to?"
- "My report was ignored. Who should I escalate to?"
- "This is urgent. Can I call someone directly?"

Current solution: Generic submissions to "the system."
Better solution: Direct connection to the responsible official.

---

## Solution Overview

### Platform Capabilities

#### 1. Natural Language Query Resolution

```
User input (any language):
"कोरमंगला में पॉटहोल किसको रिपोर्ट करें?"
(Who should I report pothole in Koramangala to?)

AI Response:
"कोरमंगला (वार्ड 98) में पॉटहोल के लिए जिम्मेदार:

1. वार्ड इंजीनियर - Mr. Rajesh Kumar
   📞 +91-80-1234-5678
   ✉️ ward98.engineer@bbmp.gov.in

2. असिस्टेंट एक्ज़िक्यूटिव इंजीनियर (AEE) - South Zone
   📞 +91-80-2345-6789

आप BBMP कंप्लेंट पोर्टल पर भी रिपोर्ट कर सकते हैं:
https://bbmp.gov.in/complaint?ward=98&issue=pothole"
```

#### 2. Smart Search

```
Query types supported:
├─ By problem type: "Who handles garbage collection?"
├─ By location: "Ward engineer for Indiranagar"
├─ By agency: "BBMP South Zone head"
├─ By name: "Contact details of Mr. Rajesh Kumar, Ward 98"
├─ By designation: "All ward engineers in Bangalore"
└─ Complex: "Who handles noise pollution from construction sites in Pune?"
```

#### 3. Hierarchical Directory

```
City: Bangalore
└─ BBMP (Municipal Corporation)
   ├─ Roads & Infrastructure
   │  ├─ South Zone
   │  │  ├─ Ward 98 (Koramangala)
   │  │  │  ├─ Corporator: Ms. Sneha Reddy
   │  │  │  │  📞 +91-98765-43210
   │  │  │  ├─ Ward Engineer: Mr. Rajesh Kumar
   │  │  │  │  📞 +91-80-1234-5678
   │  │  │  │  ✉️ ward98@bbmp.gov.in
   │  │  │  └─ AEE (Roads): Mr. Suresh Nair
   │  │  │     📞 +91-80-2345-6789
   │  │  └─ Ward 99 (HSR Layout)
   │  │     └─ ...
   │  └─ Zonal Engineer: Mr. Venkatesh Rao
   ├─ Health & Sanitation
   │  └─ ...
   └─ Revenue
      └─ ...
```

#### 4. Escalation Pathways

```
Report not resolved?

Current level: Ward Engineer (Mr. Rajesh Kumar)

Escalate to:
1. Assistant Executive Engineer - South Zone
   Mr. Suresh Nair
   📞 +91-80-2345-6789

   If no response in 7 days →

2. Executive Engineer - BBMP Roads
   Mr. Prakash Iyer
   📞 +91-80-3456-7890

   If no response in 15 days →

3. BBMP Commissioner
   Commissioner's Office
   📞 +91-80-4567-8901
   ✉️ commissioner@bbmp.gov.in
```

#### 5. Multilingual Interface

- Query in any of 8+ Indian languages
- Response in same language
- Officials' names in both English and local script
- Transliteration support for names

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
│  "Who handles potholes in Koramangala?"                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY UNDERSTANDING (Gemini)                  │
├─────────────────────────────────────────────────────────────────┤
│  Extract:                                                        │
│  • Issue type: "potholes" → category: "roads"                   │
│  • Location: "Koramangala" → ward: 98, city: Bangalore          │
│  • Intent: "who handles" → need: contact information            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESOLUTION ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│  1. Identify jurisdiction (city/ward/zone)                       │
│  2. Identify agency (Municipal/State/Central)                    │
│  3. Identify department (Roads, Health, etc.)                    │
│  4. Identify hierarchy level (Ward/Zone/City)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER QUERY                              │
├─────────────────────────────────────────────────────────────────┤
│  Firestore Query:                                                │
│  officials                                                       │
│    WHERE city = "Bangalore"                                      │
│    WHERE agency = "BBMP"                                         │
│    WHERE department = "Roads & Infrastructure"                   │
│    WHERE ward = 98                                               │
│    WHERE role IN ["Ward Engineer", "AEE", "Corporator"]          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE GENERATION (Gemini)                  │
├─────────────────────────────────────────────────────────────────┤
│  Format response in user's language:                             │
│  • Primary contact (Ward Engineer)                               │
│  • Backup contacts (AEE, Corporator)                             │
│  • Escalation path                                               │
│  • Portal links                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT                                        │
│  (Text response + structured contact cards)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Official Schema

```python
# Collection: officials
{
    "id": "uuid",

    # Personal Information
    "name": {
        "en": "Rajesh Kumar",
        "native": "राजेश कुमार",  # In local script
        "transliteration": "Raajesh Kumaar"
    },
    "designation": {
        "en": "Ward Engineer",
        "native": "वार्ड इंजीनियर"
    },
    "employee_id": "BBMP/2023/1234",

    # Contact Information
    "contact": {
        "phone": "+91-80-1234-5678",
        "mobile": "+91-98765-43210",
        "email": "ward98.engineer@bbmp.gov.in",
        "office_address": "Ward 98 Office, Koramangala, Bangalore - 560034"
    },

    # Jurisdiction
    "jurisdiction": {
        "country": "India",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bangalore",
        "zone": "South Zone",
        "ward": "98",
        "ward_name": "Koramangala",
        "geohashes": ["tdr1h", "tdr1k"]  # Area coverage
    },

    # Organizational Hierarchy
    "agency": {
        "name": "BBMP",
        "full_name": "Bruhat Bengaluru Mahanagara Palike",
        "type": "municipal_corporation",
        "department": "Roads & Infrastructure",
        "sub_department": "Ward Engineering"
    },

    # Responsibility
    "responsibilities": [
        "road_maintenance",
        "pothole_repair",
        "street_lights",
        "drainage"
    ],
    "issue_categories": [
        "pothole",
        "road_damage",
        "streetlight",
        "drainage"
    ],

    # Hierarchy
    "hierarchy_level": 3,  # 1=City, 2=Zone, 3=Ward, 4=Section
    "reports_to": {
        "official_id": "uuid-of-aee",
        "designation": "Assistant Executive Engineer"
    },
    "supervises": [
        "uuid-of-junior-engineer-1",
        "uuid-of-junior-engineer-2"
    ],

    # Office Hours
    "office_hours": {
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "hours": "10:00-18:00",
        "closed": ["Sunday", "National Holidays"]
    },

    # Status
    "status": "active|transferred|retired",
    "tenure": {
        "start_date": "2023-01-15",
        "end_date": null,  # null if currently serving
        "previous_posting": "Ward 45, West Zone"
    },

    # Verification
    "verified": true,
    "verified_by": "admin_user_id",
    "verified_at": timestamp,
    "last_updated": timestamp,

    # Engagement Metrics
    "stats": {
        "issues_resolved": 156,
        "avg_resolution_time_days": 7,
        "citizen_rating": 4.2,  # out of 5
        "response_rate": 0.85   # 85% of reports get response
    }
}
```

### Agency Schema

```python
# Collection: agencies
{
    "id": "uuid",
    "name": "BBMP",
    "full_name": {
        "en": "Bruhat Bengaluru Mahanagara Palike",
        "kn": "ಬೃಹತ್ ಬೆಂಗಳೂರು ಮಹಾನಗರ ಪಾಲಿಕೆ"
    },
    "type": "municipal_corporation|state_department|central_ministry|autonomous_body",

    "jurisdiction": {
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bangalore",
        "coverage_area_sqkm": 741
    },

    "contact": {
        "helpline": "080-22660000",
        "email": "contact@bbmp.gov.in",
        "website": "https://bbmp.gov.in",
        "complaint_portal": "https://bbmp.gov.in/complaint",
        "address": "BBMP Head Office, K.H Road, Bangalore - 560002"
    },

    "departments": [
        {
            "name": "Roads & Infrastructure",
            "head_official_id": "uuid",
            "categories": ["pothole", "road_damage", "streetlight"]
        },
        {
            "name": "Health & Sanitation",
            "head_official_id": "uuid",
            "categories": ["garbage", "sanitation", "health"]
        }
        # ... more departments
    ],

    "zones": [
        {
            "name": "South Zone",
            "wards": ["94", "95", "96", "97", "98", "99"],
            "head_official_id": "uuid"
        }
        # ... more zones
    ],

    "created_at": timestamp,
    "last_updated": timestamp
}
```

### Responsibility Mapping Schema

```python
# Collection: responsibility_mappings
{
    "id": "uuid",
    "issue_category": "pothole",
    "keywords": ["pothole", "road hole", "सड़क गड्ढा", "ರಸ್ತೆ ಹೊಡೆತ"],

    # Jurisdiction rules
    "jurisdiction_rules": [
        {
            "condition": {
                "road_type": "municipal",
                "city": "Bangalore"
            },
            "responsible_agency": "BBMP",
            "department": "Roads & Infrastructure",
            "hierarchy_level": "ward",  # Start at ward level
            "fallback_level": "zone"    # Escalate to zone if ward doesn't respond
        },
        {
            "condition": {
                "road_type": "state_highway",
                "state": "Karnataka"
            },
            "responsible_agency": "Karnataka PWD",
            "department": "State Highways",
            "hierarchy_level": "district"
        },
        {
            "condition": {
                "road_type": "national_highway"
            },
            "responsible_agency": "NHAI",
            "department": "Highway Maintenance",
            "hierarchy_level": "regional"
        }
    ],

    # Escalation path
    "escalation_levels": [
        {"level": 1, "designation": "Ward Engineer", "timeout_days": 7},
        {"level": 2, "designation": "AEE", "timeout_days": 7},
        {"level": 3, "designation": "Executive Engineer", "timeout_days": 15},
        {"level": 4, "designation": "Commissioner", "timeout_days": 30}
    ],

    "created_at": timestamp
}
```

---

## AI Query Resolution

### Query Understanding Pipeline

```python
class QueryResolver:
    """
    Resolve natural language queries to responsible officials.
    """

    async def resolve_query(self, query: str, user_location: dict = None) -> dict:
        """
        Main resolution pipeline.
        """
        # Step 1: Understand the query
        parsed_query = await self._parse_query(query, user_location)

        # Step 2: Identify responsible officials
        officials = await self._find_responsible_officials(parsed_query)

        # Step 3: Build escalation path
        escalation = await self._build_escalation_path(officials[0])

        # Step 4: Generate response
        response = await self._generate_response(
            query, parsed_query, officials, escalation
        )

        return response

    async def _parse_query(self, query: str, user_location: dict) -> dict:
        """
        Use Gemini to understand the query.
        """
        prompt = f"""
        Parse this civic query from an Indian citizen.

        Query: "{query}"
        User location (if known): {user_location}

        Extract:
        1. Issue type/category (pothole, garbage, water, etc.)
        2. Location mentioned (city, area, ward, landmark)
        3. Intent (find contact, report issue, escalate, check status)
        4. Language of query

        Respond in JSON format:
        {{
          "issue_category": "...",
          "location": {{
            "city": "...",
            "area": "...",
            "ward": "..." or null
          }},
          "intent": "...",
          "language": "..."
        }}
        """

        response = await gemini.generate(prompt)
        return parse_json(response)

    async def _find_responsible_officials(self, parsed_query: dict) -> list:
        """
        Query Firestore for responsible officials based on parsed query.
        """
        # Get responsibility mapping for issue category
        mapping = db.collection('responsibility_mappings') \
            .where('issue_category', '==', parsed_query['issue_category']) \
            .get()

        if not mapping:
            return []

        # Apply jurisdiction rules
        responsible_agency = self._apply_jurisdiction_rules(
            mapping[0], parsed_query['location']
        )

        # Query officials
        officials_query = db.collection('officials') \
            .where('agency.name', '==', responsible_agency['agency']) \
            .where('status', '==', 'active')

        # Add location filters
        if parsed_query['location'].get('ward'):
            officials_query = officials_query.where(
                'jurisdiction.ward', '==', parsed_query['location']['ward']
            )
        elif parsed_query['location'].get('zone'):
            officials_query = officials_query.where(
                'jurisdiction.zone', '==', parsed_query['location']['zone']
            )

        # Add department filter
        if responsible_agency.get('department'):
            officials_query = officials_query.where(
                'agency.department', '==', responsible_agency['department']
            )

        # Order by hierarchy level (lower = more specific)
        officials_query = officials_query.order_by('hierarchy_level', 'asc')

        officials = officials_query.get()
        return [off.to_dict() for off in officials]

    async def _build_escalation_path(self, primary_official: dict) -> list:
        """
        Build escalation hierarchy starting from primary official.
        """
        path = [primary_official]

        current = primary_official
        while current.get('reports_to'):
            supervisor_id = current['reports_to']['official_id']
            supervisor = db.collection('officials').document(supervisor_id).get()

            if supervisor.exists:
                path.append(supervisor.to_dict())
                current = supervisor.to_dict()
            else:
                break

        return path

    async def _generate_response(
        self,
        original_query: str,
        parsed_query: dict,
        officials: list,
        escalation: list
    ) -> dict:
        """
        Generate human-readable response in user's language.
        """
        prompt = f"""
        Generate a helpful response to this citizen query in {parsed_query['language']}.

        Original query: "{original_query}"

        Context:
        - Issue: {parsed_query['issue_category']}
        - Location: {parsed_query['location']}

        Responsible officials:
        {json.dumps(officials, indent=2)}

        Escalation path:
        {json.dumps(escalation, indent=2)}

        Provide:
        1. Direct answer to the query
        2. Primary contact with phone/email
        3. Backup contacts
        4. Escalation path (if needed)
        5. Portal link (if available)

        Format in a friendly, conversational tone.
        """

        response = await gemini.generate(prompt)

        return {
            "text_response": response,
            "structured_data": {
                "primary_official": officials[0] if officials else None,
                "backup_officials": officials[1:3] if len(officials) > 1 else [],
                "escalation_path": escalation,
                "portal_link": officials[0]['agency'].get('complaint_portal') if officials else None
            }
        }
```

### Example Query Resolutions

#### Example 1: Simple Query

**Input:**
```
Query: "Who handles garbage in HSR Layout?"
Location: {city: "Bangalore", area: "HSR Layout"}
```

**Output:**
```
HSR Layout (Ward 99) में कूड़ा संग्रहण के लिए जिम्मेदार:

1. स्वास्थ्य निरीक्षक - Ms. Lakshmi Devi
   📞 +91-80-2222-3333
   ✉️ ward99.health@bbmp.gov.in
   कार्यालय समय: सोमवार-शनिवार, 10 AM - 6 PM

2. वार्ड स्वच्छता पर्यवेक्षक - Mr. Kumar Swamy
   📞 +91-80-3333-4444

यदि समस्या हल नहीं होती है:
- 7 दिनों के बाद: South Zone स्वास्थ्य अधिकारी
  Dr. Anand Rao - 📞 +91-80-4444-5555

BBMP कंप्लेंट पोर्टल: https://bbmp.gov.in/complaint
```

#### Example 2: Complex Query

**Input:**
```
Query: "Construction site near my house in Pune is causing noise pollution.
        Who should I complain to?"
Location: {city: "Pune", area: "Koregaon Park"}
```

**Output:**
```
For construction noise pollution in Koregaon Park, Pune:

PRIMARY AUTHORITY:
Maharashtra Pollution Control Board (MPCB)
- Regional Officer: Mr. Santosh Patil
  📞 +91-20-1111-2222
  ✉️ pune.regional@mpcb.gov.in
- File complaint: https://mpcb.gov.in/complaint

ALTERNATE OPTIONS:
1. PMC (Pune Municipal Corporation) - Building Dept
   Ward 8 Building Inspector: Mr. Ravi Kulkarni
   📞 +91-20-2222-3333
   (For building permission violations)

2. Police - Local Station (Koregaon Park)
   📞 100 (Emergency) / 020-2605-8888
   (For immediate noise disturbance)

RECOMMENDED APPROACH:
1. File complaint with MPCB (primary authority for pollution)
2. Also inform PMC Building Dept (they may find violations)
3. If issue persists beyond 7 days, escalate to:
   MPCB Regional Director - 📞 +91-20-3333-4444
```

---

## Multi-Language Support

### Supported Languages

| Language | Code | Script | Official Query Support | Response Generation |
|----------|------|--------|------------------------|---------------------|
| English | en | Latin | ✓ | ✓ |
| Hindi | hi | Devanagari | ✓ | ✓ |
| Marathi | mr | Devanagari | ✓ | ✓ |
| Tamil | ta | Tamil | ✓ | ✓ |
| Telugu | te | Telugu | ✓ | ✓ |
| Kannada | kn | Kannada | ✓ | ✓ |
| Bengali | bn | Bengali | ✓ | ✓ |
| Gujarati | gu | Gujarati | ✓ | ✓ |

### Transliteration for Names

**Challenge:** Official names in local script, users can't type.

**Solution:** Provide transliterated versions.

```python
# Official: राजेश कुमार (Devanagari)
# Transliteration: "Rajesh Kumar" (Latin)
# Pronunciation guide: "Raajesh Kumaar"

def transliterate_name(name: str, from_script: str) -> str:
    """
    Transliterate name from Devanagari/Tamil/etc to Latin script.
    """
    # Use IndicTrans2 or Google Transliteration API
    pass
```

### Code-Mixed Queries

**Common in urban India:**
```
"Koramangala mein pothole ka complain kahan karein?"
(Mix of Hindi and English)

"HSR Layout la garbage collection yaaru handle maadthare?"
(Mix of Kannada and English)
```

**Gemini handles these natively.**

---

## User Interface

### Web Interface

#### 1. Search Bar (Prominent)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  🔍  Ask me anything about your city officials...           │
│  ────────────────────────────────────────────────────────   │
│                                                             │
│  Examples:                                                  │
│  • Who handles potholes in Koramangala?                     │
│  • Contact details for Ward 98 engineer                     │
│  • कोरमंगला में कूड़ा कौन उठाता है?                         │
│                                                             │
│  [🎤 Voice Search]  [🌐 हिंदी | मराठी | ಕನ್ನಡ]              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Response Display

```
┌─────────────────────────────────────────────────────────────┐
│  Query: "Who handles potholes in Koramangala?"              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PRIMARY CONTACT                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 👤 Mr. Rajesh Kumar                                    │ │
│  │ Ward Engineer, BBMP Ward 98                            │ │
│  │                                                        │ │
│  │ 📞 +91-80-1234-5678                                    │ │
│  │    [📞 Call] [💬 WhatsApp]                             │ │
│  │                                                        │ │
│  │ ✉️ ward98.engineer@bbmp.gov.in                         │ │
│  │    [📧 Email]                                          │ │
│  │                                                        │ │
│  │ 🕒 Office Hours: Mon-Sat, 10 AM - 6 PM                 │ │
│  │                                                        │ │
│  │ 📊 Performance: 4.2⭐ | 156 issues resolved            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  BACKUP CONTACTS                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • AEE (South Zone) - Mr. Suresh Nair                  │ │
│  │   📞 +91-80-2345-6789                                  │ │
│  │                                                        │ │
│  │ • Corporator (Ward 98) - Ms. Sneha Reddy              │ │
│  │   📞 +91-98765-43210                                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  IF NO RESPONSE?                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 1. Wait 7 days, then escalate to:                     │ │
│  │    AEE - Mr. Suresh Nair                              │ │
│  │                                                        │ │
│  │ 2. Still no response after 15 days?                   │ │
│  │    Escalate to Executive Engineer                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ONLINE PORTAL                                              │
│  You can also file a complaint online:                      │
│  🔗 https://bbmp.gov.in/complaint?ward=98&issue=pothole    │
│                                                             │
│  [📤 Share this info] [🔖 Bookmark] [👍 Helpful?]         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Browse by Location

```
┌─────────────────────────────────────────────────────────────┐
│  📍 Browse Officials by Location                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Select your city: [Bangalore ▼]                            │
│                                                             │
│  Select your area:                                          │
│  [🔍 Search wards, areas, or landmarks...]                  │
│                                                             │
│  OR Select from map:                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         [Interactive Map of Bangalore]              │   │
│  │                                                     │   │
│  │  Click on your area to see officials               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### WhatsApp Bot

```
User: "Who handles potholes in Koramangala?"

Bot:
कोरमंगला (वार्ड 98) में पॉटहोल के लिए:

👤 Mr. Rajesh Kumar
   Ward Engineer, BBMP
📞 +91-80-1234-5678
✉️ ward98.engineer@bbmp.gov.in

🕒 Office: Mon-Sat, 10 AM-6 PM

Backup:
• AEE: Mr. Suresh Nair
  📞 +91-80-2345-6789

Reply:
1 - Call Ward Engineer
2 - Send WhatsApp message
3 - Get escalation path
4 - File online complaint
```

### Voice Search (Mobile)

**Powered by Google Speech-to-Text + Gemini**

```
User: [Presses mic button]
      "कोरमंगला में पॉटहोल किसको रिपोर्ट करें?"

App: [Transcribes → Sends to AI → Gets response]
     [Displays response + Reads aloud in Hindi]
```

---

## Data Sources & Scraping

### Sources of Official Data

#### 1. Official Websites

```python
GOVERNMENT_SOURCES = [
    # Municipal Corporations
    {
        "city": "Bangalore",
        "agency": "BBMP",
        "url": "https://bbmp.gov.in/officials",
        "scraper": "bbmp_officials_scraper"
    },
    {
        "city": "Pune",
        "agency": "PMC",
        "url": "https://pmc.gov.in/en/contact-us",
        "scraper": "pmc_officials_scraper"
    },

    # State Departments
    {
        "state": "Karnataka",
        "agency": "Karnataka PWD",
        "url": "https://kpwd.karnataka.gov.in/officials",
        "scraper": "kpwd_officials_scraper"
    },

    # Central Ministries
    {
        "level": "national",
        "agency": "Ministry of Road Transport",
        "url": "https://morth.nic.in/contact",
        "scraper": "morth_officials_scraper"
    }
]
```

#### 2. RTI Responses

- File RTI requests for official directory
- Many municipalities publish in response to RTI
- Update database with RTI data

#### 3. Government Orders (Transfer orders)

```python
# Monitor government gazette for transfer orders
# Example: "IAS officer X transferred from Y to Z"
# Auto-update official status and jurisdiction
```

#### 4. Crowdsourcing

```python
# Users can suggest updates:
# "This official has been transferred"
# "New ward engineer appointed"
# Admin reviews and approves updates
```

### Grivredr-Powered Scraping

```python
class OfficialDirectoryScraper:
    """
    Use Grivredr to scrape official directories from government sites.
    """

    async def scrape_municipal_officials(self, city: str, url: str) -> list:
        """
        Scrape official directory from municipal website.
        """
        # Use Grivredr discovery to identify structure
        structure = await grivredr.discover_structure(url)

        # Extract officials
        officials = []
        for entry in structure['entries']:
            official = {
                'name': entry['name'],
                'designation': entry['designation'],
                'phone': entry.get('phone'),
                'email': entry.get('email'),
                'department': entry.get('department'),
                # ... more fields
            }
            officials.append(official)

        return officials
```

### Data Freshness Strategy

**Problem:** Officials transfer frequently.

**Solution:**
1. **Periodic rescraping:** Monthly for all sources
2. **Transfer order monitoring:** Daily check for gazette notifications
3. **User feedback:** "Is this information correct?" button
4. **Staleness detection:** Flag if contact fails repeatedly

```python
# Mark official as potentially stale if:
# - No response to 10+ citizen complaints
# - Phone number invalid/disconnected
# - Email bounces
# - Last updated > 6 months ago

if official.stats.response_rate < 0.2:
    official.status = "needs_verification"
    trigger_rescrape(official.agency.url)
```

---

## Migration Path

### Phase 1: Foundation (4-5 weeks)

**Goals:** Core data model and manual data entry for 1-2 cities

**Tasks:**
- [ ] Design data models (officials, agencies, mappings)
- [ ] Build admin panel for manual data entry
- [ ] Manually populate Bangalore officials (BBMP)
- [ ] Manually populate Pune officials (PMC)
- [ ] Create responsibility mappings for common issues

**Deliverables:**
- Database with 200+ officials (2 cities)
- Admin interface for data management

### Phase 2: AI Query Engine (3-4 weeks)

**Goals:** Natural language query resolution

**Tasks:**
- [ ] Build query parsing with Gemini
- [ ] Implement jurisdiction resolution logic
- [ ] Build official lookup engine
- [ ] Create escalation path builder
- [ ] Implement response generation (multilingual)

**Deliverables:**
- Working query resolution API
- Support for 8 Indian languages

### Phase 3: User Interfaces (4-5 weeks)

**Goals:** Web, WhatsApp, voice interfaces

**Tasks:**
- [ ] Build web search interface
- [ ] Add location-based browse (map)
- [ ] Integrate with WhatsApp bot (from Nagar Alert Hub)
- [ ] Add voice search (mobile)
- [ ] Create shareable official cards

**Deliverables:**
- Web portal live
- WhatsApp bot functional
- Mobile voice search working

### Phase 4: Automated Scraping (5-6 weeks)

**Goals:** Auto-populate officials from government sites

**Tasks:**
- [ ] Build Grivredr scrapers for top 20 cities
- [ ] Implement transfer order monitoring
- [ ] Create data validation pipeline
- [ ] Build crowdsourced update system
- [ ] Add staleness detection

**Deliverables:**
- 50+ cities covered
- 10,000+ officials in database
- Monthly auto-updates

### Phase 5: Integration with Darshi Reports (2-3 weeks)

**Goals:** Connect with existing Darshi reporting

**Tasks:**
- [ ] Add "Find responsible official" to report submission
- [ ] Auto-suggest official based on report location/category
- [ ] Show escalation path if report unresolved
- [ ] Add "Contact official directly" option

**Deliverables:**
- Seamless integration with report flow
- Users can find + contact official in one flow

### Phase 6: Scale & Optimize (Ongoing)

**Goals:** National coverage, data quality

**Tasks:**
- [ ] Expand to 100+ cities
- [ ] Improve AI resolution accuracy
- [ ] Add official performance tracking
- [ ] Build feedback loop for data quality

---

## Challenges & Mitigations

### 1. Data Availability

**Challenge:** Many municipalities don't publish official directories online.

**Mitigations:**
- RTI requests for directories
- Manual entry for major cities (prioritize)
- Crowdsourced updates (verified by admins)
- Partnerships with civic organizations

### 2. Data Staleness

**Challenge:** Officials transfer every 1-2 years, data quickly outdated.

**Mitigations:**
- Automated transfer order monitoring
- User feedback mechanism ("Is this correct?")
- Periodic rescraping (monthly)
- Staleness detection (flag unresponsive officials)

### 3. Jurisdiction Complexity

**Challenge:** Overlapping jurisdictions (municipal vs state roads, etc.)

**Mitigations:**
- Detailed responsibility mappings
- AI handles ambiguity (suggests multiple options)
- User feedback improves mappings over time
- Clear explanations ("BBMP for municipal roads, PWD for state highways")

### 4. Language Barriers

**Challenge:** Official names in local scripts, English speakers can't search.

**Mitigations:**
- Store both native script and transliteration
- AI understands queries in any language
- Response in user's language
- Voice search (no typing required)

### 5. Privacy & Security

**Challenge:** Publishing official contact info could lead to harassment.

**Mitigations:**
- Only publish info already public (government websites)
- Rate limiting on contact lookups
- Encourage use of official complaint portals (not direct calls)
- "Report misuse" option

### 6. Accuracy of AI Resolution

**Challenge:** AI might suggest wrong official.

**Mitigations:**
- Multiple contact options (primary + backups)
- User feedback ("Was this helpful?")
- Continuous improvement of responsibility mappings
- Human oversight for complex cases

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Query Understanding | **Gemini** | Parse natural language queries |
| Database | **Firestore** | Officials, agencies, mappings |
| Scraping | **Grivredr** | Auto-extract officials from websites |
| Backend | **FastAPI** | API server |
| Frontend | **SvelteKit** | Web interface |
| Voice | **Google Speech-to-Text** | Voice search |
| WhatsApp | **WhatsApp Business API** | Bot interface |
| Maps | **Google Maps** | Location-based browse |

---

## Success Metrics

### Data Coverage
- Number of cities covered (target: 100+)
- Number of officials in database (target: 50,000+)
- Data freshness (target: <10% stale entries)

### User Engagement
- Daily queries resolved
- Query resolution accuracy (user feedback)
- Average time to find official (target: <30 seconds)

### Impact
- % of Darshi reports that use official finder
- % of reports sent directly to identified officials
- Reduction in "I don't know who to contact" feedback

---

## Conclusion

The Official Directory Platform removes the navigation barrier that prevents citizens from reaching the right official. By combining:

1. **Comprehensive data** (scraped + curated)
2. **AI-powered resolution** (natural language understanding)
3. **Multilingual support** (8+ Indian languages)
4. **Multiple interfaces** (web, WhatsApp, voice)

We empower every citizen to navigate India's complex governance structure, regardless of their education, language, or technical literacy.

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Part of: Darshi Civic Suite*
