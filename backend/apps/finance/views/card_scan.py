"""QR card scan resolve endpoint for accountants."""

import json

from django.http import JsonResponse
from django.views import View

from apps.finance.services.card_scan_service import resolve_card_qr_for_finance
from apps.finance.services.exceptions import FinanceError

from .base import FinanceViewMixin


class CardScanResolveView(FinanceViewMixin, View):
    """POST { qr: "KAL-CARD-…" } → JSON with redirect to student situation."""

    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        try:
            self.require_selected_year()
        except FinanceError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)

        raw = ""
        if request.content_type and "application/json" in request.content_type:
            try:
                payload = json.loads(request.body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                payload = {}
            raw = str(payload.get("qr") or payload.get("qr_identifier") or "")
        else:
            raw = request.POST.get("qr") or request.POST.get("qr_identifier") or ""

        try:
            data = resolve_card_qr_for_finance(raw)
        except FinanceError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=404)

        return JsonResponse({"ok": True, "data": data})
