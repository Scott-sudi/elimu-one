"""Attendance schedule configuration views."""

from django.contrib import messages
from django.shortcuts import redirect

from apps.discipline.forms_schedules import VacationScheduleForm
from apps.discipline.models import AttendanceSchedule
from apps.discipline.services.exceptions import DisciplineError
from apps.discipline.services.schedule_service import (
    build_vacation_form_initial,
    save_vacation_schedule,
)
from apps.discipline.views import DisciplinePageView


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
            detail = "Vérifiez les horaires saisis."
            for field, errs in form.errors.items():
                if errs:
                    detail = f"{field}: {errs[0]}"
                    break
            messages.error(request, detail)
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
