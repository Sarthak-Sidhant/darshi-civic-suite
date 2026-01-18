"""
LEGACY DATABASE SERVICE (FIREBASE) - DEPRECATED

This module was originally used for Firebase/Firestore operations.
It has been superseded by `app.services.postgres_service`.

DO NOT USE THIS MODULE.
Use `app.services.postgres_service` for all database interactions.
"""

from app.core.exceptions import DatabaseError

def _raise_deprecation_error():
    raise NotImplementedError(
        "This service is deprecated. Please use app.services.postgres_service instead."
    )

def create_report(*args, **kwargs):
    _raise_deprecation_error()

def get_reports(*args, **kwargs):
    _raise_deprecation_error()

def get_report_by_id(*args, **kwargs):
    _raise_deprecation_error()

# ... (stubbing other functions not strictly necessary if unused)
