"""Plugin system for optional runners (Playwright built-in, Vanessa add-on)."""

from app.plugins.registry import get_registry, reset_registry

__all__ = ["get_registry", "reset_registry"]
