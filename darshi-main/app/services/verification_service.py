import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.core.logging_config import get_logger
from app.services import postgres_service as db_service, email_service

logger = get_logger(__name__)

class VerificationService:
    """
    Service for handling email verification tokens
    """

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for email verification"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def send_email_verification(email: str) -> Tuple[bool, str]:
        """
        Generate and send email verification token
        Returns: (success, token)
        """
        try:
            from app.core.config import settings

            # Check if email is enabled
            if not settings.EMAIL_ENABLED:
                logger.warning(f"Email service disabled - cannot send verification to {email}")
                return False, ""

            token = VerificationService.generate_token()
            expires = datetime.utcnow() + timedelta(hours=24)

            # Store token in database
            await db_service.update_user_verification_token(
                email=email,
                token_type='email',
                token=token,
                expires=expires
            )

            # Send email
            success = email_service.email_service.send_verification_email(email, token)

            if success:
                logger.info(f"Email verification sent to {email}")
                return True, token
            else:
                logger.error(f"Failed to send verification email to {email}")
                return False, ""

        except Exception as e:
            logger.error(f"Error sending email verification: {e}", exc_info=True)
            return False, ""

    @staticmethod
    async def verify_email_token(token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify email token and mark email as verified
        Returns: (success, email)
        """
        try:
            user = await db_service.get_user_by_verification_token(token, 'email')

            if not user:
                logger.warning("Invalid or expired email verification token")
                return False, None

            # Mark email as verified
            await db_service.mark_email_verified(user['email'])
            logger.info(f"Email verified for {user['email']}")

            return True, user['email']

        except Exception as e:
            logger.error(f"Error verifying email token: {e}", exc_info=True)
            return False, None

    @staticmethod
    async def send_password_reset(email: str) -> Tuple[bool, str]:
        """
        Generate and send password reset token
        Returns: (success, token)
        """
        try:
            # Check if user exists
            user = await db_service.get_user_by_email(email)
            if not user:
                # Don't reveal if email exists
                logger.warning(f"Password reset requested for non-existent email: {email}")
                return True, ""  # Return success to prevent email enumeration

            # Don't send reset for OAuth users (they don't have passwords)
            if user.get('oauth_provider'):
                logger.warning(f"Password reset requested for OAuth user: {email}")
                return True, ""

            token = VerificationService.generate_token()
            expires = datetime.utcnow() + timedelta(hours=1)

            # Store token in database
            await db_service.update_user_verification_token(
                email=email,
                token_type='password_reset',
                token=token,
                expires=expires
            )

            # Send email
            success = email_service.email_service.send_password_reset_email(email, token)

            if success:
                logger.info(f"Password reset email sent to {email}")
                return True, token
            else:
                logger.error(f"Failed to send password reset email to {email}")
                return False, ""

        except Exception as e:
            logger.error(f"Error sending password reset: {e}", exc_info=True)
            return False, ""

    @staticmethod
    async def reset_password(token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset password using token
        Returns: (success, email)
        """
        try:
            from app.services import auth_service

            user = await db_service.get_user_by_verification_token(token, 'password_reset')

            if not user:
                logger.warning("Invalid or expired password reset token")
                return False, None

            # Hash new password
            hashed_password = auth_service.get_password_hash(new_password)

            # Update password
            await db_service.update_user_password(user['email'], hashed_password)

            # Clear reset token
            await db_service.clear_verification_token(user['email'], 'password_reset')

            logger.info(f"Password reset successful for {user['email']}")
            return True, user['email']

        except Exception as e:
            logger.error(f"Error resetting password: {e}", exc_info=True)
            return False, None


# Singleton instance
verification_service = VerificationService()
