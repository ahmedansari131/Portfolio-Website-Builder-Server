from django.urls import path
from .views import (
    Project,
    UploadTemplate,
    ListTemplates,
    ListPortfolioProject,
    UpdateCustomizeTemplate,
    UpdateProjectImageOrDocument,
    Deployment,
    DeletePortfolioProject,
    PortfolioDomain,
    PortfolioEmailSend,
    SendPortfolioContactEmailVerificationEmail,
)
from authentication.views import UserEmailVerification

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
        "update-project-image/",
        UpdateProjectImageOrDocument.as_view(),
        name="update_project_image",
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
    path(
        "delete-project/<str:project_id>/",
        DeletePortfolioProject.as_view(),
        name="delete_project",
    ),
    path(
        "send-portfolio-verification-email/",
        SendPortfolioContactEmailVerificationEmail.as_view(),
        name="send_portfolio_contact_email",
    ),
    path(
        "send-portfolio-email/",
        PortfolioEmailSend.as_view(),
        name="send_portfolio_email",
    ),
    path(
        "check-domain-availability/",
        PortfolioDomain.as_view(),
        name="check_domain_availability",
    ),
]
