from fastapi import Depends, HTTPException, status
from app.routers.auth import get_current_user

async def check_is_admin(current_user: dict = Depends(get_current_user)):
    """
    Dependency to check if the user has admin privileges.
    """
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

async def check_is_moderator(current_user: dict = Depends(get_current_user)):
    """
    Dependency to check if the user has moderator privileges.
    """
    if current_user.get("role") not in ["moderator", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required"
        )
    return current_user
