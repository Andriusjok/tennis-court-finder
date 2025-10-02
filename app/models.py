"""Pydantic models for the Tennis Court Finder API."""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class Location(BaseModel):
    """Location information."""
    address: str = Field(..., description="Full address")
    coordinates: Optional[Coordinates] = Field(None, description="GPS coordinates")


class Court(BaseModel):
    """Tennis court information."""
    id: str = Field(..., description="Unique court identifier")
    name: str = Field(..., description="Court name")
    surface: str = Field(..., description="Court surface type")
    indoor: bool = Field(..., description="Whether the court is indoor")


class TennisClub(BaseModel):
    """Tennis club information."""
    id: str = Field(..., description="Unique club identifier")
    name: str = Field(..., description="Club name")
    location: Location = Field(..., description="Club location")
    booking_system: str = Field(..., description="Booking system type")
    courts: List[Court] = Field(default_factory=list, description="Available courts")


class TimeSlot(BaseModel):
    """Available time slot."""
    start_time: datetime = Field(..., description="Slot start time")
    end_time: datetime = Field(..., description="Slot end time")
    available: bool = Field(..., description="Whether the slot is available")
    price: Optional[float] = Field(None, description="Price for the slot")
    currency: str = Field(default="USD", description="Currency code")


class CourtAvailability(BaseModel):
    """Court availability information."""
    court_id: str = Field(..., description="Court identifier")
    court_name: str = Field(..., description="Court name")
    time_slots: List[TimeSlot] = Field(..., description="Available time slots")


class PreferredTime(BaseModel):
    """Preferred time slot for notifications."""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    start_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Start time (HH:MM)")
    end_time: str = Field(..., pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="End time (HH:MM)")


class CourtPreference(BaseModel):
    """Court preference for a specific club."""
    club_id: str = Field(..., description="Club identifier")
    court_ids: List[str] = Field(..., description="List of preferred court IDs")


class AlertPreferences(BaseModel):
    """Enhanced alert preferences."""
    minimum_slot_duration_minutes: int = Field(default=60, ge=30, le=480, description="Minimum slot duration in minutes")
    expiry_date: Optional[date] = Field(None, description="Alert expiry date (defaults to 1 year from creation)")
    max_notifications_per_day: int = Field(default=3, ge=1, le=10, description="Maximum notifications per day")
    notification_frequency_hours: int = Field(default=24, ge=1, le=168, description="Hours between availability checks")


class NotificationPreferences(BaseModel):
    """Notification preferences."""
    email_enabled: bool = Field(default=True, description="Enable email notifications")
    sms_enabled: bool = Field(default=False, description="Enable SMS notifications")


class SubscriptionRequest(BaseModel):
    """Request to create a new subscription."""
    email: EmailStr = Field(..., description="User email address")
    club_id: str = Field(..., description="Tennis club identifier")
    preferred_times: List[PreferredTime] = Field(..., description="Preferred time slots")
    notification_preferences: Optional[NotificationPreferences] = Field(
        default_factory=NotificationPreferences, description="Notification preferences"
    )


class EnhancedSubscriptionRequest(BaseModel):
    """Enhanced request to create a new alert subscription."""
    email: EmailStr = Field(..., description="User email address")
    club_preferences: List[CourtPreference] = Field(..., min_items=1, description="Club and court preferences")
    preferred_times: List[PreferredTime] = Field(..., min_items=1, description="Preferred time slots")
    alert_preferences: Optional[AlertPreferences] = Field(
        default_factory=AlertPreferences, description="Alert preferences"
    )
    notification_preferences: Optional[NotificationPreferences] = Field(
        default_factory=NotificationPreferences, description="Notification preferences"
    )


class Subscription(BaseModel):
    """Subscription information."""
    id: str = Field(..., description="Unique subscription identifier")
    email: EmailStr = Field(..., description="User email address")
    club_id: str = Field(..., description="Tennis club identifier")
    preferred_times: List[PreferredTime] = Field(..., description="Preferred time slots")
    status: str = Field(..., description="Subscription status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_notification: Optional[datetime] = Field(None, description="Last notification timestamp")


class EnhancedSubscription(BaseModel):
    """Enhanced subscription information."""
    id: str = Field(..., description="Unique subscription identifier")
    email: EmailStr = Field(..., description="User email address")
    club_preferences: List[CourtPreference] = Field(..., description="Club and court preferences")
    preferred_times: List[PreferredTime] = Field(..., description="Preferred time slots")
    alert_preferences: AlertPreferences = Field(..., description="Alert preferences")
    notification_preferences: NotificationPreferences = Field(..., description="Notification preferences")
    status: str = Field(..., description="Subscription status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_notification: Optional[datetime] = Field(None, description="Last notification timestamp")
    next_check: Optional[datetime] = Field(None, description="Next availability check timestamp")


class Error(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Current timestamp")


class ClubsResponse(BaseModel):
    """Response containing tennis clubs."""
    clubs: List[TennisClub] = Field(..., description="List of tennis clubs")


class AvailabilityResponse(BaseModel):
    """Response containing court availability."""
    club_id: str = Field(..., description="Club identifier")
    availability_date: date = Field(..., description="Date for availability")
    courts: List[CourtAvailability] = Field(..., description="Court availability information")


class SentNotification(BaseModel):
    """Record of a notification that was sent to prevent duplicates."""
    id: str = Field(..., description="Unique notification record ID")
    subscription_id: str = Field(..., description="Subscription that received the notification")
    club_id: str = Field(..., description="Club where the court is located")
    court_id: str = Field(..., description="Court that became available")
    slot_start_time: datetime = Field(..., description="Start time of the available slot")
    slot_end_time: datetime = Field(..., description="End time of the available slot")
    sent_at: datetime = Field(..., description="When the notification was sent")
    notification_type: str = Field(..., description="Type of notification (availability_alert)")


class NotificationDeduplicationKey(BaseModel):
    """Key for deduplication - represents a unique time slot notification."""
    subscription_id: str
    club_id: str
    court_id: str
    slot_start_time: datetime
    slot_end_time: datetime
