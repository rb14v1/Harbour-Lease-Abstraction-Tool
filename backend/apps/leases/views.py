from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Lease, LeaseQuery, Property
from .permissions import IsAdminOrPropertyManager
from .serializers import (
    AskQuestionSerializer,
    LeaseQuerySerializer,
    LeaseSerializer,
    LeaseTermSerializer,
    LeaseUploadSerializer,
    PropertySerializer,
)
from apps.common import blob_store


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAdminOrPropertyManager]


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAdminOrPropertyManager]

    def get_queryset(self):
        return Lease.objects.select_related("property").all()

    def create(self, request, *args, **kwargs):
        """Upload a lease document: stores via blob_store, creates Lease(status=uploaded)."""
        serializer = LeaseUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        uploaded_file = data.pop("file")
        blob_name = f"lease_{uploaded_file.name}"
        blob_path = blob_store.upload_document(
            uploaded_file, container="lease-documents", blob_name=blob_name
        )

        lease = Lease.objects.create(blob_path=blob_path, status=Lease.STATUS_UPLOADED, **data)
        return Response(LeaseSerializer(lease).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """Runs extract -> chunk -> embed -> index pipeline, sets status to processed."""
        lease = self.get_object()
        lease = services.process_lease(lease)
        return Response(LeaseSerializer(lease).data)

    @action(detail=True, methods=["get"])
    def terms(self, request, pk=None):
        lease = self.get_object()
        return Response(LeaseTermSerializer(lease.terms.all(), many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="queries")
    def queries(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            return Response(
                LeaseQuerySerializer(lease.queries.all(), many=True).data
            )

        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = services.ask_question(
            lease, request.user, serializer.validated_data["question_text"]
        )
        return Response(
            LeaseQuerySerializer(query).data, status=status.HTTP_201_CREATED
        )
