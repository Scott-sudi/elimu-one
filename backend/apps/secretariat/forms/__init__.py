"""Forms for the secretariat web interface."""

from .academic import AcademicYearForm, OptionForm, SchoolLevelForm, SectionForm
from .class_forms import SchoolClassForm, SchoolClassUpdateForm
from .communication import CommunicationForm, CommunicationPublishForm
from .document import DocumentTypeForm, StudentDocumentForm
from .enrollment import (
    ClassNewStudentForm,
    ClassReenrollmentForm,
    EnrollmentForm,
    ReenrollmentForm,
    TransferForm,
)
from .guardian import GuardianForm, StudentGuardianForm
from .student import StudentForm

__all__ = [
    "AcademicYearForm", "ClassNewStudentForm",
    "ClassReenrollmentForm", "CommunicationForm", "CommunicationPublishForm",
    "DocumentTypeForm", "EnrollmentForm",
    "GuardianForm", "OptionForm", "ReenrollmentForm", "SchoolClassForm",
    "SchoolClassUpdateForm", "SchoolLevelForm", "SectionForm", "StudentDocumentForm",
    "StudentForm", "StudentGuardianForm", "TransferForm",
]
