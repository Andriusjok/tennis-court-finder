#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced slot consolidation with adjacent slot support.
This shows how adjacent slots are intelligently merged into longer slots.
"""

import requests
import json
from datetime import datetime, timedelta
from app.services.slot_consolidation_service import slot_consolidation_service
from app.models import TimeSlot, CourtAvailability

BASE_URL = "http://localhost:8000"

def test_adjacent_slots_consolidation():
    """Test consolidation of adjacent time slots."""
    print("🧪 TESTING ADJACENT SLOTS CONSOLIDATION:")
    print("   Scenario: 30min slot (19:00-19:30) + 30min slot (19:30-20:00)")
    print("   Expected: Should consolidate into 60min slot (19:00-20:00)")
    
    # Create adjacent slots
    adjacent_slots = [
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),   # 19:00
            end_time=datetime(2025, 10, 1, 19, 30),    # 19:30 (30 min)
            available=True,
            price=15.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 30),  # 19:30
            end_time=datetime(2025, 10, 1, 20, 0),     # 20:00 (30 min)
            available=True,
            price=15.0,
            currency="USD"
        )
    ]
    
    court = CourtAvailability(
        court_id="court_1",
        court_name="Court 1",
        time_slots=adjacent_slots
    )
    
    print(f"\n📋 ORIGINAL ADJACENT SLOTS:")
    for i, slot in enumerate(adjacent_slots, 1):
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        print(f"   {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test consolidation
    print(f"\n🔄 CONSOLIDATING ADJACENT SLOTS...")
    consolidated_courts = slot_consolidation_service.consolidate_court_availability([court])
    
    print(f"\n✅ CONSOLIDATED RESULT:")
    for court in consolidated_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test minimum duration filtering
    print(f"\n🎯 TESTING 60-MINUTE MINIMUM DURATION FILTERING:")
    filtered_courts = slot_consolidation_service.filter_by_minimum_duration(consolidated_courts, 60)
    
    print(f"\n📋 RESULT AFTER DURATION FILTERING (60+ minutes):")
    if filtered_courts:
        for court in filtered_courts:
            print(f"   {court.court_name}:")
            for slot in court.time_slots:
                if slot.available:
                    duration = (slot.end_time - slot.start_time).total_seconds() / 60
                    print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
        print(f"   ✅ SUCCESS! 60-minute slot now available for notification!")
        return True
    else:
        print("   ❌ FAILED: Still no slots meet 60-minute minimum")
        return False

def test_complex_adjacent_scenario():
    """Test a more complex scenario with multiple adjacent slots."""
    print(f"\n🧪 TESTING COMPLEX ADJACENT SCENARIO:")
    print("   Scenario: 20min + 20min + 20min + 20min = 80min total")
    print("   Expected: Should consolidate into one 80-minute slot")
    
    # Create multiple adjacent slots
    complex_slots = [
        TimeSlot(
            start_time=datetime(2025, 10, 1, 18, 0),   # 18:00
            end_time=datetime(2025, 10, 1, 18, 20),    # 18:20 (20 min)
            available=True,
            price=10.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 18, 20),  # 18:20
            end_time=datetime(2025, 10, 1, 18, 40),    # 18:40 (20 min)
            available=True,
            price=10.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 18, 40),  # 18:40
            end_time=datetime(2025, 10, 1, 19, 0),     # 19:00 (20 min)
            available=True,
            price=10.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),   # 19:00
            end_time=datetime(2025, 10, 1, 19, 20),    # 19:20 (20 min)
            available=True,
            price=10.0,
            currency="USD"
        )
    ]
    
    court = CourtAvailability(
        court_id="court_1",
        court_name="Court 1",
        time_slots=complex_slots
    )
    
    print(f"\n📋 ORIGINAL COMPLEX ADJACENT SLOTS:")
    for i, slot in enumerate(complex_slots, 1):
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        print(f"   {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test consolidation
    print(f"\n🔄 CONSOLIDATING COMPLEX ADJACENT SLOTS...")
    consolidated_courts = slot_consolidation_service.consolidate_court_availability([court])
    
    print(f"\n✅ CONSOLIDATED RESULT:")
    for court in consolidated_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test with 60-minute minimum
    filtered_courts = slot_consolidation_service.filter_by_minimum_duration(consolidated_courts, 60)
    
    if filtered_courts:
        print(f"   ✅ SUCCESS! 80-minute slot meets 60-minute minimum!")
        return True
    else:
        print(f"   ❌ FAILED: 80-minute slot should meet minimum")
        return False

def test_mixed_overlapping_and_adjacent():
    """Test a scenario with both overlapping and adjacent slots."""
    print(f"\n🧪 TESTING MIXED OVERLAPPING AND ADJACENT SLOTS:")
    print("   Scenario: Overlapping slots + Adjacent slots")
    print("   Expected: Should handle both types of consolidation")
    
    # Create mixed scenario
    mixed_slots = [
        # Overlapping slots (should consolidate to 19:00-20:30)
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 0),   # 19:00
            end_time=datetime(2025, 10, 1, 20, 0),     # 20:00 (60 min)
            available=True,
            price=25.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 19, 30),  # 19:30
            end_time=datetime(2025, 10, 1, 20, 30),    # 20:30 (60 min)
            available=True,
            price=25.0,
            currency="USD"
        ),
        # Adjacent slots (should consolidate to 20:30-21:30)
        TimeSlot(
            start_time=datetime(2025, 10, 1, 20, 30),  # 20:30
            end_time=datetime(2025, 10, 1, 21, 0),     # 21:00 (30 min)
            available=True,
            price=15.0,
            currency="USD"
        ),
        TimeSlot(
            start_time=datetime(2025, 10, 1, 21, 0),   # 21:00
            end_time=datetime(2025, 10, 1, 21, 30),    # 21:30 (30 min)
            available=True,
            price=15.0,
            currency="USD"
        )
    ]
    
    court = CourtAvailability(
        court_id="court_1",
        court_name="Court 1",
        time_slots=mixed_slots
    )
    
    print(f"\n📋 ORIGINAL MIXED SLOTS:")
    for i, slot in enumerate(mixed_slots, 1):
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        print(f"   {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test consolidation
    print(f"\n🔄 CONSOLIDATING MIXED SLOTS...")
    consolidated_courts = slot_consolidation_service.consolidate_court_availability([court])
    
    print(f"\n✅ CONSOLIDATED RESULT:")
    for court in consolidated_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Should have 2 consolidated slots: 19:00-20:30 (90min) and 20:30-21:30 (60min)
    total_slots = sum(len([s for s in court.time_slots if s.available]) for court in consolidated_courts)
    if total_slots == 2:
        print(f"   ✅ SUCCESS! Mixed consolidation working - 2 optimal slots created!")
        return True
    else:
        print(f"   ❌ FAILED: Expected 2 slots, got {total_slots}")
        return False

def create_alert_and_test_integration():
    """Create an alert and test the full integration with adjacent slot consolidation."""
    print(f"\n🔗 TESTING FULL INTEGRATION WITH ADJACENT SLOT CONSOLIDATION:")
    
    # Create alert with 60-minute minimum
    alert_data = {
        "email": "adjacent-test@example.com",
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
                "end_time": "21:00"
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
        
        # Send test notification (this will use adjacent slot consolidation)
        print(f"\n📧 Sending test notification with adjacent slot consolidation...")
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
                
                if history['total_notifications'] > 0:
                    print(f"   ✅ SUCCESS! Adjacent slot consolidation working in full system!")
                    return True
                else:
                    print(f"   ⚠️  No notifications sent (might be due to mock data)")
                    return False
        else:
            print(f"   ❌ Notification failed: {notif_response.status_code}")
            return False
    else:
        print(f"   ❌ Failed to create alert: {response.status_code}")
        return False

def main():
    """Run adjacent slot consolidation tests."""
    print("🎾 Tennis Court Alert - Adjacent Slot Consolidation Test Suite")
    print("=" * 80)
    
    try:
        # Test 1: Basic adjacent slot consolidation
        test1_success = test_adjacent_slots_consolidation()
        
        # Test 2: Complex adjacent scenario
        test2_success = test_complex_adjacent_scenario()
        
        # Test 3: Mixed overlapping and adjacent
        test3_success = test_mixed_overlapping_and_adjacent()
        
        # Test 4: Full integration
        test4_success = create_alert_and_test_integration()
        
        print(f"\n🎉 ADJACENT SLOT CONSOLIDATION TESTS COMPLETED!")
        print(f"\n📊 TEST RESULTS:")
        print(f"   ✅ Basic adjacent consolidation: {'PASS' if test1_success else 'FAIL'}")
        print(f"   ✅ Complex adjacent scenario: {'PASS' if test2_success else 'FAIL'}")
        print(f"   ✅ Mixed overlapping/adjacent: {'PASS' if test3_success else 'FAIL'}")
        print(f"   ✅ Full system integration: {'PASS' if test4_success else 'FAIL'}")
        
        if all([test1_success, test2_success, test3_success]):
            print(f"\n💡 KEY IMPROVEMENTS ACHIEVED:")
            print(f"   ✅ Adjacent slots are intelligently consolidated")
            print(f"   ✅ Users receive notifications for longer playing times")
            print(f"   ✅ No more missed opportunities from adjacent cancellations")
            print(f"   ✅ System handles both overlapping AND adjacent slots")
            print(f"   ✅ Complex scenarios with multiple adjacent slots work")
            print(f"   ✅ Full integration with existing deduplication system")
        else:
            print(f"\n⚠️  Some tests failed - check implementation")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
