"""
Rate limiting configuration using slowapi.

Three tiers:
  • strict  – 5/min  (OTP request endpoints – prevents email spam)
  • auth    – 10/min (OTP verify endpoints – prevents brute-force)
  • default – 60/min (everything else)

The limiter keys on client IP by default.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# Named rate strings for use in @limiter.limit() decorators
STRICT = "5/minute"     # OTP request (email sending)
AUTH = "10/minute"       # OTP verification
DEFAULT = "60/minute"    # general API / pages
