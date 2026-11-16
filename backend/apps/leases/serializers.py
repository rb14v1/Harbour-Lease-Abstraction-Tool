from rest_framework import serializers

from .models import Lease, LeaseChunk, LeaseQuery, LeaseTerm, Property


class PropertySerializer(serializers.ModelSerializer):
    lease_count = serializers.IntegerField(source="leases.count", read_only=True)

    class Meta:
        model = Property
        fields = ["id", "address", "property_type", "created_at", "lease_count"]
        read_only_fields = ["id", "created_at"]


class LeaseTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseTerm
        fields = ["id", "lease", "term_type", "extracted_value", "source_page"]
        read_only_fields = fields


class LeaseChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseChunk
        fields = ["id", "lease", "chunk_text", "chunk_index", "search_doc_id"]
        read_only_fields = fields


class LeaseSerializer(serializers.ModelSerializer):
    property_address = serializers.CharField(source="property.address", read_only=True)

    class Meta:
        model = Lease
        fields = [
            "id",
            "property",
            "property_address",
            "tenant_name",
            "landlord_name",
            "blob_path",
            "start_date",
            "end_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "blob_path", "status", "created_at", "updated_at"]


class LeaseUploadSerializer(serializers.Serializer):
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    tenant_name = serializers.CharField(max_length=255)
    landlord_name = serializers.CharField(max_length=255)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    file = serializers.FileField()


class LeaseQuerySerializer(serializers.ModelSerializer):
    asked_by_email = serializers.CharField(source="asked_by.email", read_only=True)

    class Meta:
        model = LeaseQuery
        fields = [
            "id",
            "lease",
            "asked_by",
            "asked_by_email",
            "question_text",
            "answer_text",
            "retrieved_chunk_ids",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "lease",
            "asked_by",
            "asked_by_email",
            "answer_text",
            "retrieved_chunk_ids",
            "created_at",
        ]


class AskQuestionSerializer(serializers.Serializer):
    question_text = serializers.CharField()
