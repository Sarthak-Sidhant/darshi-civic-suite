from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from jose import jwt, JWTError
except ImportError:
    logger.warning("python-jose not installed, JWT authentication will be disabled")
    jwt = None
    JWTError = Exception

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    logger.warning("passlib not installed, password hashing will be disabled")
    pwd_context = None

def verify_password(plain_password, hashed_password):
    if not pwd_context:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    if not pwd_context:
        raise RuntimeError("Password hashing not available - passlib not installed")
    return pwd_context.hash(password)

# JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user_type: str = "citizen"):
    """
    Create JWT access token with user_type claim for role-based access control.

    Args:
        data: Token payload data (must include 'sub' claim with user identifier)
        expires_delta: Optional custom expiration time
        user_type: User type - 'citizen' or 'admin' (default: 'citizen')

    Returns:
        Encoded JWT token string
    """
    if not jwt:
        raise RuntimeError("JWT not available - python-jose not installed")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at timestamp
        "user_type": user_type,  # Distinguish admin from citizen tokens
    })

    # Validate required claims
    if "sub" not in to_encode:
        raise ValueError("Token must include 'sub' claim with user identifier")

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """
    Decode and validate JWT token.

    Returns:
        Token payload if valid, None if invalid or expired
    """
    if not jwt:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_exp": True,  # Explicitly verify expiration
                "verify_iat": True,  # Verify issued-at timestamp
            }
        )

        # Additional validation: ensure required claims exist
        if "sub" not in payload:
            logger.warning("Token missing 'sub' claim")
            return None

        # Validate user_type claim (should be present in new tokens)
        if "user_type" in payload and payload["user_type"] not in ["citizen", "admin"]:
            logger.warning(f"Invalid user_type claim: {payload['user_type']}")
            return None

        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except JWTError as e:
        logger.warning(f"Invalid or malformed token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None

def verify_token(token: str):
    """
    Verify JWT token and return payload.
    Alias for decode_token for consistency with security.py
    """
    return decode_token(token)

def create_admin_token(admin_data: dict):
    """
    Create JWT token for admin with shorter expiration time and 'admin' user_type.

    Args:
        admin_data: Admin payload data (must include email/username in 'sub' or as separate field)

    Returns:
        Encoded JWT token with user_type='admin'
    """
    expires_delta = timedelta(minutes=settings.ADMIN_TOKEN_EXPIRE_MINUTES)

    # Ensure 'sub' claim exists
    if "sub" not in admin_data:
        if "email" in admin_data:
            admin_data["sub"] = admin_data["email"]
        elif "username" in admin_data:
            admin_data["sub"] = admin_data["username"]
        else:
            raise ValueError("Admin data must include email or username")

    return create_access_token(admin_data, expires_delta=expires_delta, user_type="admin")

# 2FA removed - not needed for MVP. Can be added later with pyotp if required.
