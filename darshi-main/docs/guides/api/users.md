---
title: Users API
tags: [api, users, profile, settings, account, statistics, preferences]
related:
  - "[[authentication]]"
  - "[[reports]]"
  - "[[notifications]]"
  - "[[../architecture/data-models#users]]"
---

# Users API

← Back to [[overview|API Overview]]

User profile management, settings, statistics, and account deletion.

## Endpoints

- `GET /users/me/profile` - Get current user profile
- `PUT /users/me/profile` - Update profile
- `POST /users/me/profile-picture` - Upload profile picture
- `PUT /users/me/settings` - Update user settings
- `GET /users/me/reports` - Get user's reports
- `GET /users/me/stats` - Get user statistics
- `DELETE /users/me/account` - Delete account

---

## GET /api/v1/users/me/profile

**Get current user's complete profile**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Response

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "phone": "+919876543210",
  "city": "New Delhi",
  "state": "Delhi",
  "country": "India",
  "lat": 28.7041,
  "lng": 77.1025,
  "location_address": "Connaught Place, Delhi",
  "profile_picture": "https://cdn.darshi.app/profiles/john_doe.jpg",
  "role": "citizen",
  "email_verified": true,
  "phone_verified": false,
  "reports_count": 15,
  "upvotes_received": 234,
  "created_at": "2025-01-15T08:30:00Z"
}
```

---

## PUT /api/v1/users/me/profile

**Update user profile (including username, location, and personal details)**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Request (JSON)

```json
{
  "username": "john_doe_2025",
  "full_name": "John Doe",
  "city": "New Delhi",
  "state": "Delhi",
  "country": "India",
  "lat": 28.7041,
  "lng": 77.1025,
  "location_address": "Connaught Place, Delhi",
  "profile_picture": "https://cdn.darshi.app/profiles/new.jpg"
}
```

### Response

```json
{
  "username": "john_doe_2025",
  "email": "john@example.com",
  "full_name": "John Doe",
  "city": "New Delhi",
  "state": "Delhi",
  "country": "India",
  "lat": 28.7041,
  "lng": 77.1025,
  "location_address": "Connaught Place, Delhi",
  "profile_picture": "https://cdn.darshi.app/profiles/new.jpg",
  "role": "citizen",
  "email_verified": true,
  "phone_verified": false,
  "reports_count": 15,
  "upvotes_received": 234,
  "created_at": "2025-01-15T08:30:00Z"
}
```

### Field Descriptions

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `username` | string | Username (unique identifier) | Checks availability before updating |
| `full_name` | string | User's full name | Optional |
| `city` | string | City name | Used for onboarding completion |
| `state` | string | State/province name | Optional |
| `country` | string | Country name | Defaults to "India" |
| `lat` | float | Latitude coordinate | For location-based features |
| `lng` | float | Longitude coordinate | For location-based features |
| `location_address` | string | Human-readable address | Optional |
| `profile_picture` | string | URL to profile image | Optional |

### Notes

- **Username Changes**: Validates availability before updating (returns 400 if taken)
- **Location Fields**: Used to determine if onboarding is complete (`city` required)
- **All Fields Optional**: Only provide fields you want to update
- **Returns Updated Profile**: Full user object returned on success
- **Use Case**: Primary endpoint for onboarding flow after OAuth/magic link registration

### Example

```bash
curl -X PUT https://api.darshi.app/api/v1/users/me/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe_2025",
    "city": "New Delhi",
    "state": "Delhi",
    "country": "India",
    "lat": 28.7041,
    "lng": 77.1025
  }'
```

---

## POST /api/v1/users/me/profile-picture

**Upload profile picture to cloud storage**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK
- **Content-Type**: `multipart/form-data`

### Request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Image file (JPEG, PNG, WebP, max 5MB) |

### Response

```json
{
  "url": "https://cdn.darshi.app/profiles/john_doe_abc123.jpg",
  "message": "Profile picture uploaded successfully"
}
```

---

## PUT /api/v1/users/me/settings

**Update user preferences/settings**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Request (JSON)

```json
{
  "notification_enabled": true,
  "location_tracking_enabled": false,
  "public_profile": true
}
```

### Response

```json
{
  "message": "Settings updated successfully"
}
```

---

## GET /api/v1/users/me/reports

**Get all reports submitted by current user**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max reports to return |

### Response

```json
{
  "reports": [
    {
      "report_id": "...",
      "title": "...",
      "status": "VERIFIED",
      "upvote_count": 45,
      "comment_count": 12,
      "created_at": "2025-12-27T10:30:00Z"
    }
  ],
  "total": 15
}
```

---

## GET /api/v1/users/me/stats

**Get user statistics**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Response

```json
{
  "total_reports": 15,
  "verified_reports": 12,
  "resolved_reports": 8,
  "pending_reports": 2,
  "rejected_reports": 1,
  "total_upvotes": 234,
  "email_verified": true,
  "phone_verified": false,
  "member_since": "2025-01-15T08:30:00Z"
}
```

---

## DELETE /api/v1/users/me/account

**Delete user account and all associated data**

- **Authentication**: Required
- **Rate Limit**: Default
- **Response**: 200 OK

### Response

```json
{
  "message": "Account deleted successfully"
}
```

### ⚠️ WARNING

This action is **irreversible** and will:
- Delete all user's reports
- Delete all comments
- Remove all upvotes
- Delete profile picture
- Permanently delete account data

---

← Back to [[overview|API Overview]] | Next: [[notifications|Notifications API]] →

**Last Updated**: December 28, 2025
