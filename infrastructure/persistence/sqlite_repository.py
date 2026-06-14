"""Future SQLite repository adapter.

The MVP intentionally uses JSON persistence. This module exists as the stable
extension point for a later SQLite-backed repository without leaking storage
details into API routes or pipeline code.
"""
