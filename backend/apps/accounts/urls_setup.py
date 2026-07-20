from django.urls import path

from apps.accounts.views import SetupView

app_name = "setup"

urlpatterns = [
    path("", SetupView.as_view(), name="setup"),
]
