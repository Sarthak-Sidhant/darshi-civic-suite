from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict

class UserBase(BaseModel):
    model_config = ConfigDict(extra='ignore')

    username: str  # Unique username (required)
    email: Optional[EmailStr] = Field(None)  # Email optional for OAuth users
    role: str = Field("citizen")  # citizen, admin
    city: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    country: str = Field("India")
    lat: Optional[float] = Field(None)
    lng: Optional[float] = Field(None)
    location_address: Optional[str] = Field(None)

class UserCreate(UserBase):
    password: Optional[str] = Field(None)  # Optional for OAuth users
    full_name: Optional[str] = Field(None)

class UserInDB(UserBase):
    user_id: str
    hashed_password: Optional[str] = None  # None for OAuth users
    email_verified: bool = False
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # OAuth fields
    oauth_provider: Optional[str] = None  # google, github, facebook
    oauth_id: Optional[str] = None

    # Verification tokens
    email_verification_token: Optional[str] = None
    email_verification_expires: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    magic_link_token: Optional[str] = None
    magic_link_expires: Optional[datetime] = None
    last_login: Optional[datetime] = None

    # User preferences
    notification_enabled: bool = True
    location_tracking_enabled: bool = True
    public_profile: bool = True

class UserResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')

    username: str
    email: Optional[str] = None
    role: str = "citizen"
    full_name: Optional[str] = None
    is_verified: bool = False  # Database field name
    email_verified: bool = False  # Alias for compatibility
    profile_picture: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_address: Optional[str] = None
    oauth_provider: Optional[str] = None
    created_at: Optional[datetime] = None  # Optional to handle missing field
    badges: List[str] = []
    reputation: int = 0

class UserProfileResponse(UserResponse):
    notification_enabled: bool = True
    location_tracking_enabled: bool = True
    public_profile: bool = True

class UserUpdateProfile(BaseModel):
    username: Optional[str] = Field(None, min_length=3)
    full_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_address: Optional[str] = None
    profile_picture: Optional[str] = None

class UserUpdateSettings(BaseModel):
    notification_enabled: Optional[bool] = None
    location_tracking_enabled: Optional[bool] = None
    public_profile: Optional[bool] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerification(BaseModel):
    token: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OAuthToken(BaseModel):
    access_token: str
    token_type: str
    is_new_user: bool
    user_info: Optional[dict] = None  # For new users, contains OAuth profile info

class MagicLinkRequest(BaseModel):
    email: EmailStr
    turnstile_token: Optional[str] = None  # Cloudflare Turnstile verification token

class MagicLinkVerify(BaseModel):
    token: str
