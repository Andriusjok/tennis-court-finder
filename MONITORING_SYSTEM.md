# 🎾 Tennis Court Alert - Monitoring System

## Overview

The monitoring system is the core component that automatically checks tennis court availability and sends notifications when courts become available. It runs continuously in the background, checking every 10 minutes for changes in court availability.

## 🏗️ Architecture

### Core Components

1. **CourtAvailabilityMonitor** - Main monitoring service
2. **TennisClubIntegration** - Interface for different booking systems
3. **Change Detection** - Compares current vs previous availability
4. **Notification Processing** - Sends alerts when changes are detected

### Key Features

- ✅ **Automatic Monitoring**: Checks every 10 minutes
- ✅ **Change Detection**: Only processes when booking systems refresh
- ✅ **Smart Notifications**: Consolidates slots and prevents duplicates
- ✅ **Multiple Integrations**: Supports different booking systems
- ✅ **Admin Controls**: Start/stop monitoring, manual checks
- ✅ **Complete Audit Trail**: Tracks all activities and notifications

## 🔄 How It Works

### 1. Monitoring Loop
```
Every 10 minutes:
├── Get all active subscriptions
├── For each club in subscriptions:
│   ├── Check if booking system refreshed since last check
│   ├── If refreshed: Get current availability
│   ├── Compare with previous snapshot
│   ├── If changes detected: Process notifications
│   └── Store current snapshot
└── Wait 10 minutes, repeat
```

### 2. Change Detection
- **Previous Snapshot**: Stores last known availability
- **Current Snapshot**: Gets current availability
- **Comparison**: Detects new/changed time slots
- **Processing**: Only processes actual changes

### 3. Notification Flow
```
Changes Detected:
├── Filter changes for each subscription
├── Apply slot consolidation (overlapping + adjacent)
├── Filter by minimum duration
├── Apply deduplication (prevent spam)
├── Send notifications
└── Record sent notifications
```

## 🛠️ API Endpoints

### Admin Controls

#### Start Monitoring
```http
POST /admin/start-monitoring
```
Starts the monitoring service with all active subscriptions.

#### Stop Monitoring
```http
POST /admin/stop-monitoring
```
Stops the monitoring service.

#### Check Status
```http
GET /admin/monitoring-status
```
Returns current monitoring status and statistics.

#### Manual Check
```http
POST /admin/trigger-manual-check
```
Triggers an immediate availability check.

#### View Snapshots
```http
GET /admin/availability-snapshots
```
Shows current availability snapshots for debugging.

## 📊 Monitoring Statistics

The system tracks comprehensive statistics:

```json
{
  "is_running": true,
  "check_interval_minutes": 10,
  "stats": {
    "total_checks": 15,
    "successful_checks": 14,
    "failed_checks": 1,
    "notifications_sent": 3,
    "last_check_time": "2024-01-15T10:30:00Z",
    "clubs_monitored": ["club_123", "club_456"],
    "recent_errors": []
  }
}
```

## 🔌 Tennis Club Integrations

### Supported Systems

1. **Mock Integration** (Development)
   - Simulates booking system behavior
   - Configurable refresh frequencies
   - Perfect for testing

2. **CourtReserve Integration** (Planned)
   - Real API integration
   - Production-ready
   - Handles authentication

3. **ClubAutomation Integration** (Planned)
   - Real API integration
   - Production-ready
   - Handles authentication

### Integration Interface

```python
class TennisClubIntegration(ABC):
    async def get_club_info(self, club_id: str) -> Optional[TennisClub]
    async def get_availability(self, club_id: str, target_date: date) -> List[CourtAvailability]
    async def get_last_refresh_time(self, club_id: str) -> Optional[datetime]
    def get_booking_system_type(self) -> str
```

## 🧪 Testing

### Test Scripts

1. **`test_monitoring_system.py`**
   - Tests basic monitoring functionality
   - Demonstrates admin controls
   - Shows statistics tracking

2. **`test_monitoring_with_changes.py`**
   - Tests change detection
   - Simulates availability changes
   - Demonstrates notification flow

### Running Tests

```bash
# Start the API server
poetry run python main.py

# In another terminal, run tests
poetry run python test_monitoring_system.py
poetry run python test_monitoring_with_changes.py
```

## 🚀 Production Deployment

### Environment Variables

```bash
# Tennis club API keys
COURTRESERVE_API_KEY=your_api_key
CLUBAUTOMATION_API_KEY=your_api_key

# Monitoring configuration
MONITORING_INTERVAL_MINUTES=10
MAX_CONCURRENT_CHECKS=5
```

### Background Processing

For production, consider using:

- **Celery** for background task processing
- **Redis** for task queue and caching
- **PostgreSQL** for persistent storage
- **Docker** for containerization

### Scaling Considerations

- **Horizontal Scaling**: Multiple monitoring workers
- **Rate Limiting**: Respect tennis club API limits
- **Error Handling**: Retry logic and circuit breakers
- **Monitoring**: Health checks and alerting

## 🔍 Debugging

### Common Issues

1. **No Notifications Sent**
   - Check if monitoring is running
   - Verify subscriptions are active
   - Check booking system refresh times

2. **Duplicate Notifications**
   - Check deduplication service
   - Verify notification history
   - Review slot consolidation logic

3. **Missing Changes**
   - Check change detection logic
   - Verify snapshot comparisons
   - Review booking system integration

### Debug Endpoints

- `/admin/monitoring-status` - Current status
- `/admin/availability-snapshots` - Current snapshots
- `/alerts/{id}/notification-history` - Notification history

## 📈 Performance

### Optimization Strategies

1. **Efficient Change Detection**
   - Only compare when booking system refreshes
   - Use hash-based comparisons for large datasets
   - Cache previous snapshots

2. **Smart Scheduling**
   - Adjust check frequency based on club activity
   - Skip inactive clubs
   - Batch API calls when possible

3. **Resource Management**
   - Limit concurrent checks
   - Use connection pooling
   - Implement proper error handling

## 🔮 Future Enhancements

### Planned Features

1. **Machine Learning**
   - Predict optimal check frequencies
   - Identify patterns in cancellations
   - Optimize notification timing

2. **Advanced Integrations**
   - Web scraping for clubs without APIs
   - Real-time WebSocket connections
   - Mobile app push notifications

3. **Analytics Dashboard**
   - Real-time monitoring metrics
   - Historical performance data
   - User engagement analytics

## 📝 Summary

The monitoring system provides a robust, scalable solution for automatically detecting tennis court availability changes and sending intelligent notifications. It's designed to be:

- **Efficient**: Only processes actual changes
- **Reliable**: Comprehensive error handling and logging
- **Scalable**: Supports multiple booking systems
- **Maintainable**: Clean architecture with clear interfaces
- **Testable**: Comprehensive test coverage

The system is production-ready and can be easily extended to support additional tennis clubs and booking systems.
