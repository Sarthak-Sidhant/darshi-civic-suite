# PHILOSOPHY.md

**Darshi Development Philosophy & Workflow Guide**

This document defines the consistent workflow, design principles, and best practices for all contributors and AI assistants (LLMs) working on the Darshi codebase. Follow these guidelines to maintain code quality, consistency, and robustness.

---

## Table of Contents

1. [Core Values](#core-values)
2. [Architecture Principles](#architecture-principles)
3. [Backend Development](#backend-development)
4. [Frontend Development](#frontend-development)
5. [Error Handling Philosophy](#error-handling-philosophy)
6. [Logging Standards](#logging-standards)
7. [Testing & Validation](#testing--validation)
8. [Git Workflow](#git-workflow)
9. [Documentation Standards](#documentation-standards)
10. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Core Values

### 1. **Robustness Above All**
- **Principle**: The system must handle failures gracefully without crashing
- **Implementation**:
  - Multiple layers of error handling (try-catch, circuit breakers, retries)
  - Graceful degradation for non-critical features
  - No silent failures - every error must be logged with context
  - Input validation at every layer (router, service, database)

### 2. **User Experience is King**
- **Principle**: Every user interaction should be delightful, accessible, and informative
- **Implementation**:
  - Toast notifications for all feedback (never use alert())
  - Loading states for every async operation
  - Clear, actionable error messages
  - Accessibility-first (ARIA labels, keyboard navigation, semantic HTML)
  - Form validation with helpful hints

### 3. **Code Quality & Consistency**
- **Principle**: Code should be self-documenting, consistent, and maintainable
- **Implementation**:
  - Follow established patterns (don't reinvent the wheel)
  - DRY (Don't Repeat Yourself) - extract reusable utilities
  - Consistent naming conventions across layers
  - Type safety (TypeScript/Python type hints)
  - No console.log in production code

### 4. **Security by Design**
- **Principle**: Security should never be an afterthought
- **Implementation**:
  - Input sanitization at router level
  - Parameterized queries (Firestore prevents SQL injection by design)
  - Rate limiting on all public endpoints
  - Sensitive data never logged or exposed in errors
  - Environment-aware error details (verbose in dev, minimal in prod)

---

## Architecture Principles

### Separation of Concerns

**Layer Structure:**
```
Router Layer (app/routers/)
    ↓ (validation, sanitization)
Service Layer (app/services/)
    ↓ (business logic, error handling)
Core Utilities (app/core/)
    ↓ (shared functionality)
External Services (GCP, APIs)
```

**Rules:**
- **Routers**: Handle HTTP concerns only (validation, request/response formatting, auth)
- **Services**: Contain business logic, orchestrate operations, raise specific exceptions
- **Core**: Shared utilities (logging, security, error handling, validation)
- **No layer skipping**: Don't call external services directly from routers

### Service Design Patterns

**When to use Classes:**
- Stateful services (EmailService, SMSService with config)
- Services requiring initialization (connection pooling, SDK setup)
- Services with multiple related methods sharing state

**When to use Module-Level Functions:**
- Stateless operations (ai_service, geo_service)
- Pure functions without shared state
- Simple CRUD operations (db_service)

**Consistency Rule**: Similar services should follow similar patterns, but don't force classes where functions are clearer.

---

## Backend Development

### FastAPI Router Guidelines

```python
from fastapi import APIRouter, HTTPException, status, Request
from app.services import db_service
from app.core.validation import validate_report_data
from app.core.exceptions import DatabaseError, ValidationError
from app.core.security import limiter, sanitize_form_data
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/api/v1/resource", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_resource(request: Request, data: ResourceSchema):
    """
    Clear docstring explaining endpoint purpose, parameters, and responses.
    """
    # 1. Sanitize inputs
    sanitized = sanitize_form_data(data.dict())

    # 2. Validate
    try:
        validated_data = validate_resource(sanitized)
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Call service layer
    try:
        result = db_service.create_resource(validated_data)
        logger.info(f"Resource {result.id} created successfully")
        return result
    except DatabaseError as e:
        logger.error(f"Failed to create resource: {e}")
        raise HTTPException(status_code=500, detail=e.message)
```

### Service Layer Guidelines

```python
from app.core.logging_config import get_logger
from app.core.exceptions import DatabaseError
from app.core.error_handling import retry_database_operation, ErrorContext

logger = get_logger(__name__)

@retry_database_operation
def create_resource(data: dict) -> str:
    """
    Service function with retry decorator for robustness.
    """
    with ErrorContext("database", "create_resource"):
        try:
            # Database operation
            doc_ref = db.collection('resources').add(data)
            logger.info(f"Resource created with ID: {doc_ref.id}")
            return doc_ref.id
        except GoogleCloudError as e:
            logger.error(f"GCP error creating resource: {e}")
            raise DatabaseError(
                message="Failed to create resource",
                details=str(e),
                context={"operation": "create", "collection": "resources"}
            )
```

### Exception Handling Rules

1. **Always raise specific exceptions** (never return None/False for errors)
2. **Include context** in exceptions (IDs, operation type, relevant data)
3. **Never catch Exception without re-raising** (unless it's a fallback)
4. **Use retry decorators** for transient failures
5. **Use circuit breakers** for external services (Gemini, Nominatim)

---

## Frontend Development

### SvelteKit 5 Component Structure

```svelte
<script lang="ts">
  import { toast } from '$lib/stores/toast';
  import { getErrorMessage } from '$lib/api';
  import LoadingButton from '$lib/components/LoadingButton.svelte';
  import { validateField, validationRules } from '$lib/validation';

  // Props
  let { data } = $props();

  // State
  let loading = $state(false);
  let formData = $state({ title: '', description: '' });
  let errors = $state<Record<string, string[]>>({});
  let touched = $state<Record<string, boolean>>({});

  // Derived state
  let isValid = $derived(
    Object.keys(errors).length === 0 && formData.title.length >= 10
  );

  // Validation
  function validateTitle() {
    const result = validateField(formData.title, [
      validationRules.required(),
      validationRules.minLength(10),
      validationRules.maxLength(200)
    ]);
    errors.title = result.errors;
  }

  // Actions
  async function handleSubmit() {
    loading = true;
    try {
      const response = await api.post('/api/v1/resource', formData);
      toast.show('Resource created successfully!', 'success');
      goto('/resources');
    } catch (error) {
      toast.show(getErrorMessage(error), 'error');
    } finally {
      loading = false;
    }
  }
</script>

<main>
  <h1>Create Resource</h1>

  <form onsubmit={handleSubmit}>
    <label for="title">
      Title ({formData.title.length}/200)
      <span aria-label="required">*</span>
    </label>
    <input
      id="title"
      type="text"
      bind:value={formData.title}
      oninput={validateTitle}
      onblur={() => touched.title = true}
      aria-required="true"
      aria-invalid={errors.title?.length > 0}
      aria-describedby={errors.title?.length > 0 ? 'title-error' : undefined}
    />
    {#if touched.title && errors.title?.length > 0}
      <span id="title-error" role="alert" class="error">
        {errors.title[0]}
      </span>
    {/if}

    <LoadingButton
      type="submit"
      {loading}
      disabled={!isValid}
      variant="primary"
    >
      Create Resource
    </LoadingButton>
  </form>
</main>

<style>
  .error {
    color: var(--color-error, #dc2626);
    font-size: 0.875rem;
    margin-top: 0.25rem;
  }
</style>
```

### Frontend UX Checklist

For **EVERY** page, ensure:

- [ ] All `alert()` calls replaced with `toast.show()`
- [ ] `LoadingButton` used for all form submissions
- [ ] `LoadingSpinner` shown during initial data fetching
- [ ] Form validation with inline error messages
- [ ] Character counters for text inputs (if limits exist)
- [ ] ARIA labels on all interactive elements
- [ ] Semantic HTML (`<main>`, `<section>`, `<article>`, `<nav>`)
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Focus-visible styles for accessibility
- [ ] Error states with user-friendly messages
- [ ] Empty states for lists/collections
- [ ] No `console.log` statements
- [ ] Responsive design (mobile-first)
- [ ] Optimistic UI updates where appropriate

---

## Error Handling Philosophy

### The Three-Layer Defense

**Layer 1: Prevention**
- Input validation at router level
- Type checking (TypeScript/Pydantic)
- Sanitization of user inputs

**Layer 2: Recovery**
- Retry logic with exponential backoff
- Circuit breakers for external services
- Graceful degradation (continue with partial data)

**Layer 3: Communication**
- Structured error responses
- User-friendly error messages
- Detailed logging for debugging
- Request IDs for tracing

### Custom Exception Hierarchy

```
DarshiBaseException
├── DatabaseError
│   ├── DatabaseConnectionError
│   ├── DatabaseTimeoutError
│   ├── DocumentNotFoundError
│   └── TransactionError
├── StorageError
│   ├── UploadFailedError
│   ├── BucketNotFoundError
│   └── QuotaExceededError
├── AIServiceError
│   ├── AIServiceUnavailableError
│   ├── AIRateLimitError
│   └── AIInvalidResponseError
├── GeocodingError
├── AnalyticsError
└── ValidationError
    ├── InvalidInputError
    ├── InvalidFileError
    └── InvalidCoordinatesError
```

**Rules:**
- Always raise the most specific exception type
- Include `context` dict with relevant data
- Set `recoverable=True` if client can retry
- Never expose sensitive data in error messages

### Error Response Format

```json
{
  "error": {
    "code": "DATABASE_ERROR",
    "message": "Failed to create report",
    "details": "Connection timeout after 10s",
    "timestamp": "2025-12-19T10:30:00Z",
    "request_id": "uuid-here",
    "path": "/api/v1/report",
    "recoverable": true
  }
}
```

---

## Logging Standards

### Logging Levels

| Level | Use Case | Examples |
|-------|----------|----------|
| **DEBUG** | Internal state, flow tracking | "Fetching report by id: {id}", "Encoded location to geohash: {hash}" |
| **INFO** | Successful operations, milestones | "Report {id} created by {user}", "AI analysis completed", "User logged in" |
| **WARNING** | Recoverable errors, validation failures | "Geocoding failed, using coordinates", "Rate limit approached", "Invalid file type" |
| **ERROR** | Actual errors affecting functionality | "Database query failed", "Storage upload failed", "AI service unavailable" |
| **CRITICAL** | System-level failures | "Failed to initialize Firestore", "Cannot connect to database" |

### Logging Best Practices

```python
# ✅ GOOD - Structured, contextual logging
logger.info(f"Report {report_id} created successfully by user {username}")
logger.error(f"Failed to upload image for report {report_id}: {error}", exc_info=True)
logger.debug(f"Processing {len(reports)} reports with status {status}")

# ❌ BAD - Generic, uninformative logging
logger.info("Report created")
logger.error("Error occurred")
logger.debug("Processing")
```

**Rules:**
- Include relevant IDs (report_id, user_id, request_id)
- Use f-strings for formatting
- Add `exc_info=True` to ERROR logs for stack traces
- Use structured logging for metrics (extra={...})
- Never log sensitive data (passwords, tokens, PII)

---

## Testing & Validation

### Input Validation Layers

**Router Layer:**
```python
# Validate request format, sanitize inputs
sanitized = sanitize_form_data(data)
validate_report_data(sanitized)  # Raises ValidationError
```

**Service Layer:**
```python
# Validate business rules
if not user.is_active:
    raise ValidationError("User account is inactive")
```

**Database Layer:**
```python
# Validate data integrity (handled by Firestore schemas)
```

### Validation Rules

- **Coordinates**: Latitude [-90, 90], Longitude [-180, 180]
- **Files**: Max 10MB, image types only (jpg, jpeg, png, webp)
- **Strings**: Max lengths enforced, XSS prevention via sanitization
- **Usernames**: 3-30 chars, alphanumeric + underscore
- **Passwords**: 8+ chars, mix of upper/lower/numbers (enforced client-side)
- **Emails**: RFC 5322 compliant (use Pydantic EmailStr)
- **Phone**: E.164 format preferred (+91xxxxxxxxxx)

---

## Git Workflow

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `perf`: Performance improvement
- `style`: Formatting, missing semicolons
- `docs`: Documentation only
- `test`: Adding/modifying tests
- `chore`: Build process, tooling, dependencies

**Examples:**
```bash
feat(reports): add image hash duplicate detection

Implement SHA256 hashing of uploaded images to detect exact duplicates.
Links new reports to existing reports with identical images.

Closes #42

---

fix(auth): resolve undefined user_email variable in delete endpoint

Changed user_email to username in reports.py line 303 to match
the migration from email-based to username-based authentication.

---

refactor(logging): standardize logging levels across all services

- Changed routine CRUD operations from INFO to DEBUG
- Added WARNING logs for validation failures
- Enhanced ERROR logs with contextual information
- Eliminated silent failures in geo_service

---

feat(frontend): implement toast notification system

Replace all alert() calls with elegant toast notifications.
Includes LoadingButton, LoadingSpinner components, and comprehensive
form validation with accessibility improvements (ARIA labels, keyboard nav).
```

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch (if needed)
- Feature branches: `feat/feature-name`
- Fix branches: `fix/bug-description`

### Commit Frequency

- **Commit after each logical change** (not too granular, not too broad)
- **Push after completing a feature/fix**
- **Tag releases** with semantic versioning (v1.0.0)

---

## Documentation Standards

### When to Create Documentation

**YES - Create documentation for:**
- Architecture decisions (this file)
- API endpoints (OpenAPI/Swagger)
- Setup/deployment guides
- Complex algorithms or business logic
- Error handling patterns (ERROR_HANDLING_IMPLEMENTATION.md)
- Migration guides (USERNAME_MIGRATION.md)

**NO - Don't create documentation for:**
- Self-evident code
- Standard patterns (following conventions)
- Temporary/experimental features
- Personal notes (use code comments instead)

### Code Comments

```python
# ✅ GOOD - Explains WHY, not WHAT
# Check for duplicates within 55m radius to avoid redundant reports
duplicates = find_nearby_reports(lat, lng, category, radius=0.0005)

# ❌ BAD - States the obvious
# Create a variable called duplicates
duplicates = find_nearby_reports(lat, lng, category, radius=0.0005)
```

**Rules:**
- Use comments to explain **why**, not **what**
- Docstrings for all public functions/classes
- TODO comments include issue numbers: `# TODO(#123): Implement caching`
- Remove commented-out code (use git history instead)

### Inline Documentation

```python
def analyze_image(image_bytes: bytes) -> AIAnalysisResult:
    """
    Analyze an image using Google Gemini AI to determine if it contains
    a valid civic grievance.

    Args:
        image_bytes: Raw image data (JPEG, PNG, or WebP format)

    Returns:
        AIAnalysisResult with is_valid, category, severity, and description

    Raises:
        AIServiceError: If the Gemini API is unavailable
        AIRateLimitError: If rate limit is exceeded
        AIInvalidResponseError: If the response cannot be parsed

    Example:
        >>> with open('pothole.jpg', 'rb') as f:
        ...     result = analyze_image(f.read())
        >>> result.is_valid
        True
        >>> result.category
        'pothole'
    """
    pass
```

---

## AI Assistant Guidelines

### For LLMs Working on This Codebase

**1. Always Read Before Writing**
- **NEVER** propose changes to code you haven't read
- Use `Read` tool to understand existing patterns
- Use `Grep` tool to find similar implementations
- Check this PHILOSOPHY.md file first

**2. Follow Established Patterns**
- Look for existing examples in the codebase
- Match the style, structure, and naming conventions
- Don't reinvent patterns that already exist
- If you see inconsistencies, ask before assuming

**3. Task Planning**
- Use `TodoWrite` tool for multi-step tasks (3+ steps)
- Break complex tasks into atomic subtasks
- Mark tasks as in_progress BEFORE starting
- Mark tasks as completed IMMEDIATELY after finishing
- Update todos frequently to track progress

**4. Error Handling is Non-Negotiable**
- **ALWAYS** use specific exception types (never generic Exception)
- **ALWAYS** add retry decorators for external calls
- **ALWAYS** log errors with context
- **NEVER** return None/False for error conditions (raise exceptions)
- **NEVER** use bare `except:` blocks

**5. Logging Discipline**
- Follow the logging standards table above
- **DEBUG** for internal operations
- **INFO** for user-facing operations
- **WARNING** for validation failures
- **ERROR** for actual failures
- **CRITICAL** for system-level issues

**6. Frontend Consistency**
- **ALWAYS** replace `alert()` with `toast.show()`
- **ALWAYS** use `LoadingButton` for async actions
- **ALWAYS** add ARIA labels and semantic HTML
- **ALWAYS** validate forms with inline errors
- **NEVER** leave `console.log` statements

**7. Testing & Validation**
- Test changes locally before committing
- Verify syntax with `python -m py_compile` or `tsc --noEmit`
- Check for regressions (did you break existing functionality?)
- Validate that imports work correctly

**8. Git Commit Hygiene**
- Use conventional commit format (feat, fix, refactor, etc.)
- Write clear, descriptive commit messages
- Commit related changes together (atomic commits)
- Push after completing a feature or fix

**9. Ask When Uncertain**
- Use `AskUserQuestion` tool for ambiguous requirements
- Don't guess at user intent
- Clarify before implementing major changes
- Present options when multiple approaches exist

**10. Room for Improvement**
- This philosophy is not set in stone
- Suggest improvements if you see better patterns
- Balance consistency with pragmatism
- Don't let perfect be the enemy of good

### Workflow for New Features

```
1. Read relevant files to understand existing patterns
2. Create TodoWrite list if task has 3+ steps
3. Plan implementation (consider error cases, validation, logging)
4. Implement with proper error handling and logging
5. Add frontend UX improvements (toast, loading, accessibility)
6. Test locally (syntax check, basic functionality)
7. Remove console.log statements
8. Update documentation if needed
9. Commit with conventional commit message
10. Push to repository
```

### Workflow for Bug Fixes

```
1. Read the file with the bug
2. Understand the root cause (don't just patch symptoms)
3. Check if similar bugs exist elsewhere
4. Fix the bug with proper error handling
5. Add logging if the bug was silent
6. Add validation to prevent recurrence
7. Test the fix
8. Commit with "fix: <description>"
9. Push to repository
```

---

## Philosophy Summary

**Darshi is built on these pillars:**

1. **Robustness**: Multiple layers of error handling, no silent failures
2. **User Experience**: Accessible, informative, delightful interactions
3. **Code Quality**: Consistent, maintainable, self-documenting code
4. **Security**: Input validation, sanitization, rate limiting, minimal exposure
5. **Observability**: Structured logging, error tracking, request tracing

**For AI Assistants:**

- Read before writing
- Follow established patterns
- Plan complex tasks with todos
- Error handling is mandatory
- Logging must be structured
- Frontend must be accessible
- No console.log in production
- Commit frequently with clear messages
- Ask when uncertain
- Suggest improvements, but respect consistency

**Remember**: The goal is not just working code, but **robust, maintainable, user-friendly** code that can scale and evolve over time.

---

**Last Updated**: 2025-12-19
**Version**: 1.0.0
**Maintained By**: Darshi Development Team
