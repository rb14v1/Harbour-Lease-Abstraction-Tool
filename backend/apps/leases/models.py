from django.conf import settings
from django.db import models


class Property(models.Model):
    TYPE_OFFICE = "office"
    TYPE_RETAIL = "retail"
    TYPE_RESIDENTIAL = "residential"
    TYPE_CHOICES = [
        (TYPE_OFFICE, "Office"),
        (TYPE_RETAIL, "Retail"),
        (TYPE_RESIDENTIAL, "Residential"),
    ]

    address = models.CharField(max_length=255)
    property_type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_OFFICE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "properties"

    def __str__(self):
        return self.address


class Lease(models.Model):
    STATUS_UPLOADED = "uploaded"
    STATUS_PROCESSING = "processing"
    STATUS_PROCESSED = "processed"
    STATUS_CHOICES = [
        (STATUS_UPLOADED, "Uploaded"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PROCESSED, "Processed"),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
    tenant_name = models.CharField(max_length=255)
    landlord_name = models.CharField(max_length=255)
    blob_path = models.CharField(max_length=512, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_UPLOADED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant_name} @ {self.property.address}"


class LeaseTerm(models.Model):
    TERM_RENT = "rent"
    TERM_RENEWAL = "renewal"
    TERM_TERMINATION = "termination"
    TERM_MAINTENANCE = "maintenance"
    TERM_TYPE_CHOICES = [
        (TERM_RENT, "Rent"),
        (TERM_RENEWAL, "Renewal"),
        (TERM_TERMINATION, "Termination"),
        (TERM_MAINTENANCE, "Maintenance"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="terms")
    term_type = models.CharField(max_length=32, choices=TERM_TYPE_CHOICES)
    extracted_value = models.TextField()
    source_page = models.PositiveIntegerField()

    class Meta:
        ordering = ["source_page"]

    def __str__(self):
        return f"{self.term_type} ({self.lease_id})"


class LeaseChunk(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="chunks")
    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    search_doc_id = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["lease", "chunk_index"], name="unique_lease_chunk_index"
            )
        ]

    def __str__(self):
        return f"chunk {self.chunk_index} ({self.lease_id})"


class LeaseQuery(models.Model):
    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lease_queries"
    )
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="queries")
    question_text = models.TextField()
    answer_text = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Q({self.lease_id}): {self.question_text[:40]}"
