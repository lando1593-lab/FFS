"""Stable identifiers. ULIDs sort by creation time and never collide in practice."""

from ulid import ULID


def new_id(prefix: str = "") -> str:
    """Return a new ULID string, optionally prefixed (e.g. ``mem_01H...``)."""
    u = str(ULID())
    return f"{prefix}_{u}" if prefix else u
