"""Importer ce paquet enregistre les modules RH dans REGISTRY."""

from app.core.modules import effectifs  # noqa: F401
from app.core.modules.base import REGISTRY, Context, Module

__all__ = ["REGISTRY", "Context", "Module"]
