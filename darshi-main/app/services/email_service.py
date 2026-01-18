"""
Email Service - Resend integration for transactional emails

Handles:
- Email verification
- Password reset
- Notifications
"""

import resend
import logging
from typing import Optional
from app.core.config import settings
from app.core.exceptions import EmailError

logger = logging.getLogger(__name__)

# Initialize Resend
if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY
    logger.info("Resend email service initialized")
else:
    logger.warning("RESEND_API_KEY not configured - email service disabled")


class EmailService:
    """Email service using Resend API"""

    def __init__(self):
        self.enabled = bool(settings.EMAIL_ENABLED and settings.RESEND_API_KEY)
        self.from_email = settings.EMAIL_FROM
        self.frontend_url = settings.FRONTEND_URL

        if not self.enabled:
            logger.warning("Email service disabled. Set EMAIL_ENABLED=true and RESEND_API_KEY in .env")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email via Resend API

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body
            text_content: Plain text fallback (optional)

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            logger.warning(f"Email service disabled, skipping email to {to_email}")
            return False

        try:
            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                params["text"] = text_content

            response = resend.Emails.send(params)

            logger.info(f"Email sent successfully to {to_email} (ID: {response['id']})")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False

    async def send_verification_email(self, to_email: str, token: str, username: str) -> bool:
        """Send email verification link"""
        verification_url = f"{self.frontend_url}/verify-email?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to Darshi!</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Hi {username},</h2>
                <p>Thank you for registering with Darshi. Please verify your email address to activate your account.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
                    {verification_url}
                </p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 24 hours. If you didn't create an account, please ignore this email.
                </p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>Darshi - Civic Grievance Platform</p>
                <p>© 2024 Darshi. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Welcome to Darshi!

        Hi {username},

        Thank you for registering with Darshi. Please verify your email address to activate your account.

        Verification link: {verification_url}

        This link will expire in 24 hours. If you didn't create an account, please ignore this email.

        Darshi - Civic Grievance Platform
        © 2024 Darshi. All rights reserved.
        """

        return await self.send_email(
            to_email=to_email,
            subject="Verify your Darshi account",
            html_content=html_content,
            text_content=text_content
        )

    async def send_password_reset_email(self, to_email: str, token: str, username: str) -> bool:
        """Send password reset link"""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Reset Your Password</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Hi {username},</h2>
                <p>We received a request to reset your password. Click the button below to choose a new password.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
                    {reset_url}
                </p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 1 hour. If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                </p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>Darshi - Civic Grievance Platform</p>
                <p>© 2024 Darshi. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Reset Your Password

        Hi {username},

        We received a request to reset your password. Click the link below to choose a new password.

        Reset link: {reset_url}

        This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.

        Darshi - Civic Grievance Platform
        © 2024 Darshi. All rights reserved.
        """

        return await self.send_email(
            to_email=to_email,
            subject="Reset your Darshi password",
            html_content=html_content,
            text_content=text_content
        )

    async def send_magic_link_email(self, to_email: str, magic_link: str) -> bool:
        """Send magic link (passwordless login) email"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Sign in to Darshi</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Your login link is ready!</h2>
                <p>Click the button below to sign in to your Darshi account. No password needed!</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{magic_link}"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Sign In to Darshi
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
                    {magic_link}
                </p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 15 minutes and can only be used once. If you didn't request this link, please ignore this email.
                </p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>Darshi - Civic Grievance Platform</p>
                <p>© 2025 Darshi. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Sign in to Darshi

        Your login link is ready! Click the link below to sign in to your Darshi account. No password needed!

        Sign in link: {magic_link}

        This link will expire in 15 minutes and can only be used once. If you didn't request this link, please ignore this email.

        Darshi - Civic Grievance Platform
        © 2025 Darshi. All rights reserved.
        """

        return await self.send_email(
            to_email=to_email,
            subject="Sign in to Darshi - Magic Link",
            html_content=html_content,
            text_content=text_content
        )

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        username: str
    ) -> bool:
        """Send general notification email"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">{subject}</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #667eea;">Hi {username},</h2>
                <p>{message}</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        View on Darshi
                    </a>
                </div>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>Darshi - Civic Grievance Platform</p>
                <p>© 2024 Darshi. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {subject}

        Hi {username},

        {message}

        View on Darshi: {self.frontend_url}

        Darshi - Civic Grievance Platform
        © 2024 Darshi. All rights reserved.
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Global email service instance
email_service = EmailService()
