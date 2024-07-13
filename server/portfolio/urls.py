from django.urls import path
from .views import Project, UploadTemplate ,ListTemplates

urlpatterns = [
    path("create-project/", Project.as_view(), name="create_project"),
    path("upload-template/<template_name>/", UploadTemplate.as_view(), name="upload_template"),
    path("list-templates/", ListTemplates.as_view(), name="list_templates"),
]
