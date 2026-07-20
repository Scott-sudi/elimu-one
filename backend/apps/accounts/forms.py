"""Django forms for accounts and setup."""

from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User


class SetupAdministratorForm(forms.Form):
    nom = forms.CharField(label="Nom", max_length=100)
    postnom = forms.CharField(label="Postnom", max_length=100, required=False)
    prenom = forms.CharField(label="Prénom", max_length=100)
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    email = forms.EmailField(label="Adresse électronique", required=False)
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Le nom d'utilisateur existe déjà.")
        return username

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Les mots de passe ne correspondent pas.")
        if password:
            validate_password(password)
        return cleaned


class LoginForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)


class UserCreateForm(forms.Form):
    nom = forms.CharField(label="Nom", max_length=100)
    postnom = forms.CharField(label="Postnom", max_length=100, required=False)
    prenom = forms.CharField(label="Prénom", max_length=100)
    sexe = forms.ChoiceField(
        label="Sexe",
        choices=[("", "—")] + list(User.Gender.choices),
        required=False,
    )
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    email = forms.EmailField(label="Adresse électronique", required=False)
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    role_id = forms.ModelChoiceField(label="Rôle", queryset=Role.objects.filter(is_active=True))
    is_active = forms.BooleanField(label="Compte actif", required=False, initial=True)
    password = forms.CharField(label="Mot de passe temporaire", widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirmation", widget=forms.PasswordInput)
    must_change_password = forms.BooleanField(
        label="Obliger le changement de mot de passe",
        required=False,
        initial=True,
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Le nom d'utilisateur existe déjà.")
        return username

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Les mots de passe ne correspondent pas.")
        if password:
            validate_password(password)
        role = cleaned.get("role_id")
        if role:
            cleaned["role_id"] = role.pk
        return cleaned


class UserUpdateForm(forms.Form):
    nom = forms.CharField(label="Nom", max_length=100)
    postnom = forms.CharField(label="Postnom", max_length=100, required=False)
    prenom = forms.CharField(label="Prénom", max_length=100)
    sexe = forms.ChoiceField(
        label="Sexe",
        choices=[("", "—")] + list(User.Gender.choices),
        required=False,
    )
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    email = forms.EmailField(label="Adresse électronique", required=False)
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    role_id = forms.ModelChoiceField(label="Rôle", queryset=Role.objects.filter(is_active=True))
    is_active = forms.BooleanField(label="Compte actif", required=False)
    must_change_password = forms.BooleanField(
        label="Obliger le changement de mot de passe",
        required=False,
    )

    def __init__(self, *args, user: User | None = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("Le nom d'utilisateur existe déjà.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role_id")
        if role:
            cleaned["role_id"] = role.pk
        return cleaned


class PasswordResetForm(forms.Form):
    temporary_password = forms.CharField(label="Mot de passe temporaire", widget=forms.PasswordInput)
    temporary_password_confirm = forms.CharField(label="Confirmation", widget=forms.PasswordInput)
    must_change_password = forms.BooleanField(
        label="Obliger le changement à la prochaine connexion",
        required=False,
        initial=True,
    )

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("temporary_password")
        confirm = cleaned.get("temporary_password_confirm")
        if password and confirm and password != confirm:
            self.add_error("temporary_password_confirm", "Les mots de passe ne correspondent pas.")
        if password:
            validate_password(password)
        return cleaned


class ProfileForm(forms.Form):
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    email = forms.EmailField(label="Adresse électronique", required=False)


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(label="Ancien mot de passe", widget=forms.PasswordInput)
    new_password = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput)
    new_password_confirm = forms.CharField(label="Confirmation", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("new_password")
        confirm = cleaned.get("new_password_confirm")
        if password and confirm and password != confirm:
            self.add_error("new_password_confirm", "Les mots de passe ne correspondent pas.")
        if password:
            validate_password(password)
        return cleaned
