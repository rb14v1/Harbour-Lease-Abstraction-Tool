"""
Azure OpenAI abstraction (chat completions + embeddings), wraps the `openai`
package's AzureOpenAI client.

Real path: when settings.AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are
both set, calls real Azure OpenAI deployments named by OPENAI_CHAT_MODEL /
OPENAI_EMBEDDING_MODEL.

Stub path: when unconfigured (the default in dev/test), returns deterministic
stub text for chat completions and deterministic SHA256-seeded stub vectors
(exactly EMBEDDING_DIMENSIONS floats) for embeddings, so the same input
always produces the same output with no network access.
"""
import hashlib
import struct
from django.conf import settings


def _is_real():
    return bool(settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)


def _client():
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def pad_vector(seed_bytes: bytes, dimensions: int) -> list[float]:
    """
    Deterministically expands a seed digest into a unit-ish vector of the
    requested length by repeatedly re-hashing, unpacking 4-byte chunks as
    unsigned ints, and scaling them into roughly [-1, 1].
    """
    values: list[float] = []
    digest = seed_bytes
    while len(values) < dimensions:
        digest = hashlib.sha256(digest).digest()
        for i in range(0, len(digest), 4):
            chunk = digest[i : i + 4]
            if len(chunk) < 4:
                continue
            (as_int,) = struct.unpack(">I", chunk)
            values.append((as_int / 0xFFFFFFFF) * 2 - 1)
            if len(values) >= dimensions:
                break
    return values[:dimensions]


def embed_text(text: str) -> list[float]:
    """Returns an EMBEDDING_DIMENSIONS-length vector for `text`."""
    if _is_real():
        client = _client()
        response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL, input=text
        )
        return response.data[0].embedding

    seed = hashlib.sha256(text.encode("utf-8")).digest()
    return pad_vector(seed, settings.EMBEDDING_DIMENSIONS)


def chat_completion(messages: list[dict]) -> str:
    """
    Takes a list of {"role": ..., "content": ...} messages, returns the
    assistant's reply text.
    """
    if _is_real():
        client = _client()
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL, messages=messages
        )
        return response.choices[0].message.content

    seed_text = "|".join(f"{m.get('role')}:{m.get('content')}" for m in messages)
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:12]
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    snippet = last_user[:160].replace("\n", " ")
    return (
        f"[stub-answer:{digest}] Based on the retrieved lease context, here is a "
        f"deterministic placeholder answer to: \"{snippet}\""
    )
