from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import EmailValidator


User = settings.AUTH_USER_MODEL


class ActivePortfolioProjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Template(models.Model):
    template_name = models.CharField(max_length=50, unique=True)
    template_preview = models.URLField(blank=True, null=True)
    template_url = models.URLField(blank=True, null=True)
    template_dom_tree = models.JSONField(null=True)
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
    project_slug = models.SlugField(unique=True, blank=True)
    portfolio_title = models.CharField(max_length=50, default="Portfolio")
    portfolio_description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deployed = models.BooleanField(default=False)
    deployed_url = models.URLField(default="")
    portofolio_contact_configured_email = models.EmailField(
        max_length=254,
        blank=True,
        validators=[EmailValidator(message="Please enter a valid email address.")],
    )
    is_verified_portfolio_contact_email = models.BooleanField(default=False)
    custom_domain_name = models.CharField(
        max_length=255, blank=True, null=True, default=""
    )
    pre_built_template = models.ForeignKey(
        Template, on_delete=models.CASCADE, null=True
    )
    is_deleted = models.BooleanField(default=False, null=True)

    objects = ActivePortfolioProjectManager()  # Default manager
    all_objects = models.Manager()  # Fallback to access all, including deleted

    def save(self, *args, **kwargs):
        # Propagate the deletion to the related CustomizedTemplate
        if not self.project_slug:
            self.project_slug = slugify(self.project_name)

        if self.is_deleted:
            customized_template = getattr(self, "customizedtemplate", None)
            if customized_template:
                customized_template.is_deleted = True
                customized_template.save()
        super(PortfolioProject, self).save(*args, **kwargs)

    def __str__(self):
        return f"Project id: {self.id} | Created by: {self.created_by.username} | Project Name: {self.project_name}"


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
    css = models.JSONField(default=dict)
    js = models.JSONField(default=dict)
    assests = models.JSONField(default=dict, null=True)
    sections = models.JSONField(default=dict, null=True)
    is_deleted = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f"Custom Template Id: {self.id}"
