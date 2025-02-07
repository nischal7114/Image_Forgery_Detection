import os
import io
import hashlib
import uuid
import imagehash
import nacl.signing
import nacl.encoding
from django.db import models
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image as PILImage
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.html import format_html

User = get_user_model()

def case_image_upload_path(instance, filename):
    """Generate a unique filename while storing the original name."""
    ext = filename.split('.')[-1]  # Extract file extension
    unique_filename = f"{uuid.uuid4().hex}.{ext}"  # Generate UUID-based filename
    return os.path.join(f'cases/{instance.case.id}/', unique_filename)

class Case(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    investigator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="cases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tampering_threshold = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name

class Image(models.Model):
    case = models.ForeignKey('Case', on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=case_image_upload_path)
    original_filename = models.CharField(max_length=255, blank=True, null=True)  # Store original filename
    sha256_hash = models.CharField(max_length=64, blank=True, null=True)
    perceptual_hash = models.CharField(max_length=64, blank=True, null=True)
    digital_signature = models.TextField(blank=True, null=True)
    public_key = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def thumbnail(self):
        """Generate a small thumbnail preview for admin display."""
        try:
            if self.image:
                return format_html('<img src="{}" style="width: 100px; height: auto;" />', self.image.url)
            return "No Image"
        except Exception:
            return "Error loading thumbnail"

    def compute_sha256(self, file):
        """Compute SHA-256 hash of the original image."""
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()

    def compute_perceptual_hash(self, file):
        """Compute Perceptual Hash (pHash) for detecting image tampering."""
        img = PILImage.open(file)
        return str(imagehash.phash(img))

    def generate_keys(self):
        """Generate Ed25519 key pair (Private & Public Key)."""
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        self.public_key = verify_key.encode(encoder=nacl.encoding.Base64Encoder).decode()
        return signing_key

    def sign_data(self, data):
        """Sign data using the Ed25519 private key."""
        signing_key = self.generate_keys()
        signature = signing_key.sign(data.encode(), encoder=nacl.encoding.Base64Encoder)
        return signature.signature.decode()

    def verify_signature(self):
        """Verify the digital signature."""
        if not self.digital_signature or not self.public_key:
            return False
        try:
            verify_key = nacl.signing.VerifyKey(self.public_key.encode(), encoder=nacl.encoding.Base64Encoder)
            verify_key.verify(self.sha256_hash.encode(), nacl.encoding.Base64Encoder.decode(self.digital_signature.encode()))
            return True
        except nacl.exceptions.BadSignatureError:
            return False

    def save(self, *args, **kwargs):
        """Override save method to store original filename and compute hashes."""
        if not self.original_filename:
            self.original_filename = os.path.basename(self.image.name)  # Store original file name

        # Compute SHA-256 hash
        if not self.sha256_hash:
            self.sha256_hash = self.compute_sha256(self.image)

        # Compute Perceptual Hash
        if not self.perceptual_hash:
            self.perceptual_hash = self.compute_perceptual_hash(self.image)

        # Generate and store a digital signature
        if not self.digital_signature:
            self.digital_signature = self.sign_data(self.sha256_hash)

        # Convert image to RGB and compress it
        img = PILImage.open(self.image)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        output_io_stream = io.BytesIO()
        img.save(output_io_stream, format='JPEG', quality=70)
        output_io_stream.seek(0)

        self.image = ContentFile(output_io_stream.read(), name=self.image.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case.name} - {self.original_filename or 'Unnamed Image'}"

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True, related_name="logs")
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)  # Additional details for tampering detection
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown User'} - {self.action} at {self.timestamp}"

@receiver(post_save, sender=Case)
def log_case_creation(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.investigator,
            action=f"Created case: {instance.name}",
            case=instance
        )

@receiver(post_save, sender=Image)
def log_image_upload(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.case.investigator,
            action=f"Uploaded image '{instance.original_filename}' to case: {instance.case.name}",
            case=instance.case
        )

@receiver(post_delete, sender=Case)
def log_case_deletion(sender, instance, **kwargs):
    ActivityLog.objects.filter(case=instance).delete()  # Ensure all logs are deleted
    ActivityLog.objects.create(
        user=instance.investigator,
        action=f"Deleted case: {instance.name}",
        case=instance
    )

@receiver(post_delete, sender=Image)
def log_image_deletion(sender, instance, **kwargs):
    ActivityLog.objects.filter(case=instance.case, details__icontains=instance.original_filename).delete()
    ActivityLog.objects.create(
        user=instance.case.investigator,
        action=f"Deleted image '{instance.original_filename}' from case: {instance.case.name}",
        case=instance.case
    )
