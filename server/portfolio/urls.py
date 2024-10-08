from django.urls import path
from .views import Project, UploadTemplate, ListTemplates, ListPortfolioProject, UpdateCustomizeTemplate, Deployment

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
    path(
        "update-dom-data/",
        UpdateCustomizeTemplate.as_view(),
        name="update_dom_data",
    ),
    path(
        "deploy-portfolio/",
        Deployment.as_view(),
        name="deploy_portfolio",
    ),
    path(
        "list-deployed-portfolio/",
        Deployment.as_view(),
        name="list_deployed_portfolio",
    ),
]
