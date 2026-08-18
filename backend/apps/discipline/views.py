"""Discipline web views."""

import csv
import json
from datetime import datetime
from io import StringIO

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import DisciplineRequiredMixin
from apps.discipline.forms import (
    AttendanceRecordCorrectionForm,
    ClassFilterForm,
    DailyAttendanceFilterForm,
    ExitAuthorizationForm,
    FolderFilterForm,
    IncidentFilterForm,
    IncidentForm,
    ManualAttendanceForm,
    MeasureForm,
    QrPointageForm,
    StudentFilterForm,
    SummonsForm,
    VacationScheduleForm,
)
from apps.discipline.models import (
    AbsenceJustification,
    AttendanceScanEvent,
    AttendanceSchedule,
    ClassAttendanceSheet,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ExitAuthorization,
    ParentSummons,
)
from apps.discipline.services.class_attendance_service import (
    auto_close_elapsed_sheets,
    correct_validated_record,
    get_or_create_sheet,
    recompute_sheet_totals,
    save_sheet_draft,
    validate_sheet,
)
from apps.discipline.services.disciplinary_file_service import build_student_disciplinary_file
from apps.discipline.services.disciplinary_file_pdf_service import build_disciplinary_file_pdf
from apps.discipline.services.exceptions import DisciplineError
from apps.discipline.services.attendance_service import (
    register_identifier_pointage,
    register_manual_attendance,
    register_qr_pointage,
)
from apps.discipline.services.schedule_service import (
    build_vacation_form_initial,
    save_vacation_schedule,
)
from apps.discipline.services.student_identity_service import resolve_student_identity
from django.conf import settings
from apps.secretariat.models import Enrollment, Option, SchoolClass, SchoolLevel
from apps.secretariat.services.year_context import year_context_service


class DisciplineAcademicYearRequiredMixin:
    """Require a selected academic year for discipline pages."""

    academic_year_required = True

    def dispatch(self, request, *args, **kwargs):
        if self.academic_year_required and not year_context_service.has_session_year(request):
            return self._redirect_to_year_select()
        selected_year = year_context_service.get_selected_year(request)
        if selected_year is not None:
            try:
                auto_close_elapsed_sheets(
                    academic_year=selected_year,
                    actor=request.user if request.user.is_authenticated else None,
                    request=request,
                )
            except Exception:
                # Ne bloque pas la navigation en cas d'échec ponctuel.
                pass
        return super().dispatch(request, *args, **kwargs)

    def _redirect_to_year_select(self):
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.info(
            self.request,
            "Choisissez une année scolaire avant d'accéder à la discipline.",
        )
        return redirect("secretariat:academic-year-select")

    def require_selected_year(self):
        from apps.discipline.services.exceptions import DisciplineError

        try:
            return year_context_service.require_selected_year(self.request)
        except Exception as exc:
            raise DisciplineError(str(exc)) from exc


class DisciplineViewMixin(
    DisciplineRequiredMixin,
    DisciplineAcademicYearRequiredMixin,
):
    """Base gate for discipline pages."""


class DisciplinePageView(DisciplineViewMixin, TemplateView):
    """Simple routed page shell for module foundation."""

    template_name = "discipline/page.html"
    page_title = "Discipline"
    breadcrumb_tail = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        context.update(
            page_title=self.page_title,
            selected_year=year,
            year_writable=not year.is_closed,
            breadcrumbs=[
                ("Discipline", reverse("discipline:dashboard")),
                (self.breadcrumb_tail or self.page_title, None),
            ],
        )
        return context


class DashboardView(DisciplinePageView):
    template_name = "discipline/dashboard/index.html"
    page_title = "Tableau de bord"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        today = datetime.now().date()
        today_qs = DailyAttendance.objects.filter(academic_year=year, date=today)
        stats = {
            "present": today_qs.filter(status=DailyAttendance.Status.PRESENT).count(),
            "late": today_qs.filter(status=DailyAttendance.Status.LATE).count(),
            "absent": today_qs.filter(status=DailyAttendance.Status.ABSENT).count(),
            "authorized_exit": today_qs.filter(status=DailyAttendance.Status.AUTHORIZED_EXIT).count(),
            "scan_events_today": AttendanceScanEvent.objects.filter(
                academic_year=year,
                scanned_at__date=today,
                result=AttendanceScanEvent.Result.SUCCESS,
            ).count(),
        }
        recent_scans = (
            AttendanceScanEvent.objects.filter(academic_year=year)
            .select_related("student", "enrollment__school_class")
            .order_by("-scanned_at")[:10]
        )
        context.update(stats=stats, recent_scans=recent_scans)
        return context


class AttendanceSchedulesView(DisciplinePageView):
    """Configure morning / afternoon attendance windows and class assignment."""

    template_name = "discipline/schedules/index.html"
    page_title = "Horaires"
    breadcrumb_tail = "Horaires"

    def _forms(self, year, data=None, vacation=None):
        forms = {}
        for vac in (AttendanceSchedule.Vacation.MORNING, AttendanceSchedule.Vacation.AFTERNOON):
            initial = build_vacation_form_initial(academic_year=year, vacation=vac)
            if data is not None and vacation == vac:
                forms[vac] = VacationScheduleForm(data, academic_year=year, prefix=vac)
            else:
                forms[vac] = VacationScheduleForm(academic_year=year, prefix=vac, initial=initial)
        return forms

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        forms = kwargs.get("forms") or self._forms(year)
        context.update(
            morning_form=forms[AttendanceSchedule.Vacation.MORNING],
            afternoon_form=forms[AttendanceSchedule.Vacation.AFTERNOON],
            vacation_labels={
                AttendanceSchedule.Vacation.MORNING: "Avant-midi",
                AttendanceSchedule.Vacation.AFTERNOON: "Après-midi",
            },
        )
        return context

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        if year.is_closed:
            messages.error(request, "Année scolaire clôturée — consultation uniquement.")
            return redirect("discipline:schedules")
        vacation = (request.POST.get("vacation") or "").strip()
        if vacation not in AttendanceSchedule.Vacation.values:
            messages.error(request, "Vacation invalide.")
            return redirect("discipline:schedules")
        forms = self._forms(year, data=request.POST, vacation=vacation)
        form = forms[vacation]
        if not form.is_valid():
            messages.error(request, "Vérifiez les horaires saisis.")
            return self.render_to_response(self.get_context_data(forms=forms))
        try:
            save_vacation_schedule(
                academic_year=year,
                vacation=form.cleaned_data["vacation"],
                start_time=form.cleaned_data["start_time"],
                present_until=form.cleaned_data["present_until"],
                end_time=form.cleaned_data["end_time"],
                school_classes=form.cleaned_data["school_classes"],
                actor=request.user,
                request=request,
            )
        except DisciplineError as exc:
            messages.error(request, str(exc))
            return self.render_to_response(self.get_context_data(forms=forms))
        label = dict(AttendanceSchedule.Vacation.choices).get(vacation, vacation)
        messages.success(request, f"Horaire {label} enregistré.")
        return redirect("discipline:schedules")


class AttendanceScanView(DisciplinePageView):
    """Legacy URL — pointage is available from Présences du jour."""

    page_title = "Pointage"

    def get(self, request, *args, **kwargs):
        params = request.GET.copy()
        if not params.get("open") and params.get("mode") == "conduct":
            params["open"] = "1"
        target = reverse("discipline:attendance-daily")
        query = params.urlencode()
        if query:
            target = f"{target}?{query}"
        return redirect(target)


class DailyAttendanceView(DisciplinePageView):
    template_name = "discipline/attendance/daily.html"
    partial_template_name = "discipline/attendance/_table.html"
    page_title = "Présences du jour"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        form = DailyAttendanceFilterForm(self.request.GET)
        form.is_valid()
        target_date = form.cleaned_data.get("date") if form.is_bound else None
        target_date = target_date or datetime.now().date()

        qs = DailyAttendance.objects.filter(academic_year=year, date=target_date).select_related(
            "student",
            "enrollment__school_class",
        )

        q = (form.cleaned_data.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(student__postnom__icontains=q)
                | Q(student__prenom__icontains=q)
            )

        class_id = form.cleaned_data.get("school_class")
        if class_id:
            qs = qs.filter(enrollment__school_class__public_id=class_id)

        status = form.cleaned_data.get("status")
        if status:
            qs = qs.filter(status=status)

        mode = (self.request.GET.get("mode") or "attendance").strip().lower()
        if mode not in {"attendance", "conduct"}:
            mode = "attendance"

        class_choices = form.class_queryset(year)
        from apps.discipline.models import AttendanceSchedule

        has_schedules = AttendanceSchedule.objects.filter(
            academic_year=year,
            is_active=True,
            is_archived=False,
        ).exists()
        context.update(
            attendances=qs.order_by("enrollment__school_class__name", "student__nom", "student__prenom"),
            classes=class_choices,
            has_attendance_schedules=has_schedules,
            filters={
                "q": form.cleaned_data.get("q", "") if form.is_bound else "",
                "school_class": str(class_id) if class_id else "",
                "status": status or "",
                "date": target_date.isoformat(),
            },
            daily_summary=qs.values("status").annotate(total=Count("id")),
            default_scanner_mode=mode,
            auto_open_scanner=self.request.GET.get("open") == "1" or mode == "conduct",
        )
        return context


class AttendanceScanSubmitView(DisciplineViewMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        form = QrPointageForm(request.POST if request.POST else None)
        if not form.is_valid():
            return JsonResponse({"ok": False, "error": "QR ou opération invalide."}, status=400)
        try:
            result = register_qr_pointage(
                academic_year=year,
                qr_payload=form.cleaned_data["qr"],
                operation=form.cleaned_data.get("operation") or "arrivee",
                actor=request.user,
                request=request,
            )
        except Exception as exc:  # noqa: BLE001
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "data": {
                    "message": result.message,
                    "student_name": result.student_name,
                    "matricule": result.matricule,
                    "class_name": result.class_name,
                    "operation": result.operation,
                    "attendance_status": result.attendance_status,
                    "arrival_time": result.arrival_time,
                    "exit_time": result.exit_time,
                    "late_minutes": result.late_minutes,
                    "duplicate": result.duplicate,
                },
            }
        )


class DisciplineScannerResolveView(DisciplineViewMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        identifier = str(payload.get("identifier") or payload.get("qr") or payload.get("matricule") or "").strip()
        mode = str(payload.get("mode") or "attendance").strip().lower()
        try:
            identity = resolve_student_identity(academic_year=year, identifier=identifier)
        except Exception as exc:  # noqa: BLE001
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "data": {
                    "identifier_type": identity.identifier_type,
                    "identifier": identity.identifier,
                    "student_public_id": str(identity.student.public_id),
                    "matricule": identity.student.matricule,
                    "full_name": " ".join(
                        p
                        for p in (identity.student.nom, identity.student.postnom, identity.student.prenom)
                        if p
                    ),
                    "class_name": identity.enrollment.school_class.name,
                    "conduct_summary_url": reverse(
                        "discipline:scanner-conduct-summary",
                        kwargs={"public_id": identity.student.public_id},
                    ),
                    "dossier_url": reverse(
                        "discipline:student-disciplinary-file",
                        kwargs={"public_id": identity.student.public_id},
                    ),
                    "mode": mode,
                },
            }
        )


class DisciplineScannerAttendanceScanView(DisciplineViewMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        if year.is_closed:
            return JsonResponse({"ok": False, "error": "Année clôturée : pointage désactivé."}, status=400)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        identifier = str(payload.get("identifier") or "").strip()
        class_public_id = payload.get("class_public_id")
        sheet_date = payload.get("sheet_date")
        try:
            result = register_identifier_pointage(
                academic_year=year,
                identifier=identifier,
                actor=request.user,
                request=request,
                class_public_id=class_public_id,
                sheet_date=sheet_date,
            )
        except Exception as exc:  # noqa: BLE001
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "message": result.message,
                "data": {
                    "operation": result.operation,
                    "operation_label": result.operation_label,
                    "status": result.attendance_status,
                    "attendance_status": result.attendance_status,
                    "mention": "OK",
                    "student_name": result.student_name,
                    "matricule": result.matricule,
                    "class_name": result.class_name,
                    "arrival_time": result.arrival_time,
                    "exit_time": result.exit_time,
                    "late_minutes": result.late_minutes,
                    "duplicate": result.duplicate,
                },
            }
        )


class DisciplineStudentConductSummaryView(DisciplineViewMixin, View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        year = self.require_selected_year()
        student = get_object_or_404(
            Enrollment.objects.select_related("student", "school_class"),
            student__public_id=kwargs["public_id"],
            academic_year=year,
            status=Enrollment.Status.VALIDATED,
        )
        st = student.student
        late_count = DailyAttendance.objects.filter(
            academic_year=year,
            student=st,
            status=DailyAttendance.Status.LATE,
        ).count()
        absent_count = DailyAttendance.objects.filter(
            academic_year=year,
            student=st,
            status=DailyAttendance.Status.ABSENT,
        ).count()
        open_incidents = DisciplinaryIncident.objects.filter(
            academic_year=year,
            student=st,
            status__in=[
                DisciplinaryIncident.Status.REPORTED,
                DisciplinaryIncident.Status.REVIEW,
                DisciplinaryIncident.Status.CONFIRMED,
            ],
        ).count()
        total_incidents = DisciplinaryIncident.objects.filter(academic_year=year, student=st).count()
        pending_summons = ParentSummons.objects.filter(
            academic_year=year,
            student=st,
            status__in=[
                ParentSummons.Status.SCHEDULED,
                ParentSummons.Status.SENT,
                ParentSummons.Status.RECEIVED,
                ParentSummons.Status.CONFIRMED,
            ],
        ).count()
        active_measures = DisciplinaryMeasure.objects.filter(
            incident__academic_year=year,
            student=st,
            status__in=[DisciplinaryMeasure.Status.VALIDATED, DisciplinaryMeasure.Status.IN_PROGRESS],
        ).count()
        recent_events = []
        for row in (
            AttendanceScanEvent.objects.filter(academic_year=year, student=st)
            .order_by("-scanned_at")[:5]
        ):
            recent_events.append(
                {
                    "date": row.scanned_at.strftime("%d/%m/%Y %H:%M"),
                    "label": f"{row.get_event_type_display()} — {row.get_result_display()}",
                }
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Dossier disciplinaire chargé.",
                "data": {
                    "student": {
                        "public_id": str(st.public_id),
                        "matricule": st.matricule,
                        "full_name": " ".join(p for p in (st.nom, st.postnom, st.prenom) if p),
                        "class_name": student.school_class.name,
                    },
                    "summary": {
                        "late_count": late_count,
                        "absent_count": absent_count,
                        "open_incidents": open_incidents,
                        "total_incidents": total_incidents,
                        "pending_summons": pending_summons,
                        "active_measures": active_measures,
                    },
                    "recent_events": recent_events,
                    "open_record_url": reverse(
                        "discipline:student-disciplinary-file",
                        kwargs={"public_id": st.public_id},
                    ),
                    "dossier_url": reverse(
                        "discipline:student-disciplinary-file",
                        kwargs={"public_id": st.public_id},
                    ),
                },
            }
        )


class StudentDisciplinaryFileView(DisciplinePageView):
    template_name = "discipline/students/dossier.html"
    page_title = "Dossier disciplinaire"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        try:
            dossier = build_student_disciplinary_file(
                academic_year=year,
                student_public_id=self.kwargs["public_id"],
            )
        except DisciplineError as exc:
            raise Http404(str(exc)) from exc
        back_url = dossier.scanner_url
        class_id = (self.request.GET.get("class") or "").strip()
        if class_id:
            try:
                school_class = SchoolClass.objects.get(
                    public_id=class_id,
                    academic_year=year,
                )
                back_url = reverse(
                    "discipline:followup-class",
                    kwargs={"class_id": school_class.public_id},
                )
            except (SchoolClass.DoesNotExist, ValueError, TypeError):
                back_url = reverse("discipline:followup")
        context.update(
            dossier=dossier,
            back_url=back_url,
            school_address=getattr(settings, "SCHOOL_ADDRESS", ""),
            school_city=getattr(settings, "SCHOOL_CITY", ""),
            school_phone=getattr(settings, "SCHOOL_PHONE", ""),
            school_bp=getattr(settings, "SCHOOL_BP", ""),
            school_code=getattr(settings, "SCHOOL_CODE", ""),
        )
        return context


class StudentDisciplinaryFilePrintView(StudentDisciplinaryFileView):
    template_name = "discipline/students/dossier_print.html"


class StudentDisciplinaryFilePdfView(DisciplineViewMixin, View):
    def get(self, request, *args, **kwargs):
        year = self.require_selected_year()
        try:
            dossier = build_student_disciplinary_file(
                academic_year=year,
                student_public_id=kwargs["public_id"],
            )
        except DisciplineError as exc:
            raise Http404(str(exc)) from exc
        pdf_bytes = build_disciplinary_file_pdf(
            dossier,
            generated_by=getattr(request.user, "get_full_name", lambda: "")()
            or getattr(request.user, "username", ""),
        )
        safe_mat = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in dossier.student.matricule)
        filename = f"dossier_disciplinaire_{safe_mat}_{year.label}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AttendanceManualSubmitView(DisciplineViewMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        form = ManualAttendanceForm(request.POST or None, academic_year=year)
        if not form.is_valid():
            return JsonResponse({"ok": False, "error": "Formulaire invalide.", "errors": form.errors}, status=400)
        try:
            attendance = register_manual_attendance(
                academic_year=year,
                enrollment=form.cleaned_data["enrollment_id"],
                status=form.cleaned_data["status"],
                note=form.cleaned_data.get("note", ""),
                actor=request.user,
                request=request,
            )
        except Exception as exc:  # noqa: BLE001
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "data": {
                    "message": "Marquage manuel enregistré.",
                    "status": attendance.get_status_display(),
                    "date": attendance.date.isoformat(),
                    "student": attendance.student.matricule,
                },
            }
        )


class ClassConductListView(DisciplinePageView):
    page_title = "Classes"
    template_name = "discipline/classes/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        form = ClassFilterForm(self.request.GET)
        form.is_valid()
        q = (form.cleaned_data.get("q") or "").strip()

        classes = SchoolClass.objects.filter(academic_year=year).order_by("name")
        if q:
            classes = classes.filter(Q(name__icontains=q) | Q(code__icontains=q))

        today = datetime.now().date()
        attendance_by_class = {
            row["enrollment__school_class_id"]: row
            for row in DailyAttendance.objects.filter(academic_year=year, date=today)
            .values("enrollment__school_class_id")
            .annotate(
                present=Count("id", filter=Q(status=DailyAttendance.Status.PRESENT)),
                late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
                absent=Count("id", filter=Q(status=DailyAttendance.Status.ABSENT)),
            )
        }
        incidents_by_class = {
            row["school_class_id"]: row["total"]
            for row in DisciplinaryIncident.objects.filter(
                academic_year=year,
                status__in=[
                    DisciplinaryIncident.Status.REPORTED,
                    DisciplinaryIncident.Status.REVIEW,
                    DisciplinaryIncident.Status.CONFIRMED,
                ],
            )
            .values("school_class_id")
            .annotate(total=Count("id"))
        }
        folders_by_class = {
            row["school_class_id"]: row["total"]
            for row in ClassAttendanceSheet.objects.filter(academic_year=year)
            .values("school_class_id")
            .annotate(total=Count("id"))
        }

        rows = []
        for school_class in classes:
            attendance = attendance_by_class.get(school_class.id, {})
            enrollment_count = Enrollment.objects.filter(
                academic_year=year,
                school_class=school_class,
                status=Enrollment.Status.VALIDATED,
            ).count()
            rows.append(
                {
                    "class": school_class,
                    "students_count": enrollment_count,
                    "present": attendance.get("present", 0),
                    "late": attendance.get("late", 0),
                    "absent": attendance.get("absent", 0),
                    "open_incidents": incidents_by_class.get(school_class.id, 0),
                    "days_recorded": folders_by_class.get(school_class.id, 0),
                    "folders_url": reverse(
                        "discipline:class-attendance-folders",
                        kwargs={"class_id": school_class.public_id},
                    ),
                }
            )

        context.update(rows=rows, filters={"q": q}, today=today)
        return context


class ClassAttendanceFoldersView(DisciplinePageView):
    template_name = "discipline/attendance/folders.html"
    page_title = "Dossiers journaliers"

    def _resolve_class(self):
        year = self.require_selected_year()
        school_class = get_object_or_404(SchoolClass, public_id=self.kwargs["class_id"], academic_year=year)
        return year, school_class

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, school_class = self._resolve_class()
        form = FolderFilterForm(self.request.GET)
        form.is_valid()

        sheets = ClassAttendanceSheet.objects.filter(
            academic_year=year,
            school_class=school_class,
        ).order_by("-date")
        if form.cleaned_data.get("q_date"):
            sheets = sheets.filter(date=form.cleaned_data["q_date"])
        if form.cleaned_data.get("status"):
            sheets = sheets.filter(status=form.cleaned_data["status"])
        month_raw = (form.cleaned_data.get("month") or "").strip()
        if month_raw:
            try:
                year_part, month_part = month_raw.split("-", 1)
                sheets = sheets.filter(date__year=int(year_part), date__month=int(month_part))
            except ValueError:
                pass

        folders = []
        for sheet in sheets[:120]:
            folders.append(
                {
                    "sheet": sheet,
                    "url": reverse(
                        "discipline:class-attendance-sheet",
                        kwargs={"class_id": school_class.public_id, "sheet_date": sheet.date.isoformat()},
                    ),
                }
            )

        today = datetime.now().date()
        safe_today = today
        if safe_today < year.start_date:
            safe_today = year.start_date
        elif safe_today > year.end_date:
            safe_today = year.end_date

        today_url = reverse(
            "discipline:class-attendance-sheet",
            kwargs={"class_id": school_class.public_id, "sheet_date": safe_today.isoformat()},
        )
        context.update(
            school_class=school_class,
            folders=folders,
            today=today,
            filters={
                "q_date": form.cleaned_data.get("q_date").isoformat() if form.cleaned_data.get("q_date") else "",
                "status": form.cleaned_data.get("status") or "",
                "month": month_raw,
            },
            today_url=today_url,
        )
        return context


class ClassAttendanceSheetView(DisciplinePageView):
    template_name = "discipline/attendance/sheet.html"
    page_title = "Feuille de présence"

    def get(self, request, *args, **kwargs):
        try:
            self._resolve()
        except DisciplineError as exc:
            messages.error(request, str(exc))
            school_class = get_object_or_404(
                SchoolClass,
                public_id=self.kwargs["class_id"],
                academic_year=self.require_selected_year(),
            )
            return redirect("discipline:class-attendance-folders", class_id=school_class.public_id)
        return super().get(request, *args, **kwargs)

    def _resolve(self):
        year = self.require_selected_year()
        school_class = get_object_or_404(SchoolClass, public_id=self.kwargs["class_id"], academic_year=year)
        target_date = parse_date(self.kwargs["sheet_date"])
        if target_date is None:
            raise Http404("Date invalide.")
        sheet = get_or_create_sheet(
            academic_year=year,
            school_class=school_class,
            target_date=target_date,
            actor=self.request.user,
        )
        return year, school_class, target_date, sheet

    def post(self, request, *args, **kwargs):
        try:
            year, school_class, target_date, sheet = self._resolve()
        except DisciplineError as exc:
            messages.error(request, str(exc))
            school_class = get_object_or_404(
                SchoolClass,
                public_id=self.kwargs["class_id"],
                academic_year=self.require_selected_year(),
            )
            return redirect("discipline:class-attendance-folders", class_id=school_class.public_id)
        action = request.POST.get("action", "save_draft")
        if action == "correct":
            form = AttendanceRecordCorrectionForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Formulaire de correction invalide.")
                return redirect(
                    "discipline:class-attendance-sheet",
                    class_id=school_class.public_id,
                    sheet_date=target_date.isoformat(),
                )
            record = get_object_or_404(sheet.records, public_id=request.POST.get("record_id"))
            try:
                correct_validated_record(
                    record=record,
                    new_status=form.cleaned_data["status"],
                    reason=form.cleaned_data["reason"],
                    password=form.cleaned_data["password"],
                    actor=request.user,
                    request=request,
                )
            except Exception as exc:  # noqa: BLE001
                messages.error(request, str(exc))
            else:
                messages.success(request, "Correction enregistrée.")
            return redirect(
                "discipline:class-attendance-sheet",
                class_id=school_class.public_id,
                sheet_date=target_date.isoformat(),
            )

        statuses_by_record_id = {}
        for key, value in request.POST.items():
            if not key.startswith("record-status-"):
                continue
            record_id = key.replace("record-status-", "", 1)
            try:
                statuses_by_record_id[int(record_id)] = value
            except ValueError:
                continue
        try:
            save_sheet_draft(
                sheet=sheet,
                statuses_by_record_id=statuses_by_record_id,
                actor=request.user,
                request=request,
            )
            if action == "validate":
                validate_sheet(sheet=sheet, actor=request.user, request=request)
                messages.success(request, "Feuille validée.")
            else:
                messages.success(request, "Brouillon enregistré.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, str(exc))
        return redirect(
            "discipline:class-attendance-sheet",
            class_id=school_class.public_id,
            sheet_date=target_date.isoformat(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, school_class, target_date, sheet = self._resolve()
        records = sheet.records.select_related("student", "enrollment").order_by("student__nom", "student__prenom")
        totals = recompute_sheet_totals(sheet=sheet, save=True)
        context.update(
            selected_year=year,
            school_class=school_class,
            sheet=sheet,
            records=records,
            sheet_date=target_date,
            totals=totals,
            print_url=reverse(
                "discipline:class-attendance-sheet-print",
                kwargs={"class_id": school_class.public_id, "sheet_date": target_date.isoformat()},
            ),
            export_csv_url=reverse(
                "discipline:class-attendance-sheet-export-csv",
                kwargs={"class_id": school_class.public_id, "sheet_date": target_date.isoformat()},
            ),
            correction_form=AttendanceRecordCorrectionForm(),
        )
        return context


class ClassAttendanceSheetPrintView(ClassAttendanceSheetView):
    template_name = "discipline/attendance/sheet_print.html"

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except DisciplineError as exc:
            messages.error(request, str(exc))
            school_class = get_object_or_404(
                SchoolClass,
                public_id=self.kwargs["class_id"],
                academic_year=self.require_selected_year(),
            )
            return redirect("discipline:class-attendance-folders", class_id=school_class.public_id)


class ClassAttendanceSheetCsvExportView(DisciplineViewMixin, View):
    def get(self, request, *args, **kwargs):
        year = self.require_selected_year()
        school_class = get_object_or_404(SchoolClass, public_id=kwargs["class_id"], academic_year=year)
        target_date = parse_date(kwargs["sheet_date"])
        if target_date is None:
            return HttpResponse(status=404)
        try:
            sheet = get_or_create_sheet(
                academic_year=year,
                school_class=school_class,
                target_date=target_date,
                actor=request.user,
            )
        except DisciplineError as exc:
            messages.error(request, str(exc))
            return redirect("discipline:class-attendance-folders", class_id=school_class.public_id)
        records = sheet.records.select_related("student").order_by("student__nom", "student__prenom")

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["N°", "Matricule", "Nom complet", "Présence", "Mention", "Observation"])
        for idx, record in enumerate(records, start=1):
            writer.writerow(
                [
                    idx,
                    record.student.matricule,
                    f"{record.student.nom} {record.student.postnom} {record.student.prenom}".strip(),
                    record.presence_value if record.presence_value is not None else "",
                    record.mention,
                    record.observation,
                ]
            )
        filename = f"presence_{school_class.name.replace(' ', '_')}_{target_date.isoformat()}.csv"
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class StudentConductListView(DisciplinePageView):
    page_title = "Élèves"
    template_name = "discipline/students/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        form = StudentFilterForm(self.request.GET)
        form.is_valid()

        q = (form.cleaned_data.get("q") or "").strip()
        class_id = form.cleaned_data.get("school_class")

        enrollments = Enrollment.objects.filter(
            academic_year=year,
            status=Enrollment.Status.VALIDATED,
        ).select_related("student", "school_class")
        if q:
            enrollments = enrollments.filter(
                Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(student__postnom__icontains=q)
                | Q(student__prenom__icontains=q)
            )
        if class_id:
            enrollments = enrollments.filter(school_class__public_id=class_id)

        classes = SchoolClass.objects.filter(academic_year=year).order_by("name")
        context.update(
            enrollments=enrollments.order_by("school_class__name", "student__nom")[:200],
            classes=classes,
            filters={"q": q, "school_class": str(class_id) if class_id else ""},
        )
        return context


class ConductView(DisciplinePageView):
    """Legacy URL — conduite consolidée dans Incidents."""

    page_title = "Conduite"

    def get(self, request, *args, **kwargs):
        return redirect("discipline:incidents")

    def post(self, request, *args, **kwargs):
        return redirect("discipline:incidents")


class IncidentStudentLookupView(DisciplineViewMixin, View):
    """Resolve matricule → class for the incident create form."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        year = self.require_selected_year()
        matricule = str(request.GET.get("matricule") or "").strip()
        if not matricule:
            return JsonResponse({"ok": False, "error": "Indiquez un matricule."}, status=400)
        try:
            identity = resolve_student_identity(academic_year=year, identifier=matricule)
        except Exception as exc:  # noqa: BLE001
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        full_name = " ".join(
            p
            for p in (identity.student.nom, identity.student.postnom, identity.student.prenom)
            if p
        )
        return JsonResponse(
            {
                "ok": True,
                "data": {
                    "matricule": identity.student.matricule,
                    "full_name": full_name,
                    "class_name": identity.enrollment.school_class.name,
                },
            }
        )


class IncidentListView(DisciplinePageView):
    """Incidents + convocations (same page, toggleable tables)."""

    page_title = "Incidents"
    template_name = "discipline/incidents/list.html"

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        if year.is_closed:
            messages.error(request, "Année clôturée : création désactivée.")
            return redirect("discipline:incidents")

        form_action = (request.POST.get("form_action") or "incident").strip()
        if form_action == "summons":
            form = SummonsForm(request.POST or None, academic_year=year)
            if not form.is_valid():
                messages.error(request, "Formulaire de convocation invalide.")
                return self.render_to_response(
                    self.get_context_data(
                        summons_form=form,
                        open_summons_modal=True,
                        active_view="convocations",
                    )
                )
            summons = form.save(commit=False)
            summons.academic_year = year
            summons.created_by = request.user
            if not summons.summon_date:
                from django.utils import timezone

                summons.summon_date = timezone.localdate()
            if not summons.summon_number:
                y = year.start_date.year
                idx = ParentSummons.objects.filter(academic_year=year).count() + 1
                summons.summon_number = f"CONV-{y}-{idx:06d}"
            summons.save()
            messages.success(request, "Convocation enregistrée.")
            return redirect(f"{reverse('discipline:incidents')}?vue=convocations")

        form = IncidentForm(request.POST or None, academic_year=year, include_measure=True)
        if not form.is_valid():
            messages.error(request, "Formulaire incident invalide.")
            return self.render_to_response(
                self.get_context_data(form=form, open_create_modal=True, active_view="incidents")
            )
        incident = form.save(commit=False)
        incident.academic_year = year
        incident.reported_by = request.user
        if not incident.incident_date:
            from django.utils import timezone

            incident.incident_date = timezone.localdate()
        incident.save()
        measure = form.create_linked_measure(incident=incident, actor=request.user)
        if measure:
            messages.success(request, "Incident et mesure disciplinaire enregistrés.")
        else:
            messages.success(request, "Incident enregistré.")
        return redirect("discipline:incidents")

    def get_context_data(self, **kwargs):
        open_create_modal = kwargs.pop("open_create_modal", False)
        open_summons_modal = kwargs.pop("open_summons_modal", False)
        form = kwargs.pop("form", None)
        summons_form = kwargs.pop("summons_form", None)
        active_view = kwargs.pop("active_view", None)
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()

        if active_view is None:
            active_view = (self.request.GET.get("vue") or "incidents").strip().lower()
        if active_view not in {"incidents", "convocations"}:
            active_view = "incidents"

        filter_form = IncidentFilterForm(self.request.GET)
        filter_form.is_valid()
        cleaned = filter_form.cleaned_data

        filter_year = cleaned.get("year")
        filter_month = cleaned.get("month") or ""
        filter_day = cleaned.get("day")
        filter_level = cleaned.get("level")
        filter_option = cleaned.get("option")

        incidents = DisciplinaryIncident.objects.filter(academic_year=year).select_related(
            "student",
            "school_class",
            "school_class__level",
            "school_class__option",
            "category",
        )
        if filter_year:
            incidents = incidents.filter(incident_date__year=filter_year)
        if filter_month:
            try:
                incidents = incidents.filter(incident_date__month=int(filter_month))
            except (TypeError, ValueError):
                pass
        if filter_day:
            incidents = incidents.filter(incident_date__day=filter_day)
        if filter_level:
            incidents = incidents.filter(school_class__level__public_id=filter_level)
        if filter_option:
            incidents = incidents.filter(school_class__option__public_id=filter_option)

        summonses = ParentSummons.objects.filter(academic_year=year).select_related(
            "student",
            "incident",
            "incident__school_class",
        )
        if filter_year:
            summonses = summonses.filter(summon_date__year=filter_year)
        if filter_month:
            try:
                summonses = summonses.filter(summon_date__month=int(filter_month))
            except (TypeError, ValueError):
                pass
        if filter_day:
            summonses = summonses.filter(summon_date__day=filter_day)
        if filter_level or filter_option:
            student_ids = Enrollment.objects.filter(
                academic_year=year,
                status=Enrollment.Status.VALIDATED,
            )
            if filter_level:
                student_ids = student_ids.filter(school_class__level__public_id=filter_level)
            if filter_option:
                student_ids = student_ids.filter(school_class__option__public_id=filter_option)
            summonses = summonses.filter(
                student_id__in=student_ids.values_list("student_id", flat=True)
            )

        calendar_years = []
        start_y = year.start_date.year
        end_y = year.end_date.year
        calendar_years.extend(range(start_y, end_y + 1))
        for value in DisciplinaryIncident.objects.filter(academic_year=year).dates(
            "incident_date", "year"
        ):
            if value.year not in calendar_years:
                calendar_years.append(value.year)
        for value in ParentSummons.objects.filter(academic_year=year).dates("summon_date", "year"):
            if value.year not in calendar_years:
                calendar_years.append(value.year)
        calendar_years = sorted(set(calendar_years), reverse=True)

        filters = {
            "year": str(filter_year) if filter_year else "",
            "month": filter_month,
            "day": str(filter_day) if filter_day else "",
            "level": str(filter_level) if filter_level else "",
            "option": str(filter_option) if filter_option else "",
        }
        filter_qs_parts = [f"vue={active_view}"]
        for key, value in filters.items():
            if value:
                filter_qs_parts.append(f"{key}={value}")
        filter_qs = "&".join(filter_qs_parts)

        if form is None:
            form = IncidentForm(academic_year=year, include_measure=True)
        if summons_form is None:
            summons_form = SummonsForm(academic_year=year)

        context.update(
            active_view=active_view,
            incidents=incidents.order_by("-incident_date", "-created_at")[:300],
            summonses=summonses.order_by("-summon_date", "-created_at")[:300],
            form=form,
            summons_form=summons_form,
            open_create_modal=open_create_modal or bool(form.errors),
            open_summons_modal=open_summons_modal or bool(summons_form.errors),
            incident_lookup_url=reverse("discipline:incident-student-lookup"),
            filters=filters,
            filter_qs=filter_qs,
            filter_calendar_years=calendar_years,
            filter_months=IncidentFilterForm.base_fields["month"].choices,
            filter_days=list(range(1, 32)),
            filter_levels=SchoolLevel.objects.filter(
                school_classes__academic_year=year,
            )
            .distinct()
            .order_by("order", "name"),
            filter_options=Option.objects.filter(
                school_classes__academic_year=year,
            )
            .distinct()
            .order_by("name"),
        )
        return context


class IncidentDetailView(DisciplinePageView):
    """Full incident dossier for consultation."""

    page_title = "Détail de l'incident"
    template_name = "discipline/incidents/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        incident = get_object_or_404(
            DisciplinaryIncident.objects.select_related(
                "student",
                "school_class",
                "school_class__level",
                "school_class__option",
                "school_class__section",
                "category",
                "reported_by",
                "confirmed_by",
                "closed_by",
                "academic_year",
            ),
            public_id=self.kwargs["public_id"],
            academic_year=year,
        )
        measures = (
            DisciplinaryMeasure.objects.filter(incident=incident)
            .select_related("measure_type", "student")
            .order_by("-created_at")
        )
        summonses = (
            ParentSummons.objects.filter(incident=incident)
            .select_related("student")
            .order_by("-summon_date", "-created_at")
        )
        context.update(
            incident=incident,
            measures=measures,
            summonses=summonses,
            back_url=reverse("discipline:incidents"),
            dossier_url=reverse(
                "discipline:student-disciplinary-file",
                kwargs={"public_id": incident.student.public_id},
            ),
        )
        return context


class MeasureListView(DisciplinePageView):
    """Legacy URL — mesures are created from the incident form."""

    page_title = "Mesures disciplinaires"

    def get(self, request, *args, **kwargs):
        messages.info(
            request,
            "Les mesures disciplinaires s'enregistrent désormais avec l'incident.",
        )
        return redirect("discipline:incidents")

    def post(self, request, *args, **kwargs):
        return redirect("discipline:incidents")


class SummonsListView(DisciplinePageView):
    """Legacy URL — convocations are managed from the Incidents page."""

    page_title = "Convocations"

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('discipline:incidents')}?vue=convocations")

    def post(self, request, *args, **kwargs):
        return redirect(f"{reverse('discipline:incidents')}?vue=convocations")


class ExitAuthorizationListView(DisciplinePageView):
    page_title = "Sorties autorisées"
    template_name = "discipline/exits/list.html"

    def post(self, request, *args, **kwargs):
        year = self.require_selected_year()
        if year.is_closed:
            messages.error(request, "Année clôturée : création désactivée.")
            return redirect("discipline:exits")
        form = ExitAuthorizationForm(request.POST or None, academic_year=year)
        if not form.is_valid():
            messages.error(request, "Formulaire de sortie invalide.")
            return self.render_to_response(
                self.get_context_data(form=form, open_create_modal=True)
            )
        exit_auth = form.save(commit=False)
        exit_auth.academic_year = year
        exit_auth.authorized_by = request.user
        if not exit_auth.date:
            from django.utils import timezone

            exit_auth.date = timezone.localdate()
        exit_auth.save()
        messages.success(request, "Autorisation de sortie enregistrée.")
        return redirect("discipline:exits")

    def get_context_data(self, **kwargs):
        open_create_modal = kwargs.pop("open_create_modal", False)
        form = kwargs.pop("form", None)
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        exits = ExitAuthorization.objects.filter(academic_year=year).select_related(
            "student",
            "enrollment__school_class",
        )
        if form is None:
            form = ExitAuthorizationForm(academic_year=year)
        context.update(
            exits=exits.order_by("-date", "-created_at")[:300],
            form=form,
            open_create_modal=open_create_modal or bool(form.errors),
            incident_lookup_url=reverse("discipline:incident-student-lookup"),
        )
        return context


class ExitAuthorizationDetailView(DisciplinePageView):
    page_title = "Détail de la sortie"
    template_name = "discipline/exits/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        exit_auth = get_object_or_404(
            ExitAuthorization.objects.select_related(
                "student",
                "enrollment__school_class",
                "authorized_by",
                "academic_year",
            ),
            public_id=self.kwargs["public_id"],
            academic_year=year,
        )
        context.update(
            exit_auth=exit_auth,
            back_url=reverse("discipline:exits"),
            dossier_url=reverse(
                "discipline:student-disciplinary-file",
                kwargs={"public_id": exit_auth.student.public_id},
            ),
        )
        return context


class JustificationListView(DisciplinePageView):
    page_title = "Justificatifs d'absence"
    template_name = "discipline/justifications/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        justifications = AbsenceJustification.objects.filter(
            attendance__academic_year=year
        ).select_related("attendance__student", "attendance__enrollment__school_class", "submitted_by")
        context.update(justifications=justifications.order_by("-submitted_at")[:300])
        return context


class CaseFollowupView(DisciplinePageView):
    """Browse disciplinary dossiers by class."""

    page_title = "Suivi des dossiers"
    template_name = "discipline/followup/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        form = ClassFilterForm(self.request.GET)
        form.is_valid()
        q = (form.cleaned_data.get("q") or "").strip()

        classes = SchoolClass.objects.filter(academic_year=year).select_related(
            "level", "section", "option"
        ).order_by("name")
        if q:
            classes = classes.filter(Q(name__icontains=q) | Q(code__icontains=q))

        rows = []
        for school_class in classes:
            students_count = Enrollment.objects.filter(
                academic_year=year,
                school_class=school_class,
                status=Enrollment.Status.VALIDATED,
            ).count()
            rows.append(
                {
                    "class": school_class,
                    "students_count": students_count,
                    "class_url": reverse(
                        "discipline:followup-class",
                        kwargs={"class_id": school_class.public_id},
                    ),
                }
            )
        context.update(rows=rows, filters={"q": q})
        return context


class CaseFollowupClassView(DisciplinePageView):
    """List students of a class with link to disciplinary dossier."""

    page_title = "Dossiers de classe"
    template_name = "discipline/followup/class_students.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        school_class = get_object_or_404(
            SchoolClass.objects.select_related("level", "section", "option"),
            public_id=self.kwargs["class_id"],
            academic_year=year,
        )
        enrollments = (
            Enrollment.objects.filter(
                academic_year=year,
                school_class=school_class,
                status=Enrollment.Status.VALIDATED,
            )
            .select_related("student")
            .order_by("student__nom", "student__postnom", "student__prenom")
        )
        rows = []
        for idx, enrollment in enumerate(enrollments, start=1):
            rows.append(
                {
                    "n": idx,
                    "enrollment": enrollment,
                    "student": enrollment.student,
                    "dossier_url": reverse(
                        "discipline:student-disciplinary-file",
                        kwargs={"public_id": enrollment.student.public_id},
                    )
                    + f"?class={school_class.public_id}",
                }
            )
        context.update(
            school_class=school_class,
            rows=rows,
            back_url=reverse("discipline:followup"),
        )
        return context
