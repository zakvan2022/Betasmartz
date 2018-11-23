from django.db import models


# Create your models here.
class DocumentUpload(models.Model):
    name = models.CharField(max_length=255)
    upload = models.FileField()

    def __str__(self):
        return self.name
