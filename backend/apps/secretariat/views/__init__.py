"""Public secretariat web views."""

from .academic_years import (
    AcademicYearActionView,
    AcademicYearCreateView,
    AcademicYearDeclareCloseView,
    AcademicYearDeleteView,
    AcademicYearListView,
    AcademicYearUpdateView,
)
from .cards import (
    CardBlockView,
    CardGenerateView,
    CardListView,
    CardPngDownloadView,
    CardPreviewView,
    ClassCardsZipDownloadView,
)
from .class_enrollments import (
    ClassBulkReenrollmentView,
    ClassInscriptionView,
    ClassReenrollmentView,
    GuardianPhoneLookupView,
)
from .classes import (
    ClassActionView,
    ClassCreateView,
    ClassDetailView,
    ClassListView,
    ClassUpdateView,
)
from .communications import (
    CommunicationArchiveView,
    CommunicationClassStudentsView,
    CommunicationCreateView,
    CommunicationDeleteView,
    CommunicationDetailView,
    CommunicationListView,
    CommunicationPinView,
    CommunicationPublishView,
    CommunicationRestoreView,
    CommunicationUnpinView,
    CommunicationUpdateView,
)
from .dashboard import DashboardView
from .documents import DocumentDownloadView, DocumentListView, DocumentVerifyView
from .enrollments import (
    BulkReenrollmentView,
    EnrollmentCreateView,
    EnrollmentListView,
    ReenrollmentView,
    TransferView,
)
from .exports import ExportView
from .fee_approvals import (
    FeeAmountChangeApproveView,
    FeeAmountChangeDetailView,
    FeeAmountChangeRejectView,
    FeeApprovalDetailView,
    FeeApprovalListView,
    FeeApproveView,
    FeeRejectView,
)
from .guardians import (
    GuardianArchiveView,
    GuardianDetailView,
    GuardianListView,
    GuardianRestoreView,
    GuardianUpdateView,
)
from .organization import (
    LevelActionView,
    OptionActionView,
    OrganizationView,
    SectionActionView,
)
from .students import (
    StudentArchiveView,
    StudentCreateView,
    StudentDeleteView,
    StudentDetailView,
    StudentListView,
    StudentRestoreView,
    StudentUpdateView,
)
from .year_select import AcademicYearChangeView, AcademicYearChooseView, AcademicYearSelectView

__all__ = [name for name in globals() if name.endswith("View")]
