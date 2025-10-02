# 🎾 Frontend Implementation Guide

This guide explains how to build the frontend for the Tennis Court Alert creation flow.

## 🎯 **User Journey Overview**

The user wants to create a tennis court alert with these steps:

1. **Email Input** → Where to send alerts
2. **Club Selection** → Multi-select from available clubs  
3. **Court Selection** → Per club, show available courts
4. **Schedule Setup** → Days of week + time ranges
5. **Preferences** → Minimum slot duration, expiry date
6. **Confirmation** → Save subscription + send confirmation email

## 🔌 **API Endpoints for Frontend**

### **1. Get Available Clubs**
```http
GET /clubs
```
**Response:**
```json
{
  "clubs": [
    {
      "id": "club_123",
      "name": "Central Tennis Club",
      "location": {
        "address": "123 Tennis Street, City, State 12345",
        "coordinates": {"lat": 40.7128, "lng": -74.0060}
      },
      "booking_system": "courtreserve",
      "courts": [
        {"id": "court_1", "name": "Court 1", "surface": "hard", "indoor": false}
      ]
    }
  ]
}
```

### **2. Get Courts for a Specific Club**
```http
GET /clubs/{club_id}/courts
```
**Response:**
```json
{
  "club_id": "club_123",
  "club_name": "Central Tennis Club",
  "courts": [
    {
      "id": "court_1",
      "name": "Court 1", 
      "surface": "hard",
      "indoor": false
    }
  ]
}
```

### **3. Create Alert Subscription**
```http
POST /alerts
```
**Request Body:**
```json
{
  "email": "user@example.com",
  "club_preferences": [
    {
      "club_id": "club_123",
      "court_ids": ["court_1", "court_2"]
    }
  ],
  "preferred_times": [
    {
      "day_of_week": 1,
      "start_time": "10:00",
      "end_time": "12:00"
    }
  ],
  "alert_preferences": {
    "minimum_slot_duration_minutes": 60,
    "expiry_date": "2025-01-15",
    "max_notifications_per_day": 3,
    "notification_frequency_hours": 24
  },
  "notification_preferences": {
    "email_enabled": true,
    "sms_enabled": false
  }
}
```

## 🎨 **Frontend Implementation Steps**

### **Step 1: Email Input**
```html
<input 
  type="email" 
  placeholder="Enter your email address"
  required
/>
```

### **Step 2: Club Selection (Multi-select)**
```javascript
// Fetch clubs
const clubs = await fetch('/clubs').then(r => r.json());

// Multi-select component
<select multiple>
  {clubs.clubs.map(club => (
    <option key={club.id} value={club.id}>
      {club.name} - {club.location.address}
    </option>
  ))}
</select>
```

### **Step 3: Court Selection (Dynamic per Club)**
```javascript
// When clubs are selected, fetch courts for each
const selectedClubs = ['club_123', 'club_456'];

for (const clubId of selectedClubs) {
  const courts = await fetch(`/clubs/${clubId}/courts`).then(r => r.json());
  
  // Show court selection for this club
  <div>
    <h3>{courts.club_name}</h3>
    <select multiple>
      {courts.courts.map(court => (
        <option key={court.id} value={court.id}>
          {court.name} ({court.surface}, {court.indoor ? 'Indoor' : 'Outdoor'})
        </option>
      ))}
    </select>
  </div>
}
```

### **Step 4: Schedule Setup**
```javascript
// Days of week selector
const days = [
  {value: 0, label: 'Monday'},
  {value: 1, label: 'Tuesday'},
  // ... etc
];

// Time range picker
<div>
  <label>Day: <select>{days.map(day => <option value={day.value}>{day.label}</option>)}</select></label>
  <label>Start: <input type="time" /></label>
  <label>End: <input type="time" /></label>
  <button>Add Time Slot</button>
</div>
```

### **Step 5: Preferences**
```html
<div>
  <label>
    Minimum slot duration (minutes):
    <input type="number" min="30" max="480" value="60" />
  </label>
  
  <label>
    Alert expiry date:
    <input type="date" />
  </label>
  
  <label>
    Max notifications per day:
    <input type="number" min="1" max="10" value="3" />
  </label>
</div>
```

### **Step 6: Submit Alert**
```javascript
const createAlert = async (formData) => {
  const response = await fetch('/alerts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(formData)
  });
  
  if (response.ok) {
    const alert = await response.json();
    showSuccess(`Alert created! ID: ${alert.id}`);
    // User will receive confirmation email
  }
};
```

## 🎯 **Complete Form Example (React)**

```jsx
function AlertCreationForm() {
  const [email, setEmail] = useState('');
  const [selectedClubs, setSelectedClubs] = useState([]);
  const [clubCourts, setClubCourts] = useState({});
  const [selectedCourts, setSelectedCourts] = useState({});
  const [preferredTimes, setPreferredTimes] = useState([]);
  const [preferences, setPreferences] = useState({
    minimum_slot_duration_minutes: 60,
    expiry_date: null,
    max_notifications_per_day: 3
  });

  // Load clubs on component mount
  useEffect(() => {
    fetch('/clubs')
      .then(r => r.json())
      .then(data => setClubs(data.clubs));
  }, []);

  // Load courts when clubs are selected
  useEffect(() => {
    selectedClubs.forEach(async (clubId) => {
      if (!clubCourts[clubId]) {
        const courts = await fetch(`/clubs/${clubId}/courts`).then(r => r.json());
        setClubCourts(prev => ({...prev, [clubId]: courts.courts}));
      }
    });
  }, [selectedClubs]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const clubPreferences = selectedClubs.map(clubId => ({
      club_id: clubId,
      court_ids: selectedCourts[clubId] || []
    }));

    const alertData = {
      email,
      club_preferences: clubPreferences,
      preferred_times: preferredTimes,
      alert_preferences: preferences,
      notification_preferences: { email_enabled: true, sms_enabled: false }
    };

    try {
      const response = await fetch('/alerts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(alertData)
      });
      
      if (response.ok) {
        const alert = await response.json();
        alert('Alert created successfully! Check your email for confirmation.');
      }
    } catch (error) {
      alert('Error creating alert: ' + error.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Email input */}
      <input 
        type="email" 
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your email"
        required 
      />

      {/* Club selection */}
      <select 
        multiple 
        value={selectedClubs}
        onChange={(e) => setSelectedClubs([...e.target.selectedOptions].map(o => o.value))}
      >
        {clubs.map(club => (
          <option key={club.id} value={club.id}>
            {club.name}
          </option>
        ))}
      </select>

      {/* Court selection for each club */}
      {selectedClubs.map(clubId => (
        <div key={clubId}>
          <h3>{clubs.find(c => c.id === clubId)?.name}</h3>
          <select 
            multiple
            value={selectedCourts[clubId] || []}
            onChange={(e) => setSelectedCourts(prev => ({
              ...prev, 
              [clubId]: [...e.target.selectedOptions].map(o => o.value)
            }))}
          >
            {clubCourts[clubId]?.map(court => (
              <option key={court.id} value={court.id}>
                {court.name} ({court.surface})
              </option>
            ))}
          </select>
        </div>
      ))}

      {/* Time preferences */}
      <div>
        <h3>Preferred Times</h3>
        {preferredTimes.map((time, index) => (
          <div key={index}>
            <select value={time.day_of_week} onChange={(e) => updateTime(index, 'day_of_week', parseInt(e.target.value))}>
              <option value={0}>Monday</option>
              <option value={1}>Tuesday</option>
              {/* ... other days */}
            </select>
            <input type="time" value={time.start_time} onChange={(e) => updateTime(index, 'start_time', e.target.value)} />
            <input type="time" value={time.end_time} onChange={(e) => updateTime(index, 'end_time', e.target.value)} />
            <button type="button" onClick={() => removeTime(index)}>Remove</button>
          </div>
        ))}
        <button type="button" onClick={addTimeSlot}>Add Time Slot</button>
      </div>

      {/* Preferences */}
      <div>
        <label>
          Minimum duration (minutes):
          <input 
            type="number" 
            min="30" 
            max="480" 
            value={preferences.minimum_slot_duration_minutes}
            onChange={(e) => setPreferences(prev => ({...prev, minimum_slot_duration_minutes: parseInt(e.target.value)}))}
          />
        </label>
        
        <label>
          Expiry date:
          <input 
            type="date" 
            value={preferences.expiry_date || ''}
            onChange={(e) => setPreferences(prev => ({...prev, expiry_date: e.target.value}))}
          />
        </label>
      </div>

      <button type="submit">Create Alert</button>
    </form>
  );
}
```

## 🎨 **UI/UX Recommendations**

### **Visual Design**
- **Clean, modern interface** with tennis-themed colors (green, white)
- **Step-by-step wizard** or **single-page form** with clear sections
- **Progress indicator** showing completion status
- **Responsive design** for mobile and desktop

### **User Experience**
- **Real-time validation** of email format and time ranges
- **Helpful tooltips** explaining each field
- **Preview section** showing what the alert will monitor
- **Clear success/error messages**
- **Email confirmation** after successful creation

### **Accessibility**
- **Keyboard navigation** support
- **Screen reader** compatibility
- **High contrast** color schemes
- **Clear labels** and form structure

## 🧪 **Testing the API**

You can test the API using the interactive docs at `http://localhost:8000/docs` or with curl:

```bash
# Create an alert
curl -X POST "http://localhost:8000/alerts" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "club_preferences": [
      {
        "club_id": "club_123",
        "court_ids": ["court_1", "court_2"]
      }
    ],
    "preferred_times": [
      {
        "day_of_week": 1,
        "start_time": "10:00",
        "end_time": "12:00"
      }
    ]
  }'
```

This will create an alert and send a confirmation email (printed to console in development mode).
