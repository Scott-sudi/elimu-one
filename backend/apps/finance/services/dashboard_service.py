"""Dashboard helpers for the finance module.

Thin re-exports from situation_service for a dedicated import path.
"""

from __future__ import annotations

from apps.finance.services.situation_service import (
    arrears_queryset,
    class_situation_matrix,
    dashboard_stats,
    student_situation,
)

__all__ = [
    "arrears_queryset",
    "class_situation_matrix",
    "dashboard_stats",
    "student_situation",
]
