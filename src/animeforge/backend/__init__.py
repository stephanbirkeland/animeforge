"""AI generation backends."""

from animeforge.backend.base import GenerationBackend, GenerationRequest, GenerationResult
from animeforge.backend.fal_backend import FalBackend
from animeforge.backend.mock import MockBackend

__all__ = [
    "FalBackend",
    "GenerationBackend",
    "GenerationRequest",
    "GenerationResult",
    "MockBackend",
]
