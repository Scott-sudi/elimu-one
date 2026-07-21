"""Forms for the secretariat web interface."""

from .academic import AcademicYearForm, OptionForm, SchoolLevelForm, SectionForm
from .class_forms import SchoolClassForm
from .communication import CommunicationForm
from .document import DocumentTypeForm, StudentDocumentForm
from .enrollment import EnrollmentForm, ReenrollmentForm, TransferForm
from .guardian import GuardianForm, StudentGuardianForm
from .student import StudentForm

__all__ = [
    "AcademicYearForm", "CommunicationForm", "DocumentTypeForm", "EnrollmentForm",
    "GuardianForm", "OptionForm", "ReenrollmentForm", "SchoolClassForm",
    "SchoolLevelForm", "SectionForm", "StudentDocumentForm", "StudentForm",
    "StudentGuardianForm", "TransferForm",
]
