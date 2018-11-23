import logging
from . import serializers
from rest_framework import viewsets
from api.v1.views import ReadOnlyApiViewMixin
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_extensions.mixins import NestedViewSetMixin
from documents.models import DocumentUpload
logger = logging.getLogger('api.v1.documents.views')


class DocumentsViewSet(ReadOnlyApiViewMixin, NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    model = DocumentUpload
    queryset = DocumentUpload.objects.all()
    permission_classes = (
        IsAuthenticated,
    )

    serializer_class = serializers.DocumentUploadSerializer
