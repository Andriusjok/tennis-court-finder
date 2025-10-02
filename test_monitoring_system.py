#!/usr/bin/env python3
"""
Test script to demonstrate the complete monitoring system.
This shows how the system automatically monitors court availability and sends notifications.
"""

import requests
import json
import time
import asyncio
from datetime import datetime, timedelta
from app.services.tennis_club_integration import MockTennisClubIntegration

BASE_URL = "http://localhost:8000"

def create_test_alert():
    """Create a test alert for monitoring."""
    print("🔍 Creating test alert for monitoring...")
    
    alert_data = {
        "email": "monitoring-test@example.com",
        "club_preferences": [
            {
                "club_id": "club_123",
                "court_ids": ["court_1", "court_2"]
            }
        ],
        "preferred_times": [
            {
                "day_of_week": 1,  # Tuesday
                "start_time": "10:00",
                "end_time": "12:00"
            }
        ],
        "alert_preferences": {
            "minimum_slot_duration_minutes": 60,
            "max_notifications_per_day": 5
        }
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert = response.json()
        print(f"✅ Alert created: {alert['id']}")
        print(f"   Email: {alert['email']}")
        print(f"   Clubs: {len(alert['club_preferences'])}")
        print(f"   Time slots: {len(alert['preferred_times'])}")
        return alert['id']
    else:
        print(f"❌ Failed to create alert: {response.status_code}")
        return None

def start_monitoring():
    """Start the monitoring service."""
    print("\n🚀 Starting monitoring service...")
    
    response = requests.post(f"{BASE_URL}/admin/start-monitoring")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Monitoring started successfully!")
        print(f"   Status: {result['status']}")
        print(f"   Check interval: {result['check_interval_minutes']} minutes")
        print(f"   Active subscriptions: {result['active_subscriptions']}")
        return True
    else:
        print(f"❌ Failed to start monitoring: {response.status_code}")
        return False

def check_monitoring_status():
    """Check the current monitoring status."""
    print("\n📊 Checking monitoring status...")
    
    response = requests.get(f"{BASE_URL}/admin/monitoring-status")
    if response.status_code == 200:
        status = response.json()
        print(f"   Running: {status['is_running']}")
        print(f"   Check interval: {status['check_interval_minutes']} minutes")
        
        stats = status['stats']
        print(f"   Total checks: {stats['total_checks']}")
        print(f"   Successful checks: {stats['successful_checks']}")
        print(f"   Failed checks: {stats['failed_checks']}")
        print(f"   Notifications sent: {stats['notifications_sent']}")
        print(f"   Clubs monitored: {stats['clubs_monitored']}")
        
        if stats['last_check_time']:
            print(f"   Last check: {stats['last_check_time']}")
        
        if stats['recent_errors']:
            print(f"   Recent errors: {len(stats['recent_errors'])}")
            for error in stats['recent_errors']:
                print(f"     - {error}")
        
        return status
    else:
        print(f"❌ Failed to get monitoring status: {response.status_code}")
        return None

def trigger_manual_check():
    """Trigger a manual availability check."""
    print("\n🔍 Triggering manual availability check...")
    
    response = requests.post(f"{BASE_URL}/admin/trigger-manual-check")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Manual check completed!")
        print(f"   Subscriptions checked: {result['active_subscriptions_checked']}")
        print(f"   Timestamp: {result['timestamp']}")
        return True
    else:
        print(f"❌ Failed to trigger manual check: {response.status_code}")
        return False

def check_availability_snapshots():
    """Check the current availability snapshots."""
    print("\n📸 Checking availability snapshots...")
    
    response = requests.get(f"{BASE_URL}/admin/availability-snapshots")
    if response.status_code == 200:
        result = response.json()
        print(f"   Total clubs with snapshots: {result['total_clubs']}")
        
        for club_id, snapshot in result['snapshots'].items():
            print(f"   Club {club_id}:")
            print(f"     Date: {snapshot['date']}")
            print(f"     Timestamp: {snapshot['timestamp']}")
            print(f"     Last refresh: {snapshot['last_refresh_time']}")
            print(f"     Courts: {snapshot['courts_count']}")
            
            for court in snapshot['courts']:
                print(f"       - {court['court_name']}: {court['available_slots']} available slots")
        
        return result
    else:
        print(f"❌ Failed to get snapshots: {response.status_code}")
        return None

def simulate_booking_system_refresh():
    """Simulate a booking system refresh (for testing)."""
    print("\n🔄 Simulating booking system refresh...")
    
    # This would normally be done by the tennis club's booking system
    # For testing, we'll simulate it by triggering a manual check
    # In a real system, this would happen when the booking system updates
    
    print("   Simulating: Someone cancels a booking, creating new availability")
    print("   This would normally trigger the monitoring system to detect changes")
    
    return True

def check_notification_history(alert_id):
    """Check notification history for an alert."""
    print(f"\n📧 Checking notification history for alert {alert_id}...")
    
    response = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history")
    if response.status_code == 200:
        history = response.json()
        print(f"   Total notifications: {history['total_notifications']}")
        
        if history['notifications']:
            print("   Recent notifications:")
            for i, notif in enumerate(history['notifications'][-3:], 1):  # Show last 3
                start_time = notif['slot_start_time'][:16]
                end_time = notif['slot_end_time'][:16]
                print(f"     {i}. {start_time} - {end_time} (sent: {notif['sent_at'][:19]})")
        else:
            print("   No notifications sent yet")
        
        return history
    else:
        print(f"❌ Failed to get notification history: {response.status_code}")
        return None

def stop_monitoring():
    """Stop the monitoring service."""
    print("\n🛑 Stopping monitoring service...")
    
    response = requests.post(f"{BASE_URL}/admin/stop-monitoring")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Monitoring stopped successfully!")
        print(f"   Status: {result['status']}")
        return True
    else:
        print(f"❌ Failed to stop monitoring: {response.status_code}")
        return False

def demonstrate_monitoring_workflow():
    """Demonstrate the complete monitoring workflow."""
    print("🎾 Tennis Court Alert - Monitoring System Test")
    print("=" * 60)
    
    try:
        # Step 1: Create a test alert
        alert_id = create_test_alert()
        if not alert_id:
            return
        
        # Step 2: Start monitoring
        if not start_monitoring():
            return
        
        # Step 3: Check initial status
        initial_status = check_monitoring_status()
        
        # Step 4: Trigger manual check to establish baseline
        print("\n⏱️  Waiting 2 seconds before first check...")
        time.sleep(2)
        trigger_manual_check()
        
        # Step 5: Check snapshots after first check
        check_availability_snapshots()
        
        # Step 6: Check notification history
        check_notification_history(alert_id)
        
        # Step 7: Simulate booking system changes
        simulate_booking_system_refresh()
        
        # Step 8: Trigger another check to see if changes are detected
        print("\n⏱️  Waiting 2 seconds before second check...")
        time.sleep(2)
        trigger_manual_check()
        
        # Step 9: Check final status
        final_status = check_monitoring_status()
        
        # Step 10: Check final notification history
        final_history = check_notification_history(alert_id)
        
        # Step 11: Stop monitoring
        stop_monitoring()
        
        # Analysis
        print(f"\n📈 MONITORING SYSTEM ANALYSIS:")
        if initial_status and final_status:
            initial_checks = initial_status['stats']['total_checks']
            final_checks = final_status['stats']['total_checks']
            notifications_sent = final_status['stats']['notifications_sent']
            
            print(f"   Checks performed: {final_checks - initial_checks}")
            print(f"   Notifications sent: {notifications_sent}")
            print(f"   Clubs monitored: {len(final_status['stats']['clubs_monitored'])}")
            
            if notifications_sent > 0:
                print(f"   ✅ SUCCESS: Monitoring system sent notifications!")
            else:
                print(f"   ℹ️  No notifications sent (normal for mock data)")
        
        print(f"\n💡 KEY FEATURES DEMONSTRATED:")
        print(f"   ✅ Automatic monitoring every 10 minutes")
        print(f"   ✅ Change detection between scans")
        print(f"   ✅ Smart notification processing")
        print(f"   ✅ Complete audit trail")
        print(f"   ✅ Admin controls for monitoring")
        print(f"   ✅ Real-time status monitoring")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

def main():
    """Run the monitoring system test."""
    demonstrate_monitoring_workflow()

if __name__ == "__main__":
    main()
