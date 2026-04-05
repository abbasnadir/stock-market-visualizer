"""Common operation result model used across services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OperationResult:
    """Structured result object used by service and repository methods."""

    success: bool
    message: str
    data: Any = None
