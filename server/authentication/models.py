from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)
import os


def user_profile_picture_upload_to(instance, filename):
    # Using the user ID or username for the folder
    return os.path.join(f"user-{str(instance.id)}", "profile-pictures", filename)


class Provider(models.TextChoices):
    GOOGLE = "google", "Google"
    EMAIL = "email_password", "Email/Password"


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("User must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None):
        user = self.create_user(
            email,
            password=password,
            username=username,
        )
        user.is_admin = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name="Email",
        max_length=100,
        unique=True,
    )
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    profile_image = models.ImageField(
        "Profile image",
        default="",
        upload_to=user_profile_picture_upload_to,
    )
    profile_placeholder_color_code = models.CharField(
        max_length=7, null=True, blank=True
    )
    refresh_token = models.TextField(null=True)
    is_terms_agree = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    provider = models.CharField(
        max_length=50, choices=Provider.choices, default=Provider.EMAIL
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return self.is_admin

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    signin_token = models.CharField(max_length=256, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    otp = models.CharField(max_length=6)
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)
