from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models.user import (
    UserCreate, UserResponse, Token, PasswordChange, PasswordResetRequest,
    PasswordReset, EmailVerificationRequest, EmailVerification, MagicLinkRequest
)
from app.services import postgres_service as db_service, verification_service, email_service, auth_service
from app.core.logging_config import get_logger
from app.core.security import limiter
from app.core.config import settings

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Helpers
async def get_current_user_optional(request: Request):
    """
    Get current user from JWT token if present, otherwise return None.
    Used for endpoints that support both authenticated and anonymous access.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    payload = auth_service.decode_token(token)
    if not payload:
        return None

    # Get identifier from token
    identifier = payload.get("sub") or payload.get("username") or payload.get("email")
    if not identifier:
        return None

    # Try to find user by username first (new system)
    user = await db_service.get_user_by_username(identifier)
    if user:
        return user

    # Fall back to email (legacy system)
    user = await db_service.get_user_by_email(identifier)
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current CITIZEN user from JWT token.
    IMPORTANT: This does NOT authenticate admins - use get_current_admin for admin endpoints.
    """
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # SECURITY NOTE: We allow both citizen AND admin tokens here.
    # Admins are a superset of citizens - they need to access profile, settings, etc.
    # Admin-ONLY endpoints use get_current_admin instead.
    user_type = payload.get("user_type", "citizen")  # For logging only

    # Get identifier from token (username or email)
    identifier = payload.get("sub") or payload.get("username") or payload.get("email")
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    # Try to find user by username first (new system)
    user = await db_service.get_user_by_username(identifier)
    if user:
        return user

    # Fall back to email (legacy system)
    user = await db_service.get_user_by_email(identifier)
    if user:
        return user

    raise HTTPException(status_code=404, detail="User not found")

# Registration & Login
@router.post("/api/v1/auth/register", response_model=UserResponse)
@limiter.limit("5/hour")  # Prevent mass account creation
async def register(request: Request, user: UserCreate):
    """
    Register a new user with username, email, and password.
    - Username is required and must be unique
    - Email is required
    - Password is required
    """
    # Validate required fields
    if not user.username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not user.email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not user.password:
        raise HTTPException(status_code=400, detail="Password is required")

    # Check uniqueness constraints (prevent user enumeration by using generic error)
    username_exists = await db_service.get_user_by_username(user.username)
    email_exists = await db_service.get_user_by_email(user.email)

    if username_exists or email_exists:
        raise HTTPException(
            status_code=400,
            detail="An account with these credentials already exists"
        )

    # Hash password
    hashed_pw = auth_service.get_password_hash(user.password)

    # Save User (simplified data - only include fields that exist in DB)
    user_data = {
        "username": user.username,
        "email": user.email,
        "password_hash": hashed_pw,
        "role": "citizen",
        "is_active": True,
        "is_verified": False
    }

    user_id = await db_service.create_user(user_data)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    logger.info(f"User registered: {user.username}")

    # Get created user and return response
    created_user = await db_service.get_user_by_username(user.username)
    return UserResponse(**created_user)

@router.post("/api/v1/auth/token", response_model=Token)
@limiter.limit("10/hour")  # Prevent brute force attacks
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username/email and password.
    The 'username' field can accept:
    - Username
    - Email address
    """
    identifier = form_data.username
    user = None

    # Try to find user by username or email
    user = await db_service.get_user_by_username(identifier)
    if not user:
        user = await db_service.get_user_by_email(identifier)

    # Check if user exists
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    # Check if OAuth user (no password)
    if user.get('oauth_provider'):
        raise HTTPException(
            status_code=400,
            detail=f"This account uses {user['oauth_provider']} login. Please use 'Continue with {user['oauth_provider'].title()}'"
        )

    # Check if user has a password set
    password_hash = user.get('password_hash') or user.get('hashed_password')
    if not password_hash:
        raise HTTPException(
            status_code=400,
            detail="This account has no password set. Please reset your password."
        )

    # Verify password
    if not auth_service.verify_password(form_data.password, password_hash):
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    # Get username for token
    username = user.get('username') or user.get('email')

    # Determine user_type based on role
    user_role = user.get('role', 'citizen')
    admin_roles = ['admin', 'super_admin', 'municipality_admin', 'municipality_staff']
    user_type = 'admin' if user_role in admin_roles else 'citizen'

    # Create Token with appropriate user_type and include role + municipality_id
    token_data = {
        "sub": username,
        "role": user_role,
        "username": username
    }
    
    # Include municipality_id for municipality officials
    if user.get('municipality_id'):
        token_data['municipality_id'] = user['municipality_id']
    
    access_token = auth_service.create_access_token(
        data=token_data,
        user_type=user_type
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/v1/auth/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**current_user)

# Email Verification
@router.post("/api/v1/auth/send-email-verification")
@limiter.limit("3/hour")  # Prevent email spam
async def send_email_verification(request: Request, email_request: EmailVerificationRequest):
    """
    Send or resend email verification link.
    Can be called by unauthenticated users.
    """
    user = await db_service.get_user_by_email(email_request.email)
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}

    if user.get('email_verified'):
        raise HTTPException(status_code=400, detail="Email already verified")

    success, token = verification_service.verification_service.send_email_verification(email_request.email)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    return {"message": "Verification email sent successfully"}

@router.post("/api/v1/auth/verify-email")
@limiter.limit("10/hour")  # Reasonable limit for token verification attempts
async def verify_email(request: Request, email_verification: EmailVerification):
    """Verify email using token from email link"""
    success, email = verification_service.verification_service.verify_email_token(email_verification.token)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    return {"message": "Email verified successfully", "email": email}

# Password Reset
@router.post("/api/v1/auth/forgot-password")
@limiter.limit("3/hour")  # Prevent password reset abuse
async def forgot_password(request: Request, reset_request: PasswordResetRequest):
    """
    Request password reset link.
    Always returns success to prevent email enumeration.
    """
    success, token = verification_service.verification_service.send_password_reset(reset_request.email)

    # Always return success message, even if email doesn't exist
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/api/v1/auth/reset-password")
@limiter.limit("5/hour")  # Prevent brute force token guessing
async def reset_password(request: Request, password_reset: PasswordReset):
    """Reset password using token from email link"""
    success, email = verification_service.verification_service.reset_password(password_reset.token, password_reset.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return {"message": "Password reset successfully"}

@router.put("/api/v1/auth/change-password")
@limiter.limit("10/hour")  # Prevent brute force old password guessing
async def change_password(request: Request, password_change: PasswordChange, current_user: dict = Depends(get_current_user)):
    """
    Change password for authenticated user.
    Requires old password for security.
    """
    # Check if OAuth user
    if current_user.get('oauth_provider'):
        raise HTTPException(
            status_code=400,
            detail="OAuth users cannot change password. Manage your password through your OAuth provider."
        )

    # Verify old password (database uses 'password_hash', some models use 'hashed_password')
    password_hash = current_user.get('password_hash') or current_user.get('hashed_password')
    if not password_hash:
        raise HTTPException(
            status_code=400,
            detail="No password set for this account. Use password reset to set one."
        )
    if not auth_service.verify_password(password_change.old_password, password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    # Hash and update new password
    hashed_password = auth_service.get_password_hash(password_change.new_password)
    await db_service.update_user_password(current_user['email'], hashed_password)

    return {"message": "Password changed successfully"}

# Username Availability Check
@router.get("/api/v1/auth/check-username")
async def check_username_availability(username: str):
    """
    Check if a username is available for registration.
    Returns {"available": true/false}
    """
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    existing_user = await db_service.get_user_by_username(username)
    return {"available": existing_user is None, "username": username}


# Magic Link Authentication (Passwordless)
@router.post("/api/v1/auth/send-magic-link")
@limiter.limit("5/hour")  # Prevent spam
async def send_magic_link(request: Request, magic_request: MagicLinkRequest):
    """
    Send a magic link (passwordless login) to the user's email.
    Link expires in 15 minutes.
    """
    import secrets
    from datetime import datetime, timedelta
    
    try:
        # Check if user exists with this email
        user = await db_service.get_user_by_email(magic_request.email)
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        if user:
            # Existing user - update magic link token
            await db_service.update_user(user['username'], {
                'magic_link_token': token,
                'magic_link_expires': expires_at
            })
            logger.info(f"Magic link sent to existing user: {magic_request.email}")
        else:
            # New user - create account without password
            username = magic_request.email.split('@')[0]
            # Ensure username is unique
            counter = 1
            original_username = username
            while await db_service.get_user_by_username(username):
                username = f"{original_username}{counter}"
                counter += 1
            
            # Create user with magic link token
            user_data = {
                'username': username,
                'email': magic_request.email,
                'password_hash': None,  # No password for magic link users
                'is_active': True,
                'is_verified': False,  # Will verify on magic link click
                'role': 'citizen',
                'magic_link_token': token,
                'magic_link_expires': expires_at
            }
            await db_service.create_user(user_data)
            logger.info(f"Magic link sent to new user: {magic_request.email}")
        
        # Send email with magic link
        magic_link = f"{settings.FRONTEND_URL}/auth/magic-link?token={token}"
        await email_service.email_service.send_magic_link_email(magic_request.email, magic_link)
        
        # Security: Always return success even if email doesn't exist (prevent enumeration)
        return {"message": "If an account exists with this email, a login link has been sent"}
    
    except Exception as e:
        logger.error(f"Error sending magic link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send magic link")


@router.get("/api/v1/auth/verify-magic-link")
@limiter.limit("10/minute")  # Rate limit to prevent brute-force token guessing
async def verify_magic_link(request: Request, token: str):
    """
    Verify magic link token and authenticate user.
    Returns JWT access token if valid.

    Rate limited to 10 attempts per minute to prevent brute-force attacks.
    """
    from datetime import datetime, timezone

    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    try:
        # Find user by magic link token
        user = await db_service.get_user_by_magic_link_token(token)
        
        if not user:
            logger.warning(f"Invalid or expired magic link token attempted")
            raise HTTPException(status_code=400, detail="Invalid or expired link")
        
        # Check if token has expired (use timezone-aware datetime for comparison with TIMESTAMPTZ)
        if user.get('magic_link_expires'):
            expires_at = user['magic_link_expires']
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Expired magic link token for user: {user['username']}")
                raise HTTPException(status_code=400, detail="Link has expired. Please request a new one")
        
        # Clear magic link token (one-time use)
        await db_service.update_user(user['username'], {
            'magic_link_token': None,
            'magic_link_expires': None,
            'email_verified': True,  # Verify email on successful magic link login
            'last_login': datetime.utcnow()
        })
        
        # Generate JWT token
        access_token = auth_service.create_access_token(
            data={"sub": user['username']},
            user_type="citizen"
        )
        
        logger.info(f"Magic link authentication successful for user: {user['username']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(**user)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying magic link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify magic link")
