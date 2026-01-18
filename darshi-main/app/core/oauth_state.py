"""
OAuth State Management for CSRF Protection

This module provides secure state parameter generation and validation
for OAuth flows to prevent authorization code interception attacks.
"""

import secrets
import time
from typing import Optional, Tuple
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# In-memory state storage (for MVP)
# In production, use Redis with TTL or database with expiration
_state_store = {}
_STATE_TTL_SECONDS = 300  # 5 minutes


def generate_state() -> str:
    """
    Generate a cryptographically secure random state parameter.

    Returns:
        Random 32-character URL-safe string
    """
    state = secrets.token_urlsafe(32)
    timestamp = time.time()

    # Store state with timestamp for validation
    _state_store[state] = {
        "timestamp": timestamp,
        "used": False
    }

    logger.debug(f"Generated OAuth state: {state[:8]}...")
    return state


def validate_state(state: str) -> Tuple[bool, Optional[str]]:
    """
    Validate OAuth state parameter.

    Args:
        state: State parameter received from OAuth callback

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    if not state:
        return False, "Missing state parameter"

    # Check if state exists in store
    state_data = _state_store.get(state)
    if not state_data:
        logger.warning(f"Invalid OAuth state: {state[:8]}... (not found in store)")
        return False, "Invalid or expired state parameter"

    # Check if state already used (replay attack)
    if state_data.get("used"):
        logger.warning(f"OAuth state reuse attempt: {state[:8]}...")
        return False, "State parameter already used"

    # Check if state expired
    timestamp = state_data.get("timestamp", 0)
    if time.time() - timestamp > _STATE_TTL_SECONDS:
        logger.warning(f"OAuth state expired: {state[:8]}... (age: {time.time() - timestamp:.1f}s)")
        _state_store.pop(state, None)  # Clean up expired state
        return False, "State parameter expired"

    # Mark state as used (one-time use only)
    state_data["used"] = True

    logger.debug(f"OAuth state validated successfully: {state[:8]}...")
    return True, None


def cleanup_expired_states():
    """
    Remove expired states from store to prevent memory leaks.
    Should be called periodically (e.g., via background task).
    """
    now = time.time()
    expired_states = [
        state for state, data in _state_store.items()
        if now - data.get("timestamp", 0) > _STATE_TTL_SECONDS
    ]

    for state in expired_states:
        _state_store.pop(state, None)

    if expired_states:
        logger.debug(f"Cleaned up {len(expired_states)} expired OAuth states")

    return len(expired_states)


def get_store_size() -> int:
    """
    Get current size of state store (for monitoring).

    Returns:
        Number of states in store
    """
    return len(_state_store)
