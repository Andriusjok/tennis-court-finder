"""Tennis club integration interface and implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.models import TennisClub, CourtAvailability


class TennisClubIntegration(ABC):
    """Abstract base class for tennis club integrations."""
    
    @abstractmethod
    async def get_club_info(self, club_id: str) -> Optional[TennisClub]:
        """Get tennis club information."""
        pass
    
    @abstractmethod
    async def get_availability(
        self, 
        club_id: str, 
        target_date: date
    ) -> List[CourtAvailability]:
        """Get court availability for a specific club and date."""
        pass
    
    @abstractmethod
    async def get_last_refresh_time(self, club_id: str) -> Optional[datetime]:
        """Get the last time the booking system was refreshed."""
        pass
    
    @abstractmethod
    def get_booking_system_type(self) -> str:
        """Get the type of booking system (e.g., 'courtreserve', 'clubautomation')."""
        pass


class MockTennisClubIntegration(TennisClubIntegration):
    """Mock implementation for development and testing."""
    
    def __init__(self):
        # Simulate last refresh times for different clubs
        self._last_refresh_times = {
            "club_123": datetime.now(),
            "club_456": datetime.now(),
            "club_789": datetime.now()
        }
        # Simulate refresh frequency (some clubs refresh more often)
        self._refresh_frequencies = {
            "club_123": 5,  # Every 5 minutes
            "club_456": 15, # Every 15 minutes
            "club_789": 10  # Every 10 minutes
        }
    
    async def get_club_info(self, club_id: str) -> Optional[TennisClub]:
        """Get tennis club information from mock data."""
        from app.mock_data import get_mock_clubs
        
        clubs = get_mock_clubs()
        return next((club for club in clubs if club.id == club_id), None)
    
    async def get_availability(
        self, 
        club_id: str, 
        target_date: date
    ) -> List[CourtAvailability]:
        """Get court availability from mock data."""
        from app.mock_data import get_mock_availability
        
        availability_data = get_mock_availability(club_id, target_date)
        return availability_data.get("courts", [])
    
    async def get_last_refresh_time(self, club_id: str) -> Optional[datetime]:
        """Get the last time the booking system was refreshed."""
        return self._last_refresh_times.get(club_id)
    
    def get_booking_system_type(self) -> str:
        """Get the type of booking system."""
        return "mock"
    
    def simulate_refresh(self, club_id: str):
        """Simulate a booking system refresh (for testing)."""
        if club_id in self._last_refresh_times:
            self._last_refresh_times[club_id] = datetime.now()
    
    def get_refresh_frequency_minutes(self, club_id: str) -> int:
        """Get how often this club's booking system refreshes (in minutes)."""
        return self._refresh_frequencies.get(club_id, 10)


class CourtReserveIntegration(TennisClubIntegration):
    """Integration with CourtReserve booking system."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.courtreserve.com"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def get_club_info(self, club_id: str) -> Optional[TennisClub]:
        """Get tennis club information from CourtReserve API."""
        # TODO: Implement actual CourtReserve API integration
        # This would make HTTP requests to CourtReserve API
        pass
    
    async def get_availability(
        self, 
        club_id: str, 
        target_date: date
    ) -> List[CourtAvailability]:
        """Get court availability from CourtReserve API."""
        # TODO: Implement actual CourtReserve API integration
        # This would make HTTP requests to get availability
        pass
    
    async def get_last_refresh_time(self, club_id: str) -> Optional[datetime]:
        """Get the last time CourtReserve was refreshed."""
        # TODO: Implement actual CourtReserve API integration
        # This would check CourtReserve's last update timestamp
        pass
    
    def get_booking_system_type(self) -> str:
        """Get the type of booking system."""
        return "courtreserve"


class ClubAutomationIntegration(TennisClubIntegration):
    """Integration with ClubAutomation booking system."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.clubautomation.com"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def get_club_info(self, club_id: str) -> Optional[TennisClub]:
        """Get tennis club information from ClubAutomation API."""
        # TODO: Implement actual ClubAutomation API integration
        pass
    
    async def get_availability(
        self, 
        club_id: str, 
        target_date: date
    ) -> List[CourtAvailability]:
        """Get court availability from ClubAutomation API."""
        # TODO: Implement actual ClubAutomation API integration
        pass
    
    async def get_last_refresh_time(self, club_id: str) -> Optional[datetime]:
        """Get the last time ClubAutomation was refreshed."""
        # TODO: Implement actual ClubAutomation API integration
        pass
    
    def get_booking_system_type(self) -> str:
        """Get the type of booking system."""
        return "clubautomation"


class TennisClubIntegrationFactory:
    """Factory for creating tennis club integrations."""
    
    @staticmethod
    def create_integration(booking_system: str, **kwargs) -> TennisClubIntegration:
        """Create a tennis club integration based on booking system type."""
        if booking_system == "mock":
            return MockTennisClubIntegration()
        elif booking_system == "courtreserve":
            return CourtReserveIntegration(
                api_key=kwargs.get("api_key", ""),
                base_url=kwargs.get("base_url", "https://api.courtreserve.com")
            )
        elif booking_system == "clubautomation":
            return ClubAutomationIntegration(
                api_key=kwargs.get("api_key", ""),
                base_url=kwargs.get("base_url", "https://api.clubautomation.com")
            )
        else:
            raise ValueError(f"Unsupported booking system: {booking_system}")


# Global integration registry
tennis_club_integrations: Dict[str, TennisClubIntegration] = {
    "mock": MockTennisClubIntegration(),
    "courtreserve": CourtReserveIntegration(api_key=""),  # Will be configured via environment
    "clubautomation": ClubAutomationIntegration(api_key="")  # Will be configured via environment
}
