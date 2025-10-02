"""Notification service interface and implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
from app.models import EnhancedSubscription, CourtAvailability
from app.services.deduplication_service import deduplication_service
from app.services.slot_consolidation_service import slot_consolidation_service


class NotificationService(ABC):
    """Abstract base class for notification services."""
    
    @abstractmethod
    async def send_subscription_confirmation(self, subscription: EnhancedSubscription) -> bool:
        """Send confirmation email when subscription is created."""
        pass
    
    @abstractmethod
    async def send_availability_alert(
        self, 
        subscription: EnhancedSubscription, 
        available_courts: List[CourtAvailability]
    ) -> bool:
        """Send alert when courts become available."""
        pass
    
    @abstractmethod
    async def send_subscription_cancelled(self, subscription: EnhancedSubscription) -> bool:
        """Send confirmation when subscription is cancelled."""
        pass


class EmailNotificationService(NotificationService):
    """Email implementation of the notification service."""
    
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 587, 
                 smtp_username: str = None, smtp_password: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
    
    async def send_subscription_confirmation(self, subscription: EnhancedSubscription) -> bool:
        """Send confirmation email when subscription is created."""
        try:
            # In a real implementation, you would use an email library like aiosmtplib
            # For now, we'll just log the email content
            
            subject = "🎾 Tennis Court Alert Confirmation"
            
            # Build email content
            clubs_text = []
            for club_pref in subscription.club_preferences:
                clubs_text.append(f"• Club: {club_pref.club_id} (Courts: {', '.join(club_pref.court_ids)})")
            
            times_text = []
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for time_pref in subscription.preferred_times:
                times_text.append(f"• {day_names[time_pref.day_of_week]}: {time_pref.start_time} - {time_pref.end_time}")
            
            body = f"""
Hello!

Your tennis court alert has been successfully created! 🎾

Alert ID: {subscription.id}
Email: {subscription.email}

Club Preferences:
{chr(10).join(clubs_text)}

Preferred Times:
{chr(10).join(times_text)}

Alert Settings:
• Minimum slot duration: {subscription.alert_preferences.minimum_slot_duration_minutes} minutes
• Expiry date: {subscription.alert_preferences.expiry_date or '1 year from now'}
• Max notifications per day: {subscription.alert_preferences.max_notifications_per_day}

We'll start monitoring court availability and send you alerts when your preferred times become available.

Happy playing! 🏆

Best regards,
Tennis Court Finder Team
            """.strip()
            
            print(f"📧 EMAIL SENT TO: {subscription.email}")
            print(f"📧 SUBJECT: {subject}")
            print(f"📧 BODY:\n{body}")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to send confirmation email: {e}")
            return False
    
    async def send_availability_alert(
        self, 
        subscription: EnhancedSubscription, 
        available_courts: List[CourtAvailability]
    ) -> bool:
        """Send alert when courts become available (with deduplication and slot consolidation)."""
        try:
            # Step 1: Consolidate overlapping time slots
            consolidated_courts = slot_consolidation_service.consolidate_court_availability(available_courts)
            
            # Step 2: Filter by minimum duration requirement
            min_duration = subscription.alert_preferences.minimum_slot_duration_minutes
            filtered_courts = slot_consolidation_service.filter_by_minimum_duration(
                consolidated_courts, min_duration
            )
            
            # Step 3: Filter out time slots that have already been notified
            new_availability = deduplication_service.filter_new_availability(
                subscription, filtered_courts
            )
            
            # If no new availability, don't send notification
            if not new_availability:
                print(f"📭 No new availability for subscription {subscription.id} - skipping notification")
                return True
            
            subject = "🚨 Tennis Courts Available Now!"
            
            # Build availability details with enhanced slot information
            availability_text = []
            for court in new_availability:
                slots_text = []
                for slot in court.time_slots:
                    if slot.available:
                        duration_minutes = (slot.end_time - slot.start_time).total_seconds() / 60
                        duration_text = f"{duration_minutes:.0f}min" if duration_minutes < 60 else f"{duration_minutes/60:.1f}h"
                        
                        # Highlight if it's longer than minimum requirement
                        min_duration = subscription.alert_preferences.minimum_slot_duration_minutes
                        highlight = " ⭐" if duration_minutes > min_duration else ""
                        
                        slots_text.append(f"  - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration_text}) - ${slot.price}{highlight}")
                
                if slots_text:
                    availability_text.append(f"🏟️ {court.court_name}:")
                    availability_text.extend(slots_text)
            
            body = f"""
Great news! Tennis courts matching your preferences are now available! 🎾

Alert ID: {subscription.id}

Available Courts:
{chr(10).join(availability_text)}

Book quickly - these slots may not last long!

To manage your alerts, visit: https://tenniscourtfinder.com/subscriptions/{subscription.id}

Happy playing! 🏆

Best regards,
Tennis Court Finder Team
            """.strip()
            
            print(f"🚨 ALERT EMAIL SENT TO: {subscription.email}")
            print(f"🚨 SUBJECT: {subject}")
            print(f"🚨 BODY:\n{body}")
            print("=" * 50)
            
            # Record that these notifications were sent
            deduplication_service.record_notifications_sent(subscription, new_availability)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to send availability alert: {e}")
            return False
    
    async def send_subscription_cancelled(self, subscription: EnhancedSubscription) -> bool:
        """Send confirmation when subscription is cancelled."""
        try:
            subject = "Tennis Court Alert Cancelled"
            
            body = f"""
Your tennis court alert has been cancelled.

Alert ID: {subscription.id}
Email: {subscription.email}
Cancelled: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

You will no longer receive notifications for this alert.

If you'd like to create a new alert, visit: https://tenniscourtfinder.com

Best regards,
Tennis Court Finder Team
            """.strip()
            
            print(f"📧 CANCELLATION EMAIL SENT TO: {subscription.email}")
            print(f"📧 SUBJECT: {subject}")
            print(f"📧 BODY:\n{body}")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to send cancellation email: {e}")
            return False


# Global notification service instance
notification_service: NotificationService = EmailNotificationService()
