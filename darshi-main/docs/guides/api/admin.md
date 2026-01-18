---
title: Admin API
tags: [api, admin, moderation, analytics, dashboard, audit-logs, permissions, super-admin]
related:
  - "[[reports]]"
  - "[[users]]"
  - "[[authentication]]"
  - "[[../architecture/backend-architecture#Security Implementation]]"
---

# Admin API

← Back to [[overview|API Overview]]

Administrative operations for moderators and super admins including report management, analytics, and audit logs.

## Authentication

All admin endpoints require JWT token with `user_type='admin'` claim.

**Admin Token Expiry**: 1 hour (vs 30 days for citizen tokens)

---

## Endpoints Overview

| Endpoint | Method | Description | Role Required |
|----------|--------|-------------|---------------|
| `/admin/login` | POST | Admin login | None |
| `/admin/report/{id}/status` | PUT | Update report status | moderator |
| `/admin/reports` | GET | Get all reports (includes rejected) | moderator |
| `/admin/report/{id}` | DELETE | Delete any report | moderator |
| `/admin/report/{id}/category` | PUT | Update report category | moderator |
| `/admin/report/{id}/comment/{cid}` | DELETE | Delete comment | moderator |
| `/admin/analytics/dashboard` | GET | Dashboard analytics | moderator |
| `/admin/analytics/audit-logs` | GET | Audit logs with filters | moderator |
| `/admin/analytics/user-activity/{uid}` | GET | User activity history | moderator |
| `/admin/analytics/report-history/{rid}` | GET | Report audit history | moderator |
| `/admin/create-admin` | POST | Create new admin | super_admin |
| `/admin/admins` | GET | List all admins | super_admin |
| `/admin/manage/{email}/status` | PUT | Activate/deactivate admin | super_admin |

---

## POST /api/v1/admin/login

**Admin login endpoint**

- **Authentication**: None
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Request (JSON)

```json
{
  "email": "admin@darshi.app",
  "password": "SecureAdminPass123!"
}
```

### Response

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "admin": {
    "email": "admin@darshi.app",
    "role": "moderator"
  }
}
```

### Notes

- Authenticates from separate `admins` table (not `users`)
- JWT includes `user_type='admin'` for authorization checks
- Token expires after **1 hour**

---

## PUT /api/v1/admin/report/{report_id}/status

**Update report status (moderator action)**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 500/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

### Request (JSON)

```json
{
  "status": "IN_PROGRESS",
  "note": "Municipal team has been notified"
}
```

### Valid Status Transitions

From `VERIFIED`:
- → `IN_PROGRESS` (work started)
- → `RESOLVED` (issue fixed)
- → `REJECTED` (invalid after review)

From `IN_PROGRESS`:
- → `RESOLVED` (issue fixed)
- → `VERIFIED` (work paused)

### Response

```json
{
  "message": "Report status updated to IN_PROGRESS",
  "updated_by": "admin@darshi.app"
}
```

### Side Effects

- Sends notification to report author
- Adds timeline event for audit trail
- Logs action in `admin_logs` table

---

## GET /api/v1/admin/reports

**Get reports for admin view (includes all statuses)**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_after_id` | UUID | - | Pagination cursor |
| `status` | string | - | Filter by status |
| `limit` | integer | 20 | Max 100 |

### Response

```json
[
  {
    "report_id": "...",
    "title": "...",
    "status": "REJECTED",
    "ai_rejection_reason": "Not a civic issue",
    "created_at": "2025-12-28T10:00:00Z"
  },
  {
    "report_id": "...",
    "title": "...",
    "status": "FLAGGED",
    "created_at": "2025-12-28T09:30:00Z"
  }
]
```

### Notes

- Includes `REJECTED` and `FLAGGED` status reports (hidden from public)
- Useful for reviewing AI decisions

---

## DELETE /api/v1/admin/report/{report_id}

**Delete a report (admin override)**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report to delete |

### Response

```json
{
  "message": "Report deleted successfully",
  "deleted_by": "admin@darshi.app"
}
```

### Notes

- Can delete reports in **any status** (unlike users)
- Logs deletion in audit trail
- Cascades to comments and upvotes (PostgreSQL CASCADE)

---

## PUT /api/v1/admin/report/{report_id}/category

**Update report category (fix AI misclassification)**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 500/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

### Request (JSON)

```json
{
  "category": "Water Supply"
}
```

### Valid Categories

- Road Damage
- Garbage
- Water Supply
- Electricity
- Drainage
- Streetlight
- Other

### Response

```json
{
  "message": "Report category updated to Water Supply",
  "updated_by": "admin@darshi.app"
}
```

---

## DELETE /api/v1/admin/report/{report_id}/comment/{comment_id}

**Delete a comment from a report**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |
| `comment_id` | UUID | Comment ID |

### Response

```json
{
  "message": "Comment deleted successfully",
  "deleted_by": "admin@darshi.app"
}
```

### Use Cases

- Remove spam comments
- Delete abusive content
- Remove doxxing/personal info

---

## GET /api/v1/admin/analytics/dashboard

**Get comprehensive admin dashboard analytics**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 500/hour
- **Response**: 200 OK

### Response

```json
{
  "summary": {
    "total_reports": 1523,
    "verified_reports": 1245,
    "pending_reports": 125,
    "in_progress_reports": 98,
    "resolved_reports": 1005,
    "rejected_reports": 45,
    "average_severity": 6.7,
    "status_distribution": {
      "VERIFIED": 1245,
      "PENDING_VERIFICATION": 125,
      "IN_PROGRESS": 98,
      "RESOLVED": 1005,
      "REJECTED": 45,
      "DUPLICATE": 5
    },
    "category_distribution": {
      "Road Damage": 523,
      "Garbage": 412,
      "Water Supply": 298,
      "Electricity": 187,
      "Drainage": 103
    }
  },
  "top_categories": [
    {
      "category": "Road Damage",
      "count": 523,
      "average_severity": 7.2
    },
    {
      "category": "Garbage",
      "count": 412,
      "average_severity": 6.5
    }
  ],
  "recent_admin_actions": [
    {
      "action": "status_update",
      "admin": "admin@darshi.app",
      "report_id": "abc123",
      "details": "Updated status to RESOLVED",
      "timestamp": "2025-12-28T11:00:00Z"
    }
  ],
  "generated_at": "2025-12-28T12:00:00Z"
}
```

---

## GET /api/v1/admin/analytics/audit-logs

**Get audit logs with optional filtering**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 500/hour
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | integer | Filter by user ID |
| `resource_type` | string | Filter by resource type (report, user, comment) |
| `resource_id` | integer | Filter by resource ID |
| `action` | string | Filter by action (create, update, delete) |
| `limit` | integer | Max results (default 100) |

### Response

```json
{
  "logs": [
    {
      "id": 1,
      "admin_username": "admin@darshi.app",
      "action": "update_report_status",
      "resource_type": "report",
      "resource_id": 123,
      "details": {
        "old_status": "VERIFIED",
        "new_status": "IN_PROGRESS",
        "note": "Municipal team notified"
      },
      "ip_address": "203.0.113.42",
      "created_at": "2025-12-28T11:00:00Z"
    }
  ],
  "count": 1,
  "filters": {
    "resource_type": "report",
    "action": "update_report_status"
  }
}
```

---

## GET /api/v1/admin/analytics/user-activity/{user_id}

**Get activity history for a specific user**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | integer | User ID |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Max activities |

### Response

```json
{
  "user_id": 123,
  "username": "john_doe",
  "activity": [
    {
      "action": "create_report",
      "report_id": "abc123",
      "timestamp": "2025-12-28T10:00:00Z"
    },
    {
      "action": "upvote_report",
      "report_id": "xyz789",
      "timestamp": "2025-12-28T09:30:00Z"
    }
  ],
  "count": 2
}
```

---

## GET /api/v1/admin/analytics/report-history/{report_id}

**Get complete audit history for a report**

- **Authentication**: Required (admin JWT)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

### Response

```json
{
  "report_id": "abc123",
  "current_status": "RESOLVED",
  "timeline": [
    {
      "event": "created",
      "timestamp": "2025-12-27T10:00:00Z",
      "actor": "john_doe"
    },
    {
      "event": "verified",
      "timestamp": "2025-12-27T10:02:00Z",
      "actor": "ai_system",
      "details": "AI classified as Road Damage with severity 8"
    },
    {
      "event": "status_updated",
      "timestamp": "2025-12-28T09:00:00Z",
      "actor": "admin@darshi.app",
      "details": "Changed status from VERIFIED to IN_PROGRESS"
    },
    {
      "event": "status_updated",
      "timestamp": "2025-12-28T15:00:00Z",
      "actor": "admin@darshi.app",
      "details": "Changed status from IN_PROGRESS to RESOLVED"
    }
  ],
  "audit_logs": [
    {
      "action": "update_report_status",
      "admin": "admin@darshi.app",
      "timestamp": "2025-12-28T09:00:00Z",
      "details": {...}
    }
  ],
  "created_at": "2025-12-27T10:00:00Z"
}
```

---

## POST /api/v1/admin/create-admin

**Create a new admin user (super_admin only)**

- **Authentication**: Required (admin JWT with role=super_admin)
- **Rate Limit**: 10/hour
- **Response**: 200 OK

### Request (JSON)

```json
{
  "email": "newadmin@darshi.app",
  "password": "SecurePass123!",
  "role": "moderator"
}
```

### Valid Roles

- `moderator` - Can moderate reports, view analytics
- `super_admin` - Can manage other admins

### Response

```json
{
  "message": "Admin created successfully",
  "admin": {
    "email": "newadmin@darshi.app",
    "role": "moderator",
    "is_active": true
  }
}
```

### Notes

- Only `super_admin` can create new admins
- Logs creation in audit trail

---

## GET /api/v1/admin/admins

**List all admin users**

- **Authentication**: Required (admin JWT with role=super_admin)
- **Rate Limit**: 500/hour
- **Response**: 200 OK

### Response

```json
{
  "admins": [
    {
      "email": "admin@darshi.app",
      "role": "super_admin",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "email": "moderator@darshi.app",
      "role": "moderator",
      "is_active": true,
      "created_at": "2025-06-15T10:00:00Z"
    }
  ]
}
```

---

## PUT /api/v1/admin/manage/{admin_email}/status

**Activate or deactivate an admin account**

- **Authentication**: Required (admin JWT with role=super_admin)
- **Rate Limit**: 50/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `admin_email` | string | Admin email address |

### Request (JSON)

```json
{
  "is_active": false
}
```

### Response

```json
{
  "message": "Admin account deactivated"
}
```

### Notes

- Cannot deactivate yourself
- Logs status change in audit trail
- Deactivated admins cannot login

---

## Security Best Practices

### For Admin Clients

1. **Short token lifetime**: Admin tokens expire after 1 hour
2. **Secure storage**: Store tokens in httpOnly cookies
3. **Activity logging**: All actions logged with IP address
4. **Role-based access**: super_admin vs moderator permissions
5. **Audit trail**: Complete history of all admin actions

### For Backend

1. **Separate authentication**: Admin table separate from users
2. **JWT validation**: Check `user_type='admin'` claim
3. **Role enforcement**: Verify role for privileged operations
4. **IP logging**: Track admin actions by IP address
5. **Rate limiting**: Higher limits for admins but still enforced

---

← Back to [[overview|API Overview]]

**Last Updated**: December 28, 2025
