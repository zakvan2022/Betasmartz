from django.contrib import admin
from .models import DocumentUpload


class DocumentUploadAdmin(admin.ModelAdmin):
    model = DocumentUpload


admin.site.register(DocumentUpload, DocumentUploadAdmin)
