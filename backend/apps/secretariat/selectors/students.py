"""Student query helpers."""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet

from apps.secretariat.models import Enrollment, Student, StudentGuardian


def student_queryset() -> QuerySet[Student]:
    enrollments = Enrollment.objects.select_related(
        "academic_year", "school_class", "school_class__level",
        "school_class__section", "school_class__option",
    ).order_by("-academic_year__start_date")
    guardians = StudentGuardian.objects.select_related("guardian").order_by("-is_primary")
    return Student.objects.prefetch_related(
        Prefetch("enrollments", queryset=enrollments),
        Prefetch("guardian_links", queryset=guardians),
    )


def search_students(
    *,
    query: str = "",
    academic_year=None,
    school_class=None,
    status: str = "",
    is_archived: bool | None = False,
) -> QuerySet[Student]:
    students = student_queryset()
    if query:
        terms = query.split()
        name_query = Q()
        for term in terms:
            name_query &= (
                Q(nom__icontains=term)
                | Q(postnom__icontains=term)
                | Q(prenom__icontains=term)
                | Q(matricule__icontains=term)
            )
        students = students.filter(name_query)
    if academic_year:
        students = students.filter(enrollments__academic_year=academic_year)
    if school_class:
        students = students.filter(enrollments__school_class=school_class)
    if status:
        students = students.filter(statut=status)
    if is_archived is not None:
        students = students.filter(is_archived=is_archived)
    return students.distinct()


def get_student_detail(*, public_id) -> Student:
    return student_queryset().get(public_id=public_id)
