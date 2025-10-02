"""Notification deduplication service to prevent duplicate alerts."""

from typing import List, Set, Dict, Any
from datetime import datetime, timedelta
from app.models import (
    SentNotification, NotificationDeduplicationKey, 
    EnhancedSubscription, CourtAvailability, TimeSlot
)


class NotificationDeduplicationService:
    """Service to track and prevent duplicate notifications."""
    
    def __init__(self):
        # In-memory storage for sent notifications
        # In production, this would be a database table
        self.sent_notifications: List[SentNotification] = []
        
        # Cache for quick lookups
        self._deduplication_keys: Set[str] = set()
    
    def _generate_deduplication_key(self, key: NotificationDeduplicationKey) -> str:
        """Generate a unique string key for deduplication."""
        # Create a unique identifier for this notification
        return f"{key.subscription_id}:{key.club_id}:{key.court_id}:{key.slot_start_time.isoformat()}:{key.slot_end_time.isoformat()}"
    
    def _is_notification_sent(self, key: NotificationDeduplicationKey) -> bool:
        """Check if a notification for this time slot has already been sent."""
        dedup_key = self._generate_deduplication_key(key)
        return dedup_key in self._deduplication_keys
    
    def _record_notification_sent(self, notification: SentNotification) -> None:
        """Record that a notification was sent."""
        self.sent_notifications.append(notification)
        
        # Create deduplication key
        key = NotificationDeduplicationKey(
            subscription_id=notification.subscription_id,
            club_id=notification.club_id,
            court_id=notification.court_id,
            slot_start_time=notification.slot_start_time,
            slot_end_time=notification.slot_end_time
        )
        
        dedup_key = self._generate_deduplication_key(key)
        self._deduplication_keys.add(dedup_key)
    
    def filter_new_availability(
        self, 
        subscription: EnhancedSubscription, 
        available_courts: List[CourtAvailability]
    ) -> List[CourtAvailability]:
        """
        Filter out time slots that have already been notified to this subscription.
        Returns only new availability that hasn't been sent before.
        """
        filtered_courts = []
        
        for court in available_courts:
            # Check if this court is in the subscription's preferences
            court_is_preferred = False
            for club_pref in subscription.club_preferences:
                if court.court_id in club_pref.court_ids:
                    court_is_preferred = True
                    break
            
            if not court_is_preferred:
                continue
            
            # Filter time slots that haven't been notified
            new_time_slots = []
            for slot in court.time_slots:
                if not slot.available:
                    continue
                
                # Find the club ID for this court
                club_id = None
                for club_pref in subscription.club_preferences:
                    if court.court_id in club_pref.court_ids:
                        club_id = club_pref.club_id
                        break
                
                if not club_id:
                    continue
                
                # Create deduplication key
                key = NotificationDeduplicationKey(
                    subscription_id=subscription.id,
                    club_id=club_id,
                    court_id=court.court_id,
                    slot_start_time=slot.start_time,
                    slot_end_time=slot.end_time
                )
                
                # Only include if not already sent
                if not self._is_notification_sent(key):
                    new_time_slots.append(slot)
            
            # Only include court if it has new available slots
            if new_time_slots:
                filtered_court = CourtAvailability(
                    court_id=court.court_id,
                    court_name=court.court_name,
                    time_slots=new_time_slots
                )
                filtered_courts.append(filtered_court)
        
        return filtered_courts
    
    def record_notifications_sent(
        self, 
        subscription: EnhancedSubscription, 
        sent_courts: List[CourtAvailability]
    ) -> None:
        """Record that notifications were sent for these time slots."""
        for court in sent_courts:
            # Find the club ID for this court
            club_id = None
            for club_pref in subscription.club_preferences:
                if court.court_id in club_pref.court_ids:
                    club_id = club_pref.club_id
                    break
            
            if not club_id:
                continue
                
            for slot in court.time_slots:
                if slot.available:
                    notification = SentNotification(
                        id=f"notif_{len(self.sent_notifications) + 1}",
                        subscription_id=subscription.id,
                        club_id=club_id,
                        court_id=court.court_id,
                        slot_start_time=slot.start_time,
                        slot_end_time=slot.end_time,
                        sent_at=datetime.now(),
                        notification_type="availability_alert"
                    )
                    self._record_notification_sent(notification)
    
    def cleanup_old_notifications(self, days_to_keep: int = 30) -> None:
        """Remove old notification records to prevent memory bloat."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Remove old notifications
        self.sent_notifications = [
            notif for notif in self.sent_notifications 
            if notif.sent_at > cutoff_date
        ]
        
        # Rebuild deduplication keys cache
        self._deduplication_keys.clear()
        for notif in self.sent_notifications:
            key = NotificationDeduplicationKey(
                subscription_id=notif.subscription_id,
                club_id=notif.club_id,
                court_id=notif.court_id,
                slot_start_time=notif.slot_start_time,
                slot_end_time=notif.slot_end_time
            )
            dedup_key = self._generate_deduplication_key(key)
            self._deduplication_keys.add(dedup_key)
    
    def get_notification_history(self, subscription_id: str) -> List[SentNotification]:
        """Get notification history for a specific subscription."""
        return [
            notif for notif in self.sent_notifications 
            if notif.subscription_id == subscription_id
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication service statistics."""
        return {
            "total_notifications_sent": len(self.sent_notifications),
            "unique_deduplication_keys": len(self._deduplication_keys),
            "oldest_notification": min(
                (notif.sent_at for notif in self.sent_notifications), 
                default=None
            ),
            "newest_notification": max(
                (notif.sent_at for notif in self.sent_notifications), 
                default=None
            )
        }


# Global deduplication service instance
deduplication_service = NotificationDeduplicationService()
