"""
Idempotent seed data migration.

Creates demo users, properties, leases (with terms + chunks already
populated), and a handful of sample LeaseQuery history rows.

Uses RunPython + get_or_create throughout (never set_password() on a
historical model -- django.contrib.auth.hashers.make_password() is used
instead, since historical models from apps.get_model() do not carry the
real model's set_password() method).

Term extraction and chunking call straight into apps.common (plain,
model-free utility modules) so the same deterministic stub logic used at
runtime is used here -- no network access, fully reproducible.
"""
import datetime

from django.contrib.auth.hashers import make_password
from django.db import migrations

from apps.common import ai, document_intelligence, search_store

SEARCH_INDEX = "lease_chunks"
CHUNK_SIZE_CHARS = 500

DEMO_PASSWORD = "Demo1234!"


def _chunk_text(text, chunk_size=CHUNK_SIZE_CHARS):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _lease_document_text(tenant_name, landlord_name, address, lease_no):
    return (
        f"LEASE AGREEMENT #{lease_no}\n\n"
        f"This lease is between landlord {landlord_name} and tenant {tenant_name} "
        f"for the premises located at {address}.\n\n"
        f"RENT. Tenant shall pay monthly base rent to {landlord_name} on the first "
        f"day of each month for the premises at {address}, lease #{lease_no}.\n\n"
        f"RENEWAL. {tenant_name} may renew this lease by providing written notice to "
        f"{landlord_name} prior to the expiration of the term, lease #{lease_no}.\n\n"
        f"TERMINATION. Either party may terminate this lease for {tenant_name} at "
        f"{address} by providing advance written notice, lease #{lease_no}.\n\n"
        f"MAINTENANCE. Responsibility for maintenance and repairs at {address} is "
        f"allocated between {landlord_name} and {tenant_name}, lease #{lease_no}.\n\n"
        f"ADDITIONAL PROVISIONS. This lease #{lease_no} for {tenant_name} is governed "
        f"by the laws applicable to {address} and binds {landlord_name} and "
        f"{tenant_name} and their respective successors and assigns."
    )


PROPERTIES = [
    ("100 Market Street, San Francisco, CA", "office"),
    ("250 Retail Row, Austin, TX", "retail"),
    ("77 Harbor View Apartments, Seattle, WA", "residential"),
    ("12 Innovation Drive, Boston, MA", "office"),
    ("900 Commerce Plaza, Chicago, IL", "retail"),
    ("4 Lakeside Residences, Denver, CO", "residential"),
]

LEASES = [
    # (property_index, tenant_name, landlord_name, start, end)
    (0, "Acme Consulting LLC", "Market Street Holdings", "2023-01-01", "2026-12-31"),
    (0, "Bright Analytics Inc", "Market Street Holdings", "2022-06-01", "2025-05-31"),
    (1, "Retail Dynamics Co", "Row Property Partners", "2023-03-01", "2028-02-28"),
    (1, "Sunrise Boutique LLC", "Row Property Partners", "2021-09-01", "2024-08-31"),
    (2, "Harbor Residential Mgmt", "Harbor View Trust", "2024-01-01", "2025-12-31"),
    (3, "Innovate Robotics Inc", "Drive Commercial REIT", "2022-01-01", "2027-01-01"),
    (4, "Plaza Fashion Group", "Commerce Plaza LP", "2023-07-01", "2026-06-30"),
    (5, "Lakeside Property Services", "Lakeside Holdings LLC", "2024-02-01", "2026-01-31"),
]

SAMPLE_QUESTIONS = [
    "What is the monthly rent for this lease?",
    "How much notice is required to terminate this lease?",
    "Who is responsible for maintenance and repairs?",
]


def seed_data(apps, schema_editor):
    User = apps.get_model("users", "User")
    Property = apps.get_model("leases", "Property")
    Lease = apps.get_model("leases", "Lease")
    LeaseTerm = apps.get_model("leases", "LeaseTerm")
    LeaseChunk = apps.get_model("leases", "LeaseChunk")
    LeaseQuery = apps.get_model("leases", "LeaseQuery")

    pm_user, _ = User.objects.get_or_create(
        email="pm@example.com",
        defaults={
            "first_name": "Priya",
            "last_name": "Manager",
            "role": "property_manager",
            "is_staff": False,
            "is_superuser": False,
            "password": make_password(DEMO_PASSWORD),
        },
    )
    admin_user, _ = User.objects.get_or_create(
        email="admin@example.com",
        defaults={
            "first_name": "Alex",
            "last_name": "Admin",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
            "password": make_password(DEMO_PASSWORD),
        },
    )

    property_objs = []
    for address, property_type in PROPERTIES:
        prop, _ = Property.objects.get_or_create(
            address=address, defaults={"property_type": property_type}
        )
        property_objs.append(prop)

    search_store.reset_index(SEARCH_INDEX)

    lease_objs = []
    for idx, (prop_idx, tenant, landlord, start, end) in enumerate(LEASES):
        prop = property_objs[prop_idx]
        lease, created = Lease.objects.get_or_create(
            property=prop,
            tenant_name=tenant,
            landlord_name=landlord,
            defaults={
                "blob_path": f"stub://lease-documents/seed_lease_{idx}.txt",
                "start_date": datetime.date.fromisoformat(start),
                "end_date": datetime.date.fromisoformat(end),
                "status": "processed",
            },
        )
        lease_objs.append(lease)

        if not created:
            continue

        document_text = _lease_document_text(tenant, landlord, prop.address, idx + 1)
        raw_bytes = document_text.encode("utf-8")

        for term in document_intelligence.extract_lease_terms(raw_bytes):
            LeaseTerm.objects.get_or_create(
                lease=lease,
                term_type=term["term_type"],
                source_page=term["source_page"],
                defaults={"extracted_value": term["extracted_value"]},
            )

        search_items = []
        for chunk_idx, chunk in enumerate(_chunk_text(document_text)):
            search_doc_id = f"lease-{lease.id}-chunk-{chunk_idx}"
            LeaseChunk.objects.get_or_create(
                lease=lease,
                chunk_index=chunk_idx,
                defaults={"chunk_text": chunk, "search_doc_id": search_doc_id},
            )
            vector = ai.embed_text(chunk)
            search_items.append(
                {
                    "id": search_doc_id,
                    "vector": vector,
                    "payload": {
                        "lease_id": lease.id,
                        "chunk_index": chunk_idx,
                        "chunk_text": chunk,
                    },
                }
            )
        if search_items:
            search_store.upsert_chunks(SEARCH_INDEX, search_items)

    # Sample LeaseQuery history rows for the first 3 leases.
    for lease, question in zip(lease_objs[:3], SAMPLE_QUESTIONS):
        if LeaseQuery.objects.filter(lease=lease, question_text=question).exists():
            continue
        chunk_ids = list(
            LeaseChunk.objects.filter(lease=lease).values_list("search_doc_id", flat=True)[:2]
        )
        answer = ai.chat_completion(
            [
                {"role": "system", "content": "You are a lease abstraction assistant."},
                {"role": "user", "content": f"Lease context chunks: {chunk_ids}\n\nQuestion: {question}"},
            ]
        )
        LeaseQuery.objects.create(
            asked_by=pm_user,
            lease=lease,
            question_text=question,
            answer_text=answer,
            retrieved_chunk_ids=chunk_ids,
        )


def unseed_data(apps, schema_editor):
    # Intentionally left as a no-op: seed data is demo data, not reversed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0002_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]
