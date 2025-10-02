"""Court availability monitoring service."""

import asyncio
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field

from app.models import EnhancedSubscription, CourtAvailability, TennisClub
from app.services.tennis_club_integration import tennis_club_integrations, TennisClubIntegration
from app.services.notification_service import notification_service
from app.services.slot_consolidation_service import slot_consolidation_service
from app.services.deduplication_service import deduplication_service


@dataclass
class AvailabilitySnapshot:
    """Snapshot of court availability at a specific time."""
    club_id: str
    date: date
    courts: List[CourtAvailability]
    timestamp: datetime
    last_refresh_time: Optional[datetime] = None


@dataclass
class MonitoringStats:
    """Statistics for the monitoring service."""
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    notifications_sent: int = 0
    last_check_time: Optional[datetime] = None
    clubs_monitored: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)


class CourtAvailabilityMonitor:
    """Service to monitor court availability and send notifications."""
    
    def __init__(self, check_interval_minutes: int = 10):
        self.check_interval_minutes = check_interval_minutes
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Store previous availability snapshots for change detection
        self.previous_snapshots: Dict[str, AvailabilitySnapshot] = {}
        
        # Statistics
        self.stats = MonitoringStats()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self, subscriptions: List[EnhancedSubscription]):
        """Start the monitoring loop."""
        if self.is_running:
            self.logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting court availability monitoring (every {self.check_interval_minutes} minutes)")
        
        # Start the monitoring task
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(subscriptions)
        )
        
        try:
            await self.monitoring_task
        except asyncio.CancelledError:
            self.logger.info("Monitoring stopped")
        finally:
            self.is_running = False
    
    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping court availability monitoring")
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self, subscriptions: List[EnhancedSubscription]):
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._check_all_subscriptions(subscriptions)
                
                # Wait for the next check interval
                await asyncio.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.stats.errors.append(f"{datetime.now()}: {str(e)}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _check_all_subscriptions(self, subscriptions: List[EnhancedSubscription]):
        """Check availability for all active subscriptions."""
        self.stats.last_check_time = datetime.now()
        self.stats.total_checks += 1
        
        # Get unique clubs from all subscriptions
        clubs_to_check = self._get_clubs_to_monitor(subscriptions)
        
        self.logger.info(f"Checking availability for {len(clubs_to_check)} clubs")
        
        # Check each club
        for club_id in clubs_to_check:
            try:
                await self._check_club_availability(club_id, subscriptions)
                self.stats.successful_checks += 1
                self.stats.clubs_monitored.add(club_id)
            except Exception as e:
                self.logger.error(f"Error checking club {club_id}: {e}")
                self.stats.failed_checks += 1
                self.stats.errors.append(f"{datetime.now()}: Club {club_id}: {str(e)}")
    
    def _get_clubs_to_monitor(self, subscriptions: List[EnhancedSubscription]) -> Set[str]:
        """Get unique club IDs from all active subscriptions."""
        clubs = set()
        for subscription in subscriptions:
            if subscription.status == "active":
                for club_pref in subscription.club_preferences:
                    clubs.add(club_pref.club_id)
        return clubs
    
    async def _check_club_availability(
        self, 
        club_id: str, 
        subscriptions: List[EnhancedSubscription]
    ):
        """Check availability for a specific club."""
        # Get the integration for this club
        integration = await self._get_integration_for_club(club_id)
        if not integration:
            self.logger.warning(f"No integration found for club {club_id}")
            return
        
        # Check if the booking system has been refreshed since last check
        last_refresh = await integration.get_last_refresh_time(club_id)
        previous_snapshot = self.previous_snapshots.get(club_id)
        
        if previous_snapshot and last_refresh:
            # Only check if the booking system has been refreshed
            if last_refresh <= previous_snapshot.last_refresh_time:
                self.logger.debug(f"Club {club_id} booking system not refreshed since last check")
                return
        
        # Get current availability
        today = date.today()
        current_availability = await integration.get_availability(club_id, today)
        
        # Create current snapshot
        current_snapshot = AvailabilitySnapshot(
            club_id=club_id,
            date=today,
            courts=current_availability,
            timestamp=datetime.now(),
            last_refresh_time=last_refresh
        )
        
        # Check for changes
        if previous_snapshot:
            changes = self._detect_availability_changes(previous_snapshot, current_snapshot)
            if changes:
                self.logger.info(f"Availability changes detected for club {club_id}: {len(changes)} changes")
                await self._process_availability_changes(club_id, changes, subscriptions)
            else:
                self.logger.debug(f"No availability changes for club {club_id}")
        else:
            # First time checking this club, no changes to process
            self.logger.info(f"First availability check for club {club_id}")
        
        # Store current snapshot for next comparison
        self.previous_snapshots[club_id] = current_snapshot
    
    async def _get_integration_for_club(self, club_id: str) -> Optional[TennisClubIntegration]:
        """Get the appropriate integration for a club."""
        # For now, use mock integration for all clubs
        # In production, this would determine the integration based on club's booking system
        return tennis_club_integrations.get("mock")
    
    def _detect_availability_changes(
        self, 
        previous: AvailabilitySnapshot, 
        current: AvailabilitySnapshot
    ) -> List[CourtAvailability]:
        """Detect changes in court availability between snapshots."""
        changes = []
        
        # Create maps for easy comparison
        previous_courts = {court.court_id: court for court in previous.courts}
        current_courts = {court.court_id: court for court in current.courts}
        
        # Check for new or changed courts
        for court_id, current_court in current_courts.items():
            previous_court = previous_courts.get(court_id)
            
            if not previous_court:
                # New court available
                changes.append(current_court)
            else:
                # Check for changes in time slots
                if self._court_availability_changed(previous_court, current_court):
                    changes.append(current_court)
        
        return changes
    
    def _court_availability_changed(
        self, 
        previous_court: CourtAvailability, 
        current_court: CourtAvailability
    ) -> bool:
        """Check if a court's availability has changed."""
        # Compare available time slots
        previous_slots = {
            (slot.start_time, slot.end_time, slot.available) 
            for slot in previous_court.time_slots
        }
        current_slots = {
            (slot.start_time, slot.end_time, slot.available) 
            for slot in current_court.time_slots
        }
        
        return previous_slots != current_slots
    
    async def _process_availability_changes(
        self, 
        club_id: str, 
        changes: List[CourtAvailability], 
        subscriptions: List[EnhancedSubscription]
    ):
        """Process availability changes and send notifications."""
        # Find subscriptions that are interested in this club
        relevant_subscriptions = [
            sub for sub in subscriptions 
            if sub.status == "active" and 
            any(club_pref.club_id == club_id for club_pref in sub.club_preferences)
        ]
        
        if not relevant_subscriptions:
            self.logger.debug(f"No active subscriptions for club {club_id}")
            return
        
        # Process each relevant subscription
        for subscription in relevant_subscriptions:
            try:
                # Filter changes to only include courts this subscription cares about
                relevant_changes = self._filter_changes_for_subscription(changes, subscription)
                
                if relevant_changes:
                    # Send notification
                    success = await notification_service.send_availability_alert(
                        subscription, relevant_changes
                    )
                    
                    if success:
                        self.stats.notifications_sent += 1
                        self.logger.info(f"Notification sent to {subscription.email} for club {club_id}")
                    else:
                        self.logger.error(f"Failed to send notification to {subscription.email}")
                
            except Exception as e:
                self.logger.error(f"Error processing subscription {subscription.id}: {e}")
    
    def _filter_changes_for_subscription(
        self, 
        changes: List[CourtAvailability], 
        subscription: EnhancedSubscription
    ) -> List[CourtAvailability]:
        """Filter availability changes to only include courts relevant to the subscription."""
        relevant_changes = []
        
        for change in changes:
            # Check if this court is in the subscription's preferences
            for club_pref in subscription.club_preferences:
                if change.court_id in club_pref.court_ids:
                    relevant_changes.append(change)
                    break
        
        return relevant_changes
    
    def get_stats(self) -> MonitoringStats:
        """Get monitoring statistics."""
        return self.stats
    
    def get_previous_snapshots(self) -> Dict[str, AvailabilitySnapshot]:
        """Get previous availability snapshots (for debugging)."""
        return self.previous_snapshots


# Global monitoring service instance
monitoring_service = CourtAvailabilityMonitor(check_interval_minutes=10)
