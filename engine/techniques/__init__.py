"""Technique registry. Importing this package registers all techniques."""

from engine.techniques.base import available_techniques, get_technique  # noqa: F401
from engine.techniques import substitution  # noqa: F401  (registers itself)
from engine.techniques import pseudonymization  # noqa: F401  (registers itself)
from engine.techniques import stubs  # noqa: F401  (Sophie's, register when implemented)
