"""Serializers for the secretariat REST API."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.secretariat.models import (
    AcademicYear,
    Communication,
    CommunicationTarget,
    Enrollment,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
    StudentCard,
)
from apps.secretariat.services import (
    academic_service,
    card_service,
    communication_service,
    enrollment_service,
    guardian_service,
    student_service,
)
from apps.secretariat.services.exceptions import SecretariatError


def _service_call(serializer, function, *args, **kwargs):
    request = serializer.context.get("request")
    try:
        return function(
            *args,
            actor=getattr(request, "user", None),
            request=request,
            **kwargs,
        )
    except (SecretariatError, DjangoValidationError) as exc:
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        raise serializers.ValidationError(detail) from exc


class PublicIdRelatedField(serializers.SlugRelatedField):
    """Represent model relations by their stable public UUID."""

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "public_id")
        super().__init__(**kwargs)


class AcademicYearListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ("public_id", "label", "start_date", "end_date", "is_active", "is_closed")


class AcademicYearDetailSerializer(AcademicYearListSerializer):
    class Meta(AcademicYearListSerializer.Meta):
        fields = AcademicYearListSerializer.Meta.fields + ("created_at", "updated_at")


class AcademicYearWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ("label", "start_date", "end_date", "is_active")

    def create(self, validated_data):
        return _service_call(self, academic_service.create_academic_year, **validated_data)

    def update(self, instance, validated_data):
        return _service_call(
            self,
            academic_service.update_academic_year,
            instance,
            **validated_data,
        )


class SchoolLevelListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolLevel
        fields = ("public_id", "name", "code", "order", "is_active")


class SchoolLevelDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolLevel
        fields = (
            "public_id",
            "name",
            "code",
            "order",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )


class SchoolLevelWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolLevel
        fields = ("name", "code", "order", "description", "is_active")

    def create(self, validated_data):
        return _service_call(self, academic_service.create_level, **validated_data)


class SectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ("public_id", "name", "code", "is_active")


class SectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = (
            "public_id",
            "name",
            "code",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )


class SectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ("name", "code", "description", "is_active")

    def create(self, validated_data):
        return _service_call(self, academic_service.create_section, **validated_data)


class OptionListSerializer(serializers.ModelSerializer):
    section = SectionListSerializer(read_only=True)

    class Meta:
        model = Option
        fields = ("public_id", "name", "code", "section", "is_active")


class OptionDetailSerializer(serializers.ModelSerializer):
    section = SectionListSerializer(read_only=True)

    class Meta:
        model = Option
        fields = (
            "public_id",
            "name",
            "code",
            "section",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )


class OptionWriteSerializer(serializers.ModelSerializer):
    section = PublicIdRelatedField(
        queryset=Section.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Option
        fields = ("name", "code", "section", "description", "is_active")

    def create(self, validated_data):
        return _service_call(self, academic_service.create_option, **validated_data)


class SchoolClassListSerializer(serializers.ModelSerializer):
    academic_year = AcademicYearListSerializer(read_only=True)
    level = SchoolLevelListSerializer(read_only=True)
    section = SectionListSerializer(read_only=True)
    option = OptionListSerializer(read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = (
            "public_id",
            "name",
            "code",
            "letter",
            "academic_year",
            "level",
            "section",
            "option",
            "max_capacity",
            "enrollment_count",
            "is_active",
        )


class SchoolClassDetailSerializer(SchoolClassListSerializer):
    class Meta(SchoolClassListSerializer.Meta):
        fields = SchoolClassListSerializer.Meta.fields + (
            "room",
            "description",
            "created_at",
            "updated_at",
        )


class SchoolClassWriteSerializer(serializers.ModelSerializer):
    academic_year = PublicIdRelatedField(queryset=AcademicYear.objects.all())
    level = PublicIdRelatedField(queryset=SchoolLevel.objects.all())
    section = PublicIdRelatedField(
        queryset=Section.objects.all(),
        required=False,
        allow_null=True,
    )
    option = PublicIdRelatedField(
        queryset=Option.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SchoolClass
        fields = (
            "academic_year",
            "level",
            "section",
            "option",
            "letter",
            "name",
            "code",
            "max_capacity",
            "room",
            "description",
            "is_active",
        )

    def create(self, validated_data):
        return _service_call(self, academic_service.create_school_class, **validated_data)


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    current_class = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            "public_id",
            "matricule",
            "full_name",
            "sexe",
            "photo",
            "statut",
            "is_active",
            "current_class",
        )

    def get_full_name(self, obj):
        return " ".join(part for part in (obj.nom, obj.postnom, obj.prenom) if part)

    def get_current_class(self, obj):
        enrollments = getattr(obj, "current_enrollments", ())
        enrollment = enrollments[0] if enrollments else None
        if not enrollment:
            return None
        return {
            "public_id": str(enrollment.school_class.public_id),
            "name": enrollment.school_class.name,
            "academic_year": enrollment.academic_year.label,
        }


class StudentDetailSerializer(StudentListSerializer):
    class Meta(StudentListSerializer.Meta):
        fields = StudentListSerializer.Meta.fields + (
            "nom",
            "postnom",
            "prenom",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "adresse",
            "ancien_etablissement",
            "date_admission",
            "is_archived",
            "groupe_sanguin",
            "allergies",
            "conditions_medicales",
            "observations",
            "created_at",
            "updated_at",
        )


class StudentWriteSerializer(serializers.ModelSerializer):
    matricule = serializers.CharField(required=False, read_only=True)

    class Meta:
        model = Student
        fields = (
            "matricule",
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "adresse",
            "photo",
            "ancien_etablissement",
            "date_admission",
            "statut",
            "is_active",
            "groupe_sanguin",
            "allergies",
            "conditions_medicales",
            "observations",
        )

    def create(self, validated_data):
        return _service_call(self, student_service.create_student, **validated_data)

    def update(self, instance, validated_data):
        return _service_call(
            self,
            student_service.update_student,
            instance,
            **validated_data,
        )


class GuardianListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = (
            "public_id",
            "full_name",
            "telephone_principal",
            "email",
            "is_active",
            "is_archived",
        )

    def get_full_name(self, obj):
        return str(obj)


class GuardianDetailSerializer(GuardianListSerializer):
    class Meta(GuardianListSerializer.Meta):
        fields = GuardianListSerializer.Meta.fields + (
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "telephone_secondaire",
            "adresse",
            "profession",
            "numero_identification",
            "created_at",
            "updated_at",
        )


class GuardianWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = (
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "telephone_principal",
            "telephone_secondaire",
            "email",
            "adresse",
            "profession",
            "is_active",
        )

    def create(self, validated_data):
        return _service_call(self, guardian_service.create_guardian, **validated_data)

    def update(self, instance, validated_data):
        return _service_call(
            self,
            guardian_service.update_guardian,
            instance,
            **validated_data,
        )


class EnrollmentListSerializer(serializers.ModelSerializer):
    student = StudentListSerializer(read_only=True)
    academic_year = AcademicYearListSerializer(read_only=True)
    school_class = SchoolClassListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "public_id",
            "enrollment_number",
            "student",
            "academic_year",
            "school_class",
            "enrollment_type",
            "enrollment_date",
            "status",
        )


class EnrollmentDetailSerializer(EnrollmentListSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta(EnrollmentListSerializer.Meta):
        fields = EnrollmentListSerializer.Meta.fields + (
            "provenance",
            "observation",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {
            "public_id": str(obj.created_by.public_id),
            "username": obj.created_by.username,
        }


class EnrollmentWriteSerializer(serializers.ModelSerializer):
    student = PublicIdRelatedField(queryset=Student.objects.all())
    school_class = PublicIdRelatedField(queryset=SchoolClass.objects.all())
    force_over_capacity = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "student",
            "school_class",
            "enrollment_type",
            "enrollment_date",
            "status",
            "provenance",
            "observation",
            "force_over_capacity",
        )

    def create(self, validated_data):
        return _service_call(self, enrollment_service.create_enrollment, **validated_data)


class StudentCardListSerializer(serializers.ModelSerializer):
    student = StudentListSerializer(read_only=True)
    enrollment = serializers.SlugRelatedField(read_only=True, slug_field="public_id")

    class Meta:
        model = StudentCard
        fields = (
            "public_id",
            "card_number",
            "student",
            "enrollment",
            "generated_at",
            "expires_at",
            "is_active",
            "is_blocked",
        )


class StudentCardDetailSerializer(StudentCardListSerializer):
    class Meta(StudentCardListSerializer.Meta):
        fields = StudentCardListSerializer.Meta.fields + (
            "qr_identifier",
            "block_reason",
            "qr_image",
            "pdf_file",
            "updated_at",
        )


class StudentCardWriteSerializer(serializers.Serializer):
    enrollment = PublicIdRelatedField(queryset=Enrollment.objects.all())
    replace_existing = serializers.BooleanField(default=False)

    def create(self, validated_data):
        return _service_call(self, card_service.generate_card, **validated_data)


class CommunicationTargetSerializer(serializers.ModelSerializer):
    academic_year = PublicIdRelatedField(
        queryset=AcademicYear.objects.all(),
        required=False,
        allow_null=True,
    )
    level = PublicIdRelatedField(
        queryset=SchoolLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    section = PublicIdRelatedField(
        queryset=Section.objects.all(),
        required=False,
        allow_null=True,
    )
    option = PublicIdRelatedField(
        queryset=Option.objects.all(),
        required=False,
        allow_null=True,
    )
    school_class = PublicIdRelatedField(
        queryset=SchoolClass.objects.all(),
        required=False,
        allow_null=True,
    )
    student = PublicIdRelatedField(
        queryset=Student.objects.all(),
        required=False,
        allow_null=True,
    )
    guardian = PublicIdRelatedField(
        queryset=Guardian.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CommunicationTarget
        fields = (
            "target_type",
            "academic_year",
            "level",
            "section",
            "option",
            "school_class",
            "student",
            "guardian",
        )


class CommunicationListSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    target_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Communication
        fields = (
            "public_id",
            "title",
            "category",
            "priority",
            "status",
            "published_at",
            "expires_at",
            "author",
            "is_pinned",
            "target_count",
        )

    def get_author(self, obj):
        if not obj.author:
            return None
        return {
            "public_id": str(obj.author.public_id),
            "username": obj.author.username,
        }


class CommunicationDetailSerializer(CommunicationListSerializer):
    targets = CommunicationTargetSerializer(many=True, read_only=True)

    class Meta(CommunicationListSerializer.Meta):
        fields = CommunicationListSerializer.Meta.fields + (
            "content",
            "attachment",
            "targets",
            "created_at",
            "updated_at",
        )


class CommunicationWriteSerializer(serializers.ModelSerializer):
    targets = CommunicationTargetSerializer(many=True, required=False)

    class Meta:
        model = Communication
        fields = (
            "title",
            "content",
            "category",
            "priority",
            "expires_at",
            "attachment",
            "is_pinned",
            "targets",
        )

    def validate(self, attrs):
        if self.instance is None and not attrs.get("targets"):
            raise serializers.ValidationError(
                {"targets": "Au moins une cible de communication est requise."}
            )
        return attrs

    def create(self, validated_data):
        targets = validated_data.pop("targets")
        return _service_call(
            self,
            communication_service.create_draft,
            targets=targets,
            **validated_data,
        )

    def update(self, instance, validated_data):
        if "targets" in validated_data:
            raise serializers.ValidationError(
                {"targets": "Les cibles ne peuvent pas être remplacées après la création."}
            )
        if instance.status != Communication.Status.DRAFT:
            raise serializers.ValidationError(
                "Seul un brouillon peut être modifié."
            )
        return super().update(instance, validated_data)


class CardResolveSerializer(serializers.ModelSerializer):
    matricule = serializers.CharField(source="student.matricule")
    full_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source="enrollment.school_class.name")
    section = serializers.SerializerMethodField()
    option = serializers.SerializerMethodField()
    academic_year = serializers.CharField(source="enrollment.academic_year.label")
    card_status = serializers.SerializerMethodField()

    class Meta:
        model = StudentCard
        fields = (
            "matricule",
            "full_name",
            "class_name",
            "section",
            "option",
            "academic_year",
            "is_active",
            "is_blocked",
            "block_reason",
            "card_status",
        )

    def get_full_name(self, obj):
        student = obj.student
        return " ".join(
            part for part in (student.nom, student.postnom, student.prenom) if part
        )

    def get_section(self, obj):
        section = obj.enrollment.school_class.section
        return section.name if section else "Tronc commun"

    def get_option(self, obj):
        option = obj.enrollment.school_class.option
        return option.name if option else None

    def get_card_status(self, obj):
        if obj.is_blocked:
            return "blocked"
        return "active" if obj.is_active else "inactive"
