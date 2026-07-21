"""School class forms."""

from apps.secretariat.models import SchoolClass

from .academic import StyledModelForm


class SchoolClassForm(StyledModelForm):
    class Meta:
        model = SchoolClass
        fields = (
            "academic_year", "level", "section", "option", "name", "code",
            "max_capacity", "room", "description", "is_active",
        )
        labels = {
            "academic_year": "Année scolaire", "level": "Niveau", "section": "Section",
            "option": "Option", "name": "Nom", "code": "Code",
            "max_capacity": "Capacité maximale", "room": "Local",
            "description": "Description", "is_active": "Active",
        }
