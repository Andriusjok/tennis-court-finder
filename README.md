# Tennis Court Finder

A Python-based application that monitors tennis court availability across integrated booking systems and sends real-time alerts to users when requested court times become available.

## Getting Started

### Prerequisites
- **mise**: Development environment manager
- **Poetry**: Python dependency management
- **Python 3.8+**: Managed via mise

### Local Development Setup

1. **Install mise**
   ```bash
   # macOS
   brew install mise
   
   # Or visit https://mise.jdx.dev/ for other installation methods
   ```

2. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tennis-court-finder
   ```

3. **Set up Python environment with mise**
   ```bash
   mise install
   # This will install the Python version specified in .mise.toml
   ```

4. **Install dependencies with Poetry**
   ```bash
   poetry install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run the application**
   ```bash
   poetry run python main.py
   ```

7. **Access the API**
   - API documentation: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`

## Architecture

The application follows a decoupled architecture with clear separation of concerns:

### Core Interfaces

#### Notification System
- **Interface**: `NotificationService`
- **Purpose**: Handles user alerts when court availability changes
- **Available Implementations**:
  - Email notifications

#### Tennis Club Integration
- **Interface**: `TennisClubService`
- **Purpose**: Manages integration with tennis club booking systems
- **Available Implementations**:
  - TBD (to be implemented)

### API Endpoints

The application exposes RESTful APIs for:

- **User Subscriptions**: Subscribe to court availability alerts
- **Club Management**: View available tennis clubs and their booking systems
- **Time Slots**: Query and monitor available court times

### Key Components

- **Booking Monitor**: Continuously monitors court availability
- **Alert Engine**: Processes availability changes and triggers notifications
- **API Gateway**: RESTful interface for external integrations
- **Configuration Management**: Environment-based configuration system

## API Development

### OpenAPI-First Design

The API is designed using an OpenAPI-first approach:

1. **Specification**: `openapi.yaml` defines the complete API contract
2. **Implementation**: FastAPI application matches the specification
3. **Validation**: Server generation script ensures consistency

### Available Endpoints

- `GET /health` - Health check
- `GET /clubs` - List available tennis clubs
- `GET /clubs/{club_id}/availability` - Get court availability for a club
- `POST /subscriptions` - Create a new subscription
- `GET /subscriptions/{subscription_id}` - Get subscription details
- `DELETE /subscriptions/{subscription_id}` - Cancel a subscription

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Server Generation

Validate API consistency between specification and implementation:

```bash
poetry run python scripts/generate_server.py
```

This script:
- Loads the OpenAPI specification
- Validates the schema structure
- Checks endpoint consistency
- Reports any mismatches between spec and implementation
