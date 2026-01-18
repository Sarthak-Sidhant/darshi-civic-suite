"""
OAuth Service - Authlib integration for Google, Facebook, GitHub

Handles:
- OAuth 2.0 authorization flows
- User info retrieval from providers
- Account linking/creation
"""

import logging
from typing import Optional, Dict
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from app.core.config import settings
from app.services import postgres_service as db_service
from app.services.auth_service import create_access_token, create_admin_token

logger = logging.getLogger(__name__)

# Initialize OAuth with authlib
oauth = OAuth()

# Register Google OAuth
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account'  # Always show account picker
        }
    )
    logger.info("Google OAuth registered")
else:
    logger.warning("Google OAuth not configured (missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)")

# Register GitHub OAuth (if credentials configured)
if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
    oauth.register(
        name='github',
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )
    logger.info("GitHub OAuth registered")
else:
    logger.info("GitHub OAuth not configured (missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET)")

# Register Facebook OAuth (if credentials configured)
if settings.FACEBOOK_APP_ID and settings.FACEBOOK_APP_SECRET:
    oauth.register(
        name='facebook',
        client_id=settings.FACEBOOK_APP_ID,
        client_secret=settings.FACEBOOK_APP_SECRET,
        access_token_url='https://graph.facebook.com/v18.0/oauth/access_token',
        access_token_params=None,
        authorize_url='https://www.facebook.com/v18.0/dialog/oauth',
        authorize_params=None,
        api_base_url='https://graph.facebook.com/v18.0/',
        client_kwargs={'scope': 'email public_profile'},
    )
    logger.info("Facebook OAuth registered")
else:
    logger.info("Facebook OAuth not configured (missing FACEBOOK_APP_ID or FACEBOOK_APP_SECRET)")


class OAuthService:
    """Service for handling OAuth authentication"""

    @staticmethod
    async def get_authorization_url(provider: str, request: Request) -> Optional[str]:
        """
        Get OAuth authorization URL for provider

        Args:
            provider: 'google', 'github', or 'facebook'
            request: Starlette request object

        Returns:
            Authorization URL to redirect user to
        """
        try:
            client = oauth.create_client(provider)
            if not client:
                logger.error(f"OAuth provider '{provider}' not configured")
                return None

            # Get redirect URI from settings (property method)
            redirect_uri = getattr(settings, f"{provider.upper()}_REDIRECT_URI")
            return await client.authorize_redirect(request, redirect_uri)

        except Exception as e:
            logger.error(f"Error creating authorization URL for {provider}: {e}", exc_info=True)
            return None

    @staticmethod
    async def handle_oauth_callback(provider: str, request: Request) -> Optional[Dict]:
        """
        Handle OAuth callback and get user info

        Args:
            provider: 'google', 'github', or 'facebook'
            request: Starlette request object with callback parameters

        Returns:
            User info dict with:
            {
                "provider": str,
                "provider_user_id": str,
                "email": str,
                "name": str,
                "picture": str (optional),
                "email_verified": bool
            }
        """
        try:
            client = oauth.create_client(provider)
            if not client:
                logger.error(f"OAuth provider '{provider}' not configured")
                return None

            # Exchange code for token
            token = await client.authorize_access_token(request)
            if not token:
                logger.error(f"{provider} token exchange failed")
                return None

            # Get user info based on provider
            if provider == 'google':
                return await OAuthService._get_google_user_info(client, token)
            elif provider == 'github':
                return await OAuthService._get_github_user_info(client, token)
            elif provider == 'facebook':
                return await OAuthService._get_facebook_user_info(client, token)
            else:
                logger.error(f"Unknown OAuth provider: {provider}")
                return None

        except Exception as e:
            logger.error(f"Error handling {provider} OAuth callback: {e}", exc_info=True)
            return None

    @staticmethod
    async def _get_google_user_info(client, token: Dict) -> Optional[Dict]:
        """Parse Google user info from token"""
        try:
            # Google returns user info in id_token (OpenID Connect)
            userinfo = token.get('userinfo')
            if not userinfo:
                # Fallback: fetch from userinfo endpoint
                resp = await client.get('userinfo', token=token)
                userinfo = resp.json()

            return {
                "provider": "google",
                "provider_user_id": userinfo.get('sub'),
                "email": userinfo.get('email'),
                "name": userinfo.get('name'),
                "picture": userinfo.get('picture'),
                "email_verified": userinfo.get('email_verified', False)
            }

        except Exception as e:
            logger.error(f"Error parsing Google user info: {e}", exc_info=True)
            return None

    @staticmethod
    async def _get_github_user_info(client, token: Dict) -> Optional[Dict]:
        """Fetch GitHub user info"""
        try:
            # Get user profile
            resp = await client.get('user', token=token)
            user_data = resp.json()

            # Get primary email
            email_resp = await client.get('user/emails', token=token)
            emails = email_resp.json()
            primary_email = next((e for e in emails if e.get('primary')), {})

            return {
                "provider": "github",
                "provider_user_id": str(user_data.get('id')),
                "email": primary_email.get('email') or user_data.get('email'),
                "name": user_data.get('name') or user_data.get('login'),
                "picture": user_data.get('avatar_url'),
                "email_verified": primary_email.get('verified', False)
            }

        except Exception as e:
            logger.error(f"Error fetching GitHub user info: {e}", exc_info=True)
            return None

    @staticmethod
    async def _get_facebook_user_info(client, token: Dict) -> Optional[Dict]:
        """Fetch Facebook user info"""
        try:
            # Get user profile with fields
            resp = await client.get(
                'me',
                params={'fields': 'id,name,email,picture'},
                token=token
            )
            user_data = resp.json()

            return {
                "provider": "facebook",
                "provider_user_id": user_data.get('id'),
                "email": user_data.get('email'),
                "name": user_data.get('name'),
                "picture": user_data.get('picture', {}).get('data', {}).get('url'),
                "email_verified": True  # Facebook verifies emails
            }

        except Exception as e:
            logger.error(f"Error fetching Facebook user info: {e}", exc_info=True)
            return None

    @staticmethod
    async def create_or_get_oauth_user(oauth_info: Dict, client_ip: str = None) -> Optional[Dict]:
        """
        Create new user or get existing user from OAuth info

        Args:
            oauth_info: Dict with provider, provider_user_id, email, name, etc.
            client_ip: Client IP address for location tracking (optional)

        Returns:
            User dict with access_token, or None on error
        """
        try:
            provider = oauth_info['provider']
            provider_user_id = oauth_info['provider_user_id']
            email = oauth_info.get('email')
            name = oauth_info.get('name')

            # Check if user exists with this OAuth account
            existing_user = await db_service.get_user_by_oauth(provider, provider_user_id)

            if existing_user:
                # User exists - generate JWT token based on role
                user_role = existing_user.get('role', 'citizen')
                logger.info(f"OAuth login: {existing_user['username']} via {provider} (role: {user_role})")
                
                # Generate admin token for admin users
                if user_role == 'admin':
                    access_token = create_admin_token({
                        "sub": existing_user['username'],
                        "role": user_role,
                        "username": existing_user['username']
                    })
                else:
                    access_token = create_access_token(data={"sub": existing_user['username']})

                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "username": existing_user['username'],
                        "email": existing_user.get('email'),
                        "role": user_role
                    }
                }

            # Check if email already exists (account linking)
            if email:
                email_user = await db_service.get_user_by_email(email)
                if email_user:
                    # Link OAuth to existing email account
                    await db_service.update_user(email, {
                        'oauth_provider': provider,
                        'oauth_id': provider_user_id,
                        'email_verified': oauth_info.get('email_verified', False)
                    })

                    logger.info(f"OAuth linked to existing account: {email_user['username']} via {provider}")
                    
                    # Generate admin token for admin users
                    user_role = email_user.get('role', 'citizen')
                    if user_role == 'admin':
                        access_token = create_admin_token({
                            "sub": email_user['username'],
                            "role": user_role,
                            "username": email_user['username']
                        })
                    else:
                        access_token = create_access_token(data={"sub": email_user['username']})

                    return {
                        "access_token": access_token,
                        "token_type": "bearer",
                        "user": {
                            "username": email_user['username'],
                            "email": email_user.get('email'),
                            "role": user_role
                        }
                    }

            # Create new user with OAuth
            # Generate username from name (preferred) or email
            import re
            import random
            import string

            base_username = None

            if name and name.strip():
                # Use name: "Sarthak Sidhant" -> "sarthak_sidhant"
                base_username = name.lower().strip()
                base_username = re.sub(r'[^a-z0-9]+', '_', base_username)  # Replace non-alphanumeric with _
                base_username = re.sub(r'_+', '_', base_username)  # Collapse multiple underscores
                base_username = base_username.strip('_')  # Remove leading/trailing underscores

            if not base_username and email:
                # Fallback to email: use part before @ but keep it readable
                # "sarthaksidhantisopolice@gmail.com" -> try to make it shorter
                email_part = email.split('@')[0].lower()

                # Remove common email suffixes like numbers at end
                email_clean = re.sub(r'\d+$', '', email_part)

                # Replace non-alphanumeric with underscores
                email_clean = re.sub(r'[^a-z0-9]+', '_', email_clean)
                email_clean = re.sub(r'_+', '_', email_clean).strip('_')

                # If email is too long (>20 chars), take first 15 chars
                if len(email_clean) > 20:
                    email_clean = email_clean[:15].rstrip('_')

                base_username = email_clean if email_clean else None

            if not base_username:
                # Final fallback: generate random username
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                base_username = f"{provider}_user_{random_suffix}"

            # Ensure username has minimum length (3 chars)
            if len(base_username) < 3:
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                base_username = f"{base_username}_{random_suffix}"

            # Ensure username is unique
            username = base_username
            counter = 1
            while await db_service.get_user_by_username(username):
                username = f"{base_username}_{counter}"
                counter += 1

            # Create user
            user_data = {
                'username': username,
                'email': email,
                'password_hash': None,  # OAuth users don't have passwords
                'oauth_provider': provider,
                'oauth_id': provider_user_id,
                'email_verified': oauth_info.get('email_verified', False),
                'is_active': True,
                'is_verified': oauth_info.get('email_verified', False),
                'role': 'citizen'
            }

            created_username = await db_service.create_user(user_data)

            if not created_username:
                logger.error(f"Failed to create OAuth user for {provider}:{provider_user_id}")
                return None

            logger.info(f"New OAuth user created: {username} via {provider}")

            # Create user metadata with IP geolocation (non-blocking, fire and forget)
            if client_ip:
                try:
                    from app.services.ip_location_service import get_location_from_ip
                    location = await get_location_from_ip(client_ip)
                    if location:
                        await db_service.create_user_metadata(
                            username=username,
                            ip=client_ip,
                            city=location.get('city'),
                            region=location.get('region'),
                            country=location.get('country'),
                            country_code=location.get('country_code'),
                            lat=location.get('lat'),
                            lng=location.get('lng'),
                            isp=location.get('isp'),
                            timezone=location.get('timezone'),
                            vpn_detected=location.get('vpn_detected', False)
                        )
                    else:
                        # Store IP even if geolocation failed
                        await db_service.create_user_metadata(username=username, ip=client_ip)
                except Exception as e:
                    logger.warning(f"Failed to create user metadata: {e}")
                    # Non-critical, continue

            # Generate JWT token
            access_token = create_access_token(data={"sub": username})

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "username": username,
                    "email": email,
                    "role": "citizen"
                },
                "is_new_user": True  # Flag for frontend to know this is a new user
            }

        except Exception as e:
            logger.error(f"Error creating/getting OAuth user: {e}", exc_info=True)
            return None


# Global OAuth service instance
oauth_service = OAuthService()
