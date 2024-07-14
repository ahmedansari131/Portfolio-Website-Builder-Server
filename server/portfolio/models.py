from django.db import models
from django.conf import settings


User = settings.AUTH_USER_MODEL


class Template(models.Model):
    template_name = models.CharField(max_length=50, unique=True)
    template_preview = models.URLField(blank=True, null=True)
    template_url = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    liked = models.IntegerField(default=0, null=True)
    saved = models.IntegerField(default=0, null=True)
    bucket_name = models.CharField(max_length=100, null=True)
    cloudfront_domain = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"Template: { self.id}"


class PortfolioProject(models.Model):
    project_name = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deployed = models.BooleanField(default=False)
    deployed_url = models.URLField(default="")

    def __str__(self):
        return f"Project name: {self.project_name} | Created by: {self.created_by}"


class CustomizedTemplate(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    portfolio_project = models.OneToOneField(
        PortfolioProject, on_delete=models.CASCADE, default=""
    )
    title = models.CharField(max_length=50, default="Portfolio")
    meta = models.JSONField(default=dict)
    links = models.JSONField(default=dict)
    scripts = models.JSONField(default=dict)
    body = models.JSONField(default=dict)
    style = models.JSONField(default=dict)
    css = models.URLField(default="")
    js = models.URLField(default="")
