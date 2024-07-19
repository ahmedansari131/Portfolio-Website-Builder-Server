from django.urls import path
from .views import Project, UploadTemplate, ListTemplates, ListPortfolioProject

urlpatterns = [
    path("create-project/", Project.as_view(), name="create_project"),
    path(
        "get-custom-template-data/<custom_template_id>/<portfolio_project_id>/",
        Project.as_view(),
        name="get_template_data",
    ),
    path(
        "upload-template/<template_name>/",
        UploadTemplate.as_view(),
        name="upload_template",
    ),
    path("list-templates/", ListTemplates.as_view(), name="list_templates"),
    path(
        "list-portfolio-projects/",
        ListPortfolioProject.as_view(),
        name="list_portfolio_projects",
    ),
]
