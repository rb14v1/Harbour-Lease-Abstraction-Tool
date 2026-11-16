from django.contrib import admin

from .models import Lease, LeaseChunk, LeaseQuery, LeaseTerm, Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["id", "address", "property_type", "created_at"]
    search_fields = ["address"]


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ["id", "tenant_name", "property", "status", "start_date", "end_date"]
    list_filter = ["status", "property__property_type"]
    search_fields = ["tenant_name", "landlord_name"]


@admin.register(LeaseTerm)
class LeaseTermAdmin(admin.ModelAdmin):
    list_display = ["id", "lease", "term_type", "source_page"]
    list_filter = ["term_type"]


@admin.register(LeaseChunk)
class LeaseChunkAdmin(admin.ModelAdmin):
    list_display = ["id", "lease", "chunk_index", "search_doc_id"]


@admin.register(LeaseQuery)
class LeaseQueryAdmin(admin.ModelAdmin):
    list_display = ["id", "lease", "asked_by", "created_at"]
