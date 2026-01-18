"""
OAuth Router - Handles OAuth flows with Google, GitHub, Facebook using authlib

Endpoints:
- GET /auth/{provider}/login - Redirect to OAuth provider
- GET /auth/{provider}/callback - Handle OAuth callback
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.services.oauth_service import oauth_service, oauth
from app.services.ip_location_service import get_client_ip
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/auth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """
    Initiate OAuth login flow

    Args:
        provider: 'google', 'github', or 'facebook'

    Returns:
        Redirect to OAuth provider's authorization page
    """
    if provider not in ['google', 'github', 'facebook']:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    try:
        logger.info(f"OAuth login initiated for {provider}")

        # Get OAuth client
        client = oauth.create_client(provider)
        if not client:
            logger.error(f"{provider.capitalize()} OAuth client not configured - missing credentials")
            raise HTTPException(
                status_code=501,
                detail=f"{provider.capitalize()} OAuth not configured"
            )

        # Get redirect URI from settings (property method)
        redirect_uri = getattr(settings, f"{provider.upper()}_REDIRECT_URI")
        logger.info(f"OAuth {provider} redirect_uri: {redirect_uri}")

        # Create authorization URL
        redirect_data = await client.authorize_redirect(request, redirect_uri)

        logger.info(f"OAuth authorization redirect created for {provider}")

        return redirect_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth login error for {provider}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/signin?error=oauth_init_failed"
        )


@router.get("/api/v1/auth/{provider}/callback")
async def oauth_callback(provider: str, request: Request):
    """
    Handle OAuth callback

    Args:
        provider: 'google', 'github', or 'facebook'
        request: FastAPI request with query parameters (code, state, etc.)

    Returns:
        Redirect to frontend with JWT token
    """
    if provider not in ['google', 'github', 'facebook']:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    try:
        logger.info(f"OAuth callback received for {provider}")

        # Log query params for debugging (excluding sensitive data)
        query_params = dict(request.query_params)
        safe_params = {k: v for k, v in query_params.items() if k not in ['code', 'state']}
        logger.info(f"OAuth callback params (safe): {safe_params}")

        # Handle OAuth callback and get user info
        oauth_info = await oauth_service.handle_oauth_callback(provider, request)

        if not oauth_info:
            logger.error(f"OAuth callback failed for {provider} - no user info returned")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/signin?error=oauth_callback_failed"
            )

        logger.info(f"OAuth user info retrieved: provider={provider}, email={oauth_info.get('email')}")

        # Get client IP for location tracking
        client_ip = get_client_ip(request)
        logger.debug(f"OAuth callback client IP: {client_ip}")

        # Create or get user and generate JWT (pass IP for new user location tracking)
        result = await oauth_service.create_or_get_oauth_user(oauth_info, client_ip=client_ip)

        if not result:
            logger.error(f"Failed to create/get OAuth user for {provider}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/signin?error=user_creation_failed"
            )

        # Redirect to frontend with token
        access_token = result['access_token']
        user = result['user']

        logger.info(f"OAuth login successful: {user['username']} via {provider}")

        # Store suggested username for onboarding (if new user needs to set it)
        # Generate clean username from name or email
        import re
        suggested_username = ''

        name = oauth_info.get('name', '')
        if name and name.strip():
            suggested_username = name.lower().strip()
            suggested_username = re.sub(r'[^a-z0-9]+', '_', suggested_username)
            suggested_username = re.sub(r'_+', '_', suggested_username).strip('_')

        if not suggested_username:
            email = oauth_info.get('email', '')
            if email:
                email_part = email.split('@')[0].lower()
                email_clean = re.sub(r'\d+$', '', email_part)  # Remove trailing numbers
                email_clean = re.sub(r'[^a-z0-9]+', '_', email_clean)
                email_clean = re.sub(r'_+', '_', email_clean).strip('_')
                # Truncate long emails
                if len(email_clean) > 20:
                    email_clean = email_clean[:15].rstrip('_')
                suggested_username = email_clean

        # Redirect to frontend with token and suggested username
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}&username={user['username']}&suggested_username={suggested_username}"
        )

    except Exception as e:
        logger.error(f"OAuth callback error for {provider}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/signin?error=oauth_error&message={str(e)}"
        )


# Legacy endpoints for backwards compatibility (redirect to new endpoints)
@router.get("/api/v1/auth/google/login")
async def google_login_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_login('google', request)


@router.get("/api/v1/auth/google/callback")
async def google_callback_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_callback('google', request)


@router.get("/api/v1/auth/github/login")
async def github_login_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_login('github', request)


@router.get("/api/v1/auth/github/callback")
async def github_callback_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_callback('github', request)


@router.get("/api/v1/auth/facebook/login")
async def facebook_login_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_login('facebook', request)


@router.get("/api/v1/auth/facebook/callback")
async def facebook_callback_redirect(request: Request):
    """Redirect to new unified OAuth endpoint"""
    return await oauth_callback('facebook', request)
