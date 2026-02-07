"""
Application configuration from environment variables.

All settings have sensible defaults for local development.
A .env file in the project root is loaded automatically (if present).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file before reading any env vars
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Environment ───────────────────────────────────────────────────────────

ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

# ── Paths ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# SQLite database file
DB_PATH: str = os.getenv("DB_PATH", str(DATA_DIR / "tennis_court_finder.db"))

# ── JWT ───────────────────────────────────────────────────────────────────

JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_DAYS: int = int(os.getenv("JWT_EXPIRY_DAYS", "7"))

# ── SMTP ──────────────────────────────────────────────────────────────────

SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@tenniscourtfinder.local")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def smtp_enabled() -> bool:
    """True when SMTP credentials are fully configured."""
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)


# ── Notifier ──────────────────────────────────────────────────────────────

# How often the notifier checks for slot transitions (seconds).
NOTIFIER_INTERVAL: float = float(os.getenv("NOTIFIER_INTERVAL", "60"))

# Minimum seconds between two emails for the *same* subscription.
NOTIFIER_COOLDOWN: float = float(os.getenv("NOTIFIER_COOLDOWN", "300"))
