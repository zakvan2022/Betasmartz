import logging
from rest_framework import serializers
from api.v1.serializers import ReadOnlyModelSerializer
from documents.models import DocumentUpload
logger = logging.getLogger('api.v1.documents.serializers')


class DocumentUploadSerializer(ReadOnlyModelSerializer):

    class Meta:
        model = DocumentUpload
