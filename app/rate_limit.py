from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

STRICT = "5/minute"  # OTP request (email sending)
AUTH = "10/minute"  # OTP verification
DEFAULT = "60/minute"  # general API / pages
