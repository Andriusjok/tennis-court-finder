"""Mock data for the Tennis Court Finder API."""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from app.models import (
    TennisClub, Court, Location, Coordinates, CourtAvailability, 
    TimeSlot, Subscription, PreferredTime
)


def get_mock_clubs() -> List[TennisClub]:
    """Generate mock tennis clubs data."""
    return [
        TennisClub(
            id="club_123",
            name="Central Tennis Club",
            location=Location(
                address="123 Tennis Street, City, State 12345",
                coordinates=Coordinates(lat=40.7128, lng=-74.0060)
            ),
            booking_system="courtreserve",
            courts=[
                Court(id="court_1", name="Court 1", surface="hard", indoor=False),
                Court(id="court_2", name="Court 2", surface="clay", indoor=False),
                Court(id="court_3", name="Court 3", surface="hard", indoor=True),
            ]
        ),
        TennisClub(
            id="club_456",
            name="Riverside Tennis Center",
            location=Location(
                address="456 River Road, Riverside, CA 90210",
                coordinates=Coordinates(lat=34.0522, lng=-118.2437)
            ),
            booking_system="clubautomation",
            courts=[
                Court(id="court_4", name="Court A", surface="grass", indoor=False),
                Court(id="court_5", name="Court B", surface="hard", indoor=True),
            ]
        ),
        TennisClub(
            id="club_789",
            name="Mountain View Tennis",
            location=Location(
                address="789 Mountain Ave, Mountain View, CA 94041",
                coordinates=Coordinates(lat=37.3861, lng=-122.0839)
            ),
            booking_system="tennisbookings",
            courts=[
                Court(id="court_6", name="Center Court", surface="hard", indoor=False),
                Court(id="court_7", name="Side Court", surface="clay", indoor=False),
                Court(id="court_8", name="Indoor Court", surface="hard", indoor=True),
            ]
        )
    ]


def get_mock_availability(club_id: str, target_date: date = None) -> Dict[str, Any]:
    """Generate mock court availability data."""
    if target_date is None:
        target_date = date.today()
    
    # Different availability patterns for different clubs
    availability_data = {
        "club_123": {
            "courts": [
                CourtAvailability(
                    court_id="court_1",
                    court_name="Court 1",
                    time_slots=[
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=9)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=10)),
                            available=True,
                            price=25.00,
                            currency="USD"
                        ),
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=10)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=11)),
                            available=False,
                            price=25.00,
                            currency="USD"
                        ),
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=11)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=12)),
                            available=True,
                            price=30.00,
                            currency="USD"
                        ),
                    ]
                ),
                CourtAvailability(
                    court_id="court_2",
                    court_name="Court 2",
                    time_slots=[
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=14)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=15)),
                            available=True,
                            price=20.00,
                            currency="USD"
                        ),
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=15)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=16)),
                            available=True,
                            price=20.00,
                            currency="USD"
                        ),
                    ]
                )
            ]
        },
        "club_456": {
            "courts": [
                CourtAvailability(
                    court_id="court_4",
                    court_name="Court A",
                    time_slots=[
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=8)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=9)),
                            available=True,
                            price=35.00,
                            currency="USD"
                        ),
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=16)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=17)),
                            available=True,
                            price=40.00,
                            currency="USD"
                        ),
                    ]
                )
            ]
        },
        "club_789": {
            "courts": [
                CourtAvailability(
                    court_id="court_6",
                    court_name="Center Court",
                    time_slots=[
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=10)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=11)),
                            available=True,
                            price=45.00,
                            currency="USD"
                        ),
                        TimeSlot(
                            start_time=datetime.combine(target_date, datetime.min.time().replace(hour=11)),
                            end_time=datetime.combine(target_date, datetime.min.time().replace(hour=12)),
                            available=True,
                            price=45.00,
                            currency="USD"
                        ),
                    ]
                )
            ]
        }
    }
    
    return availability_data.get(club_id, {"courts": []})


def get_mock_subscriptions() -> List[Subscription]:
    """Generate mock subscription data."""
    return [
        Subscription(
            id="sub_456",
            email="user@example.com",
            club_id="club_123",
            preferred_times=[
                PreferredTime(day_of_week=1, start_time="10:00", end_time="12:00"),
                PreferredTime(day_of_week=3, start_time="14:00", end_time="16:00"),
            ],
            status="active",
            created_at=datetime.now() - timedelta(days=5),
            last_notification=datetime.now() - timedelta(hours=2)
        ),
        Subscription(
            id="sub_789",
            email="player@example.com",
            club_id="club_456",
            preferred_times=[
                PreferredTime(day_of_week=0, start_time="08:00", end_time="10:00"),
                PreferredTime(day_of_week=5, start_time="16:00", end_time="18:00"),
            ],
            status="active",
            created_at=datetime.now() - timedelta(days=10),
            last_notification=None
        )
    ]


def get_mock_subscription_by_id(subscription_id: str) -> Subscription:
    """Get a specific mock subscription by ID."""
    subscriptions = get_mock_subscriptions()
    for sub in subscriptions:
        if sub.id == subscription_id:
            return sub
    return None
