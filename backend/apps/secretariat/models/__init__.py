"""Public model exports for the secretariat application."""

from __future__ import annotations

from .academic import AcademicYear, Option, SchoolClass, SchoolLevel, Section
from .card import StudentCard
from .communication import (
    Communication,
    CommunicationReceipt,
    CommunicationTarget,
)
from .document import DocumentType, StudentDocument
from .enrollment import ClassTransfer, Enrollment
from .guardian import Guardian, StudentGuardian
from .settings import SecretariatSetting
from .student import Student

__all__ = [
    "AcademicYear",
    "ClassTransfer",
    "Communication",
    "CommunicationReceipt",
    "CommunicationTarget",
    "DocumentType",
    "Enrollment",
    "Guardian",
    "Option",
    "SchoolClass",
    "SchoolLevel",
    "Section",
    "SecretariatSetting",
    "Student",
    "StudentCard",
    "StudentDocument",
    "StudentGuardian",
]
