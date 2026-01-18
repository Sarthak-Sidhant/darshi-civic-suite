# Darshi Unified Integration Architecture
> **Status:** Draft
> **Version:** 1.0

This document outlines the infrastructure and architectural plan for hosting and managing the suite of Darshi integrations (Fund Tracking, Govt Communication, Grivredr, Nagar Alert Hub, Official Directory).

**Core Principle:** A secure, event-driven ecosystem where identifying a signal in one system (e.g., a power cut report) instantly propagates to others (e.g., alert hub, official directory) without exposing internal logic to the outside world.

---

## 1. High-Level Architecture: The "Civic Intelligence Grid"

We will move from a monolithic app to a **Modulith (Modular Monolith)** or **Microservices** architecture (depending on scale) centered around a shared **Event Bus**.

### System Diagram

```mermaid
graph TD
    subgraph "External World (Untrusted)"
        User[Citizens / Web / App]
        Gov[Govt Portals]
        AuthBroad[Authority Broadcasts]
    end

    subgraph "Security Perimeter (DMZ)"
        API_GW[**API Gateway**<br/>Rate Limiting, WAF, AuthZ]
    end

    subgraph "Darshi Core Ecosystem (Private Network)"
        %% The Central Nervous System
        EventBus{**Event Bus**<br/>(Kafka / PubSub)}

        %% Shared Infrastructure Services
        AuthService[**Identity Service**<br/>Unified Auth & RBAC]
        AIGateway[**AI Gateway**<br/>Gemini/Vertex Cost & Policy Control]
        GeoEngine[**Geo Service**<br/>Location Normalization]

        %% Domain Services (The Integrations)
        FundSvc[**Fund Tracker Service**<br/>MP/MLA Analytics]
        CommSvc[**Public Comm Service**<br/>Announcement Translation]
        AlertSvc[**Nagar Alert Hub**<br/>Real-time Disruptions]
        DirSvc[**Directory Service**<br/>Official Hierarchy]
        
        %% The "Factory" (Isolated)
        Grivredr[**Grivredr Engine**<br/>Scraper Factory & Execution]
    end

    %% Flow Connections
    User -->|HTTPS| API_GW
    AuthBroad -->|HTTPS| API_GW
    API_GW --> AuthService
    API_GW --> AlertSvc
    API_GW --> FundSvc
    API_GW --> CommSvc
    API_GW --> DirSvc

    %% Internal Communication
    AlertSvc <--> EventBus
    CommSvc <--> EventBus
    DirSvc <--> EventBus
    FundSvc <--> EventBus
    
    %% AI Usage
    AlertSvc --> AIGateway
    CommSvc --> AIGateway
    Grivredr --> AIGateway
    DirSvc --> AIGateway

    %% Scraping Logic
    Grivredr -->|Scrapes| Gov
    CommSvc -->|Fetches| Gov
    FundSvc -->|Fetches| Gov
```

---

## 2. Infrastructure Plan

### A. Compute & Hosting
*   **Containerization:** Docker for all services.
*   **Orchestration:** Kubernetes (GKE) or Cloud Run (for serverless scalability).
*   **Isolation:**
    *   **Public Services:** (Alerts, Dashboard) run in public-facing subnet.
    *   **Restricted Services:** (Grivredr, Scrapers) run in private subnets with strict egress rules (only allowing whitelisted govt domains).

### B. Communication Strategy (Inter-Service)
Services should **not** talk directly via HTTP where possible. Instead, they should emit **Domain Events**.

**Example Workflow: "Power Outage Reported"**
1.  **Nagar Alert Hub** receives a user report: "Power cut in Koramangala".
2.  **Nagar Alert Hub** validates it and publishes event: `event.disruption.power_outage { loc: "Koramangala" }`.
3.  **Directory Service** listens to `event.disruption.*`. It automatically looks up the "BESCOM Assistant Engineer" for Koramangala and attaches that contact info to the event metadata.
4.  **Comm Service** listens to `event.disruption.*`. It checks if there are any official circulars about "Scheduled Maintenance" in Koramangala today. If yes, it links the official reason.
5.  **Result:** The final alert sent to users contains: *The report + The Official to Call + The Official Reason*, all assembled asynchronously.

### C. Data Storage
*   **Hot Storage (Real-time):** Firestore (for Alerts, User Sessions).
*   **Warm Storage (Structured):** PostgreSQL (for Official Directory, Fund Projects).
*   **Cold Storage (Analytics):** BigQuery (for historical analysis of patterns).
*   **Vector Store:** pgvector or Pinecone (for semantic search in Directory & Announcements).

---

## 3. Security & Anti-Abuse Architecture
"No third party can utilize or abuse our tool." → This requires a **Zero Trust** approach.

### Layer 1: The Fortress Gate (API Gateway)
*   **Strict Rate Limiting:** Per IP, per User ID, and per Endpoint.
    *   *Example:* An unverified user can only request "Search Officials" 5 times/minute.
*   **API Key Management:** Internal keys for our frontend/mobile app are rotated daily.
*   **Bot Detection:** Integrate Cloud Armor or Cloudflare to block scrapers trying to scrape *our* data.

### Layer 2: Service Identity (mTLS)
*   **Internal Trust:** Service A can only talk to Service B if it presents a valid cryptographic certificate.
*   **Benefit:** If an attacker compromises the "Web Dashboard", they cannot directly command the "Grivredr Engine" to attack a target because they lack the specific mTLS certificate.

### Layer 3: The AI Guardian (AI Gateway)
*   **Prompt Injection Defense:** A middleware layer that scans all user inputs before sending them to Gemini.
    *   *Blocks:* "Ignore previous instructions", "Generate toxic content".
*   **Cost Firewall:** Strict budget caps. If "Fund Tracker" burns 50% of the daily budget, it is throttled automatically to save capacity for "Critical Alerts".

### Layer 4: The Grivredr Sandbox
*   **Risk:** Scrapers can be abused to DDoS sites.
*   **Control:**
    *   **Egress Filtering:** Grivredr containers can ONLY connect to domains explicitly whitelisted in the database (e.g., `*.gov.in`).
    *   **Rate Governance:** "Politeness" policies enforced at the network level (e.g., max 1 request per 2 seconds to `mplads.gov.in`).

---

## 4. Integration Logic: How they speak

### Shared Services
Instead of duplicating logic, these Core Services power the integrations:

1.  **`GeoService`**:
    *   **Input:** "Ward 98", "Koramangala", Lat/Long.
    *   **Output:** Standardized `place_id`, `geohash`, `parent_jurisdiction`.
    *   *Used by:* Fund Tracker (Project mapping), Alerts (Geofencing), Directory (Jurisdiction lookup).

2.  **`AuthService`**:
    *   **Role:** Central User Profile.
    *   *Feature:* A user subscribes to "Water Alerts" in Nagar Alert Hub. This preference is stored centrally. When the Fund Tracker shows a new "Water Pipeline Project" in their area, we can notify them because we know their interest.

### Cross-Pollination Examples

| Trigger Event | Source System | Reactive Action | Target System |
| :--- | :--- | :--- | :--- |
| **New MP Fund Project Sanctioned** | Fund Tracker | "Is this a road project?" -> Create 'Road Work' alert for residents | Nagar Alert Hub |
| **New Govt Circular: "Heavy Rain Alert"** | Comm Service | Broadcast "Weather Warning" to relevant districts | Nagar Alert Hub |
| **User queries: "Who fixes road?"** | Directory Svc | If user location has active "Road Work" alert, show that first | Nagar Alert Hub |
| **Scraper breaks on Portal Change** | Grivredr | Notify Admin -> Trigger "Maintenance Mode" for that data source | Core Dashboard |

---

## 5. Technology Stack Recommendations

*   **Language:** Python (FastAPI) for AI/Scraping services; Go or Node.js for high-throughput Alert Hub.
*   **Communication:** gRPC (Internal), GraphQL (Frontend Aggregation).
*   **Event Bus:** Google Pub/Sub (serverless, ideal for GCP).
*   **AI:** Vertex AI (Gemini Pro) for logic, Vertex AI Vision for image verification.

## 6. Implementation Stages

1.  **Phase 1: The Core Grid.** Set up the API Gateway, Auth Service, and Pub/Sub Event Bus.
2.  **Phase 2: Independent Cells.** Deploy `Directory Service` and `Comm Service` as standalone modules connected to the Grid.
3.  **Phase 3: The Nervous System.** Implement the Event Bus logic to make them talk (e.g., Directory enriching Alerts).
4.  **Phase 4: The Fortress.** Implement full mTLS, aggressive rate limiting, and the Grivredr sandbox.
