#!/usr/bin/env python3
"""
Test script to demonstrate the overlapping time slot issue.
This shows what happens when a longer booking is cancelled and creates multiple overlapping slots.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def create_alert_with_60min_preference():
    """Create an alert with 60-minute minimum preference."""
    print("🔍 Creating alert with 60-minute minimum preference...")
    
    alert_data = {
        "email": "overlap-test@example.com",
        "club_preferences": [
            {
                "club_id": "club_123",
                "court_ids": ["court_1"]
            }
        ],
        "preferred_times": [
            {
                "day_of_week": 1,  # Tuesday
                "start_time": "19:00",
                "end_time": "20:30"  # User wants 19:00-20:30 range
            }
        ],
        "alert_preferences": {
            "minimum_slot_duration_minutes": 60  # 60-minute minimum
        }
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert = response.json()
        print(f"✅ Alert created: {alert['id']}")
        print(f"   Email: {alert['email']}")
        print(f"   Preferred time: {alert['preferred_times'][0]['start_time']} - {alert['preferred_times'][0]['end_time']}")
        print(f"   Minimum duration: {alert['alert_preferences']['minimum_slot_duration_minutes']} minutes")
        return alert['id']
    else:
        print(f"❌ Failed to create alert: {response.status_code}")
        return None

def simulate_90min_cancellation():
    """Simulate what happens when a 90-minute booking is cancelled."""
    print(f"\n🎭 SIMULATING 90-MINUTE BOOKING CANCELLATION:")
    print("   Scenario: Someone cancels their 19:00-20:30 booking (90 minutes)")
    print("   This creates overlapping 60-minute slots:")
    print("   - Slot 1: 19:00-20:00 (60 minutes)")
    print("   - Slot 2: 19:30-20:30 (60 minutes)")
    print("   - Slot 3: 19:00-20:30 (90 minutes) - the original slot")
    
    # This is what the booking system would typically return
    overlapping_slots = [
        {
            "start_time": "19:00",
            "end_time": "20:00",
            "duration_minutes": 60
        },
        {
            "start_time": "19:30", 
            "end_time": "20:30",
            "duration_minutes": 60
        },
        {
            "start_time": "19:00",
            "end_time": "20:30", 
            "duration_minutes": 90
        }
    ]
    
    return overlapping_slots

def test_current_behavior(alert_id):
    """Test what the current system would do with overlapping slots."""
    print(f"\n🧪 TESTING CURRENT SYSTEM BEHAVIOR:")
    print("   Sending notification with overlapping time slots...")
    
    # Send test notification (this uses the current mock data)
    response = requests.post(f"{BASE_URL}/alerts/{alert_id}/test-notification")
    if response.status_code == 200:
        print("   ✅ Notification sent successfully")
    else:
        print(f"   ❌ Notification failed: {response.status_code}")
        return
    
    # Check notification history
    history_response = requests.get(f"{BASE_URL}/alerts/{alert_id}/notification-history")
    if history_response.status_code == 200:
        history = history_response.json()
        print(f"   📊 Total notifications sent: {history['total_notifications']}")
        
        print(f"\n📋 NOTIFICATION BREAKDOWN:")
        for i, notif in enumerate(history['notifications'], 1):
            start_time = notif['slot_start_time'][:16]
            end_time = notif['slot_end_time'][:16]
            duration = (datetime.fromisoformat(notif['slot_end_time']) - 
                       datetime.fromisoformat(notif['slot_start_time'])).total_seconds() / 60
            
            print(f"   {i}. {start_time} - {end_time} ({duration:.0f} minutes)")
        
        # Analyze the issue
        print(f"\n⚠️  CURRENT SYSTEM ISSUES:")
        if history['total_notifications'] > 1:
            print("   ❌ User receives MULTIPLE alerts for overlapping slots")
            print("   ❌ This creates notification spam")
            print("   ❌ User might be confused by multiple similar alerts")
            print("   ❌ No intelligent slot consolidation")
        else:
            print("   ✅ Only one notification sent (unexpected - might be due to mock data)")
    
    return history['total_notifications']

def demonstrate_ideal_behavior():
    """Show what the ideal behavior should be."""
    print(f"\n💡 IDEAL BEHAVIOR FOR OVERLAPPING SLOTS:")
    print("   When a 90-minute booking is cancelled (19:00-20:30):")
    print("   ✅ User should receive ONE alert for the full 90-minute slot")
    print("   ✅ Alert should mention: '90-minute slot available: 19:00-20:30'")
    print("   ✅ No duplicate notifications for overlapping 60-minute segments")
    print("   ✅ User gets the maximum value (longer playing time)")
    print("   ✅ Clean, non-confusing notification experience")

def show_solution_approach():
    """Show how to solve the overlapping slot problem."""
    print(f"\n🔧 SOLUTION APPROACH:")
    print("   1. **Slot Consolidation Algorithm**:")
    print("      - Detect overlapping time slots")
    print("      - Merge them into the longest possible slot")
    print("      - Send one notification for the consolidated slot")
    print()
    print("   2. **Smart Deduplication**:")
    print("      - Track notifications by time range, not individual slots")
    print("      - Prevent notifications for overlapping time periods")
    print("      - Prioritize longer slots over shorter ones")
    print()
    print("   3. **Enhanced Notification Content**:")
    print("      - Show the full available time range")
    print("      - Mention the total duration")
    print("      - Highlight that it's a longer slot than minimum")

def main():
    """Run the overlapping slot test."""
    print("🎾 Tennis Court Alert - Overlapping Time Slots Test")
    print("=" * 70)
    
    try:
        # Create alert
        alert_id = create_alert_with_60min_preference()
        if not alert_id:
            return
        
        # Simulate the scenario
        overlapping_slots = simulate_90min_cancellation()
        
        # Test current behavior
        notifications_sent = test_current_behavior(alert_id)
        
        # Show ideal behavior
        demonstrate_ideal_behavior()
        
        # Show solution
        show_solution_approach()
        
        print(f"\n🎯 CONCLUSION:")
        print(f"   Current system sends: {notifications_sent} notifications")
        print(f"   Ideal system should send: 1 notification")
        print(f"   Improvement needed: Slot consolidation algorithm")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
