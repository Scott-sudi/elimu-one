from django.test import TestCase
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


class LogoutAPIViewTests(TestCase):
	def test_logout_blacklists_refresh_token(self):
		user = User.objects.create_user(
			username="api-test-user",
			password="secure-test-password",
			nom="Api",
			prenom="Test",
		)
		refresh = RefreshToken.for_user(user)
		self.client.force_login(user)

		response = self.client.post(
			"/api/v1/auth/logout/",
			data={"refresh": str(refresh)},
			content_type="application/json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		with self.assertRaises(TokenError):
			RefreshToken(str(refresh)).check_blacklist()
