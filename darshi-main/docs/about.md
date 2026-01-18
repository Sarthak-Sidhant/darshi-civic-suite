---
title: About Darshi
tags: [about, overview, mission, platform]
aliases: [About, What is Darshi]
created: 2025-12-21
updated: 2025-12-21
---

# About Darshi

> **Darshi** (दर्शी) - Sanskrit for "one who sees" or "observer"

**Darshi is a civic accountability platform that empowers citizens to report, track, and resolve civic issues in their communities.** Using AI-powered verification and geospatial analytics, Darshi helps hold local authorities accountable while building a comprehensive database of civic infrastructure problems.

[[README|← Documentation Hub]]

---

## The Problem We're Solving

### Broken Civic Infrastructure
- Potholes damage vehicles and cause accidents
- Broken streetlights compromise public safety
- Overflowing garbage bins create health hazards
- Poor drainage leads to flooding during monsoons
- Damaged roads disrupt daily commutes

### Lack of Accountability
- Citizens don't know where or how to report issues
- Reports get lost in bureaucratic processes
- No transparency on whether issues are being addressed
- Duplicate reports waste administrative resources
- No data-driven approach to prioritize critical problems

### Limited Public Awareness
- Communities don't know about problems in their area
- No way to see patterns or hotspots of civic neglect
- Citizens can't collectively voice concerns
- Authorities lack data to allocate resources effectively

---

## Our Solution

### 1. **Easy Reporting**
**Citizens can report civic issues in seconds:**
- 📱 Take a photo of the problem
- 📍 Location is automatically captured via GPS
- ✍️ Add a short title and description
- 🚀 Submit anonymously or with an account

**No bureaucracy. No complicated forms. Just snap and submit.**

### 2. **AI-Powered Verification**
**Google Gemini AI automatically analyzes every submission:**
- 🔍 Verifies the image contains a legitimate civic issue
- 🏷️ Classifies the problem (pothole, garbage, streetlight, etc.)
- ⚠️ Assigns severity level (1-10 scale)
- ❌ Rejects spam, irrelevant, or inappropriate content

**This prevents false reports and reduces manual moderation work.**

### 3. **Duplicate Detection**
**Smart algorithms prevent redundant reports:**
- 🖼️ Perceptual image hashing (dHash) detects visually similar photos
- 🗺️ Geospatial proximity checks (within ~55 meters)
- 🔗 Links duplicate reports to existing ones
- 📊 Shows community support through upvotes

**Citizens see if someone already reported the issue before submitting.**

### 4. **Community Engagement**
**Citizens can interact with reports:**
- 👍 **Upvote** reports to show community support
- 💬 **Comment** to provide additional context or updates
- 📢 **Share** reports to raise awareness
- 🔔 **Get notified** when status changes

**More upvotes = more visibility = more pressure on authorities.**

### 5. **Real-Time Tracking**
**Transparent lifecycle for every report:**
- ⏳ **Pending Verification** - AI is analyzing the submission
- ✅ **Verified** - Confirmed as a legitimate civic issue
- 🔧 **In Progress** - Authorities are addressing it
- ✔️ **Resolved** - Issue has been fixed
- ❌ **Rejected** - Not a valid civic issue
- 🚩 **Flagged** - Requires manual review

**Citizens can track progress and hold authorities accountable.**

### 6. **Hotspot Analytics**
**BigQuery-powered insights identify patterns:**
- 🔥 **Hotspot Alerts** - Areas with 3+ critical issues in 24 hours
- 📊 **Category Trends** - Which problems are most common
- 📈 **Time-Series Analysis** - How quickly issues get resolved
- 🗺️ **Geographic Clustering** - Regions that need attention

**Data-driven decision making for resource allocation.**

---

## How It Works

### For Citizens

```
1. Open Darshi → Tap "Submit Report"
2. Take photo of civic issue
3. Add title (e.g., "Large pothole on Main Street")
4. Add description (optional but recommended)
5. Location is auto-captured via GPS
6. Submit → AI analyzes within seconds
7. Get notified when status changes
8. Track progress on the report page
```

**Anonymous submissions allowed** - No account required to report issues (10 reports/hour limit).
**Registered users get 5x higher limits** (50 reports/hour) and can track their submissions.

### For Authorities

```
1. Admin logs in to dashboard
2. Views all reports by status, category, or location
3. Sees hotspot alerts for critical areas
4. Updates report status (In Progress, Resolved)
5. Adds admin notes for transparency
6. Citizens get notified automatically
```

**Audit trail preserved** - Every status change is logged with timestamps and admin identity.

### For the Community

```
1. Browse feed to see nearby issues
2. Upvote reports you've also noticed
3. Comment with additional details
4. Share reports on social media
5. Monitor hotspot alerts
6. Celebrate when issues get resolved
```

**Collective voice amplified** - Multiple citizens reporting the same issue creates pressure for action.

---

## Technology Stack

### Backend (Python + FastAPI)
- **FastAPI** - High-performance async web framework
- **Google Cloud Firestore** - NoSQL database for reports, users, comments
- **Google Cloud Storage** - Image hosting with automatic optimization
- **Google Gemini AI** - Image analysis and classification
- **BigQuery** - Analytics and hotspot detection
- **JWT Authentication** - Secure token-based auth

### Frontend (TypeScript + SvelteKit)
- **SvelteKit 5** - Modern reactive framework with Runes
- **Leaflet** - Interactive maps with India boundaries
- **Native CSS** - Ultra-lightweight, no frameworks
- **TypeScript** - Type-safe development
- **Progressive Web App** - Works offline, installable

### Infrastructure
- **Firebase Hosting** - Frontend deployment
- **Google Cloud Run** - Serverless backend (auto-scaling)
- **Cloud Build** - CI/CD pipeline
- **Cloud Logging** - Centralized logging

**Designed for scale** - Handles thousands of reports with geospatial indexing and caching.

---

## Key Features

### 🤖 AI Verification
- **Automatic classification** - AI categorizes issues (pothole, garbage, etc.)
- **Severity assessment** - 1-10 scale based on visual analysis
- **Spam filtering** - Rejects invalid submissions automatically
- **Confidence scoring** - AI provides explanation for decisions

### 🗺️ Geospatial Features
- **GPS auto-capture** - Location detected automatically
- **Geohash indexing** - Fast proximity queries (precision 9 ≈ 4.77m × 4.77m)
- **Address search** - Search by street name or landmark
- **Map view** - See all reports on an interactive map
- **Cluster visualization** - Identify problem areas at a glance

### 🔒 Security & Privacy
- **Input sanitization** - All user input is sanitized to prevent XSS
- **Rate limiting** - 10 reports/hour (anonymous), 50/hour (authenticated)
- **JWT authentication** - Secure token-based sessions
- **CORS protection** - Environment-specific origin policies
- **Admin audit logs** - Every admin action is tracked

### 📊 Analytics & Insights
- **Hotspot detection** - Areas with clusters of severe issues
- **Category breakdown** - Which problems are most prevalent
- **Status tracking** - Resolution rates and timelines
- **User statistics** - Top contributors and community engagement

### 📱 Mobile-First Design
- **Responsive layout** - Works on phones, tablets, desktops
- **Touch-friendly UI** - Large buttons, swipe gestures
- **Offline support** - Progressive Web App functionality
- **Image optimization** - WebP + JPEG fallback for compatibility
- **Fast loading** - Critical CSS, lazy loading, code splitting

### ♿ Accessibility
- **WCAG 2.1 compliant** - Semantic HTML, ARIA labels
- **Keyboard navigation** - Full site usable without mouse
- **Screen reader support** - Proper heading structure and labels
- **High contrast** - Readable text on all backgrounds
- **Focus indicators** - Clear visual feedback

---

## The Vision

### Short Term (2025)
- ✅ Launch MVP with core reporting features
- ✅ Deploy in pilot cities across India
- 🎯 Onboard 1,000+ active users
- 🎯 Track 10,000+ civic issues
- 🎯 Measure resolution rates and timelines

### Medium Term (2026)
- 🎯 Expand to 50+ cities nationwide
- 🎯 Partner with municipal corporations for direct integration
- 🎯 Add SMS/WhatsApp notifications for status updates
- 🎯 Implement email digests for hotspot alerts
- 🎯 Build public API for third-party integrations

### Long Term (2027+)
- 🎯 Scale to 100+ cities across India
- 🎯 Predictive analytics (forecast where issues will occur)
- 🎯 Budget transparency (show how tax money is allocated)
- 🎯 Citizen satisfaction surveys post-resolution
- 🎯 Replicate model in other developing countries

**The ultimate goal:** Make civic infrastructure accountability the norm, not the exception.

---

## Impact Metrics

### What Success Looks Like
- **For Citizens:** Faster issue resolution (target: <7 days for critical issues)
- **For Authorities:** Data-driven resource allocation and reduced duplicate reports
- **For Communities:** Increased awareness and collective pressure for action
- **For Society:** Improved civic infrastructure and quality of life

### Measuring Impact
- 📈 Number of reports submitted
- ✅ Percentage of reports resolved
- ⏱️ Average time to resolution
- 🔥 Reduction in hotspot areas
- 📊 Citizen satisfaction ratings
- 💬 Community engagement (upvotes, comments, shares)

---

## Open Source & Transparency

### Why Open Source?
- **Transparency** - Code is auditable by anyone
- **Trust** - No hidden algorithms or data manipulation
- **Collaboration** - Community contributions improve the platform
- **Replicability** - Other communities can deploy their own instances

### Contributing
Darshi welcomes contributions! See our [[03-development/Development-Guide|Development Guide]] to get started.

**Ways to contribute:**
- 🐛 Report bugs or suggest features
- 💻 Submit pull requests
- 📝 Improve documentation
- 🌐 Translate UI to regional languages
- 🎨 Design improvements

---

## Privacy & Data Policy

### What We Collect
- **Report data:** Photos, location, title, description, timestamp
- **User data (optional):** Email/phone for account creation, username
- **Interaction data:** Upvotes, comments (linked to user accounts)
- **Analytics:** Usage patterns, error logs (anonymized)

### What We Don't Collect
- ❌ Personal identifiable information (unless you create an account)
- ❌ Device fingerprinting or tracking across sites
- ❌ Browsing history or third-party data
- ❌ Biometric or sensitive personal data

### Data Retention
- **Active reports:** Retained indefinitely for transparency
- **Resolved reports:** Archived after 2 years
- **User accounts:** Deletable at any time
- **Logs:** 90-day retention for troubleshooting

### Data Security
- 🔒 All data encrypted in transit (HTTPS)
- 🔒 Database access restricted to authenticated services
- 🔒 Regular security audits and penetration testing
- 🔒 No third-party data sharing (except Google Cloud infrastructure)

---

## Frequently Asked Questions

### Can I report anonymously?
**Yes!** You don't need an account to submit reports. However, registered users get 5x higher rate limits (50 vs 10 reports/hour).

### How does AI verification work?
Google Gemini AI analyzes the image to determine if it contains a civic issue, classifies the category (pothole, garbage, etc.), and assigns a severity score. The AI rejects spam, irrelevant content, or inappropriate images automatically.

### What if my report is rejected?
If the AI rejects your report, you'll see a reason (e.g., "No civic issue detected in image"). You can edit and resubmit with a clearer photo.

### How long until issues get resolved?
Resolution time depends on the severity and local authorities' response. Darshi tracks average resolution times and displays them publicly to encourage accountability.

### Can I delete my report?
Yes, you can delete reports you submitted (if you're logged in and own them). However, reports in "Verified", "In Progress", or "Resolved" status cannot be deleted by users (contact admin if needed).

### Is Darshi affiliated with the government?
**No.** Darshi is an independent civic tech platform. We aim to work *with* authorities, not replace them.

### How do I become an admin/moderator?
Contact the platform administrators. Admins are vetted and given special access to update report statuses and manage content.

### Can I export data for research?
Yes, we plan to provide public APIs and data exports for academic research and civic analysis (with privacy safeguards).

---

## Contact & Support

**For general inquiries:**
- 📧 Email: contact@darshi.app
- 🌐 Website: https://darshi.app

**For technical support:**
- 📚 Documentation: https://darshi.app/docs
- 🐛 GitHub Issues: https://github.com/YOUR_USERNAME/darshi/issues

**For partnerships:**
- 🤝 Municipal corporations interested in integration
- 🏛️ NGOs working on civic governance
- 🎓 Academic researchers studying civic tech

---

## Credits

**Built by:** Sidhant Sarthak
**Technologies:** Google Cloud Platform, SvelteKit, FastAPI, Gemini AI
**Inspired by:** SeeClickFix, FixMyStreet, and civic tech movements worldwide

**Special thanks to:**
- Open-source communities for tools and libraries
- Early testers and feedback providers
- Citizens who believe in accountable governance

---

## Learn More

- [[quick_start|Quick Start Guide]] - Get up and running in 15 minutes
- [[01-architecture/Architecture-Overview|Architecture Overview]] - Deep dive into system design
- [[05-features/Features-Overview|Features Overview]] - Explore all features
- [[PHILOSOPHY|Development Philosophy]] - Our approach to building robust software

---

**Ready to make a difference?** [Submit your first report →](https://darshi.app/submit)

---

**Last Updated:** 2025-12-21
**Version:** 1.0.0
