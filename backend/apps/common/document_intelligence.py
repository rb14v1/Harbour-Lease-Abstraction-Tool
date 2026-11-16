"""
Document extraction abstraction (wraps azure-ai-documentintelligence).

Real path: when settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and
AZURE_DOCUMENT_INTELLIGENCE_KEY are both set, this would call Azure AI
Document Intelligence's "prebuilt-document" model (a lease is a general
contract document; a production deployment analysing leases specifically
would instead target the "prebuilt-contract" model) to pull full text and
field-level data out of the uploaded file.

Stub path: when unconfigured (the default in dev/test), this module treats
the uploaded document as plain text (tests/dev uploads are plain-text or
simple PDF-like text files), splits it into paragraphs, and deterministically
derives fake-but-structured lease terms from a SHA256 hash of each
paragraph's content so the exact same input always yields the exact same
output across runs and machines.
"""
import hashlib
from django.conf import settings

TERM_TYPES = ["rent", "renewal", "termination", "maintenance"]


def _is_real():
    return bool(
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        and settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
    )


def _sha256_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def extract_text(raw_bytes: bytes) -> str:
    """Returns the full text content of a document."""
    if _is_real():
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY),
        )
        poller = client.begin_analyze_document("prebuilt-document", body=raw_bytes)
        result = poller.result()
        return result.content or ""

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore")


def extract_lease_terms(raw_bytes: bytes) -> list[dict]:
    """
    Returns a list of {term_type, extracted_value, source_page} dicts.

    Stub derivation: the text is split into non-empty paragraphs; every
    paragraph is classified into a term_type via `sha256(paragraph) %
    len(TERM_TYPES)`, and an extracted_value is derived deterministically
    from the same hash plus the paragraph content so results are
    reproducible. `source_page` is a 1-indexed paragraph position used as a
    stand-in for a real page number.
    """
    text = extract_text(raw_bytes)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    terms = []
    for idx, paragraph in enumerate(paragraphs):
        digest = _sha256_int(paragraph)
        term_type = TERM_TYPES[digest % len(TERM_TYPES)]

        if term_type == "rent":
            amount = 1000 + (digest % 9000)
            extracted_value = f"${amount}.00 per month"
        elif term_type == "renewal":
            years = 1 + (digest % 5)
            extracted_value = f"Renewable for {years} year(s) upon written notice"
        elif term_type == "termination":
            days = 30 + (digest % 150)
            extracted_value = f"{days} days written notice required to terminate"
        else:  # maintenance
            party = "Landlord" if digest % 2 == 0 else "Tenant"
            extracted_value = f"{party} responsible for maintenance and repairs"

        terms.append(
            {
                "term_type": term_type,
                "extracted_value": extracted_value,
                "source_page": idx + 1,
            }
        )
    return terms
