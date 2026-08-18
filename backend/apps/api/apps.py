from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "api"
    verbose_name = "API"

    def ready(self) -> None:
        # Enregistre les signaux push (présence, paiement, incident, convocation).
        from apps.api import parents_push_signals  # noqa: F401
