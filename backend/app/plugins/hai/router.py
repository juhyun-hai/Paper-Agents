"""
HAI plugin router marker.

The actual ``/api/hai/*`` endpoints currently live in
``backend.app.api.trending`` (``hai_router``) for historical reasons. Rather
than move the endpoint implementations (which would touch a lot of existing
state — see CLAUDE.md: "절대 기존 컬럼 drop / migration 안 함"), this module
*re-exports* that router so the rest of the codebase can treat the plugin as a
single import surface.

To disable the lab routes in a fork, set::

    ENABLE_HAI_PLUGIN=false

before launching the API (handled in ``backend/app/main.py``).
"""

from __future__ import annotations

from ...api.trending import hai_router

#: The FastAPI router exposing ``/api/hai/*`` endpoints. Same object as
#: ``backend.app.api.trending.hai_router``; re-exported here so the plugin
#: gate has a single import path.
router = hai_router

__all__ = ["router", "hai_router"]
