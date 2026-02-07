# core/models/user_profile.py

from django.conf import settings
from django.db import models

from core.validators import (
    validate_image_extension,
    validate_image_mime,
    FileSizeValidator,
    ImageDimensionsValidator,
)

def signature_upload_path(instance, filename):
    return f"signatures/user_{instance.user_id}/{filename}"

class UserProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    title = models.CharField(max_length=100, blank=True, default="")
    signature = models.ImageField(
            upload_to=signature_upload_path, 
            null=True, 
            blank=True,
            validators=[
                validate_image_extension,
                validate_image_mime,
                FileSizeValidator(1),              # ✅ 1 MB (ganti 0.5 kalau mau 500KB)
                ImageDimensionsValidator(1200, 600) # ✅ opsional
            ]    
            
    )

    def __str__(self):
        return f"Profile: {self.user}"
