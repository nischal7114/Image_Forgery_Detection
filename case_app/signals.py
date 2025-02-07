from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Case, Image, ActivityLog

# Log case creation
@receiver(post_save, sender=Case)
def log_case_creation(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.investigator,
            action=f"Created case: {instance.name}",
            case=instance,
        )

# Log image upload
@receiver(post_save, sender=Image)
def log_image_upload(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.case.investigator,
            action=f"Uploaded image to case: {instance.case.name}",
            case=instance.case,
        )

# Log image deletion
@receiver(post_delete, sender=Image)
def log_image_deletion(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=instance.case.investigator,
        action=f"Deleted image from case: {instance.case.name}",
        case=instance.case,
    )
