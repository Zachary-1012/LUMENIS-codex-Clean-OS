"""LUMENIS local-first AI runtime; advisory only, never Production Truth."""

from .contracts import RuntimeMode
from .service import LocalFirstAIService

__all__ = ["LocalFirstAIService", "RuntimeMode"]
