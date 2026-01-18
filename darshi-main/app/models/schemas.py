from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class AIAnalysisResult(BaseModel):
    is_valid: bool
    category: str
    severity: int
    description: str

class ReportResponse(BaseModel):
    report_id: str
    status: str

class AlertBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = "medium" # low, medium, high, critical
    category: str # traffic, power, water, safety, community
    geohash: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: int = 0
    expires_in_hours: Optional[int] = 24 # Helper for creation

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: str
    status: str
    source: str
    author_id: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    resolved_at: Optional[datetime]
    sent_count: Optional[int] = 0
    delivery_count: Optional[int] = 0
    read_count: Optional[int] = 0


class AlertUpdate(BaseModel):
    """Schema for updating an existing alert."""
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    expires_in_hours: Optional[int] = None


class AlertSubscription(BaseModel):
    """User alert subscription preferences."""
    home_geohash: Optional[str] = None
    work_geohash: Optional[str] = None
    custom_geohashes: Optional[List[str]] = None
    subscription_radius_km: float = 5.0
    categories: List[str] = ["traffic", "power", "water", "safety", "community"]
    severity_threshold: str = "low"  # low, medium, high, critical
    enabled: bool = True
    notify_in_app: bool = True
    notify_whatsapp: bool = False
    whatsapp_number: Optional[str] = None
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None


class AlertSubscriptionResponse(AlertSubscription):
    """Response model for alert subscription."""
    user_id: str
    created_at: datetime
    updated_at: datetime


class MunicipalityRole(BaseModel):
    user_id: str
    municipality_id: str
    department: str # mayor, roads, sanitation, electricity, traffic
    is_active: bool

class DashboardStats(BaseModel):
    total_reports: int
    pending_reports: int
    resolved_reports: int
    avg_resolution_time_hours: float
    active_alerts: int
    reports_by_category: dict
    reports_by_status: dict

