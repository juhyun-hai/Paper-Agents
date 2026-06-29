"""
Plugins package — lab-specific or deployment-specific extensions.

Each subpackage (e.g. `hai`) is intended to be optional. Disabling a plugin
should never break the core arXiv ingestion / summarization pipeline.

Toggles are read by ``backend.app.main`` from environment variables:

- ``ENABLE_HAI_PLUGIN`` (default: ``true``) — HAI Lab (SNU) curation routes.

See ``docs/PLUGIN_HAI.md`` for fork-friendly instructions on isolating or
removing lab-specific behavior.
"""
