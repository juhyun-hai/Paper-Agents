"""
HAI Lab (Hyperautonomy AI Lab, Seoul National University) plugin.

This package is an isolation layer for all lab-specific behavior so that a
fork can disable it via the ``ENABLE_HAI_PLUGIN=false`` environment variable
without touching the database schema or core ingestion code.

Public surface:
- ``config``  — keyword/member lists + matching helpers (copy of
  ``backend.app.core.hai_config``; the legacy module is preserved for
  backward compatibility and currently still consumed by daily_cron and
  trending routes).
- ``scoring`` — pure ``compute_hai_bonus(...)`` extracted from the
  featured_score v4 formula.
- ``router``  — thin marker that re-exports the FastAPI router defined in
  ``backend.app.api.trending`` so plugin enable/disable lives in one place.
"""

from . import config, scoring, router  # noqa: F401

__all__ = ["config", "scoring", "router"]
