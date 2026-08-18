from django.contrib import admin

from .models import (
    AbsenceJustification,
    AttendanceScanEvent,
    AttendanceSchedule,
    ClassAttendanceSheet,
    ConductCategory,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    DisciplinaryMeasureType,
    ExitAuthorization,
    IncidentParticipant,
    ParentSummons,
    StudentAttendanceRecord,
)


@admin.register(ConductCategory)
class ConductCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "observation_type", "default_severity", "is_active", "is_archived")
    list_filter = ("observation_type", "default_severity", "is_active", "is_archived")
    search_fields = ("code", "name")


@admin.register(AttendanceSchedule)
class AttendanceScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "academic_year",
        "vacation",
        "school_class",
        "level",
        "start_time",
        "present_until",
        "end_time",
        "is_active",
    )
    list_filter = ("academic_year", "vacation", "is_active", "is_archived")
    search_fields = ("label", "school_class__name", "level__name")


@admin.register(DailyAttendance)
class DailyAttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "student", "enrollment", "status", "arrival_time", "late_minutes", "source")
    list_filter = ("academic_year", "status", "source", "date")
    search_fields = ("student__matricule", "student__nom", "enrollment__school_class__name")


@admin.register(AttendanceScanEvent)
class AttendanceScanEventAdmin(admin.ModelAdmin):
    list_display = ("scanned_at", "event_type", "result", "student", "enrollment")
    list_filter = ("academic_year", "event_type", "result")
    search_fields = ("qr_identifier", "student__matricule", "student__nom")


@admin.register(DisciplinaryIncident)
class DisciplinaryIncidentAdmin(admin.ModelAdmin):
    list_display = ("incident_date", "title", "student", "school_class", "severity", "status")
    list_filter = ("academic_year", "severity", "status", "category")
    search_fields = ("title", "student__matricule", "student__nom")


@admin.register(IncidentParticipant)
class IncidentParticipantAdmin(admin.ModelAdmin):
    list_display = ("incident", "student", "role", "is_confirmed")
    list_filter = ("role", "is_confirmed")


@admin.register(DisciplinaryMeasureType)
class DisciplinaryMeasureTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "minimum_severity", "requires_validation", "is_active")
    list_filter = ("minimum_severity", "requires_validation", "is_active")
    search_fields = ("code", "name")


@admin.register(DisciplinaryMeasure)
class DisciplinaryMeasureAdmin(admin.ModelAdmin):
    list_display = ("student", "measure_type", "status", "start_date", "end_date", "is_cancelled")
    list_filter = ("status", "is_cancelled", "measure_type")
    search_fields = ("student__matricule", "student__nom", "incident__title")


@admin.register(ParentSummons)
class ParentSummonsAdmin(admin.ModelAdmin):
    list_display = ("summon_number", "student", "summon_date", "status", "delivery_mode")
    list_filter = ("academic_year", "status", "delivery_mode")
    search_fields = ("summon_number", "student__matricule", "student__nom")


@admin.register(AbsenceJustification)
class AbsenceJustificationAdmin(admin.ModelAdmin):
    list_display = ("attendance", "reason", "status", "submitted_at")
    list_filter = ("status",)
    search_fields = ("reason", "attendance__student__matricule")


@admin.register(ExitAuthorization)
class ExitAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status", "planned_exit_time", "actual_exit_time")
    list_filter = ("academic_year", "status")
    search_fields = ("student__matricule", "student__nom")


@admin.register(ClassAttendanceSheet)
class ClassAttendanceSheetAdmin(admin.ModelAdmin):
    list_display = ("school_class", "date", "status", "total_students", "total_present", "total_absent", "total_unmarked")
    list_filter = ("academic_year", "status", "date")
    search_fields = ("school_class__name",)


@admin.register(StudentAttendanceRecord)
class StudentAttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("sheet", "student", "status", "presence_value", "mention")
    list_filter = ("status", "sheet__academic_year")
    search_fields = ("student__matricule", "student__nom", "sheet__school_class__name")
