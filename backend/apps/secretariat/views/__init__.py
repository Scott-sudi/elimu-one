"""Public secretariat web views."""

from .academic_years import AcademicYearActionView, AcademicYearCreateView, AcademicYearListView
from .cards import CardBlockView, CardGenerateView, CardListView, CardPreviewView
from .classes import ClassCreateView, ClassDetailView, ClassListView
from .communications import CommunicationCreateView, CommunicationDetailView, CommunicationListView, CommunicationPublishView
from .dashboard import DashboardView
from .documents import DocumentDownloadView, DocumentListView, DocumentVerifyView
from .enrollments import BulkReenrollmentView, EnrollmentCreateView, EnrollmentListView, ReenrollmentView, TransferView
from .exports import ExportView
from .guardians import GuardianDetailView, GuardianListView
from .organization import OrganizationView
from .students import StudentArchiveView, StudentCreateView, StudentDetailView, StudentListView, StudentUpdateView

__all__ = [name for name in globals() if name.endswith("View")]
