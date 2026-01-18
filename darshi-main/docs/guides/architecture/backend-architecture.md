---
title: Backend Architecture
tags: [backend, fastapi, python, postgresql, services, error-handling, async, sqlalchemy, redis, caching]
related:
  - "[[overview]]"
  - "[[data-models]]"
  - "[[../api/overview]]"
  - "[[../../reference/PHILOSOPHY]]"
---

# Backend Architecture

← Back to [[overview|Architecture Overview]]

Detailed backend architecture for Darshi's FastAPI application.

## Project Structure

```
app/
├── main.py                    # FastAPI app, middleware, CORS
├── core/                      # Core utilities
│   ├── config.py             # Settings (Pydantic)
│   ├── exceptions.py         # 32 custom exception types
│   ├── error_handling.py     # Circuit breakers, retry logic
│   ├── security.py           # JWT, bcrypt, rate limiting
│   ├── validation.py         # Input validators
│   ├── logging_config.py     # Structured logging
│   ├── redis_client.py       # Redis connection
│   ├── cache.py              # Caching layer
│   └── http_client.py        # HTTP client with retries
├── db/                        # Database layer
│   ├── session.py            # AsyncSession management
│   ├── models.py             # SQLAlchemy ORM models
│   └── migrations/           # Alembic migrations
├── routers/                   # API endpoints
│   ├── reports.py            # Report CRUD, upvotes, comments
│   ├── admin.py              # Admin dashboard
│   ├── auth.py               # Authentication
│   ├── oauth.py              # OAuth providers
│   ├── users.py              # User management
│   └── notifications.py      # Push notifications
├── services/                  # Business logic
│   ├── postgres_service.py   # PostgreSQL operations
│   ├── ai_service.py         # Gemini AI integration
│   ├── storage_service.py    # Cloudflare R2
│   ├── geo_service.py        # Geocoding, geohashing
│   ├── auth_service.py       # JWT, passwords
│   ├── admin_service.py      # Admin operations
│   ├── image_service.py      # Image hashing, duplicates
│   └── oauth_service.py      # OAuth integration
├── models/                    # Pydantic schemas
└── middleware/                # Custom middleware
```

## Service Layer Design

All services use **module-level functions** (not classes):

```python
from app.core.error_handling import retry_database_operation
from app.core.exceptions import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

@retry_database_operation
async def create_report(db: AsyncSession, data: dict) -> int:
    """Create a new report in PostgreSQL."""
    try:
        stmt = insert(Report).values(**data).returning(Report.id)
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar()
    except SQLAlchemyError as e:
        await db.rollback()
        raise DatabaseError("Failed to create report", details=str(e))
```

## Error Handling (3-Layer Defense)

### Layer 1: Prevention
- Input validation (`core/validation.py`)
- Type checking (Pydantic)
- Sanitization (`sanitize_form_data()`)

### Layer 2: Recovery
- Retry decorators: `@retry_database_operation`, `@retry_ai_operation`
- Circuit breakers: Gemini (5 failures/120s), Nominatim (3 failures/60s)
- Graceful degradation

### Layer 3: Communication
- Structured error responses with request IDs
- User-friendly messages
- Detailed logging with context

## Custom Exceptions

```python
DarshiBaseException (base class)
├── DatabaseError → PostgreSQL operations
├── StorageError → Cloudflare R2 operations
├── AIServiceError → Gemini API failures
├── GeocodingError → Nominatim failures
├── ValidationError → Input validation (400)
└── AuthenticationError → Auth failures (401)
```

## Database Layer

### SQLAlchemy ORM Models

```python
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography

Base = declarative_base()

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    report_id = Column(UUID, unique=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geography(geometry_type='POINT', srid=4326))
    geohash = Column(String(10))
    status = Column(String(30), default="PENDING_VERIFICATION")
    category = Column(String(50))
    severity = Column(Integer)
    image_urls = Column(ARRAY(Text))
    image_data = Column(JSONB)
    upvote_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    timeline = Column(JSONB, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Async Database Operations

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Create async engine
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/darshi",
    pool_size=20,
    max_overflow=10
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency for routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Caching Strategy

### Redis Cache Layers

1. **Report list**: 5 minutes TTL
2. **Individual report**: 15 minutes TTL
3. **Geocoding results**: 24 hours TTL
4. **AI verification**: Permanent

```python
from app.core.cache import cache

@cache(ttl=300)  # 5 minutes
async def get_popular_reports(db: AsyncSession):
    result = await db.execute(
        select(Report)
        .where(Report.status == "VERIFIED")
        .order_by(Report.upvote_count.desc())
        .limit(10)
    )
    return result.scalars().all()
```

## Circuit Breakers

### Gemini AI Circuit Breaker

- Threshold: 5 failures within 120 seconds
- Half-open: Allow 1 test after 60s
- If test succeeds → Reset
- If test fails → Back to open

### Nominatim Circuit Breaker

- Threshold: 3 failures within 60 seconds
- Half-open: Allow 1 test after 30s
- Fallback: Continue without geocoding

## Background Task Processing

```python
from fastapi import BackgroundTasks

@router.post("/report")
async def create_report(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Create report
    report_id = await postgres_service.create_report(db, data)

    # Queue background AI verification
    background_tasks.add_task(
        ai_service.verify_report,
        report_id
    )

    return {"report_id": report_id}
```

## Middleware

### Performance Monitoring

```python
from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

## Security Implementation

### JWT Authentication

```python
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        return {"username": username, "user_id": payload.get("user_id")}
    except JWTError:
        raise AuthenticationError("Invalid token")
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

@router.post("/report")
@limiter.limit("10/hour")  # Anonymous
@limiter.limit("50/hour", key_func=get_jwt_identity)  # Authenticated
async def create_report(...):
    ...
```

---

← Back to [[overview|Architecture Overview]] | Next: [[frontend-architecture|Frontend Architecture]] →

**Last Updated**: December 28, 2025
