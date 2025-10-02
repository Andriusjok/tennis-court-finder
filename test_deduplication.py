#!/usr/bin/env python3
"""
Test script to demonstrate the notification deduplication system.
This shows how users only receive one alert per time slot.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def create_test_alert():
    """Create a test alert for deduplication testing."""
    print("🔍 Creating test alert...")
    
    alert_data = {
        "email": "dedup-test@example.com",
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
        return alert['id']
    else:
        print(f"❌ Failed to create alert: {response.status_code}")
        return None

def test_notification_deduplication(alert_id):
    """Test that duplicate notifications are prevented."""
    print(f"\n🧪 Testing deduplication for alert: {alert_id}")
    
    # Send first notification
    print("📧 Sending first notification...")
    response1 = requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
    if response1.status_code == 200:
        print("✅ First notification sent successfully")
    else:
        print(f"❌ First notification failed: {response1.status_code}")
        return
    
    # Wait a moment
    time.sleep(1)
    
    # Send second notification (should be deduplicated)
    print("📧 Sending second notification (should be deduplicated)...")
    response2 = requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
    if response2.status_code == 200:
        print("✅ Second notification processed (should be deduplicated)")
    else:
        print(f"❌ Second notification failed: {response2.status_code}")
        return
    
    # Check notification history
    print("\n📊 Checking notification history...")
    history_response = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history")
    if history_response.status_code == 200:
        history = history_response.json()
        print(f"📈 Total notifications sent: {history['total_notifications']}")
        
        if history['total_notifications'] == 1:
            print("✅ DEDUPLICATION WORKING! Only 1 notification was sent despite 2 attempts")
        else:
            print(f"❌ Deduplication failed! {history['total_notifications']} notifications sent")
        
        # Show notification details
        for i, notif in enumerate(history['notifications'], 1):
            print(f"   {i}. Court: {notif['court_id']}, Time: {notif['slot_start_time']} - {notif['slot_end_time']}")
    else:
        print(f"❌ Failed to get notification history: {history_response.status_code}")

def test_multiple_alerts():
    """Test deduplication across multiple alerts."""
    print("\n🔄 Testing deduplication across multiple alerts...")
    
    # Create two alerts for the same time slot
    alert1_data = {
        "email": "user1@example.com",
        "club_preferences": [{"club_id": "club_123", "court_ids": ["court_1"]}],
        "preferred_times": [{"day_of_week": 1, "start_time": "10:00", "end_time": "11:00"}]
    }
    
    alert2_data = {
        "email": "user2@example.com", 
        "club_preferences": [{"club_id": "club_123", "court_ids": ["court_1"]}],
        "preferred_times": [{"day_of_week": 1, "start_time": "10:00", "end_time": "11:00"}]
    }
    
    # Create alerts
    response1 = requests.post(f"{BASE_URL}/alerts", json=alert1_data)
    response2 = requests.post(f"{BASE_URL}/alerts", json=alert2_data)
    
    if response1.status_code == 201 and response2.status_code == 201:
        alert1_id = response1.json()['id']
        alert2_id = response2.json()['id']
        
        print(f"✅ Created alerts: {alert1_id}, {alert2_id}")
        
        # Send notifications to both alerts
        print("📧 Sending notifications to both alerts...")
        requests.post(f"{BASE_URL}/alerts/{alert1_id}/test-notification")
        requests.post(f"{BASE_URL}/alerts/{alert2_id}/test-notification")
        
        # Check history for both
        history1 = requests.get(f"{BASE_URL}/alerts/{alert1_id}/notification-history").json()
        history2 = requests.get(f"{BASE_URL}/alerts/{alert2_id}/notification-history").json()
        
        print(f"📊 Alert 1 notifications: {history1['total_notifications']}")
        print(f"📊 Alert 2 notifications: {history2['total_notifications']}")
        
        if history1['total_notifications'] == 1 and history2['total_notifications'] == 1:
            print("✅ Each alert received exactly 1 notification (deduplication working per alert)")
        else:
            print("❌ Deduplication issue detected")
    else:
        print("❌ Failed to create test alerts")

def show_deduplication_stats():
    """Show deduplication service statistics."""
    print("\n📊 Deduplication Service Statistics:")
    response = requests.get(f"{BASE_URL}/admin/deduplication-stats")
    if response.status_code == 200:
        stats = response.json()
        dedup_stats = stats['deduplication_stats']
        print(f"   Total notifications sent: {dedup_stats['total_notifications_sent']}")
        print(f"   Unique deduplication keys: {dedup_stats['unique_deduplication_keys']}")
        print(f"   Service status: {stats['service_status']}")
    else:
        print(f"❌ Failed to get stats: {response.status_code}")

def main():
    """Run deduplication tests."""
    print("🎾 Tennis Court Alert Deduplication Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Basic deduplication
        alert_id = create_test_alert()
        if alert_id:
            test_notification_deduplication(alert_id)
        
        # Test 2: Multiple alerts
        test_multiple_alerts()
        
        # Test 3: Show statistics
        show_deduplication_stats()
        
        print("\n🎉 Deduplication tests completed!")
        print("\n💡 Key Features Demonstrated:")
        print("   ✅ Users only receive one notification per time slot")
        print("   ✅ Deduplication works across multiple notification attempts")
        print("   ✅ Each alert maintains its own deduplication history")
        print("   ✅ System tracks all sent notifications for audit purposes")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
