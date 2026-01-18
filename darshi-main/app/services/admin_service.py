"""
Admin user management service.
Handles admin authentication using PostgreSQL users table with role='admin'.
Admins are stored in the main users table, not a separate collection.
"""

from datetime import datetime
from typing import Optional, List
from app.services import postgres_service as db_service, auth_service
from fastapi import HTTPException, status
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def create_admin(
    username: str,
    email: str,
    password: str,
    role: str = "admin",
    created_by: str = "system"
) -> dict:
    """
    Create a new admin user in the users table.

    Args:
        username: Unique username for admin
        email: Admin email address
        password: Plain text password (will be hashed)
        role: Always 'admin' for admin users
        created_by: Username of admin who created this account

    Returns:
        dict: Created admin data (without password hash)

    Raises:
        HTTPException: If admin already exists or validation fails
    """
    try:
        # Validate role
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin' for admin accounts"
            )

        # Check if user already exists
        existing_user = await db_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with username '{username}' already exists"
            )

        if email:
            existing_email = await db_service.get_user_by_email(email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User with email '{email}' already exists"
                )

        # Hash password
        password_hash = auth_service.get_password_hash(password)

        # Create admin user
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': 'admin',
            'is_active': True,
            'is_verified': True,  # Admins are pre-verified
            'email_verified': True
        }

        user_id = await db_service.create_user(user_data)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create admin user"
            )

        logger.info(f"Admin created: {username} by {created_by}")

        return {
            "username": username,
            "email": email,
            "role": "admin",
            "created_at": datetime.utcnow(),
            "is_active": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )


async def authenticate_admin(username: str, password: str) -> Optional[dict]:
    """
    Authenticate admin credentials.

    Args:
        username: Admin username
        password: Plain text password

    Returns:
        dict: Admin data if authentication successful, None otherwise
    """
    try:
        # Get user from database
        user = await db_service.get_user_by_username(username)

        if not user:
            logger.warning(f"Admin login failed: user '{username}' not found")
            return None

        # Check if user is admin
        if user.get('role') != 'admin':
            logger.warning(f"Login failed: user '{username}' is not an admin")
            return None

        # Check if admin is active
        if not user.get('is_active', True):
            logger.warning(f"Login failed: admin '{username}' is inactive")
            return None

        # Verify password
        password_hash = user.get('password_hash', '')
        if not password_hash or not auth_service.verify_password(password, password_hash):
            logger.warning(f"Admin login failed: invalid password for '{username}'")
            return None

        # Update last login time (optional - you can add this field to users table if needed)
        logger.info(f"Admin logged in successfully: {username}")

        # Return admin data without password
        return {
            "username": user['username'],
            "email": user.get('email'),
            "role": user.get('role'),
            "created_at": user.get('created_at'),
            "is_active": user.get('is_active', True)
        }

    except Exception as e:
        logger.error(f"Admin authentication error: {e}", exc_info=True)
        return None


async def get_admin(username: str) -> Optional[dict]:
    """
    Get admin by username.

    Args:
        username: Admin username

    Returns:
        dict: Admin data (without password) or None if not found
    """
    try:
        user = await db_service.get_user_by_username(username)

        if not user:
            return None

        # Verify user is admin
        if user.get('role') != 'admin':
            return None

        return {
            "username": user['username'],
            "email": user.get('email'),
            "role": user.get('role'),
            "created_at": user.get('created_at'),
            "is_active": user.get('is_active', True)
        }

    except Exception as e:
        logger.error(f"Failed to get admin '{username}': {e}", exc_info=True)
        return None


async def update_admin_status(
    username: str,
    is_active: bool,
    updated_by: str
) -> bool:
    """
    Activate or deactivate an admin account.

    Args:
        username: Admin username
        is_active: New status
        updated_by: Username of admin making the change

    Returns:
        bool: True if successful

    Raises:
        HTTPException: If admin not found or update fails
    """
    try:
        admin = await get_admin(username)

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin '{username}' not found"
            )

        # Update status
        success = await db_service.update_user(username, {
            'is_active': is_active
        })

        if success:
            logger.info(f"Admin '{username}' status updated to {'active' if is_active else 'inactive'} by {updated_by}")
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update admin status"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update admin status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update admin status: {str(e)}"
        )


async def list_admins(include_inactive: bool = False) -> List[dict]:
    """
    List all admin users.

    Args:
        include_inactive: Whether to include inactive admins

    Returns:
        list: List of admin data (without passwords)
    """
    try:
        # This would need a new function in postgres_service.py
        # For now, we can't efficiently list all admins without it
        # TODO: Add get_users_by_role() to postgres_service.py
        logger.warning("list_admins() not yet implemented - requires get_users_by_role()")
        return []

    except Exception as e:
        logger.error(f"Failed to list admins: {e}", exc_info=True)
        return []


async def verify_admin_permission(
    username: str,
    required_role: str = "admin"
) -> bool:
    """
    Verify if user has admin permission.

    Args:
        username: Username to check
        required_role: Required role (always 'admin' for this system)

    Returns:
        bool: True if user has admin permission
    """
    try:
        if required_role != "admin":
            logger.warning(f"Unknown role '{required_role}' requested")
            return False

        user = await db_service.get_user_by_username(username)

        if not user:
            return False

        # Check if user is admin and active
        is_admin = user.get('role') == 'admin'
        is_active = user.get('is_active', True)

        return is_admin and is_active

    except Exception as e:
        logger.error(f"Failed to verify admin permission for '{username}': {e}", exc_info=True)
        return False
