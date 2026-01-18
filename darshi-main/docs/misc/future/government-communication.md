# Government Communication Platform Integration

> Making Government Announcements Accessible Through AI-Powered Translation

**Part of: Darshi Civic Suite**

This document outlines the integration strategy for making government circulars and announcements accessible to all citizens regardless of language barriers or literacy levels.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture](#architecture)
5. [Data Model](#data-model)
6. [Content Pipeline](#content-pipeline)
7. [Translation & Simplification](#translation--simplification)
8. [Audio Generation](#audio-generation)
9. [User Interface](#user-interface)
10. [Discovery & Aggregation](#discovery--aggregation)
11. [Migration Path](#migration-path)
12. [Challenges & Mitigations](#challenges--mitigations)
13. [Tech Stack](#tech-stack)

---

## Executive Summary

**Problem:** Government announcements are published in inaccessible bureaucratic language, often only in English or regional languages, excluding large portions of the population.

**Solution:** Automatically fetch, translate, simplify, and deliver government announcements in plain language across multiple formats (text, audio) and languages.

**Value Proposition:** Every citizen can understand what their government is saying, regardless of education level or language preference.

---

## Problem Statement

### The Accessibility Crisis

1. **Bureaucratic Language Barrier**
   - Government documents use complex legal/administrative English
   - Example: "The undersigned is directed to bring to your notice..."
   - Citizens need: "Important update about..."

2. **Language Diversity**
   - National announcements often only in English/Hindi
   - State/district announcements only in regional language
   - Migrants don't speak local language
   - No pan-India unified access point

3. **Literacy Challenges**
   - ~25% of Indian adults have limited literacy
   - Cannot read long PDF circulars
   - Need audio/video formats

4. **Scattered Sources**
   - Ministry websites (50+ national ministries)
   - State government portals (28+ states)
   - District administration websites (700+ districts)
   - No single place to check "what did government announce today?"

5. **Discovery Problem**
   - Even tech-savvy citizens don't know where to look
   - Critical announcements buried in PDFs
   - No search across all government sources

### Current Gaps in Darshi

Darshi focuses on:
- Citizen → Government (reporting issues)
- Reactive problem-solving

Missing:
- Government → Citizen (announcements, policies)
- Proactive information dissemination
- Multi-modal accessibility (audio, simplified text)

---

## Solution Overview

### Platform Capabilities

1. **Universal Aggregation**
   - Scrape/fetch announcements from all government sources
   - National ministries, state governments, district offices
   - Support multiple formats: web pages, PDFs, press releases

2. **AI-Powered Translation**
   - Translate to 8+ Indian languages
   - Maintain meaning and context
   - Handle domain-specific terminology

3. **Simplification**
   - Rewrite bureaucratic language into plain language
   - "Grade 5 reading level" versions available
   - Extract key points, deadlines, affected citizens

4. **Multi-Modal Output**
   - Text (web, mobile)
   - Audio (text-to-speech in native languages)
   - Summary cards (visual, shareable)
   - WhatsApp integration (leveraging Nagar Alert Hub)

5. **Personalization**
   - Filter by location (state, district, city)
   - Filter by category (health, education, employment, etc.)
   - Subscribe to specific topics
   - Get notified of relevant announcements

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GOVERNMENT SOURCES                            │
├─────────────────────────────────────────────────────────────────┤
│  Ministry     State Gov    District     PIB          Gazette    │
│  Websites     Portals      Offices      (Press)      of India   │
└──────┬────────────┬──────────┬────────────┬────────────┬────────┘
       │            │          │            │            │
       ▼            ▼          ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  Web Scrapers  │  RSS Feeds  │  API Clients  │  PDF Parsers    │
│  (Grivredr)    │             │               │                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRACTION LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Content Extraction (from HTML, PDF, images)                    │
│  Metadata Extraction (date, ministry, category, jurisdiction)   │
│  Deduplication (same announcement from multiple sources)        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI PROCESSING LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Gemini Multimodal Processing                                   │
│  ├── Language Detection                                         │
│  ├── Content Classification (category, urgency, audience)       │
│  ├── Translation to 8+ languages                                │
│  ├── Simplification (multiple reading levels)                   │
│  ├── Key Information Extraction (deadlines, eligibility, etc.)  │
│  └── Summary Generation                                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AUDIO GENERATION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  Text-to-Speech (Google Cloud TTS / ElevenLabs)                 │
│  ├── Generate audio in user's preferred language                │
│  ├── Natural, conversational voice                              │
│  └── Cache generated audio files                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  Firestore (Real-time)           │  Cloud Storage               │
│  ├── Announcements               │  ├── Original PDFs           │
│  ├── Translations                │  ├── Generated audio         │
│  ├── User subscriptions          │  └── Summary cards           │
│  └── Notification queue          │                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  Web Portal    Mobile App    WhatsApp    Voice        Email     │
│  (Darshi)      (PWA)         (Alerts)    (Hotline)    (Digest)  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. Discovery Layer
- **Web Scrapers:** Grivredr-powered adaptive scrapers for government portals
- **RSS Feeds:** Where available (PIB, some ministries)
- **API Clients:** For government APIs (e.g., data.gov.in)
- **PDF Parsers:** Extract text from scanned/native PDFs

#### 2. Extraction Layer
- **Content Extraction:** Clean HTML, parse PDFs, OCR images
- **Metadata Extraction:** Date, ministry, category, geography
- **Deduplication:** Hash-based + semantic similarity

#### 3. AI Processing Layer
- **Gemini:** Translation, simplification, summarization
- **Classification:** Auto-categorize by topic and audience

#### 4. Audio Generation Layer
- **TTS:** Natural-sounding audio in multiple languages
- **Caching:** Store generated audio to avoid redundant processing

---

## Data Model

### Announcement Schema

```python
# Collection: announcements
{
    "id": "uuid",
    "title": {
        "original": "string",  # Original title
        "en": "string",        # English
        "hi": "string",        # Hindi
        "mr": "string",        # Marathi
        # ... other languages
    },

    # Original content
    "content": {
        "original": {
            "text": "string",       # Extracted text
            "language": "en|hi|...",
            "format": "html|pdf|text"
        },
        "source_url": "string",
        "source_pdf_url": "string | null",
        "source_document_id": "string | null"
    },

    # Processed content
    "translations": {
        "en": {
            "full": "string",           # Full translation
            "simplified": "string",      # Grade 5 level
            "summary": "string",         # 2-3 sentence summary
            "key_points": [...]          # Bullet points
        },
        "hi": {...},
        # ... other languages
    },

    # Audio versions
    "audio_urls": {
        "en": "gs://bucket/announcements/{id}/en.mp3",
        "hi": "gs://bucket/announcements/{id}/hi.mp3",
        # ... other languages
    },

    # Metadata
    "source": {
        "ministry": "Ministry of Health",
        "department": "Department of Health Services",
        "state": "Maharashtra | null",  # null for national
        "district": "Pune | null",
        "level": "national|state|district|municipal"
    },

    # Classification
    "category": "health|education|employment|infrastructure|finance|...",
    "subcategory": "vaccination|admission|jobs|...",
    "tags": ["covid", "vaccination", "children"],

    "urgency": "low|medium|high|critical",
    "audience": ["citizens", "businesses", "farmers", ...],

    # Geographic scope
    "jurisdiction": {
        "type": "national|state|district|city",
        "state": "string | null",
        "district": "string | null",
        "city": "string | null",
        "geohashes": [...]  # Affected areas
    },

    # Important dates
    "published_date": timestamp,
    "effective_date": timestamp | null,
    "deadline": timestamp | null,
    "expiry_date": timestamp | null,

    # Processing metadata
    "discovered_at": timestamp,
    "processed_at": timestamp,
    "last_updated": timestamp,
    "processing_status": "pending|processing|completed|failed",
    "translation_status": {
        "en": "completed",
        "hi": "completed",
        # ...
    },

    # Engagement metrics
    "views": int,
    "audio_plays": int,
    "shares": int,

    # Deduplication
    "content_hash": "sha256",
    "duplicate_of": "uuid | null",
    "related_announcements": [...]
}
```

### User Subscription Schema

```python
# Collection: announcement_subscriptions
{
    "user_id": "string",
    "phone_number": "string",  # For WhatsApp
    "email": "string | null",

    # Language preference
    "preferred_language": "en|hi|mr|...",
    "reading_level": "original|simplified",  # Simplified = Grade 5 level
    "prefer_audio": bool,

    # Location-based filters
    "location": {
        "state": "string | null",
        "district": "string | null",
        "city": "string | null"
    },
    "include_national": bool,  # Subscribe to national announcements

    # Topic-based filters
    "categories": ["health", "education", "employment"],
    "tags": ["covid", "scholarship", "farmer"],

    # Notification preferences
    "notification_channels": ["whatsapp", "email", "push", "sms"],
    "urgency_threshold": "medium|high|critical",  # Only notify for these
    "digest_frequency": "realtime|daily|weekly|none",

    "created_at": timestamp,
    "updated_at": timestamp
}
```

### Source Registry Schema

```python
# Collection: government_sources
{
    "id": "uuid",
    "name": "Ministry of Health and Family Welfare",
    "url": "https://mohfw.gov.in",
    "type": "ministry|state_gov|district_office|psu|authority",

    "scraping_config": {
        "method": "rss|scraper|api",
        "scraper_id": "string | null",  # Grivredr scraper ID
        "rss_url": "string | null",
        "api_endpoint": "string | null",
        "selectors": {...}  # CSS selectors for content
    },

    "update_frequency": "hourly|daily|weekly",
    "last_scraped": timestamp,
    "next_scrape": timestamp,

    "jurisdiction": {
        "level": "national|state|district",
        "state": "string | null",
        "district": "string | null"
    },

    "primary_language": "en|hi|...",
    "status": "active|paused|error",

    "created_at": timestamp
}
```

---

## Content Pipeline

### Discovery & Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULED SCRAPER                             │
│              (Runs hourly/daily per source config)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                    Check source type
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   RSS    │    │  Scraper │    │   API    │
    │  Parser  │    │ (Grivredr)│   │  Client  │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
                  Extract content
                  (HTML/PDF/Image)
                         │
                         ▼
                  Extract metadata
                  (date, ministry, etc.)
                         │
                         ▼
                  Calculate content hash
                         │
                         ▼
                  Check for duplicate
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    New content    Duplicate        Updated
                   (skip)           (version)
         │                              │
         └──────────────┬───────────────┘
                        │
                        ▼
              Create announcement record
                        │
                        ▼
              Queue for AI processing
```

### AI Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│               ANNOUNCEMENT PROCESSING PIPELINE                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                 Step 1: Language Detection
                 (Gemini identifies source language)
                           │
                           ▼
                 Step 2: Content Analysis
                 Extract:
                 • Category (health, education, etc.)
                 • Urgency (low, medium, high, critical)
                 • Audience (citizens, businesses, etc.)
                 • Key dates (deadline, effective date)
                 • Geographic scope
                           │
                           ▼
                 Step 3: Translation (Parallel)
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         Translate to  Translate to  Translate to
         English (en)  Hindi (hi)    Marathi (mr)
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                 Step 4: Simplification
                 For each language:
                 • Original (bureaucratic)
                 • Simplified (Grade 5 level)
                 • Summary (2-3 sentences)
                 • Key points (bullets)
                           │
                           ▼
                 Step 5: Audio Generation
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         TTS: English  TTS: Hindi   TTS: Marathi
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                 Step 6: Store & Publish
                 • Save to Firestore
                 • Upload audio to GCS
                 • Index for search
                 • Trigger notifications
```

---

## Translation & Simplification

### Translation Strategy

**Approach:** Context-aware, domain-specific translation

```python
async def translate_announcement(
    content: str,
    source_language: str,
    target_language: str,
    metadata: dict
) -> dict:
    """
    Translate government announcement with context preservation.
    """
    prompt = f"""
    You are translating an official government announcement from {source_language} to {target_language}.

    Context:
    - Ministry/Department: {metadata['ministry']}
    - Category: {metadata['category']}
    - Audience: {metadata['audience']}

    IMPORTANT:
    1. Preserve all technical terms, schemes names, dates, numbers
    2. Maintain official tone
    3. Keep formatting (paragraphs, bullets, headings)
    4. Translate idioms contextually, don't transliterate

    Original text:
    {content}

    Provide translation in {target_language}.
    """

    response = await gemini.generate(prompt)
    return {
        "translated_text": response,
        "language": target_language,
        "confidence": extract_confidence(response)
    }
```

### Simplification Strategy

**Goal:** Make content accessible to Grade 5 reading level

```python
async def simplify_content(
    content: str,
    language: str,
    target_level: str = "grade5"
) -> dict:
    """
    Rewrite bureaucratic language into plain language.
    """
    prompt = f"""
    Rewrite this government announcement in simple {language}.

    Target audience: Someone with {target_level} education level.

    Guidelines:
    1. Use simple, common words (avoid: "aforementioned", "henceforth")
    2. Short sentences (max 15-20 words)
    3. Active voice ("Government will provide" not "will be provided by government")
    4. Explain technical terms in parentheses
    5. Keep all important information (dates, eligibility, procedures)

    EXAMPLES:
    ❌ "The undersigned is directed to bring to your notice that..."
    ✅ "Important update:"

    ❌ "Eligible beneficiaries may avail of the scheme..."
    ✅ "If you qualify, you can get benefits from this program..."

    Original text:
    {content}

    Provide simplified version:
    """

    response = await gemini.generate(prompt)
    return {
        "simplified_text": response,
        "reading_level": target_level
    }
```

### Summary Generation

```python
async def generate_summary(content: str, language: str) -> dict:
    """
    Generate multi-level summaries.
    """
    prompt = f"""
    Generate summaries of this government announcement in {language}.

    Provide:
    1. TLDR (1 sentence, max 20 words)
    2. Short summary (2-3 sentences)
    3. Key points (3-5 bullet points)
    4. Action items (what citizens need to do, if any)

    Original text:
    {content}

    Format response as JSON.
    """

    response = await gemini.generate(prompt)
    return parse_json(response)
```

---

## Audio Generation

### Text-to-Speech Pipeline

```python
class AnnouncementAudioGenerator:
    """
    Generate natural-sounding audio for announcements.
    Uses Google Cloud TTS with WaveNet voices.
    """

    def __init__(self):
        self.tts_client = texttospeech.TextToSpeechClient()
        self.storage_client = storage.Client()

    async def generate_audio(
        self,
        announcement_id: str,
        text: str,
        language: str,
        reading_level: str = "simplified"
    ) -> str:
        """
        Generate audio file and upload to Cloud Storage.
        """
        # Select voice based on language
        voice = self._select_voice(language)

        # Prepare text (add pauses for better comprehension)
        processed_text = self._prepare_text_for_audio(text)

        # Generate audio
        synthesis_input = texttospeech.SynthesisInput(text=processed_text)

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9,  # Slightly slower for clarity
            pitch=0.0
        )

        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Upload to Cloud Storage
        filename = f"announcements/{announcement_id}/{language}_{reading_level}.mp3"
        blob = self.storage_client.bucket(BUCKET_NAME).blob(filename)
        blob.upload_from_string(response.audio_content, content_type="audio/mpeg")

        # Make public
        blob.make_public()

        return blob.public_url

    def _select_voice(self, language: str) -> texttospeech.VoiceSelectionParams:
        """Select appropriate WaveNet voice for language."""
        voice_map = {
            "en": ("en-IN", "en-IN-Wavenet-D"),  # Indian English, male
            "hi": ("hi-IN", "hi-IN-Wavenet-A"),  # Hindi, female
            "mr": ("mr-IN", "mr-IN-Wavenet-A"),  # Marathi
            "ta": ("ta-IN", "ta-IN-Wavenet-A"),  # Tamil
            "te": ("te-IN", "te-IN-Wavenet-A"),  # Telugu
            "bn": ("bn-IN", "bn-IN-Wavenet-A"),  # Bengali
            "gu": ("gu-IN", "gu-IN-Wavenet-A"),  # Gujarati
            "kn": ("kn-IN", "kn-IN-Wavenet-A"),  # Kannada
        }

        lang_code, name = voice_map.get(language, voice_map["en"])

        return texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=name
        )

    def _prepare_text_for_audio(self, text: str) -> str:
        """
        Add SSML markup for better audio rendering.
        """
        # Add pauses after sentences
        text = text.replace('. ', '. <break time="500ms"/> ')

        # Add pauses after commas
        text = text.replace(', ', ', <break time="300ms"/> ')

        # Wrap in SSML
        return f'<speak>{text}</speak>'
```

### Audio Features

**Supported Languages:**
- English (Indian accent)
- Hindi
- Marathi
- Tamil
- Telugu
- Bengali
- Gujarati
- Kannada

**Voice Options:**
- Standard clarity (faster generation)
- WaveNet (natural, human-like)

**Accessibility:**
- Adjustable playback speed (web player)
- Downloadable MP3 (offline listening)
- Shareable via WhatsApp

---

## User Interface

### Web Portal Features

#### 1. Announcement Feed
```
┌─────────────────────────────────────────────────────────────┐
│  Government Announcements                    [Filters ▼]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔴 CRITICAL │ Ministry of Health │ Today, 10:30 AM        │
│  ────────────────────────────────────────────────────       │
│  New COVID Vaccination Drive for Children 15-18             │
│  ─────────────────────────────────────────────────          │
│  Registration opens December 28. Free vaccines at all       │
│  government centers. Bring birth certificate...             │
│                                                             │
│  [Read More] [🔊 Listen in Hindi] [Share]                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🟡 MEDIUM │ Maharashtra Govt │ Yesterday, 3:15 PM         │
│  ────────────────────────────────────────────────────       │
│  New Property Tax Payment Deadline Extended                 │
│  ─────────────────────────────────────────────────          │
│  Deadline extended to January 31, 2025. Pay online or...   │
│                                                             │
│  [Read More] [🔊 Listen in Marathi] [Share]                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Filters & Search
```
┌─────────────────────────────────────────────────────────────┐
│  Filters                                                    │
├─────────────────────────────────────────────────────────────┤
│  📍 Location                                                │
│     ☑ National                                              │
│     ☑ Maharashtra                                           │
│     ☑ Pune District                                         │
│                                                             │
│  📁 Categories                                              │
│     ☑ Health                                                │
│     ☐ Education                                             │
│     ☑ Employment                                            │
│     ☐ Infrastructure                                        │
│                                                             │
│  🕒 Time Range                                              │
│     ○ Last 24 hours                                         │
│     ● Last 7 days                                           │
│     ○ Last 30 days                                          │
│                                                             │
│  🚨 Urgency                                                 │
│     ☑ Critical                                              │
│     ☑ High                                                  │
│     ☐ Medium                                                │
│     ☐ Low                                                   │
│                                                             │
│  [Apply Filters]                                            │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Announcement Detail View
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Announcements                                    │
├─────────────────────────────────────────────────────────────┤
│  🔴 CRITICAL                                                │
│  Ministry of Health and Family Welfare                      │
│  Published: December 27, 2024 │ Effective: January 1, 2025 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  New COVID Vaccination Drive for Children Aged 15-18       │
│                                                             │
│  [Original] [Simplified ✓] [Summary]                       │
│  [🔊 Listen in: English ▼]                                 │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  KEY POINTS:                                                │
│  • Registration starts December 28, 2024                    │
│  • Free vaccination at all government health centers        │
│  • Bring child's birth certificate or school ID            │
│  • First dose: January 1-15, Second dose: After 84 days    │
│                                                             │
│  FULL ANNOUNCEMENT (Simplified):                            │
│                                                             │
│  The government is starting a new vaccination program for   │
│  children between 15 and 18 years old. This is to protect  │
│  them from COVID-19.                                        │
│                                                             │
│  Who can get the vaccine?                                   │
│  Children who are 15, 16, 17, or 18 years old on January   │
│  1, 2025.                                                   │
│                                                             │
│  How to register?                                           │
│  ...                                                        │
│                                                             │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  ORIGINAL ANNOUNCEMENT:                                     │
│  [View Original PDF] [View Original Webpage]                │
│                                                             │
│  Source: Ministry of Health and Family Welfare              │
│  Reference Number: S-29012/01/2024-DHS                      │
│                                                             │
│  [📱 Share on WhatsApp] [✉️ Email] [🔗 Copy Link]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Mobile Experience (PWA)

**Key Features:**
- Swipe between announcements (card UI)
- Voice playback with background audio support
- Offline reading (cached announcements)
- Push notifications for critical alerts
- Share to WhatsApp directly

### WhatsApp Integration

**Use Cases:**

1. **Daily Digest**
   ```
   📢 Government Updates - December 28

   3 new announcements today:

   1. 🔴 CRITICAL - Health Ministry
      New COVID vaccination for teens
      [Read] [Listen]

   2. 🟡 MEDIUM - Maharashtra Govt
      Property tax deadline extended
      [Read] [Listen]

   3. 🟢 LOW - Employment Ministry
      New apprenticeship scheme
      [Read] [Listen]

   Reply with number to read full announcement
   ```

2. **Instant Critical Alerts**
   ```
   🚨 URGENT GOVERNMENT ALERT

   Ministry of Home Affairs
   Cyclone warning for coastal areas

   Please evacuate if you are in:
   • Ratnagiri district
   • Sindhudurg district

   Cyclone expected: Tomorrow 6 AM

   [Read full alert] [Safety instructions]
   ```

3. **Query Support**
   ```
   User: "Any new scholarship announcements?"

   Bot: Found 2 recent scholarship announcements:

   1. National Scholarship Portal - Last date Dec 31
   2. Maharashtra Scholarship - Last date Jan 15

   Reply with number to learn more
   ```

---

## Discovery & Aggregation

### Source Types

#### 1. National Ministries (50+)
```python
NATIONAL_SOURCES = [
    {
        "name": "Ministry of Health and Family Welfare",
        "url": "https://mohfw.gov.in",
        "type": "ministry",
        "scraping_method": "rss",
        "rss_url": "https://mohfw.gov.in/feeds/LatestUpdates.xml"
    },
    {
        "name": "Ministry of Education",
        "url": "https://www.education.gov.in",
        "type": "ministry",
        "scraping_method": "scraper",
        "update_frequency": "daily"
    },
    {
        "name": "Press Information Bureau (PIB)",
        "url": "https://pib.gov.in",
        "type": "press_bureau",
        "scraping_method": "api",
        "api_endpoint": "https://pib.gov.in/api/releases"
    },
    # ... 47 more ministries
]
```

#### 2. State Governments (28 states + 8 UTs)
```python
STATE_SOURCES = [
    {
        "name": "Government of Maharashtra",
        "url": "https://maharashtra.gov.in",
        "state": "Maharashtra",
        "type": "state_government",
        "scraping_method": "scraper",
        "primary_language": "mr"  # Marathi
    },
    # ... 35 more states/UTs
]
```

#### 3. District Administrations (700+)
```python
# Auto-discovery from state government portals
# Example: https://pune.nic.in
```

### Scraper Management

**Leverage Grivredr Architecture:**

```python
class GovernmentSourceScraper:
    """
    Adaptive scraper for government portals.
    Uses Grivredr's AI-powered scraping.
    """

    async def discover_source_structure(self, url: str) -> dict:
        """Use Grivredr to auto-discover announcement list structure."""
        pass

    async def scrape_announcements(self, source_id: str) -> list:
        """Scrape new announcements from source."""
        pass

    async def extract_content(self, announcement_url: str) -> dict:
        """Extract full content from announcement page/PDF."""
        pass
```

### Deduplication Strategy

**Problem:** Same announcement published on:
- Ministry website
- PIB press release
- State government portal
- District website

**Solution:**
1. **Content Hash:** SHA256 of cleaned text
2. **Fuzzy Matching:** Semantic similarity (Gemini embeddings)
3. **Reference Numbers:** Extract and match official reference IDs

```python
async def check_duplicate(new_announcement: dict) -> str | None:
    """
    Check if announcement already exists.
    Returns existing announcement ID if duplicate.
    """
    # Step 1: Exact hash match
    content_hash = calculate_hash(new_announcement['content'])
    exact_match = db.collection('announcements') \
        .where('content_hash', '==', content_hash) \
        .limit(1).get()

    if exact_match:
        return exact_match[0].id

    # Step 2: Reference number match
    if new_announcement.get('reference_number'):
        ref_match = db.collection('announcements') \
            .where('reference_number', '==', new_announcement['reference_number']) \
            .limit(1).get()

        if ref_match:
            return ref_match[0].id

    # Step 3: Semantic similarity (for near-duplicates)
    embedding = await generate_embedding(new_announcement['content'])
    similar = await vector_search(embedding, threshold=0.95)

    if similar:
        return similar[0]['id']

    return None  # Not a duplicate
```

---

## Migration Path

### Phase 1: Foundation (3-4 weeks)

**Goals:** Core infrastructure for announcement ingestion

**Tasks:**
- [ ] Design data model (announcements, sources, subscriptions)
- [ ] Build source registry system
- [ ] Implement PDF parser and text extractor
- [ ] Set up scraper orchestration (scheduled jobs)
- [ ] Create deduplication pipeline

**Deliverables:**
- Firestore collections for announcements
- Scraper framework (Grivredr-based)
- Basic web UI showing announcements feed

### Phase 2: AI Processing (4-5 weeks)

**Goals:** Translation, simplification, summarization

**Tasks:**
- [ ] Implement Gemini translation pipeline (8 languages)
- [ ] Build simplification engine (Grade 5 level)
- [ ] Create summary generation (TLDR, key points)
- [ ] Add content classification (category, urgency)
- [ ] Build metadata extraction (dates, eligibility)

**Deliverables:**
- Multi-language announcement content
- Simplified versions alongside originals
- Auto-categorization working

### Phase 3: Audio Generation (2-3 weeks)

**Goals:** Text-to-speech in multiple languages

**Tasks:**
- [ ] Integrate Google Cloud TTS
- [ ] Implement voice selection per language
- [ ] Build audio generation pipeline
- [ ] Set up Cloud Storage for audio files
- [ ] Add audio player to web UI

**Deliverables:**
- Audio versions of all announcements
- Embedded audio player in web app
- Downloadable MP3 files

### Phase 4: Source Discovery (3-4 weeks)

**Goals:** Auto-discover and scrape government sources

**Tasks:**
- [ ] Map all national ministry websites
- [ ] Map all state government portals
- [ ] Build Grivredr scrapers for top 20 sources
- [ ] Implement RSS feed readers (where available)
- [ ] Set up scheduled scraping (Cloud Scheduler)

**Deliverables:**
- 50+ national sources scraped
- 28 state sources scraped
- Daily automated scraping

### Phase 5: User Features (3-4 weeks)

**Goals:** Subscriptions, notifications, personalization

**Tasks:**
- [ ] Build subscription management UI
- [ ] Implement notification system (WhatsApp, email, push)
- [ ] Add filters and search to web UI
- [ ] Create daily digest generation
- [ ] Build query bot for WhatsApp

**Deliverables:**
- Users can subscribe to topics/locations
- WhatsApp daily digest working
- Smart filtering and search

### Phase 6: Scale & Optimize (Ongoing)

**Goals:** Production-ready, scalable system

**Tasks:**
- [ ] Optimize scraping costs (caching, rate limits)
- [ ] Optimize translation costs (batch processing)
- [ ] Implement vector search for semantic queries
- [ ] Add analytics dashboard
- [ ] Mobile app improvements

---

## Challenges & Mitigations

### 1. Source Fragmentation

**Challenge:** 1000+ government websites, no standard format.

**Mitigations:**
- Prioritize high-traffic sources (ministries, PIB)
- Use Grivredr's adaptive scraping (AI-powered)
- Community contribution model (add your district source)
- RSS where available (low-maintenance)

### 2. Translation Quality

**Challenge:** Government terminology is domain-specific (legal, medical, technical).

**Mitigations:**
- Provide original alongside translation
- Build domain-specific glossaries
- Human review for critical announcements
- User feedback mechanism ("report translation error")

### 3. Timeliness

**Challenge:** Critical announcements need immediate dissemination.

**Mitigations:**
- Hourly scraping for high-priority sources
- RSS polling every 15 minutes (where available)
- Priority queue for "critical" urgency
- Direct API integration (where available)

### 4. Audio Generation Costs

**Challenge:** TTS costs can add up at scale.

**Mitigations:**
- Only generate audio for announcements with >10 views
- Cache generated audio (never regenerate)
- Use standard TTS for low-priority, WaveNet for high-priority
- Batch processing during off-peak hours

### 5. Legal & Accuracy

**Challenge:** Misrepresenting government announcements could cause legal issues.

**Mitigations:**
- Always link to original source (PDF/webpage)
- Clear disclaimer: "Unofficial translation/simplification"
- Watermark: "For informational purposes only"
- Human review for legal/financial announcements

### 6. Source Changes

**Challenge:** Government websites change layout, breaking scrapers.

**Mitigations:**
- Grivredr's self-healing scrapers (AI adapts to changes)
- Monitor scraper health (alert on failures)
- Fallback to manual notification when scraper breaks
- Quarterly scraper maintenance sprints

---

## Tech Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Content Discovery | **Grivredr** (AI Scrapers) | Adaptive scraping of government portals |
| Translation | **Gemini** | Multi-language translation & simplification |
| Audio Generation | **Google Cloud TTS** | Natural-sounding speech in 8+ languages |
| Database | **Firestore** | Announcements, subscriptions, metadata |
| Storage | **Cloud Storage** | PDFs, audio files, images |
| Search | **Firestore + Algolia** | Full-text search, filters |
| Notifications | **WhatsApp Business API** | Push announcements to users |
| Scheduling | **Cloud Scheduler** | Periodic scraping jobs |
| Backend | **FastAPI** | API server |
| Frontend | **SvelteKit** | Web portal |

### Integration with Darshi

```
┌──────────────────────────────────────────────────────────┐
│                    DARSHI CIVIC SUITE                     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │  Darshi    │  │   Nagar    │  │  Government│         │
│  │  Issues    │  │   Alert    │  │  Comms     │         │
│  │  (Core)    │  │   Hub      │  │  Platform  │         │
│  └─────┬──────┘  └──────┬─────┘  └──────┬─────┘         │
│        │                │               │                │
│        └────────────────┼───────────────┘                │
│                         │                                │
│  ┌──────────────────────┴──────────────────────┐         │
│  │         SHARED INFRASTRUCTURE               │         │
│  ├────────────────────────────────────────────┤         │
│  │ • User accounts & authentication           │         │
│  │ • WhatsApp messaging service               │         │
│  │ • Location & geohash utilities             │         │
│  │ • Notification delivery system             │         │
│  │ • Multi-language support                   │         │
│  │ • Gemini AI client                         │         │
│  └────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Platform Health
- Number of sources scraped (target: 100+)
- Scraping success rate (target: >95%)
- Translation accuracy (human eval sample)
- Audio generation coverage (% of announcements)

### User Engagement
- Daily active users
- Announcements viewed per user
- Audio playback rate
- Share rate (WhatsApp, social media)

### Accessibility Impact
- Languages accessed (diversity metric)
- Simplified version usage rate
- Audio vs text consumption ratio
- Regional reach (tier 2/3 cities)

### Timeliness
- Average time from government publish to platform availability
- Critical announcement SLA (<1 hour)

---

## Conclusion

The Government Communication Platform integration transforms Darshi from a citizen → government reporting tool into a **bidirectional civic engagement platform**. Citizens can both report issues AND stay informed about government actions.

By making government communication accessible through AI-powered translation, simplification, and audio generation, we democratize access to official information—especially critical for India's linguistically diverse, multi-literate population.

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Part of: Darshi Civic Suite*
