from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    LoginView,
    ProfileView,
    RoleListView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserPasswordResetView,
    UserStatusView,
    UserUpdateView,
    logout_view,
)

app_name = "accounts"

urlpatterns = [
    path("connexion/", LoginView.as_view(), name="login"),
    path("deconnexion/", logout_view, name="logout"),
    path("utilisateurs/", UserListView.as_view(), name="users"),
    path("utilisateurs/nouveau/", UserCreateView.as_view(), name="user_create"),
    path("utilisateurs/<uuid:public_id>/", UserDetailView.as_view(), name="user_detail"),
    path("utilisateurs/<uuid:public_id>/modifier/", UserUpdateView.as_view(), name="user_update"),
    path(
        "utilisateurs/<uuid:public_id>/statut/<str:action>/",
        UserStatusView.as_view(),
        name="user_status",
    ),
    path(
        "utilisateurs/<uuid:public_id>/mot-de-passe/",
        UserPasswordResetView.as_view(),
        name="user_reset_password",
    ),
    path("roles/", RoleListView.as_view(), name="roles"),
    path("profil/", ProfileView.as_view(), name="profile"),
    path("profil/mot-de-passe/", ChangePasswordView.as_view(), name="change_password"),
]
