"""Filtered CSV/XLSX exports."""

import csv
from io import BytesIO

from django.http import HttpResponse
from django.views import View
from openpyxl import Workbook

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.models import Enrollment, Student


class ExportView(SecretaryRequiredMixin, View):
    dataset = "students"
    file_format = "csv"

    def rows(self):
        if self.dataset == "enrollments":
            qs = Enrollment.objects.select_related("student", "academic_year", "school_class")
            if self.request.GET.get("status"):
                qs = qs.filter(status=self.request.GET["status"])
            return ["Numéro", "Élève", "Année", "Classe", "Statut"], (
                [e.enrollment_number, str(e.student), e.academic_year.label, e.school_class.name, e.get_status_display()]
                for e in qs
            )
        qs = Student.objects.all()
        if self.request.GET.get("status"):
            qs = qs.filter(statut=self.request.GET["status"])
        return ["Matricule", "Nom", "Postnom", "Prénom", "Sexe", "Statut"], (
            [s.matricule, s.nom, s.postnom, s.prenom, s.get_sexe_display(), s.get_statut_display()] for s in qs
        )

    def get(self, request):
        self.file_format = self.kwargs.get("file_format", "csv").lower()
        if self.file_format not in {"csv", "xlsx"}:
            self.file_format = "csv"
        headers, rows = self.rows()
        filename = f"{self.dataset}.{self.file_format}"
        if self.file_format == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Export"
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            output = BytesIO()
            workbook.save(output)
            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response.write("\ufeff")
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
