"""Application update package."""

from app.update.checker import UpdateCheckError, UpdateInfo, check_for_updates
from app.update.installer import apply_update

__all__ = [
    "UpdateCheckError",
    "UpdateInfo",
    "apply_update",
    "check_for_updates",
]
