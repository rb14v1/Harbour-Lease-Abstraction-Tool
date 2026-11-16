"""
Blob storage abstraction (wraps azure-storage-blob).

Real path: when settings.AZURE_STORAGE_CONNECTION_STRING is set, documents
are uploaded to / downloaded from Azure Blob Storage via BlobServiceClient.

Stub path: when it is blank (the default in dev/test), documents are written
to / read from local disk under MEDIA_ROOT/blob_stub/<container>/<blob_name>.
Both paths expose the exact same function signatures so callers never need
to know which mode is active.
"""
import os
import uuid
from django.conf import settings


def _is_real():
    return bool(settings.AZURE_STORAGE_CONNECTION_STRING)


def _stub_root(container: str) -> str:
    root = os.path.join(str(settings.MEDIA_ROOT), "blob_stub", container)
    os.makedirs(root, exist_ok=True)
    return root


def upload_document(file, container: str, blob_name: str | None = None) -> str:
    """
    Uploads `file` (a file-like object with .read(), or raw bytes) to
    `container` under `blob_name` (auto-generated if not given).

    Returns a blob_path identifier that `download_document` can consume.
    In real mode this is "azure://<container>/<blob_name>".
    In stub mode this is "stub://<container>/<blob_name>".
    """
    if blob_name is None:
        blob_name = f"{uuid.uuid4().hex}.txt"

    data = file.read() if hasattr(file, "read") else file
    if isinstance(data, str):
        data = data.encode("utf-8")

    if _is_real():
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = client.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass
        container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        return f"azure://{container}/{blob_name}"

    root = _stub_root(container)
    path = os.path.join(root, blob_name)
    with open(path, "wb") as f:
        f.write(data)
    return f"stub://{container}/{blob_name}"


def download_document(blob_path: str) -> bytes:
    """Downloads the bytes referenced by a blob_path returned from upload_document."""
    scheme, _, rest = blob_path.partition("://")
    container, _, blob_name = rest.partition("/")

    if scheme == "azure":
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = client.get_container_client(container)
        return container_client.download_blob(blob_name).readall()

    root = _stub_root(container)
    path = os.path.join(root, blob_name)
    with open(path, "rb") as f:
        return f.read()
