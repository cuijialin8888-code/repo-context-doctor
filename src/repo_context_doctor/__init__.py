"""Repo Context Doctor public package."""

from repo_context_doctor.models import TOOL_VERSION
from repo_context_doctor.scanner import scan_repository

__all__ = ["TOOL_VERSION", "scan_repository"]
__version__ = TOOL_VERSION
