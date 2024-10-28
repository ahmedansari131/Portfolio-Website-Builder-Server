from django.contrib import admin
from .models import (
    Template,
    CustomizedTemplate,
    PortfolioProject,
    DeletedPortfolioProject,
)

admin.site.register(Template)
admin.site.register(CustomizedTemplate)


class PortfolioProjectAdmin(admin.ModelAdmin):
    list_display = ["project_name", "is_deleted"]

    def get_queryset(self, request):
        # Only show items marked as deleted
        return PortfolioProject.all_objects.filter(is_deleted=False)


admin.site.register(PortfolioProject, PortfolioProjectAdmin)


class DeletedPortfolioProjectAdmin(admin.ModelAdmin):
    list_display = ["project_name", "is_deleted"]

    def get_queryset(self, request):
        # Only show items marked as deleted
        return PortfolioProject.all_objects.filter(is_deleted=True)

    # Optional: Action to recover deleted projects
    actions = ["recover_projects"]

    def recover_projects(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Selected projects have been recovered.")

    recover_projects.short_description = "Recover selected deleted projects"


admin.site.register(DeletedPortfolioProject, DeletedPortfolioProjectAdmin)
