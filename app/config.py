from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH: str = os.getenv("DB_PATH", str(DATA_DIR / "tennis_court_finder.db"))

JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_DAYS: int = int(os.getenv("JWT_EXPIRY_DAYS", "7"))

SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@tenniscourtfinder.local")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# "auto" (default) = send if credentials configured; "true"/"false" = force
_SMTP_ENABLED_OVERRIDE: str = os.getenv("SMTP_ENABLED", "auto")


def smtp_enabled() -> bool:
    if _SMTP_ENABLED_OVERRIDE.lower() == "false":
        return False
    if _SMTP_ENABLED_OVERRIDE.lower() == "true":
        return True
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)


NOTIFIER_INTERVAL: float = float(os.getenv("NOTIFIER_INTERVAL", "60"))
NOTIFIER_COOLDOWN: float = float(os.getenv("NOTIFIER_COOLDOWN", "300"))
