"""Main FastAPI application for Tennis Court Finder."""

from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import yaml
import os

from app.models import (
    HealthResponse, ClubsResponse, AvailabilityResponse, 
    SubscriptionRequest, Subscription, Error
)
from app.mock_data import get_mock_clubs, get_mock_availability, get_mock_subscriptions, get_mock_subscription_by_id

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
