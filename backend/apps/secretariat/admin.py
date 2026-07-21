"""Simple administration for secretariat reference and operational data."""

from __future__ import annotations

from django.contrib import admin

from apps.secretariat.models import (
    AcademicYear,
    ClassTransfer,
    Communication,
    CommunicationReceipt,
    CommunicationTarget,
    DocumentType,
    Enrollment,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    SecretariatSetting,
    Student,
    StudentCard,
    StudentDocument,
    StudentGuardian,
)


class SearchableAdmin(admin.ModelAdmin):
    list_per_page = 50


@admin.register(Student)
class StudentAdmin(SearchableAdmin):
    list_display = ("matricule", "nom", "postnom", "prenom", "statut", "is_active")
    list_filter = ("statut", "sexe", "is_archived")
    search_fields = ("matricule", "nom", "postnom", "prenom")


@admin.register(Guardian)
class GuardianAdmin(SearchableAdmin):
    list_display = ("nom", "postnom", "prenom", "telephone_principal", "is_active")
    search_fields = ("nom", "postnom", "prenom", "telephone_principal", "email")


@admin.register(Enrollment)
class EnrollmentAdmin(SearchableAdmin):
    list_display = ("enrollment_number", "student", "school_class", "status", "enrollment_date")
    list_filter = ("status", "enrollment_type", "academic_year")
    search_fields = ("enrollment_number", "student__matricule", "student__nom")


@admin.register(SchoolClass)
class SchoolClassAdmin(SearchableAdmin):
    list_display = ("code", "name", "academic_year", "level", "max_capacity", "is_active")
    list_filter = ("academic_year", "level", "is_active")
    search_fields = ("code", "name")


@admin.register(Communication)
class CommunicationAdmin(SearchableAdmin):
    list_display = ("title", "category", "priority", "status", "published_at")
    list_filter = ("category", "priority", "status")
    search_fields = ("title", "content")


admin.site.register(
    (
        AcademicYear,
        ClassTransfer,
        CommunicationReceipt,
        CommunicationTarget,
        DocumentType,
        Option,
        SchoolLevel,
        Section,
        SecretariatSetting,
        StudentCard,
        StudentDocument,
        StudentGuardian,
    ),
)
