---
title: Notifications API
tags: [api, notifications, push, webpush, vapid, in-app, alerts, browser-push, service-worker]
related:
  - "[[users]]"
  - "[[reports]]"
  - "[[../architecture/backend-architecture#Background Task Processing]]"
---

# Notifications API

← Back to [[overview|API Overview]]

In-app notifications and browser push notification subscriptions (WebPush/VAPID).

## Endpoints

- `GET /notifications` - Get user notifications
- `PUT /notifications/{id}/read` - Mark notification as read
- `PUT /notifications/read-all` - Mark all as read
- `DELETE /notifications/{id}` - Delete notification
- `POST /notifications/push/subscribe` - Subscribe to push notifications
- `DELETE /notifications/push/unsubscribe` - Unsubscribe from push

---

## GET /api/v1/notifications

**Get notifications for current user**

- **Authentication**: Required
- **Rate Limit**: 30/minute
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `unread_only` | boolean | false | Filter to unread only |
| `limit` | integer | 50 | Max 100 |

### Response

```json
{
  "notifications": [
    {
      "id": "notif_uuid_1",
      "title": "Report Milestone",
      "message": "Your report has reached 50 upvotes!",
      "type": "milestone",
      "read": false,
      "data": {
        "report_id": "abc123",
        "upvote_count": 50
      },
      "created_at": "2025-12-28T10:30:00Z"
    },
    {
      "id": "notif_uuid_2",
      "title": "New Comment",
      "message": "user2 commented on your report",
      "type": "comment",
      "read": true,
      "data": {
        "report_id": "abc123",
        "comment_id": "comment_uuid",
        "commenter": "user2"
      },
      "created_at": "2025-12-28T09:15:00Z"
    }
  ],
  "unread_count": 1
}
```

### Notification Types

- `milestone` - Report reached upvote milestone (10, 50, 100, 500, 1000)
- `comment` - Someone commented on user's report
- `status_update` - Report status changed (admin action)
- `system` - System announcements

---

## PUT /api/v1/notifications/{notification_id}/read

**Mark a single notification as read**

- **Authentication**: Required
- **Rate Limit**: 100/minute
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `notification_id` | UUID | Notification ID |

### Response

```json
{
  "success": true
}
```

---

## PUT /api/v1/notifications/read-all

**Mark all notifications as read**

- **Authentication**: Required
- **Rate Limit**: 20/minute
- **Response**: 200 OK

### Response

```json
{
  "marked_read": 5
}
```

---

## DELETE /api/v1/notifications/{notification_id}

**Delete a notification**

- **Authentication**: Required
- **Rate Limit**: 50/minute
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `notification_id` | UUID | Notification ID |

### Response

```json
{
  "success": true
}
```

---

## POST /api/v1/notifications/push/subscribe

**Save browser push notification subscription**

- **Authentication**: Required
- **Rate Limit**: 10/minute
- **Response**: 200 OK

### Request (JSON)

```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": {
    "p256dh": "base64_encoded_key",
    "auth": "base64_encoded_auth"
  },
  "user_agent": "Mozilla/5.0..."
}
```

### Response

```json
{
  "subscription_id": "sub_uuid",
  "message": "Push notifications enabled"
}
```

### Browser Implementation

```javascript
// Request permission
const permission = await Notification.requestPermission();

if (permission === 'granted') {
  // Get service worker registration
  const registration = await navigator.serviceWorker.ready;

  // Subscribe to push
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: 'VAPID_PUBLIC_KEY'
  });

  // Send to backend
  await fetch('/api/v1/notifications/push/subscribe', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: {
        p256dh: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('p256dh')))),
        auth: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('auth'))))
      },
      user_agent: navigator.userAgent
    })
  });
}
```

---

## DELETE /api/v1/notifications/push/unsubscribe

**Remove browser push notification subscription**

- **Authentication**: Required
- **Rate Limit**: 10/minute
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `endpoint` | string | Yes | Push subscription endpoint URL |

### Response

```json
{
  "success": true,
  "message": "Push notifications disabled"
}
```

### Browser Implementation

```javascript
// Get current subscription
const registration = await navigator.serviceWorker.ready;
const subscription = await registration.pushManager.getSubscription();

if (subscription) {
  // Unsubscribe from push
  await subscription.unsubscribe();

  // Notify backend
  await fetch(`/api/v1/notifications/push/unsubscribe?endpoint=${encodeURIComponent(subscription.endpoint)}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
}
```

---

## Push Notification Events

Push notifications are triggered for:

1. **Report Milestones**: 10, 50, 100, 500, 1000 upvotes
2. **Comments**: Someone comments on user's report
3. **Status Updates**: Admin changes report status (IN_PROGRESS, RESOLVED)
4. **System Announcements**: Important platform updates

---

← Back to [[overview|API Overview]] | Next: [[admin|Admin API]] →

**Last Updated**: December 28, 2025
