---
title: Authentication API
tags: [api, auth, jwt, oauth, security, login, register, token, verification, password]
related:
  - "[[users]]"
  - "[[overview]]"
  - "[[../architecture/backend-architecture#Security Implementation]]"
---

# Authentication API

← Back to [[overview|API Overview]]

This page documents all authentication-related endpoints including registration, login, email/phone verification, and OAuth flows.

## Table of Contents

- [Username/Password Authentication](#usernamepassword-authentication)
- [Magic Link Authentication](#magic-link-authentication)
- [OAuth 2.0 Integration](#oauth-20-integration)
- [Email Verification](#email-verification)
- [Phone Verification](#phone-verification)
- [Password Management](#password-management)

---

## Username/Password Authentication

### POST /api/v1/auth/register

**Create a new user account**

- **Authentication**: None
- **Rate Limit**: 5/hour (prevents mass account creation)
- **Response**: 201 Created

#### Request Body (JSON)

```json
{
  "username": "string (required)",
  "email": "string (optional, required if phone not provided)",
  "phone": "string (optional, required if email not provided)",
  "password": "string (optional for phone-only users)",
  "full_name": "string (optional)",
  "lat": "float (optional)",
  "lng": "float (optional)",
  "location_address": "string (optional)",
  "role": "string (default: citizen)"
}
```

#### Response

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "phone": "+919876543210",
  "full_name": "John Doe",
  "role": "citizen",
  "email_verified": false,
  "phone_verified": false,
  "created_at": "2025-12-28T10:30:00Z"
}
```

#### Notes

- Username is **required** and must be **unique**
- At least one of `email` or `phone` required
- Password optional for phone-only users (use OTP instead)
- Verification email sent if `EMAIL_ENABLED` and email provided
- Generic error returned if credentials exist (prevents user enumeration)

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

---

### POST /api/v1/auth/token

**Login with username/email/phone and password**

- **Authentication**: None
- **Rate Limit**: 10/hour (brute-force protection)
- **Response**: 200 OK

#### Request Body (form-urlencoded)

```
username=<username|email|phone>&password=<password>
```

#### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Token Structure

JWT token includes:
```json
{
  "sub": "john_doe",
  "user_id": 123,
  "role": "citizen",
  "exp": 1735209600,
  "iat": 1732531200
}
```

#### Notes

- `username` field accepts username, email, or phone number
- Token includes `user_type='citizen'`
- Token expiration: **30 days**
- Brute-force protection via rate limiting

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=SecurePass123!"
```

---

### GET /api/v1/auth/me

**Get current authenticated user information**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: Default
- **Response**: 200 OK

#### Response

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "phone": "+919876543210",
  "full_name": "John Doe",
  "role": "citizen",
  "email_verified": true,
  "phone_verified": false
}
```

#### Example

```bash
curl https://api.darshi.app/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Magic Link Authentication

Passwordless authentication via email link. Magic links are one-time use, expire in 15 minutes, and automatically create accounts for new users.

### GET /api/v1/auth/check-username

**Check if a username is available for registration**

- **Authentication**: None
- **Rate Limit**: Default
- **Response**: 200 OK

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | Username to check (min 3 characters) |

#### Response

```json
{
  "available": true,
  "username": "john_doe"
}
```

#### Notes

- Returns `available: true` if username is not taken
- Returns `available: false` if username already exists
- Validates username length (minimum 3 characters)
- Used for real-time validation during onboarding

#### Example

```bash
curl https://api.darshi.app/api/v1/auth/check-username?username=john_doe
```

---

### POST /api/v1/auth/send-magic-link

**Send passwordless login link to user's email**

- **Authentication**: None
- **Rate Limit**: 5/hour (prevents spam)
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "email": "john@example.com"
}
```

#### Response

```json
{
  "message": "If an account exists with this email, a login link has been sent"
}
```

#### Flow Details

1. **Existing User**: Updates `magic_link_token` and `magic_link_expires` fields
2. **New User**:
   - Creates account automatically
   - Generates unique username from email (e.g., `john` from `john@example.com`)
   - Handles username conflicts by appending numbers (`john1`, `john2`, etc.)
   - Sets `password_hash` to NULL (passwordless)
   - Sets `is_verified` to FALSE until magic link is clicked

3. **Email Sent**:
   - Magic link URL: `{FRONTEND_URL}/auth/magic-link?token={token}`
   - Token expires in 15 minutes
   - One-time use only

#### Security Features

- **User Enumeration Prevention**: Always returns success message
- **Rate Limited**: Maximum 5 requests per hour per IP
- **Secure Tokens**: 32-byte URL-safe random tokens
- **Time Limited**: 15-minute expiration window
- **One-Time Use**: Token cleared after verification

#### Notes

- Creates new users automatically (no separate registration needed)
- No password required for magic link users
- Email verification happens automatically on magic link click
- Generic response prevents revealing if email exists

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/send-magic-link \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

---

### GET /api/v1/auth/verify-magic-link

**Verify magic link token and authenticate user**

- **Authentication**: None
- **Rate Limit**: 10/hour
- **Response**: 200 OK

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Magic link token from email |

#### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": null,
    "role": "citizen",
    "email_verified": true,
    "created_at": "2025-12-28T10:30:00Z"
  }
}
```

#### Flow Details

1. **Token Validation**:
   - Checks if token exists in database
   - Verifies token hasn't expired (15-minute window)
   - Returns 400 error if invalid or expired

2. **On Success**:
   - Clears `magic_link_token` and `magic_link_expires` (one-time use)
   - Sets `email_verified` to TRUE
   - Updates `last_login` timestamp
   - Generates JWT access token (30-day expiry)

3. **Returns**:
   - JWT access token for authentication
   - Complete user profile object

#### Error Responses

**Invalid or Expired Token (400)**:
```json
{
  "error": {
    "code": "ValidationError",
    "message": "Invalid or expired link",
    "details": "Please request a new magic link",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

**Token Expired (400)**:
```json
{
  "error": {
    "code": "ValidationError",
    "message": "Link has expired. Please request a new one",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

#### Notes

- Token is single-use (cleared after verification)
- Automatically verifies email address
- Returns full JWT token for immediate authentication
- Updates last login timestamp
- Frontend should store token in localStorage/sessionStorage

#### Example

```bash
curl "https://api.darshi.app/api/v1/auth/verify-magic-link?token=abc123def456..."
```

#### Frontend Integration

```javascript
// Magic link verification page
const params = new URLSearchParams(window.location.search);
const token = params.get('token');

if (token) {
  const response = await fetch(
    `https://api.darshi.app/api/v1/auth/verify-magic-link?token=${token}`
  );

  if (response.ok) {
    const { access_token, user } = await response.json();
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(user));

    // Redirect to onboarding if profile incomplete, else home
    if (!user.city) {
      window.location.href = '/onboarding';
    } else {
      window.location.href = '/';
    }
  }
}
```

---

## OAuth 2.0 Integration

Darshi supports OAuth 2.0 authentication with multiple providers.

### Supported Providers

1. **Google OAuth** - Most popular
2. **GitHub OAuth** - For developers
3. **Facebook OAuth** - Social integration

### OAuth Flow Diagram

```
1. User clicks "Sign in with Google"
   ↓
2. Redirect to /api/v1/oauth/google/login
   ↓
3. Backend redirects to Google OAuth consent screen
   ↓
4. User authorizes app
   ↓
5. Google redirects to /api/v1/oauth/google/callback?code=xxx
   ↓
6. Backend exchanges code for access token
   ↓
7. Fetch user profile from Google API
   ↓
8. Create or update user in database
   ↓
9. Generate JWT token
   ↓
10. Redirect to frontend with token in URL
    ↓
11. Frontend stores token in localStorage
    ↓
12. User is logged in
```

---

### GET /api/v1/oauth/google/login

**Redirect to Google OAuth login page**

- **Authentication**: None
- **Response**: 302 Redirect
- **Redirect URL**: `https://accounts.google.com/o/oauth2/v2/auth`

#### Notes

- Generates `state` parameter for CSRF protection
- Requires `GOOGLE_CLIENT_ID` configuration

#### Example

```html
<a href="https://api.darshi.app/api/v1/oauth/google/login">
  Sign in with Google
</a>
```

---

### GET /api/v1/oauth/google/callback

**Handle Google OAuth callback**

- **Authentication**: None
- **Response**: 302 Redirect

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Yes | Authorization code from Google |
| `state` | string | Yes | State parameter (CSRF validation) |
| `error` | string | No | Error code if failed |

#### Redirect Response

```
https://darshi.app/auth/callback?token={jwt_token}&is_new={boolean}
```

#### Notes

- Validates `state` parameter to prevent CSRF
- Creates new user if OAuth ID not found
- Links OAuth to existing email-based user if found
- Returns JWT token via redirect query parameter

---

### GET /api/v1/oauth/github/login

**Redirect to GitHub OAuth login page**

- **Authentication**: None
- **Response**: 302 Redirect
- **Redirect URL**: `https://github.com/login/oauth/authorize`

---

### GET /api/v1/oauth/github/callback

**Handle GitHub OAuth callback**

- **Authentication**: None
- **Response**: 302 Redirect

Query parameters same as Google callback.

---

### GET /api/v1/oauth/facebook/login

**Redirect to Facebook OAuth login page**

- **Authentication**: None
- **Response**: 302 Redirect
- **Redirect URL**: `https://www.facebook.com/v18.0/dialog/oauth`

---

### GET /api/v1/oauth/facebook/callback

**Handle Facebook OAuth callback**

- **Authentication**: None
- **Response**: 302 Redirect

Query parameters same as Google callback.

---

## Email Verification

### POST /api/v1/auth/send-email-verification

**Send or resend email verification link**

- **Authentication**: None
- **Rate Limit**: 3/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "email": "john@example.com"
}
```

#### Response

```json
{
  "message": "If the email exists, a verification link has been sent"
}
```

#### Notes

- **Generic response** to prevent email enumeration
- Returns success even if email doesn't exist
- Verification link expires after 24 hours

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/send-email-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

---

### POST /api/v1/auth/verify-email

**Verify email using token from email link**

- **Authentication**: None
- **Rate Limit**: 10/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response

```json
{
  "message": "Email verified successfully",
  "email": "john@example.com"
}
```

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"token": "verification_token_here"}'
```

---

## Phone Verification

### POST /api/v1/auth/send-phone-verification

**Send phone verification code (OTP)**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 5/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "phone": "+919876543210"
}
```

#### Response

```json
{
  "message": "Verification code sent successfully"
}
```

#### Notes

- Phone number must be in E.164 format (+country_code...)
- OTP expires after 10 minutes
- Maximum 3 OTP requests per phone per hour

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/send-phone-verification \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919876543210"}'
```

---

### POST /api/v1/auth/verify-phone

**Verify phone using OTP code**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 10/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "phone": "+919876543210",
  "code": "123456"
}
```

#### Response

```json
{
  "message": "Phone verified successfully"
}
```

#### Notes

- Code must match the OTP sent
- Code expires after 10 minutes
- Maximum 5 verification attempts per OTP

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/verify-phone \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919876543210", "code": "123456"}'
```

---

## Password Management

### POST /api/v1/auth/forgot-password

**Request password reset link**

- **Authentication**: None
- **Rate Limit**: 3/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "email": "john@example.com"
}
```

#### Response

```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```

#### Notes

- Always returns success to prevent email enumeration
- Reset links are time-limited (1 hour)
- Only one active reset link per email

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

---

### POST /api/v1/auth/reset-password

**Reset password using token from email link**

- **Authentication**: None
- **Rate Limit**: 5/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123!"
}
```

#### Response

```json
{
  "message": "Password reset successfully"
}
```

#### Notes

- Token expires after 1 hour
- Password must meet security requirements
- Old tokens are invalidated after successful reset

#### Example

```bash
curl -X POST https://api.darshi.app/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset_token_here",
    "new_password": "NewSecurePass123!"
  }'
```

---

### PUT /api/v1/auth/change-password

**Change password for authenticated user**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 10/hour
- **Response**: 200 OK

#### Request Body (JSON)

```json
{
  "old_password": "OldSecurePass123!",
  "new_password": "NewSecurePass123!"
}
```

#### Response

```json
{
  "message": "Password changed successfully"
}
```

#### Notes

- **Not available for OAuth users** (no password set)
- Requires correct old password for security
- New password must meet security requirements

#### Example

```bash
curl -X PUT https://api.darshi.app/api/v1/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldSecurePass123!",
    "new_password": "NewSecurePass123!"
  }'
```

---

## Security Best Practices

### For Client Applications

1. **Store tokens securely**
   - Use httpOnly cookies (preferred)
   - Or localStorage with XSS protection
   - Never store in sessionStorage for sensitive apps

2. **Handle token expiration**
   - Check token expiry before requests
   - Implement token refresh logic
   - Redirect to login when expired

3. **Use HTTPS only**
   - Never send tokens over HTTP
   - Validate SSL certificates

4. **Implement CSRF protection**
   - Use OAuth `state` parameter
   - Validate state on callback

### For Backend Integration

1. **Validate JWT tokens**
   - Verify signature with `SECRET_KEY`
   - Check expiration time
   - Validate issuer/audience

2. **Rate limiting**
   - Respect rate limit headers
   - Implement exponential backoff
   - Cache tokens (don't re-authenticate each request)

3. **Error handling**
   - Never expose sensitive info in errors
   - Log authentication failures
   - Monitor for brute-force attempts

---

## Error Responses

### 400 Bad Request

```json
{
  "error": {
    "code": "ValidationError",
    "message": "Invalid input data",
    "details": "Email format is invalid",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### 401 Unauthorized

```json
{
  "error": {
    "code": "AuthenticationError",
    "message": "Invalid credentials",
    "details": "Username or password is incorrect",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### 429 Too Many Requests

```json
{
  "error": {
    "code": "RateLimitExceeded",
    "message": "Too many requests",
    "details": "Maximum 10 requests per hour. Try again in 45 minutes.",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

---

← Back to [[overview|API Overview]] | Next: [[reports|Reports API]] →

**Last Updated**: December 28, 2025
