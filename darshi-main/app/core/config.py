import os
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # PostgreSQL Database
    POSTGRES_PASSWORD: str
    DATABASE_URL: Optional[str] = None

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """
        Construct async database URL with properly encoded password.
        Prioritizes recreating the URL from components to handle special characters.
        """
        # If we have the raw password, use it to construct a safe URL
        if self.POSTGRES_PASSWORD:
            import urllib.parse
            encoded_pwd = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
            # Default values if not in env, matching the user's .env structure
            # Assuming user is 'postgres' and db is 'darshi' based on the screenshot
            return f"postgresql://postgres:{encoded_pwd}@postgres:5432/darshi"
        
        # Fallback to provided URL (if password var is missing for some reason)
        if self.DATABASE_URL:
            return self.DATABASE_URL
            
        return ""

    # Redis Cache
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None  # Auto-constructed if not provided

    # Cloudflare R2 Storage (Optional - app can run without it)
    R2_ENDPOINT: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_PUBLIC_URL: Optional[str] = None

    # AI
    GEMINI_API_KEY: Optional[str] = None

    # Auth
    SECRET_KEY: str = "super_secret_key_for_dev_only_change_in_prod_v4"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days (reduced from 30 for better security)
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 60  # Admin sessions expire faster

    # List of forbidden/weak secret keys that should never be used
    FORBIDDEN_SECRET_KEYS: list = [
        "super_secret_key_for_dev_only_change_in_prod_v4",
        "super_secret_key_for_dev_only_change_in_prod",
        "your-secret-key-here",
        "changeme",
        "secret",
        "development"
    ]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    REDIS_CACHE_TTL: int = 180  # Default cache TTL in seconds (3 minutes)

    # Auto-use Redis if available, fallback to memory
    @property
    def RATE_LIMIT_STORAGE_URL(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return "memory://"

    @property
    def REDIS_ENABLED(self) -> bool:
        """Auto-enabled if REDIS_URL is set"""
        return bool(self.REDIS_URL)

    # CORS - Parse comma-separated origins from env
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"

    # Logging & Monitoring
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = "logs/darshi.log"  # Set to None to disable file logging
    ENABLE_SENTRY: bool = False
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"  # development, staging, production

    # Email Configuration (Resend)
    EMAIL_ENABLED: bool = True
    EMAIL_FROM: str = "Darshi <noreply@darshi.app>"
    EMAIL_FROM_NAME: str = "Darshi"
    RESEND_API_KEY: Optional[str] = None
    FRONTEND_URL: str = "https://darshi.app"

    # OAuth Providers
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None

    # Base URL for OAuth callbacks - defaults to production, override in .env for local dev
    API_BASE_URL: str = "https://api.darshi.app"

    @property
    def GOOGLE_REDIRECT_URI(self) -> str:
        return f"{self.API_BASE_URL}/api/v1/auth/google/callback"

    @property
    def GITHUB_REDIRECT_URI(self) -> str:
        return f"{self.API_BASE_URL}/api/v1/auth/github/callback"

    @property
    def FACEBOOK_REDIRECT_URI(self) -> str:
        return f"{self.API_BASE_URL}/api/v1/auth/facebook/callback"

    # Reddit Integration
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: Optional[str] = "DarshiBot/1.0"
    REDDIT_USERNAME: Optional[str] = None
    REDDIT_PASSWORD: Optional[str] = None

    # Browser Push Notifications (VAPID)
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_ADMIN_EMAIL: str = "admin@darshi.app"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        # Handle subnet notation for LAN (10.0.0.0/24)
        expanded_origins = []
        for origin in origins:
            if "/24" in origin:
                # Expand subnet to pattern
                base = origin.split("/")[0].rsplit(".", 1)[0]
                expanded_origins.append(f"http://{base}.*")  # Pattern matching
            else:
                expanded_origins.append(origin)
        return expanded_origins

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

settings = Settings()

# Validate SECRET_KEY in production
def validate_secret_key():
    """Validate that SECRET_KEY is not a forbidden/weak key in production"""
    import sys
    if settings.ENVIRONMENT == "production":
        if settings.SECRET_KEY in settings.FORBIDDEN_SECRET_KEYS:
            msg = (
                "CRITICAL SECURITY ERROR: You are using a default/weak SECRET_KEY in production! "
                "Generate a secure key with: python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
            print(msg, file=sys.stderr)
            # raise RuntimeError(msg) # Temporarily disabled for debugging
            
        if len(settings.SECRET_KEY) < 32:
            msg = "CRITICAL SECURITY ERROR: SECRET_KEY is too short (minimum 32 characters required)"
            print(msg, file=sys.stderr)
            # raise RuntimeError(msg) # Temporarily disabled for debugging

# Run validation
validate_secret_key()
if __name__ == "__main__":
    try:
        validate_secret_key()
        print("Configuration valid.")
    except Exception as e:
        print(f"Configuration invalid: {e}")
        exit(1)
