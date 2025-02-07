from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Case, Image, ActivityLog

User = get_user_model()

class CaseAppTests(TestCase):
    def setUp(self):
        """
        Set up a test user and initial data.
        """
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.admin_user = User.objects.create_superuser(username="adminuser", password="adminpassword")
        self.case = Case.objects.create(
            name="Test Case",
            description="A test case description",
            investigator=self.user
        )

    # Test Case Model
    def test_case_creation(self):
        """
        Test if a case can be created successfully.
        """
        self.assertEqual(self.case.name, "Test Case")
        self.assertEqual(self.case.description, "A test case description")
        self.assertEqual(self.case.investigator, self.user)
        self.assertIsNotNone(self.case.created_at)

    def test_case_update(self):
        """
        Test if a case can be updated.
        """
        self.case.name = "Updated Test Case"
        self.case.save()
        self.assertEqual(self.case.name, "Updated Test Case")

    # Test Image Model
    def test_image_upload(self):
        """
        Test if an image can be uploaded to a case.
        """
        image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        uploaded_image = Image.objects.create(case=self.case, image=image)
        self.assertEqual(uploaded_image.case, self.case)
        self.assertTrue(uploaded_image.image.name.endswith("test_image.jpg"))

    # Test Activity Logging
    def test_activity_log_creation(self):
        """
        Test if an activity log is created successfully.
        """
        log = ActivityLog.objects.create(user=self.user, action="Created a case")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "Created a case")
        self.assertIsNotNone(log.timestamp)

    # Test Permissions
    def test_case_creation_permission(self):
        """
        Test if only logged-in users can create cases.
        """
        self.client.login(username="testuser", password="testpassword")
        response = self.client.post("/cases/create/", {
            "name": "Permission Test Case",
            "description": "Testing permissions"
        })
        self.assertEqual(response.status_code, 302)  # Redirect indicates success
        self.assertTrue(Case.objects.filter(name="Permission Test Case").exists())

    def test_unauthenticated_user_access(self):
        """
        Test that unauthenticated users cannot create cases.
        """
        response = self.client.post("/cases/create/", {
            "name": "Unauthenticated Test Case",
            "description": "Should not be created"
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        self.assertFalse(Case.objects.filter(name="Unauthenticated Test Case").exists())
