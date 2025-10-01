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


class Subscription(BaseModel):
    """Subscription information."""
    id: str = Field(..., description="Unique subscription identifier")
    email: EmailStr = Field(..., description="User email address")
    club_id: str = Field(..., description="Tennis club identifier")
    preferred_times: List[PreferredTime] = Field(..., description="Preferred time slots")
    status: str = Field(..., description="Subscription status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_notification: Optional[datetime] = Field(None, description="Last notification timestamp")


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
