from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordReset


class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "is_admin", "is_active")
    list_filter = ("is_admin",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "profile_image", "is_terms_agree")}),
        ("Permissions", {"fields": ("is_admin", "is_active", "is_superuser")}),
        ("Other", {"fields": ("profile_placeholder_color_code", "refresh_token", "provider")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
    search_fields = ("email", "username")
    ordering = ("email",)
    filter_horizontal = ()


admin.site.register(User, UserAdmin)
admin.site.register(PasswordReset)
