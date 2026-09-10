"""Compatibility location for the audio routing adapter.

The implementation remains in ``app.router`` for now so existing imports and
external integrations keep working while the package boundary is introduced.
"""

from ...router import AudioRouter

__all__ = ["AudioRouter"]
