# Nagar Alert Hub Integration

> Community-Integrated Public Disruption Intelligence for Tier-2 & Tier-3 Cities

This document outlines the integration strategy for evolving Darshi into a comprehensive city intelligence platform by incorporating Nagar Alert Hub capabilities.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Core Synergy](#core-synergy)
5. [Architecture](#architecture)
6. [Data Model](#data-model)
7. [WhatsApp Integration](#whatsapp-integration)
8. [Authority Integration](#authority-integration)
9. [Intelligence Layer](#intelligence-layer)
10. [User Interface](#user-interface)
11. [Agent Workflows](#agent-workflows)
12. [Multilingual Support](#multilingual-support)
13. [Migration Path](#migration-path)
14. [Challenges & Mitigations](#challenges--mitigations)
15. [Tech Stack](#tech-stack)

---

## Executive Summary

**Darshi** currently handles civic issue reporting (potholes, garbage, streetlights) with AI-powered verification. **Nagar Alert Hub** extends this to real-time community alerts delivered via WhatsApp, creating a unified platform for both static infrastructure issues and dynamic city disruptions.

**Value Proposition:** The only system that catches infrastructure issues AND real-time disruptions, works through WhatsApp (no app download), has AI verification (no misinformation), connects citizens AND authorities, and learns and predicts city patterns.

---

## Problem Statement

### Current Challenges in Tier-2/3 Cities

1. **Frequent Disruptions:** Road closures, power cuts, traffic jams, water issues, festival crowds, market congestion, school bus delays, safety incidents
2. **No Unified System:** No real-time method to inform residents quickly and reliably
3. **Information Chaos:** People depend on scattered WhatsApp forwards, informal groups, local pages, and hearsay
4. **Delayed Awareness:** Residents learn updates too late → blocked routes, unavailable services, overcrowded markets, escalated emergencies
5. **Authority Communication Gap:** Existing civic apps fail due to low adoption; authorities struggle to broadcast verified alerts

### What Darshi Currently Solves

- Infrastructure issue reporting with photo evidence
- AI-powered verification and categorization
- Duplicate detection via image hash and geolocation
- Admin dashboard for issue tracking
- Hotspot detection for problem clusters

### What's Missing

- Real-time dynamic event handling
- WhatsApp-based communication (no app download required)
- Authority broadcast integration
- Predictive intelligence
- Two-way citizen-authority communication

---

## Solution Overview

### Integrated Platform Capabilities

1. **WhatsApp-Based Alert Engine**
   - Delivers all city updates directly to users
   - Authorities push verified alerts
   - AI cleans, standardizes, and summarizes messages across multiple languages

2. **Geo-Verified Citizen Reporting**
   - Users submit photos/videos with location via WhatsApp or web
   - AI identifies disruption type, validates authenticity
   - Merges duplicate reports automatically

3. **Real-Time Web Dashboard**
   - Mobile-friendly, no app required
   - Live disruptions: power outages, blocked roads, traffic, accidents, water issues
   - Auto-refreshing map with color-coded pins

4. **Predictive Intelligence**
   - Detects emerging issues early
   - Recommends alternate routes or timings
   - Sends personalized location-based alerts based on user movement patterns

---

## Core Synergy

| Darshi (Current) | Nagar Alert Hub (New) |
|------------------|----------------------|
| Static infrastructure issues (potholes, garbage) | Dynamic disruptions (traffic, power cuts, crowds) |
| Web-based submission | WhatsApp-based interaction |
| Individual report tracking | Community-wide broadcasting |
| Admin-managed resolution | Authority + AI-driven alerts |
| Reactive reporting | Proactive predictions |
| Single-city focus | Multi-city scalable |

### Unified Value

- **Citizens:** One source of truth for all city happenings
- **Authorities:** Direct channel to reach citizens with verified information
- **City:** Reduced chaos, faster response, data-driven planning

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│  Web App     WhatsApp    Authority    External APIs   Sensors   │
│  (Darshi)    Messages    Broadcasts   (Traffic/Power) (Future)  │
└──────┬────────────┬──────────┬────────────┬────────────┬────────┘
       │            │          │            │            │
       ▼            ▼          ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  Message Parser │ Image Processor │ Location Extractor │ Dedup  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI PROCESSING LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Gemini Multimodal Analysis                                      │
│  ├── Event Classification (type, severity, affected area)       │
│  ├── Authenticity Validation (real? current? location match?)   │
│  ├── Language Processing (Hindi, regional, code-mixed)          │
│  └── Duplicate/Cluster Detection                                │
├─────────────────────────────────────────────────────────────────┤
│  Vertex AI Models                                                │
│  ├── Event Clustering & Correlation                             │
│  ├── Pattern Recognition                                        │
│  └── Predictive Alerts                                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  Firestore (Real-time)           │  BigQuery (Analytics)        │
│  ├── Reports/Events              │  ├── Historical patterns     │
│  ├── User subscriptions          │  ├── Hotspot analysis        │
│  ├── Authority accounts          │  ├── Prediction models       │
│  └── Alert queue                 │  └── City insights           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  WhatsApp        Web Dashboard    Authority        Push          │
│  Broadcasts      (Real-time Map)  Notifications   Notifications  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. Ingestion Layer
- **Web Submissions:** Existing Darshi flow (multipart form upload)
- **WhatsApp Gateway:** WhatsApp Business API integration
- **Authority Portal:** Authenticated broadcast interface
- **External APIs:** Traffic data, power grid status (future)

#### 2. AI Processing Layer
- **Gemini Multimodal:** Image/video analysis, text understanding
- **Vertex AI:** Classification models, clustering, predictions
- **Language Models:** Multilingual processing, transliteration

#### 3. Data Layer
- **Firestore:** Real-time event storage, user data, subscriptions
- **BigQuery:** Historical analysis, pattern detection, reporting

#### 4. Output Layer
- **WhatsApp:** Personalized and broadcast alerts
- **Web Dashboard:** Real-time map, filters, search
- **Authority Dashboard:** Management, broadcasting, analytics

---

## Data Model

### Extended Report Schema

```python
{
    # === EXISTING DARSHI FIELDS ===
    "id": "uuid",
    "title": "string",
    "description": "string",
    "category": "pothole|garbage|streetlight|...",
    "latitude": float,
    "longitude": float,
    "geohash": "string",  # Precision 5
    "image_url": "string",
    "image_hash": "sha256",
    "status": "PENDING_VERIFICATION|VERIFIED|REJECTED|...",
    "severity": 1-10,
    "user_id": "string",
    "created_at": timestamp,
    "updated_at": timestamp,
    "timeline": [...],
    "upvotes": int,
    "upvoters": [...],

    # === NEW: EVENT CHARACTERISTICS ===
    "event_type": "infrastructure|disruption|community|safety",
    "is_dynamic": bool,  # Does this resolve on its own?
    "expected_duration_minutes": int | null,
    "affected_radius_meters": int,  # Impact zone

    # === NEW: SOURCE TRACKING ===
    "source": "web|whatsapp|authority|automated|external_api",
    "source_message_id": "string | null",  # WhatsApp message ID
    "authority_verified": bool,
    "authority_id": "string | null",
    "authority_note": "string | null",

    # === NEW: TEMPORAL RELEVANCE ===
    "valid_until": timestamp | null,  # When alert expires
    "last_confirmed": timestamp,  # Last citizen confirmation
    "confirmation_count": int,  # How many people confirmed still active
    "auto_expire": bool,  # Should system auto-resolve?

    # === NEW: CLUSTERING ===
    "cluster_id": "uuid | null",
    "is_cluster_primary": bool,  # Is this the main report in cluster?
    "related_report_ids": [...],

    # === NEW: RESOLUTION ===
    "resolution_source": "authority|timeout|citizen_confirmed|auto",
    "resolution_eta": timestamp | null,
    "resolution_note": "string | null"
}
```

### New Collections

#### User Subscriptions
```python
# Collection: user_subscriptions
{
    "user_id": "string",
    "phone_number": "string",  # For WhatsApp
    "whatsapp_opted_in": bool,
    "preferred_language": "en|hi|...",

    # Location-based subscriptions
    "home_location": {"lat": float, "lng": float, "geohash": "string"},
    "work_location": {"lat": float, "lng": float, "geohash": "string"},
    "custom_locations": [...],
    "subscription_radius_km": float,

    # Alert preferences
    "alert_types": ["traffic", "power", "water", "safety", "events"],
    "severity_threshold": 1-10,  # Only alert if severity >= threshold
    "quiet_hours": {"start": "22:00", "end": "07:00"},

    "created_at": timestamp,
    "updated_at": timestamp
}
```

#### Authority Accounts
```python
# Collection: authorities
{
    "id": "string",
    "name": "Traffic Police - Pune",
    "type": "traffic|power|water|municipal|police|admin",
    "jurisdiction_geohashes": [...],  # Areas they manage
    "contact_email": "string",
    "contact_phone": "string",
    "api_key": "string",  # For programmatic access
    "broadcast_permissions": ["traffic", "safety", "events"],
    "verified": bool,
    "created_at": timestamp
}
```

#### Alert Queue
```python
# Collection: alert_queue
{
    "id": "string",
    "report_id": "string",  # Related report
    "alert_type": "broadcast|targeted|escalation",
    "target_geohashes": [...],
    "target_user_ids": [...],  # For targeted alerts
    "message_template": "string",
    "language_variants": {
        "en": "Traffic jam on MG Road...",
        "hi": "एमजी रोड पर ट्रैफिक जाम..."
    },
    "priority": "low|medium|high|critical",
    "status": "pending|sending|sent|failed",
    "scheduled_at": timestamp,
    "sent_at": timestamp | null,
    "delivery_stats": {
        "total": int,
        "delivered": int,
        "read": int,
        "failed": int
    }
}
```

### Extended Category Taxonomy

```python
CATEGORIES = {
    # Infrastructure (Existing Darshi)
    "infrastructure": [
        "pothole",
        "garbage",
        "streetlight",
        "drainage",
        "road_damage",
        "footpath",
        "public_toilet",
        "park_maintenance"
    ],

    # Dynamic Disruptions (New)
    "disruption": [
        "traffic_congestion",
        "traffic_accident",
        "road_closure",
        "road_construction",
        "power_outage",
        "water_supply",
        "flooding",
        "waterlogging",
        "gas_leak"
    ],

    # Community Events (New)
    "community": [
        "festival",
        "rally_protest",
        "market_congestion",
        "vip_movement",
        "sports_event",
        "religious_gathering",
        "school_traffic",
        "wedding_baraat"
    ],

    # Safety Alerts (New)
    "safety": [
        "fire",
        "building_collapse",
        "crime_alert",
        "medical_emergency",
        "animal_sighting",  # Stray dogs, snakes, etc.
        "suspicious_activity"
    ]
}
```

---

## WhatsApp Integration

### Architecture

```
User sends WhatsApp message (text/photo/video/location)
                    │
                    ▼
         WhatsApp Business API
         (Cloud API / On-Premise)
                    │
                    ▼
         Webhook Receiver (FastAPI)
                    │
                    ▼
    ┌───────────────┴───────────────┐
    │     Message Type Router       │
    ├───────────────────────────────┤
    │ Text → Intent Classification  │
    │ Image → Gemini Analysis       │
    │ Video → Frame Extraction + AI │
    │ Location → Geohash Encoding   │
    │ Contact → Subscription Mgmt   │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │      AI Processing            │
    ├───────────────────────────────┤
    │ • Extract/validate location   │
    │ • Classify event type         │
    │ • Assess severity             │
    │ • Check for duplicates        │
    │ • Validate authenticity       │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │      Response Generator       │
    ├───────────────────────────────┤
    │ • Acknowledgment message      │
    │ • Clarification questions     │
    │ • Status update               │
    │ • Related alerts              │
    └───────────────────────────────┘
```

### Inbound Message Flows

#### 1. Report Submission
```
User: "Traffic jam near City Mall" + 📷 photo

System:
1. Parse text → Extract keywords (traffic, City Mall)
2. Analyze photo → Confirm traffic congestion
3. Extract location → From photo EXIF or text geocoding
4. Check duplicates → Similar reports in area?
5. Create report → Store in Firestore
6. Respond → "Thanks! Traffic congestion reported near City Mall.
              We'll alert others in the area. Report ID: #12345"
```

#### 2. Status Query
```
User: "What's happening near Gandhi Chowk?"

System:
1. Extract location → Gandhi Chowk coordinates
2. Query active events → Within 2km radius
3. Summarize → Group by type, sort by severity
4. Respond → "🚦 Active near Gandhi Chowk:
              • Traffic slow on MG Road (accident, clearing)
              • Power out in Sector 5 (ETA: 30 mins)
              • Festival crowd at Temple (until 10 PM)"
```

#### 3. Route Query
```
User: "Best route to railway station?"

System:
1. Get user's current location (if shared)
2. Query disruptions along common routes
3. Calculate impact scores
4. Respond → "🗺️ Recommended: Via Ring Road
              ❌ Avoid: MG Road (accident, 45 min delay)
              ❌ Avoid: Station Road (waterlogging)"
```

#### 4. Subscription Management
```
User: "Alert me about power cuts in Sector 15"

System:
1. Parse intent → Subscription request
2. Extract: type=power, location=Sector 15
3. Update user subscription
4. Respond → "✅ You'll receive power outage alerts for Sector 15.
              Reply STOP to unsubscribe."
```

### Outbound Alert Types

#### 1. Broadcast Alerts (High Severity)
```
🚨 TRAFFIC ALERT - Pune

Major accident on Pune-Mumbai Expressway near Lonavala.
Highway blocked, expect 2+ hour delays.

🔄 Alternatives:
• Old Mumbai Highway via Talegaon
• Delay travel if possible

Source: Traffic Police (Verified)
Updated: 10:30 AM

Reply INFO for more details
```

#### 2. Targeted Alerts (Based on Subscription)
```
⚡ POWER ALERT - Your Area

Unscheduled power cut in Sector 15, Pune.
Started: 2:30 PM
Expected restoration: 4:00 PM
Reason: Transformer maintenance

Source: MSEDCL (Verified)

Reply UPDATES for notifications when restored
```

#### 3. Predictive Alerts
```
📊 PREDICTED - Tomorrow

Heavy traffic expected near Shivaji Stadium tomorrow 5-8 PM.
Reason: IPL Match

💡 Suggestions:
• Leave before 4 PM or after 9 PM
• Use Metro if traveling to FC Road area
• Parking limited, use public transport

Reply REMIND to get alert tomorrow at 3 PM
```

### WhatsApp Business API Setup

```python
# app/services/whatsapp_service.py

class WhatsAppService:
    """
    Handles WhatsApp Business API integration.
    Supports both Cloud API and On-Premise deployment.
    """

    def __init__(self):
        self.api_url = settings.WHATSAPP_API_URL
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

    async def send_message(
        self,
        to: str,
        message: str,
        template: str = None,
        language: str = "en"
    ) -> dict:
        """Send a WhatsApp message to a user."""
        pass

    async def send_template(
        self,
        to: str,
        template_name: str,
        parameters: list,
        language: str = "en"
    ) -> dict:
        """Send a pre-approved template message."""
        pass

    async def send_broadcast(
        self,
        user_ids: list[str],
        message: str,
        priority: str = "normal"
    ) -> dict:
        """Send message to multiple users."""
        pass

    async def process_webhook(self, payload: dict) -> dict:
        """Process incoming webhook from WhatsApp."""
        pass
```

---

## Authority Integration

### Authority Dashboard Features

#### 1. Alert Broadcasting
- Compose and send verified alerts
- Select target area (draw on map or select geohashes)
- Set severity and duration
- Multi-language message composition
- Schedule future alerts
- Track delivery and read rates

#### 2. Report Management
- View citizen reports in jurisdiction
- Verify/reject reports
- Add official updates and ETAs
- Merge duplicate reports
- Escalate to other departments

#### 3. Situational Awareness
- Real-time map of all active issues
- Cluster detection and trending
- Historical comparison
- Response time metrics

#### 4. Analytics
- Report volume by type, area, time
- Resolution time tracking
- Citizen satisfaction (feedback)
- Prediction accuracy

### Authority Types & Permissions

| Authority Type | Can Broadcast | Can Verify | Can Resolve | Categories |
|----------------|---------------|------------|-------------|------------|
| Traffic Police | Yes | Yes | Yes | traffic_*, road_closure |
| Electricity Board | Yes | Yes | Yes | power_outage |
| Water Department | Yes | Yes | Yes | water_supply |
| Municipal Corp | Yes | Yes | Yes | infrastructure, garbage |
| District Admin | Yes | Yes | Yes | ALL |
| Police | Yes | Yes | Limited | safety_* |

### Authority API Endpoints

```python
# New endpoints for authority integration

# Authority Authentication
POST /api/v1/authority/login
POST /api/v1/authority/register  # Requires admin approval

# Broadcasting
POST /api/v1/authority/broadcast
GET  /api/v1/authority/broadcasts  # History
GET  /api/v1/authority/broadcast/{id}/stats

# Report Management
GET  /api/v1/authority/reports  # In jurisdiction
PUT  /api/v1/authority/report/{id}/verify
PUT  /api/v1/authority/report/{id}/update
PUT  /api/v1/authority/report/{id}/resolve

# Analytics
GET  /api/v1/authority/analytics/overview
GET  /api/v1/authority/analytics/response-times
GET  /api/v1/authority/analytics/hotspots
```

### Escalation Flow

```
Citizen Report (High Severity)
         │
         ▼
    AI Verification
         │
         ├── Severity >= 8?
         │        │
         │        ▼ Yes
         │   Auto-escalate to relevant authority
         │        │
         │        ▼
         │   Authority notified via:
         │   • Dashboard alert
         │   • Email notification
         │   • WhatsApp (if configured)
         │        │
         │        ▼
         │   15 min timeout?
         │        │
         │        ▼ No response
         │   Escalate to supervisor
         │        │
         │        ▼
         │   30 min timeout?
         │        │
         │        ▼ No response
         │   Escalate to district admin
         │
         └── Severity < 8
                  │
                  ▼
             Normal queue
```

---

## Intelligence Layer

### Pattern Detection (BigQuery)

#### Daily Patterns
```sql
-- Identify recurring traffic congestion patterns
SELECT
  EXTRACT(DAYOFWEEK FROM created_at) as day_of_week,
  EXTRACT(HOUR FROM created_at) as hour,
  geohash_prefix,
  COUNT(*) as incident_count,
  AVG(severity) as avg_severity
FROM `darshi_analytics.events`
WHERE
  category LIKE 'traffic%'
  AND created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY day_of_week, hour, geohash_prefix
HAVING incident_count >= 5
ORDER BY incident_count DESC
```

#### Correlation Analysis
```sql
-- Find correlations (e.g., rain → waterlogging → traffic)
SELECT
  a.category as trigger_category,
  b.category as result_category,
  COUNT(*) as correlation_count,
  AVG(TIMESTAMP_DIFF(b.created_at, a.created_at, MINUTE)) as avg_lag_minutes
FROM `darshi_analytics.events` a
JOIN `darshi_analytics.events` b
  ON ST_DISTANCE(
    ST_GEOGPOINT(a.longitude, a.latitude),
    ST_GEOGPOINT(b.longitude, b.latitude)
  ) < 1000  -- Within 1km
  AND b.created_at > a.created_at
  AND b.created_at < TIMESTAMP_ADD(a.created_at, INTERVAL 2 HOUR)
WHERE a.category != b.category
GROUP BY trigger_category, result_category
HAVING correlation_count >= 10
```

### Predictive Alerts

#### Types of Predictions

1. **Time-Based**
   - "School zone traffic at 8 AM and 2 PM"
   - "Market congestion on Saturdays"
   - "Temple crowd on festival days"

2. **Event-Based**
   - "Traffic spike when cricket match ends"
   - "Power load increase during heat waves"
   - "Waterlogging when rainfall > 50mm"

3. **Correlation-Based**
   - "Accident on highway → traffic on alternate routes"
   - "Power outage in area A → load increase in area B"

#### Prediction Pipeline

```
Historical Data (BigQuery)
         │
         ▼
Pattern Extraction
├── Time series analysis
├── Geospatial clustering
├── Event correlation
└── Seasonality detection
         │
         ▼
Vertex AI Model Training
├── Classification: What type of event?
├── Regression: How severe?
├── Time series: When will it happen?
└── Clustering: What areas affected?
         │
         ▼
Real-time Triggers
├── Calendar events (festivals, holidays)
├── Weather forecasts
├── Scheduled events (matches, rallies)
├── Current conditions (ongoing incidents)
         │
         ▼
Prediction Generation
         │
         ▼
Alert if confidence > threshold
```

### Clustering Algorithm

```python
def cluster_reports(reports: list, radius_meters: int = 500) -> list:
    """
    Cluster nearby reports of the same type.
    Uses DBSCAN-like approach with geohash optimization.
    """
    clusters = []

    # Group by category first
    by_category = group_by(reports, 'category')

    for category, cat_reports in by_category.items():
        # Use geohash for initial grouping (fast)
        by_geohash = group_by(cat_reports, lambda r: r.geohash[:6])

        for geohash, geo_reports in by_geohash.items():
            # Fine-grained clustering within geohash
            sub_clusters = dbscan(
                geo_reports,
                eps=radius_meters,
                min_samples=2,
                metric=haversine_distance
            )

            for cluster in sub_clusters:
                # Create cluster record
                primary = max(cluster, key=lambda r: r.upvotes + r.severity)
                clusters.append({
                    'primary_report_id': primary.id,
                    'report_ids': [r.id for r in cluster],
                    'category': category,
                    'center': calculate_centroid(cluster),
                    'severity': max(r.severity for r in cluster),
                    'report_count': len(cluster),
                    'affected_radius': calculate_spread(cluster)
                })

    return clusters
```

---

## User Interface

### Real-Time Map Dashboard

#### Features
- **Live Map:** Color-coded pins by event type
- **Clustering:** Grouped markers for dense areas
- **Filters:** Type, severity, time, source
- **Search:** Address or landmark lookup
- **Layers:** Traffic, power grid, water zones
- **Auto-refresh:** Every 30 seconds
- **Offline:** Cached map tiles for poor connectivity

#### Color Coding
```
🔴 Red     - Critical/Safety (accidents, fire, crime)
🟠 Orange  - High severity (major traffic, power outage)
🟡 Yellow  - Medium (congestion, water issues)
🟢 Green   - Low/Resolved
🔵 Blue    - Community events (neutral)
⚪ Gray    - Expired/Historical
```

#### Pin Interactions
```
Click pin → Show summary card
├── Event type icon
├── Title/description
├── Severity badge
├── Time ago
├── Source (citizen/authority)
├── Action buttons:
│   ├── "Still happening" (confirm)
│   ├── "Resolved" (report resolution)
│   ├── "Share" (WhatsApp/copy link)
│   └── "Navigate" (open in maps)
```

### Mobile PWA Enhancements

- **Add to Home Screen:** Native app-like experience
- **Push Notifications:** Via service worker
- **Offline Mode:** View cached reports, queue submissions
- **Location Background:** Track for relevant alerts (with permission)
- **Quick Actions:** Long-press for report, query, or share

### Report Submission Flow (Enhanced)

```
Step 1: Capture
├── Take photo/video
├── Select from gallery
└── Text-only report

Step 2: Location
├── Auto-detect GPS
├── Pick on map
├── Search address
└── Share current location

Step 3: Details
├── AI auto-suggests:
│   ├── Category (from image)
│   ├── Severity (from image)
│   └── Description (from image)
├── User can edit/override
└── Add additional notes

Step 4: Submit
├── Show preview
├── Submit button
└── Share to WhatsApp option

Step 5: Confirmation
├── Report ID
├── Current status
├── Expected processing time
└── "Subscribe to updates" option
```

---

## Agent Workflows

### Alert Generation Agent

```yaml
name: alert_generation_agent
trigger:
  - new_cluster_detected
  - authority_broadcast
  - severity_threshold_exceeded

steps:
  1. analyze_event:
      - Determine affected area (geohashes)
      - Calculate impact radius
      - Identify affected user segments

  2. generate_content:
      - Create alert title
      - Write description (concise, actionable)
      - Add relevant details (source, ETA, alternatives)
      - Translate to supported languages

  3. determine_recipients:
      - Query subscribed users in affected area
      - Filter by alert preferences
      - Respect quiet hours

  4. send_alerts:
      - Queue WhatsApp messages
      - Send push notifications
      - Update dashboard

  5. track_metrics:
      - Log send attempts
      - Track delivery status
      - Monitor engagement
```

### Escalation Agent

```yaml
name: escalation_agent
trigger:
  - high_severity_report (severity >= 8)
  - no_authority_response (timeout: 15min)
  - cluster_size_exceeded (count >= 5)

steps:
  1. assess_situation:
      - Compile all related reports
      - Calculate aggregate severity
      - Identify affected population

  2. identify_authority:
      - Match category to authority type
      - Find authority for jurisdiction
      - Check authority availability

  3. prepare_escalation:
      - Generate summary report
      - Attach evidence (images, locations)
      - Add citizen report count
      - Include historical context

  4. send_escalation:
      - Notify via dashboard
      - Send email
      - Send WhatsApp (if configured)
      - Log escalation event

  5. monitor_response:
      - Set response timeout (15min)
      - If no response → escalate to supervisor
      - If supervisor timeout → notify district admin
```

### Resolution Agent

```yaml
name: resolution_agent
trigger:
  - authority_marks_resolved
  - auto_expire_timeout
  - citizen_confirms_resolved (count >= 3)

steps:
  1. verify_resolution:
      - Check resolution source
      - For auto-expire: verify no recent confirmations
      - For citizen: check confirmation count

  2. update_status:
      - Mark report as resolved
      - Update cluster if applicable
      - Record resolution details

  3. notify_stakeholders:
      - Alert users who reported/upvoted
      - Message: "Issue resolved" + details
      - Request feedback (optional)

  4. archive_for_analysis:
      - Calculate resolution time
      - Log resolution path
      - Update authority metrics
      - Feed into pattern analysis
```

### Duplicate Detection Agent

```yaml
name: duplicate_detection_agent
trigger:
  - new_report_created

steps:
  1. exact_match_check:
      - Compare image hash (SHA256)
      - If match → mark as duplicate immediately

  2. proximity_check:
      - Query reports in same geohash (precision 6)
      - Filter by same category
      - Filter by time window (24h for infrastructure, 2h for disruptions)

  3. similarity_analysis:
      - If candidates found:
        - Compare descriptions (semantic similarity)
        - Compare images (Gemini visual comparison)
        - Calculate confidence score

  4. decide_action:
      - Confidence > 90%: Auto-merge
      - Confidence 70-90%: Link as related
      - Confidence < 70%: Keep separate

  5. update_records:
      - Add to cluster if merged
      - Update confirmation count
      - Notify original reporter (optional)
```

---

## Multilingual Support

### Supported Languages (Initial)

| Language | Code | Script | Priority |
|----------|------|--------|----------|
| English | en | Latin | P0 |
| Hindi | hi | Devanagari | P0 |
| Marathi | mr | Devanagari | P1 |
| Tamil | ta | Tamil | P1 |
| Telugu | te | Telugu | P1 |
| Kannada | kn | Kannada | P2 |
| Bengali | bn | Bengali | P2 |

### Processing Pipeline

```
Input (any language/script)
         │
         ▼
Language Detection (Gemini)
         │
         ▼
┌────────┴────────┐
│ Structured Data │
│   Extraction    │
└────────┬────────┘
         │
    Standardized JSON
    (English keys, original values preserved)
         │
         ▼
┌────────┴────────┐
│    Storage      │
│ (Multilingual)  │
└────────┬────────┘
         │
         ▼
┌────────┴────────┐
│ Output Generation│
│ (User's language)│
└─────────────────┘
```

### Code-Mixed Text Handling

Common in India: "Yahan pe bohot traffic hai near City Mall"

```python
async def process_mixed_language_text(text: str) -> dict:
    """
    Process code-mixed text (Hindi-English common in India).
    """
    prompt = """
    Analyze this message which may be in Hindi, English, or mixed.
    Extract:
    1. Event type (traffic, power, water, safety, infrastructure, community)
    2. Location mentioned (if any)
    3. Severity (1-10)
    4. Key details

    Respond in JSON format.

    Message: {text}
    """

    response = await gemini.generate(prompt.format(text=text))
    return parse_json(response)
```

### Alert Templates (Multilingual)

```python
ALERT_TEMPLATES = {
    "traffic_congestion": {
        "en": "🚦 TRAFFIC ALERT: Heavy traffic on {location}. Expect {delay} delay. Alternative: {alternative}",
        "hi": "🚦 ट्रैफिक अलर्ट: {location} पर भारी ट्रैफिक। {delay} की देरी। विकल्प: {alternative}",
        "mr": "🚦 ट्रॅफिक अलर्ट: {location} वर जास्त ट्रॅफिक. {delay} उशीर. पर्याय: {alternative}"
    },
    "power_outage": {
        "en": "⚡ POWER ALERT: Outage in {location}. Expected restoration: {eta}. Reason: {reason}",
        "hi": "⚡ बिजली अलर्ट: {location} में बिजली गुल। बहाली: {eta}। कारण: {reason}",
        "mr": "⚡ वीज अलर्ट: {location} मध्ये वीज गेली. पुनर्स्थापना: {eta}. कारण: {reason}"
    }
}
```

---

## Migration Path

### Phase 1: Foundation (4-6 weeks)

**Goals:** Extend Darshi data model, add real-time capabilities

**Tasks:**
- [ ] Extend report schema with new fields
- [ ] Add new event categories (disruptions, community, safety)
- [ ] Implement temporal validity (valid_until, auto_expire)
- [ ] Add clustering logic
- [ ] Create real-time map view with filters
- [ ] Set up BigQuery analytics pipeline

**Deliverables:**
- Extended API supporting all event types
- Real-time dashboard with live map
- Basic clustering and duplicate detection

### Phase 2: WhatsApp Integration (6-8 weeks)

**Goals:** Enable two-way WhatsApp communication

**Tasks:**
- [ ] Set up WhatsApp Business API account
- [ ] Implement webhook receiver for incoming messages
- [ ] Build message parsing and intent detection
- [ ] Integrate Gemini for message/image analysis
- [ ] Create outbound messaging service
- [ ] Implement user subscription management
- [ ] Design and approve message templates
- [ ] Build basic alert broadcasting

**Deliverables:**
- Citizens can report via WhatsApp
- Citizens can query status via WhatsApp
- System can broadcast alerts to subscribed users

### Phase 3: Authority Layer (4-6 weeks)

**Goals:** Enable authority verification and broadcasting

**Tasks:**
- [ ] Design authority dashboard UI
- [ ] Implement authority authentication
- [ ] Build broadcast composition interface
- [ ] Create verification workflow
- [ ] Implement escalation logic
- [ ] Add authority analytics
- [ ] Onboard pilot authorities (traffic police, electricity)

**Deliverables:**
- Authority dashboard for verification and broadcasting
- Automated escalation pipeline
- Authority performance metrics

### Phase 4: Intelligence (6-8 weeks)

**Goals:** Add predictive capabilities

**Tasks:**
- [ ] Build pattern detection queries (BigQuery)
- [ ] Train Vertex AI classification models
- [ ] Implement prediction pipeline
- [ ] Create predictive alert system
- [ ] Add personalized recommendations
- [ ] Build correlation detection

**Deliverables:**
- Predictive alerts for common patterns
- Personalized route/timing suggestions
- Correlation-based early warning

### Phase 5: Scale & Optimize (Ongoing)

**Goals:** Multi-city deployment, optimization

**Tasks:**
- [ ] Multi-tenant architecture
- [ ] City-specific configuration
- [ ] Regional language expansion
- [ ] Performance optimization
- [ ] Cost optimization (WhatsApp messages, AI calls)
- [ ] Advanced analytics and reporting

**Deliverables:**
- Multi-city deployment capability
- Comprehensive admin analytics
- Optimized costs at scale

---

## Challenges & Mitigations

### 1. WhatsApp Business API Costs

**Challenge:** Per-message pricing (₹0.50-1.50 per message) can be expensive at scale.

**Mitigations:**
- Batch alerts to reduce message count
- Use user-initiated conversations (free for 24h)
- Implement smart throttling (don't over-alert)
- Encourage web dashboard for non-urgent queries
- Tiered subscription (free: limited alerts, premium: all alerts)

### 2. Spam and Fake Reports

**Challenge:** Bad actors could flood system with false reports.

**Mitigations:**
- AI verification of images (Gemini)
- Reputation scoring for users
- Rate limiting per user
- Require location verification
- Community flagging of false reports
- Phone number verification for WhatsApp

### 3. Authority Adoption

**Challenge:** Government agencies may be slow to adopt new technology.

**Mitigations:**
- Start with progressive authorities (traffic police often tech-savvy)
- Provide clear ROI metrics
- Minimal training required (simple dashboard)
- Integration with existing systems via API
- Pilot program with measurable outcomes

### 4. Alert Fatigue

**Challenge:** Too many notifications = users ignore them.

**Mitigations:**
- Severity-based filtering
- User-controlled preferences
- Smart aggregation (one alert for cluster, not each report)
- Quiet hours respect
- Relevance scoring based on user patterns
- Easy unsubscribe

### 5. Privacy Concerns

**Challenge:** Location tracking and message content are sensitive.

**Mitigations:**
- Explicit opt-in for location services
- Data minimization (only collect what's needed)
- Clear privacy policy
- No location history storage (only current subscriptions)
- Anonymization for analytics
- GDPR/India DPDP compliance

### 6. Misinformation Risk

**Challenge:** Unverified reports could cause panic or misdirection.

**Mitigations:**
- AI verification before broadcasting
- Authority verification for safety alerts
- Clear labeling (citizen report vs verified)
- Community confirmation requirements
- Rapid correction mechanism
- Legal disclaimer for unverified content

### 7. System Reliability

**Challenge:** System must work during actual emergencies when most needed.

**Mitigations:**
- Multi-region deployment
- Graceful degradation
- Offline capability for web app
- WhatsApp as backup (highly reliable)
- Circuit breakers for external services
- Regular disaster recovery testing

### 8. Moderation at Scale

**Challenge:** Can't manually review all reports.

**Mitigations:**
- AI-first moderation (Gemini)
- Confidence thresholds (auto-approve high confidence)
- Community moderation (trusted users)
- Authority override capability
- Automated escalation for edge cases

---

## Tech Stack

### Aligned with Google AI Ecosystem

| Component | Technology | Purpose |
|-----------|------------|---------|
| AI Analysis | **Gemini** | Multimodal verification (images, videos, text) |
| ML Models | **Vertex AI** | Event classification, clustering, predictions |
| Real-time DB | **Firebase/Firestore** | Reports, subscriptions, live data |
| Analytics | **BigQuery** | Historical patterns, hotspots, insights |
| Deployment | **Firebase Studio** | Rapid iteration, hosting |
| Automation | **Agent Builder** | Alert generation, escalation workflows |
| Backend | **FastAPI (Python)** | API server, business logic |
| Frontend | **SvelteKit** | Web dashboard, PWA |
| Messaging | **WhatsApp Business API** | Citizen communication |
| Maps | **Google Maps Platform** | Visualization, geocoding |
| Storage | **Google Cloud Storage** | Images, videos |
| Auth | **Firebase Auth** | User authentication |

### Integration Points

```
┌──────────────────────────────────────────────────────────┐
│                    DARSHI CORE                           │
├──────────────────────────────────────────────────────────┤
│  FastAPI Backend                                         │
│  ├── Existing: Report, Auth, Admin APIs                 │
│  ├── New: WhatsApp webhook, Authority APIs              │
│  └── New: Subscription, Alert APIs                      │
├──────────────────────────────────────────────────────────┤
│  SvelteKit Frontend                                      │
│  ├── Existing: Report submission, Admin dashboard       │
│  ├── New: Real-time map, Filters                        │
│  └── New: Authority dashboard                           │
└──────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
    │   Gemini     │ │ Vertex   │ │  BigQuery    │
    │   API        │ │ AI       │ │              │
    ├──────────────┤ ├──────────┤ ├──────────────┤
    │ • Image      │ │ • Event  │ │ • Patterns   │
    │   analysis   │ │   class- │ │ • Hotspots   │
    │ • Text       │ │   ifier  │ │ • Predictions│
    │   processing │ │ • Cluster│ │ • Reports    │
    │ • Validation │ │   models │ │              │
    └──────────────┘ └──────────┘ └──────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
    │  Firestore   │ │  GCS     │ │ WhatsApp     │
    │              │ │          │ │ Business API │
    ├──────────────┤ ├──────────┤ ├──────────────┤
    │ • Reports    │ │ • Images │ │ • Inbound    │
    │ • Users      │ │ • Videos │ │ • Outbound   │
    │ • Subs       │ │ • Docs   │ │ • Templates  │
    │ • Alerts     │ │          │ │              │
    └──────────────┘ └──────────┘ └──────────────┘
```

---

## Success Metrics

### Citizen Engagement
- WhatsApp subscribers per city
- Report submission rate (web + WhatsApp)
- Alert open/read rates
- Query response satisfaction
- Time to resolution (citizen-reported)

### Authority Adoption
- Authorities onboarded per city
- Verified alerts published
- Response time to citizen escalations
- Resolution rate for escalated issues

### Platform Health
- AI verification accuracy
- False positive/negative rates
- Duplicate detection accuracy
- Prediction accuracy
- System uptime
- Message delivery rate

### City Impact
- Average time to public awareness (before vs after)
- Reduction in misinformation incidents
- Citizen satisfaction surveys
- Authority efficiency metrics
- Media coverage / public perception

---

## Conclusion

Integrating Nagar Alert Hub with Darshi creates a comprehensive civic intelligence platform that:

1. **Leverages existing strengths:** Darshi's AI verification, geospatial capabilities, and robust backend
2. **Addresses real needs:** WhatsApp-based communication for maximum reach in Tier-2/3 cities
3. **Connects stakeholders:** Citizens, authorities, and the platform in a unified ecosystem
4. **Scales intelligently:** From reactive reporting to predictive alerts

The phased migration path ensures we can deliver value incrementally while building toward the full vision.

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Part of: Darshi Civic Suite*
