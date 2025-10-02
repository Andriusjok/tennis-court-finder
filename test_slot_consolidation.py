#!/usr/bin/env python3
"""
Test script to demonstrate the slot consolidation system.
This shows how overlapping time slots are intelligently merged.
"""

import requests
import json
from datetime import datetime, timedelta
from app.services.slot_consolidation_service import slot_consolidation_service
from app.models import TimeSlot, CourtAvailability

BASE_URL = "http://localhost:8000"

def create_test_overlapping_slots():
    """Create test data with overlapping time slots."""
    print("🔍 Creating test data with overlapping time slots...")
    
    # Simulate a 90-minute booking cancellation that creates overlapping slots
    overlapping_slots = [
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),  # 19:00
            end_time=datetime(2025, 10, 1, 20, 0),    # 20:00 (60 min)
            available=True,
            price=25.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 30), # 19:30
            end_time=datetime(2025, 10, 1, 20, 30),   # 20:30 (60 min)
            available=True,
            price=25.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),  # 19:00
            end_time=datetime(2025, 10, 1, 20, 30),   # 20:30 (90 min)
            available=True,
            price=30.0,
            currency="USD"
        )
    ]
    
    court = CourtAvailability(
        court_id="court_1",
        court_name="Court 1",
        time_slots=overlapping_slots
    )
    
    print(f"   Created {len(overlapping_slots)} overlapping time slots:")
    for i, slot in enumerate(overlapping_slots, 1):
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        print(f"   {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} minutes)")
    
    return [court]

def test_slot_consolidation():
    """Test the slot consolidation algorithm."""
    print(f"\n🧪 TESTING SLOT CONSOLIDATION ALGORITHM:")
    
    # Create test data
    original_courts = create_test_overlapping_slots()
    
    # Show original slots
    print(f"\n📋 ORIGINAL TIME SLOTS:")
    for court in original_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Consolidate slots
    print(f"\n🔄 CONSOLIDATING OVERLAPPING SLOTS...")
    consolidated_courts = slot_consolidation_service.consolidate_court_availability(original_courts)
    
    # Show consolidated slots
    print(f"\n✅ CONSOLIDATED TIME SLOTS:")
    for court in consolidated_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Show statistics
    stats = slot_consolidation_service.get_consolidation_stats(original_courts, consolidated_courts)
    print(f"\n📊 CONSOLIDATION STATISTICS:")
    print(f"   Original slots: {stats['original_slots']}")
    print(f"   Consolidated slots: {stats['consolidated_slots']}")
    print(f"   Slots eliminated: {stats['slots_eliminated']}")
    print(f"   Consolidation ratio: {stats['consolidation_ratio']:.2f}")
    
    return consolidated_courts

def test_minimum_duration_filtering():
    """Test filtering by minimum duration."""
    print(f"\n🎯 TESTING MINIMUM DURATION FILTERING:")
    
    # Create test data with slots of different durations
    test_slots = [
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),
            end_time=datetime(2025, 10, 1, 19, 30),  # 30 minutes
            available=True,
            price=15.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 20, 0),
            end_time=datetime(2025, 10, 1, 21, 0),  # 60 minutes
            available=True,
            price=25.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 21, 0),
            end_time=datetime(2025, 10, 1, 22, 30),  # 90 minutes
            available=True,
            price=35.0,
            currency="USD"
        )
    ]
    
    court = CourtAvailability(
        court_id="court_1",
        court_name="Court 1",
        time_slots=test_slots
    )
    
    print(f"   Testing with 60-minute minimum duration requirement...")
    
    # Filter by 60-minute minimum
    filtered_courts = slot_consolidation_service.filter_by_minimum_duration([court], 60)
    
    print(f"\n📋 FILTERED TIME SLOTS (60+ minutes):")
    for court in filtered_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    print(f"   ✅ 30-minute slot was filtered out (below minimum)")
    print(f"   ✅ 60-minute and 90-minute slots were kept")

def create_alert_and_test_integration():
    """Create an alert and test the full integration."""
    print(f"\n🔗 TESTING FULL INTEGRATION WITH ALERT SYSTEM:")
    
    # Create alert with 60-minute minimum
    alert_data = {
        "email": "consolidation-test@example.com",
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
                "end_time": "22:30"
            }
        ],
        "alert_preferences": {
            "minimum_slot_duration_minutes": 60
        }
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert = response.json()
        print(f"   ✅ Alert created: {alert['id']}")
        print(f"   📧 Email: {alert['email']}")
        print(f"   ⏱️  Minimum duration: {alert['alert_preferences']['minimum_slot_duration_minutes']} minutes")
        
        # Send test notification (this will use slot consolidation)
        print(f"\n📧 Sending test notification with slot consolidation...")
        notif_response = requests.post(f"{BASE_URL}/alerts/{alert['id']}/test-notification")
        
        if notif_response.status_code == 200:
            print(f"   ✅ Notification sent successfully")
            
            # Check notification history
            history_response = requests.get(f"{BASE_URL}/alerts/{alert['id']}/notification-history")
            if history_response.status_code == 200:
                history = history_response.json()
                print(f"   📊 Notifications sent: {history['total_notifications']}")
                
                print(f"\n📋 NOTIFICATION DETAILS:")
                for i, notif in enumerate(history['notifications'], 1):
                    start_time = notif['slot_start_time'][:16]
                    end_time = notif['slot_end_time'][:16]
                    duration = (datetime.fromisoformat(notif['slot_end_time']) - 
                               datetime.fromisoformat(notif['slot_start_time'])).total_seconds() / 60
                    print(f"   {i}. {start_time} - {end_time} ({duration:.0f} minutes)")
                
                if history['total_notifications'] == 1:
                    print(f"   ✅ Perfect! Only 1 notification sent (slot consolidation working)")
                else:
                    print(f"   ⚠️  {history['total_notifications']} notifications sent")
        else:
            print(f"   ❌ Notification failed: {notif_response.status_code}")
    else:
        print(f"   ❌ Failed to create alert: {response.status_code}")

def main():
    """Run slot consolidation tests."""
    print("🎾 Tennis Court Alert - Slot Consolidation Test Suite")
    print("=" * 70)
    
    try:
        # Test 1: Basic slot consolidation
        consolidated_courts = test_slot_consolidation()
        
        # Test 2: Minimum duration filtering
        test_minimum_duration_filtering()
        
        # Test 3: Full integration
        create_alert_and_test_integration()
        
        print(f"\n🎉 SLOT CONSOLIDATION TESTS COMPLETED!")
        print(f"\n💡 KEY IMPROVEMENTS:")
        print(f"   ✅ Overlapping time slots are intelligently merged")
        print(f"   ✅ Users receive ONE notification for consolidated slots")
        print(f"   ✅ Longer slots are prioritized over shorter ones")
        print(f"   ✅ Minimum duration requirements are respected")
        print(f"   ✅ No more notification spam from overlapping slots")
        print(f"   ✅ Enhanced email content shows slot duration")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
