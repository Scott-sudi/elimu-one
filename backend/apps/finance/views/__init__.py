"""Public finance web views."""

from .arrears import ArrearsListView
from .card_scan import CardScanResolveView
from .classes import (
    ClassFeeAmountChangeView,
    ClassListView,
    ClassOtherFeeCreateView,
    ClassSituationView,
)
from .dashboard import DashboardView
from .fees import (
    FeeArchiveView,
    FeeCreateView,
    FeeDetailView,
    FeeListView,
    FeeRequestsListView,
    FeeRequestsRedirectView,
    FeeSubmitView,
    FeeWithdrawView,
)
from .payments import (
    PaymentCancelView,
    PaymentCreateView,
    PaymentDetailView,
    PaymentListView,
    PaymentMatriculeLookupView,
)
from .receipts import ReceiptDetailView, ReceiptListView, ReceiptPDFView
from .reports import ArrearsExportView, PaymentsPeriodExportView, ReportsIndexView
from .students import StudentSearchView, StudentSituationView

__all__ = [name for name in globals() if name.endswith("View")]
