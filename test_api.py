#!/usr/bin/env python3
"""
Simple test script for the Tennis Court Finder API.
Run this to test all the main functionality.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("✅ Health check passed!")
        print(f"   Response: {response.json()}")
    else:
        print(f"❌ Health check failed: {response.status_code}")
    print()

def test_get_clubs():
    """Test getting available clubs."""
    print("🔍 Testing get clubs endpoint...")
    response = requests.get(f"{BASE_URL}/clubs")
    if response.status_code == 200:
        clubs = response.json()
        print("✅ Clubs retrieved successfully!")
        print(f"   Found {len(clubs['clubs'])} clubs:")
        for club in clubs['clubs']:
            print(f"   - {club['name']} (ID: {club['id']})")
    else:
        print(f"❌ Failed to get clubs: {response.status_code}")
    print()

def test_get_club_courts():
    """Test getting courts for a specific club."""
    print("🔍 Testing get club courts endpoint...")
    response = requests.get(f"{BASE_URL}/clubs/club_123/courts")
    if response.status_code == 200:
        courts_data = response.json()
        print("✅ Club courts retrieved successfully!")
        print(f"   Club: {courts_data['club_name']}")
        print(f"   Courts: {len(courts_data['courts'])}")
        for court in courts_data['courts']:
            print(f"   - {court['name']} ({court['surface']}, {'Indoor' if court['indoor'] else 'Outdoor'})")
    else:
        print(f"❌ Failed to get club courts: {response.status_code}")
    print()

def test_create_alert():
    """Test creating a new alert."""
    print("🔍 Testing create alert endpoint...")
    
    # Create a test alert
    alert_data = {
        "email": "test@example.com",
        "club_preferences": [
            {
                "club_id": "club_123",
                "court_ids": ["court_1", "court_2"]
            },
            {
                "club_id": "club_456", 
                "court_ids": ["court_4"]
            }
        ],
        "preferred_times": [
            {
                "day_of_week": 1,  # Tuesday
                "start_time": "10:00",
                "end_time": "12:00"
            },
            {
                "day_of_week": 3,  # Thursday
                "start_time": "14:00",
                "end_time": "16:00"
            }
        ],
        "alert_preferences": {
            "minimum_slot_duration_minutes": 90,
            "expiry_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
            "max_notifications_per_day": 2
        }
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=alert_data)
    if response.status_code == 201:
        alert = response.json()
        print("✅ Alert created successfully!")
        print(f"   Alert ID: {alert['id']}")
        print(f"   Email: {alert['email']}")
        print(f"   Clubs: {len(alert['club_preferences'])}")
        print(f"   Time slots: {len(alert['preferred_times'])}")
        print(f"   Status: {alert['status']}")
        return alert['id']
    else:
        print(f"❌ Failed to create alert: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_get_alert(alert_id):
    """Test getting an alert by ID."""
    if not alert_id:
        return
        
    print("🔍 Testing get alert endpoint...")
    response = requests.get(f"{BASE_URL}/alerts/{alert_id}")
    if response.status_code == 200:
        alert = response.json()
        print("✅ Alert retrieved successfully!")
        print(f"   Alert ID: {alert['id']}")
        print(f"   Created: {alert['created_at']}")
        print(f"   Status: {alert['status']}")
    else:
        print(f"❌ Failed to get alert: {response.status_code}")
    print()

def test_error_handling():
    """Test error handling with invalid data."""
    print("🔍 Testing error handling...")
    
    # Test with invalid email
    invalid_data = {
        "email": "not-an-email",
        "club_preferences": [{"club_id": "club_123", "court_ids": ["court_1"]}],
        "preferred_times": [{"day_of_week": 1, "start_time": "10:00", "end_time": "12:00"}]
    }
    
    response = requests.post(f"{BASE_URL}/alerts", json=invalid_data)
    if response.status_code == 422:  # Validation error
        print("✅ Error handling works correctly!")
        print("   Invalid email was rejected as expected")
    else:
        print(f"❌ Error handling failed: {response.status_code}")
    print()

def main():
    """Run all tests."""
    print("🎾 Tennis Court Finder API Test Suite")
    print("=" * 50)
    
    try:
        test_health()
        test_get_clubs()
        test_get_club_courts()
        alert_id = test_create_alert()
        test_get_alert(alert_id)
        test_error_handling()
        
        print("🎉 All tests completed!")
        print("\n💡 Check your server terminal for email notifications!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the server is running: poetry run python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
