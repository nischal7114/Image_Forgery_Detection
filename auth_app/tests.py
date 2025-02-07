from django.test import TestCase
from .models import Role, User

class AuthAppTests(TestCase):
    def setUp(self):
        # Create a role and user for testing
        self.role = Role.objects.create(name="Investigator")
        self.user = User.objects.create_user(username="testuser", password="testpassword", role=self.role)

    def test_user_creation(self):
        """Test that a user is created with the correct username and role"""
        self.assertEqual(self.user.username, "testuser")
        self.assertTrue(self.user.check_password("testpassword"))
        self.assertEqual(self.user.role.name, "Investigator")

    def test_valid_login(self):
        """Test that a valid user can log in"""
        login_successful = self.client.login(username="testuser", password="testpassword")
        self.assertTrue(login_successful)

    def test_invalid_login(self):
        """Test that login fails with invalid credentials"""
        login_successful = self.client.login(username="invaliduser", password="wrongpassword")
        self.assertFalse(login_successful)

    def test_login_without_role(self):
        """Test that a user without a role can still log in (if allowed)"""
        # Create a user without a role
        no_role_user = User.objects.create_user(username="noroleuser", password="nopass")
        login_successful = self.client.login(username="noroleuser", password="nopass")
        self.assertTrue(login_successful)
