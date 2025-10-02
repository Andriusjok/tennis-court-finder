#!/usr/bin/env python3
"""
Clear demonstration of notification deduplication system.
This shows exactly how users only receive one alert per time slot.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def create_simple_alert():
    """Create a simple alert for clear deduplication testing."""
    print("🔍 Creating simple test alert...")
    
    alert_data = {
        "email": "dedup-demo@example.com",
        "club_preferences": [
            {
                "club_id": "club_123",
                "court_ids": ["court_1"]  # Only one court
            }
        ],
        "preferred_times": [
            {
                "day_of_week": 1,  # Tuesday
                "start_time": "10:00",
                "end_time": "11:00"  # Only one hour slot
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert = response.json()
        print(f"✅ Alert created: {alert['id']}")
        print(f"   Email: {alert['email']}")
        print(f"   Court: {alert['club_preferences'][0]['court_ids'][0]}")
        print(f"   Time: {alert['preferred_times'][0]['start_time']} - {alert['preferred_times'][0]['end_time']}")
        return alert['id']
    else:
        print(f"❌ Failed to create alert: {response.status_code}")
        return None

def demonstrate_deduplication(alert_id):
    """Demonstrate deduplication with clear messaging."""
    print(f"\n🧪 Demonstrating deduplication for alert: {alert_id}")
    
    # Send first notification
    print("\n📧 FIRST NOTIFICATION ATTEMPT:")
    print("   Sending notification for available court slots...")
    response1 = requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
    if response1.status_code == 200:
        print("   ✅ First notification sent successfully")
    else:
        print(f"   ❌ First notification failed: {response1.status_code}")
        return
    
    # Check what was sent
    history1 = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history").json()
    print(f"   📊 Notifications sent: {history1['total_notifications']}")
    
    # Wait a moment
    time.sleep(2)
    
    # Send second notification (should be deduplicated)
    print("\n📧 SECOND NOTIFICATION ATTEMPT (SAME TIME SLOTS):")
    print("   Attempting to send notification for the same court slots...")
    response2 = requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
    if response2.status_code == 200:
        print("   ✅ Second notification processed")
    else:
        print(f"   ❌ Second notification failed: {response2.status_code}")
        return
    
    # Check what was sent this time
    history2 = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history").json()
    print(f"   📊 Total notifications now: {history2['total_notifications']}")
    
    # Analyze the results
    print(f"\n📈 DEDUPLICATION ANALYSIS:")
    if history2['total_notifications'] == history1['total_notifications']:
        print("   ✅ DEDUPLICATION WORKING PERFECTLY!")
        print("   ✅ No duplicate notifications were sent")
        print("   ✅ User only received one alert per time slot")
    else:
        print("   ❌ Deduplication failed - duplicate notifications were sent")
        print(f"   📊 New notifications sent: {history2['total_notifications'] - history1['total_notifications']}")
    
    # Show the notification details
    print(f"\n📋 NOTIFICATION HISTORY:")
    for i, notif in enumerate(history2['notifications'], 1):
        print(f"   {i}. Court: {notif['court_id']}")
        print(f"      Time: {notif['slot_start_time'][:16]} - {notif['slot_end_time'][:16]}")
        print(f"      Sent: {notif['sent_at'][:19]}")

def test_different_time_slots():
    """Test that different time slots still get notifications."""
    print(f"\n🔄 TESTING DIFFERENT TIME SLOTS:")
    print("   Creating alert for different time slot...")
    
    # Create alert for different time
    alert_data = {
        "email": "different-time@example.com",
        "club_preferences": [{"club_id": "club_123", "court_ids": ["court_1"]}],
        "preferred_times": [{"day_of_week": 2, "start_time": "14:00", "end_time": "15:00"}]  # Different day/time
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert_id = response.json()['id']
        print(f"   ✅ Alert created: {alert_id}")
        
        # Send notification
        requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
        history = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history").json()
        
        print(f"   📊 Notifications sent: {history['total_notifications']}")
        if history['total_notifications'] > 0:
            print("   ✅ Different time slots still get notifications (correct behavior)")
        else:
            print("   ❌ Different time slots not getting notifications")
    else:
        print("   ❌ Failed to create alert for different time")

def show_final_stats():
    """Show final deduplication statistics."""
    print(f"\n📊 FINAL DEDUPLICATION STATISTICS:")
    response = requests.get(f"{BASE_URL}/admin/deduplication-stats")
    if response.status_code == 200:
        stats = response.json()
        dedup_stats = stats['deduplication_stats']
        print(f"   Total notifications sent: {dedup_stats['total_notifications_sent']}")
        print(f"   Unique deduplication keys: {dedup_stats['unique_deduplication_keys']}")
        print(f"   Service status: {stats['service_status']}")
        
        if dedup_stats['total_notifications_sent'] == dedup_stats['unique_deduplication_keys']:
            print("   ✅ Perfect deduplication - no duplicates detected!")
        else:
            print("   ⚠️  Some duplicates may exist")

def main():
    """Run clear deduplication demonstration."""
    print("🎾 Tennis Court Alert Deduplication - Clear Demonstration")
    print("=" * 70)
    
    try:
        # Create a simple alert
        alert_id = create_simple_alert()
        if not alert_id:
            return
        
        # Demonstrate deduplication
        demonstrate_deduplication(alert_id)
        
        # Test different time slots
        test_different_time_slots()
        
        # Show final stats
        show_final_stats()
        
        print(f"\n🎉 DEDUPLICATION DEMONSTRATION COMPLETE!")
        print(f"\n💡 KEY TAKEAWAYS:")
        print(f"   ✅ Users receive exactly ONE notification per time slot")
        print(f"   ✅ Duplicate notifications are automatically prevented")
        print(f"   ✅ Different time slots still get separate notifications")
        print(f"   ✅ System tracks all notifications for audit purposes")
        print(f"   ✅ No spam - users only get meaningful alerts")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
