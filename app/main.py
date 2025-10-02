"""Main FastAPI application for Tennis Court Finder."""

from datetime import datetime, date
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.utils import get_openapi
import yaml
import os
import asyncio

from app.models import (
    HealthResponse, ClubsResponse, AvailabilityResponse, 
    SubscriptionRequest, Subscription, Error,
    EnhancedSubscriptionRequest, EnhancedSubscription
)
from app.mock_data import get_mock_clubs, get_mock_availability, get_mock_subscriptions, get_mock_subscription_by_id
from app.services.notification_service import notification_service
from app.services.deduplication_service import deduplication_service
from app.services.monitoring_service import monitoring_service

# Create FastAPI app
app = FastAPI(
    title="Tennis Court Finder API",
    description="API for monitoring tennis court availability and sending alerts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# In-memory storage for subscriptions (in production, use a database)
subscriptions_db = get_mock_subscriptions()
enhanced_subscriptions_db = []


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now()
    )


@app.get("/clubs", response_model=ClubsResponse)
async def get_tennis_clubs():
    """Get available tennis clubs."""
    try:
        clubs = get_mock_clubs()
        return ClubsResponse(clubs=clubs)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve tennis clubs",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/clubs/{club_id}/availability", response_model=AvailabilityResponse)
async def get_club_availability(
    club_id: str,
    date_param: Optional[str] = Query(None, description="Date to check availability (YYYY-MM-DD)")
):
    """Get court availability for a specific club."""
    try:
        # Parse date if provided
        target_date = date.today()
        if date_param:
            try:
                target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=Error(
                        error="validation_error",
                        message="Invalid date format. Use YYYY-MM-DD",
                        details={"provided_date": date_param}
                    ).dict()
                )
        
        # Check if club exists
        clubs = get_mock_clubs()
        club_exists = any(club.id == club_id for club in clubs)
        if not club_exists:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Tennis club not found",
                    details={"club_id": club_id}
                ).dict()
            )
        
        # Get availability data
        availability_data = get_mock_availability(club_id, target_date)
        
        return AvailabilityResponse(
            club_id=club_id,
            availability_date=target_date,
            courts=availability_data["courts"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve court availability",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/subscriptions", response_model=Subscription, status_code=201)
async def create_subscription(subscription_request: SubscriptionRequest):
    """Create a new subscription."""
    try:
        # Validate club exists
        clubs = get_mock_clubs()
        club_exists = any(club.id == subscription_request.club_id for club in clubs)
        if not club_exists:
            raise HTTPException(
                status_code=400,
                detail=Error(
                    error="validation_error",
                    message="Invalid club ID",
                    details={"club_id": subscription_request.club_id}
                ).dict()
            )
        
        # Create new subscription
        new_subscription = Subscription(
            id=f"sub_{len(subscriptions_db) + 1}",
            email=subscription_request.email,
            club_id=subscription_request.club_id,
            preferred_times=subscription_request.preferred_times,
            status="active",
            created_at=datetime.now(),
            last_notification=None
        )
        
        subscriptions_db.append(new_subscription)
        
        return new_subscription
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to create subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/subscriptions/{subscription_id}", response_model=Subscription)
async def get_subscription(subscription_id: str):
    """Get subscription details."""
    try:
        subscription = get_mock_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Subscription not found",
                    details={"subscription_id": subscription_id}
                ).dict()
            )
        
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.delete("/subscriptions/{subscription_id}", status_code=204)
async def cancel_subscription(subscription_id: str):
    """Cancel a subscription."""
    try:
        global subscriptions_db
        subscription = get_mock_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Subscription not found",
                    details={"subscription_id": subscription_id}
                ).dict()
            )
        
        # Remove subscription from database
        subscriptions_db = [sub for sub in subscriptions_db if sub.id != subscription_id]
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to cancel subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/alerts", response_model=EnhancedSubscription, status_code=201)
async def create_enhanced_subscription(subscription_request: EnhancedSubscriptionRequest):
    """Create a new enhanced tennis court alert subscription."""
    try:
        # Validate all clubs exist
        clubs = get_mock_clubs()
        club_ids = {club.id for club in clubs}
        
        for club_pref in subscription_request.club_preferences:
            if club_pref.club_id not in club_ids:
                raise HTTPException(
                    status_code=400,
                    detail=Error(
                        error="validation_error",
                        message="Invalid club ID",
                        details={"club_id": club_pref.club_id}
                    ).dict()
                )
            
            # Validate court IDs for each club
            club = next(club for club in clubs if club.id == club_pref.club_id)
            valid_court_ids = {court.id for court in club.courts}
            
            for court_id in club_pref.court_ids:
                if court_id not in valid_court_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=Error(
                            error="validation_error",
                            message="Invalid court ID for club",
                            details={"club_id": club_pref.club_id, "court_id": court_id}
                        ).dict()
                    )
        
        # Set default expiry date if not provided
        alert_prefs = subscription_request.alert_preferences
        if alert_prefs.expiry_date is None:
            from datetime import timedelta
            alert_prefs.expiry_date = (datetime.now() + timedelta(days=365)).date()
        
        # Create new enhanced subscription
        new_subscription = EnhancedSubscription(
            id=f"alert_{len(enhanced_subscriptions_db) + 1}",
            email=subscription_request.email,
            club_preferences=subscription_request.club_preferences,
            preferred_times=subscription_request.preferred_times,
            alert_preferences=alert_prefs,
            notification_preferences=subscription_request.notification_preferences,
            status="active",
            created_at=datetime.now(),
            last_notification=None,
            next_check=datetime.now()  # Will be updated by the monitoring service
        )
        
        enhanced_subscriptions_db.append(new_subscription)
        
        # Send confirmation email
        await notification_service.send_subscription_confirmation(new_subscription)
        
        return new_subscription
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to create alert subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/alerts/{alert_id}", response_model=EnhancedSubscription)
async def get_enhanced_subscription(alert_id: str):
    """Get enhanced subscription details."""
    try:
        subscription = next((sub for sub in enhanced_subscriptions_db if sub.id == alert_id), None)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Alert subscription not found",
                    details={"alert_id": alert_id}
                ).dict()
            )
        
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve alert subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.delete("/alerts/{alert_id}", status_code=204)
async def cancel_enhanced_subscription(alert_id: str):
    """Cancel an enhanced subscription."""
    try:
        global enhanced_subscriptions_db
        subscription = next((sub for sub in enhanced_subscriptions_db if sub.id == alert_id), None)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Alert subscription not found",
                    details={"alert_id": alert_id}
                ).dict()
            )
        
        # Send cancellation email
        await notification_service.send_subscription_cancelled(subscription)
        
        # Remove subscription from database
        enhanced_subscriptions_db = [sub for sub in enhanced_subscriptions_db if sub.id != alert_id]
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to cancel alert subscription",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/clubs/{club_id}/courts")
async def get_club_courts(club_id: str):
    """Get available courts for a specific club."""
    try:
        clubs = get_mock_clubs()
        club = next((club for club in clubs if club.id == club_id), None)
        
        if not club:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Tennis club not found",
                    details={"club_id": club_id}
                ).dict()
            )
        
        return {
            "club_id": club_id,
            "club_name": club.name,
            "courts": [
                {
                    "id": court.id,
                    "name": court.name,
                    "surface": court.surface,
                    "indoor": court.indoor
                }
                for court in club.courts
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve club courts",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/alerts/{alert_id}/test-notification")
async def test_alert_notification(alert_id: str):
    """Test sending a notification for an alert (for testing deduplication)."""
    try:
        subscription = next((sub for sub in enhanced_subscriptions_db if sub.id == alert_id), None)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Alert subscription not found",
                    details={"alert_id": alert_id}
                ).dict()
            )
        
        # Get some mock availability data
        mock_courts = []
        for club_pref in subscription.club_preferences:
            availability_data = get_mock_availability(club_pref.club_id)
            mock_courts.extend(availability_data["courts"])
        
        # Send notification (this will use deduplication)
        success = await notification_service.send_availability_alert(subscription, mock_courts)
        
        if success:
            return {
                "message": "Test notification sent successfully",
                "alert_id": alert_id,
                "deduplication_applied": True
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=Error(
                    error="notification_failed",
                    message="Failed to send test notification"
                ).dict()
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to send test notification",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/alerts/{alert_id}/notification-history")
async def get_notification_history(alert_id: str):
    """Get notification history for a specific alert."""
    try:
        subscription = next((sub for sub in enhanced_subscriptions_db if sub.id == alert_id), None)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=Error(
                    error="not_found",
                    message="Alert subscription not found",
                    details={"alert_id": alert_id}
                ).dict()
            )
        
        history = deduplication_service.get_notification_history(alert_id)
        return {
            "alert_id": alert_id,
            "total_notifications": len(history),
            "notifications": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve notification history",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/admin/deduplication-stats")
async def get_deduplication_stats():
    """Get deduplication service statistics (admin endpoint)."""
    try:
        stats = deduplication_service.get_stats()
        return {
            "deduplication_stats": stats,
            "service_status": "active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to retrieve deduplication stats",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/admin/cleanup-notifications")
async def cleanup_old_notifications(days_to_keep: int = 30):
    """Clean up old notification records (admin endpoint)."""
    try:
        deduplication_service.cleanup_old_notifications(days_to_keep)
        return {
            "message": f"Cleaned up notifications older than {days_to_keep} days",
            "days_to_keep": days_to_keep
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to cleanup notifications",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/admin/start-monitoring")
async def start_monitoring():
    """Start the court availability monitoring service."""
    try:
        if monitoring_service.is_running:
            return {
                "message": "Monitoring is already running",
                "status": "running",
                "check_interval_minutes": monitoring_service.check_interval_minutes
            }
        
        # Start monitoring with all active subscriptions
        active_subscriptions = [
            sub for sub in enhanced_subscriptions_db 
            if sub.status == "active"
        ]
        
        # Start monitoring in background
        asyncio.create_task(monitoring_service.start_monitoring(active_subscriptions))
        
        return {
            "message": "Monitoring started successfully",
            "status": "started",
            "check_interval_minutes": monitoring_service.check_interval_minutes,
            "active_subscriptions": len(active_subscriptions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to start monitoring",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/admin/stop-monitoring")
async def stop_monitoring():
    """Stop the court availability monitoring service."""
    try:
        await monitoring_service.stop_monitoring()
        
        return {
            "message": "Monitoring stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to stop monitoring",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/admin/monitoring-status")
async def get_monitoring_status():
    """Get the current monitoring service status."""
    try:
        stats = monitoring_service.get_stats()
        
        return {
            "is_running": monitoring_service.is_running,
            "check_interval_minutes": monitoring_service.check_interval_minutes,
            "stats": {
                "total_checks": stats.total_checks,
                "successful_checks": stats.successful_checks,
                "failed_checks": stats.failed_checks,
                "notifications_sent": stats.notifications_sent,
                "last_check_time": stats.last_check_time,
                "clubs_monitored": list(stats.clubs_monitored),
                "recent_errors": stats.errors[-5:] if stats.errors else []
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to get monitoring status",
                details={"exception": str(e)}
            ).dict()
        )


@app.post("/admin/trigger-manual-check")
async def trigger_manual_check():
    """Manually trigger a court availability check."""
    try:
        # Get active subscriptions
        active_subscriptions = [
            sub for sub in enhanced_subscriptions_db 
            if sub.status == "active"
        ]
        
        # Trigger manual check
        await monitoring_service._check_all_subscriptions(active_subscriptions)
        
        return {
            "message": "Manual check completed",
            "active_subscriptions_checked": len(active_subscriptions),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to trigger manual check",
                details={"exception": str(e)}
            ).dict()
        )


@app.get("/admin/availability-snapshots")
async def get_availability_snapshots():
    """Get current availability snapshots (for debugging)."""
    try:
        snapshots = monitoring_service.get_previous_snapshots()
        
        result = {}
        for club_id, snapshot in snapshots.items():
            result[club_id] = {
                "club_id": snapshot.club_id,
                "date": snapshot.date.isoformat(),
                "timestamp": snapshot.timestamp.isoformat(),
                "last_refresh_time": snapshot.last_refresh_time.isoformat() if snapshot.last_refresh_time else None,
                "courts_count": len(snapshot.courts),
                "courts": [
                    {
                        "court_id": court.court_id,
                        "court_name": court.court_name,
                        "available_slots": len([slot for slot in court.time_slots if slot.available])
                    }
                    for court in snapshot.courts
                ]
            }
        
        return {
            "snapshots": result,
            "total_clubs": len(snapshots)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=Error(
                error="internal_error",
                message="Failed to get availability snapshots",
                details={"exception": str(e)}
            ).dict()
        )


def custom_openapi():
    """Generate OpenAPI schema from YAML file."""
    if app.openapi_schema:
        return app.openapi_schema
    
    # Load OpenAPI spec from YAML file
    openapi_yaml_path = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")
    try:
        with open(openapi_yaml_path, 'r') as f:
            openapi_spec = yaml.safe_load(f)
        
        # Use the YAML spec as the base
        app.openapi_schema = openapi_spec
        return app.openapi_schema
    except FileNotFoundError:
        # Fallback to auto-generated schema
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
