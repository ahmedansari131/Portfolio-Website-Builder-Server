from django.urls import path
from .views import Project

urlpatterns = [
    path(
        "create-project/", Project.as_view(), name="create_project"
    ),
]
