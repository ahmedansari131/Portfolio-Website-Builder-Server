from django.contrib import admin
from .models import Template, CustomizedTemplate, PortfolioProject

admin.site.register(Template)
admin.site.register(CustomizedTemplate)
admin.site.register(PortfolioProject)