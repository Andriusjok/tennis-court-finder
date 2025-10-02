#!/usr/bin/env python3
"""
Test script to demonstrate the adjacent slot consolidation issue.
This shows what happens when two adjacent slots become available.
"""

import requests
import json
from datetime import datetime, timedelta
from app.services.slot_consolidation_service import slot_consolidation_service
from app.models import TimeSlot, CourtAvailability

BASE_URL = "http://localhost:8000"

def create_adjacent_slots_scenario():
    """Create test data with adjacent (non-overlapping) time slots."""
    print("🔍 Creating test data with adjacent time slots...")
    print("   Scenario: 30min slot (19:00-19:30) + 30min slot (19:30-20:00)")
    print("   User wants: 60min minimum duration")
    print("   Problem: Current system sees 2 separate 30min slots (below minimum)")
    
    # Create adjacent slots (not overlapping)
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
    
    print(f"   Created {len(adjacent_slots)} adjacent time slots:")
    for i, slot in enumerate(adjacent_slots, 1):
        duration = (slot.end_time - slot.start_time).total_seconds() / 60
        print(f"   {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} minutes)")
    
    return [court]

def test_current_adjacent_behavior():
    """Test what the current system does with adjacent slots."""
    print(f"\n🧪 TESTING CURRENT SYSTEM WITH ADJACENT SLOTS:")
    
    # Create test data
    original_courts = create_adjacent_slots_scenario()
    
    # Test current consolidation (should NOT work for adjacent slots)
    print(f"\n🔄 Testing current consolidation algorithm...")
    consolidated_courts = slot_consolidation_service.consolidate_court_availability(original_courts)
    
    print(f"\n📋 RESULT AFTER CURRENT CONSOLIDATION:")
    for court in consolidated_courts:
        print(f"   {court.court_name}:")
        for slot in court.time_slots:
            if slot.available:
                duration = (slot.end_time - slot.start_time).total_seconds() / 60
                print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    
    # Test minimum duration filtering
    print(f"\n🎯 Testing 60-minute minimum duration filtering...")
    filtered_courts = slot_consolidation_service.filter_by_minimum_duration(consolidated_courts, 60)
    
    print(f"\n📋 RESULT AFTER DURATION FILTERING (60+ minutes):")
    if filtered_courts:
        for court in filtered_courts:
            print(f"   {court.court_name}:")
            for slot in court.time_slots:
                if slot.available:
                    duration = (slot.end_time - slot.start_time).total_seconds() / 60
                    print(f"     - {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')} ({duration:.0f} min)")
    else:
        print("   ❌ NO SLOTS MEET 60-MINUTE MINIMUM!")
        print("   ❌ User receives NO notification despite 60min being available!")
    
    return len(filtered_courts) == 0

def demonstrate_ideal_behavior():
    """Show what the ideal behavior should be."""
    print(f"\n💡 IDEAL BEHAVIOR FOR ADJACENT SLOTS:")
    print("   When adjacent slots become available (19:00-19:30 + 19:30-20:00):")
    print("   ✅ System should detect adjacent slots")
    print("   ✅ System should consolidate them into one 60-minute slot")
    print("   ✅ User should receive notification: '60-minute slot: 19:00-20:00'")
    print("   ✅ User gets the full playing time they want")

def show_solution_approach():
    """Show how to solve the adjacent slot problem."""
    print(f"\n🔧 SOLUTION APPROACH:")
    print("   1. **Adjacent Slot Detection**:")
    print("      - Detect slots that end exactly when another starts")
    print("      - Group adjacent slots together")
    print("      - Create consolidated slots from adjacent groups")
    print()
    print("   2. **Enhanced Consolidation Algorithm**:")
    print("      - First: Consolidate overlapping slots (current)")
    print("      - Second: Consolidate adjacent slots (new)")
    print("      - Third: Filter by minimum duration")
    print()
    print("   3. **Smart Slot Grouping**:")
    print("      - Sort slots by start time")
    print("      - Find chains of adjacent slots")
    print("      - Merge each chain into one optimal slot")

def main():
    """Run the adjacent slot test."""
    print("🎾 Tennis Court Alert - Adjacent Slots Test")
    print("=" * 60)
    
    try:
        # Test current behavior
        no_slots_available = test_current_adjacent_behavior()
        
        # Show ideal behavior
        demonstrate_ideal_behavior()
        
        # Show solution
        show_solution_approach()
        
        print(f"\n🎯 CONCLUSION:")
        if no_slots_available:
            print("   ❌ CURRENT SYSTEM FAILS: No notification sent for adjacent slots")
            print("   ❌ User misses 60-minute opportunity")
            print("   ✅ SOLUTION NEEDED: Adjacent slot consolidation algorithm")
        else:
            print("   ✅ Current system handles adjacent slots correctly")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
