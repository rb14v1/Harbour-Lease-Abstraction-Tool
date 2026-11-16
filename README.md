# Lease Abstraction Tool

A full-stack demo app for uploading commercial lease documents, extracting
key lease terms, and asking natural-language questions about a lease using a
retrieval-augmented generation (RAG) pipeline.

Stack: React (Vite + TypeScript) frontend, Django 5 + Django REST Framework
backend, PostgreSQL (or SQLite in dev/test), JWT auth, and five Azure
AI services each wrapped in a dual-path real/stub abstraction.

## Architecture: what's real vs. stubbed

Every external service lives behind a small module in `backend/apps/common/`
with one function signature regardless of mode. In dev/test (`USE_SQLITE=True`,
the default) every service runs in **deterministic-stub mode**: no network
calls, no cost, no Azure account needed, and the exact same input always
produces the exact same output (seeded with SHA256 hashes) so tests are
reproducible.

1. **Blob storage** (`blob_store.py`, wraps `azure-storage-blob`) — stores
   uploaded lease documents. Real: Azure Blob Storage via `BlobServiceClient`,
   used when `AZURE_STORAGE_CONNECTION_STRING` is set. Stub: writes/reads
   files under `backend/media/blob_stub/`.
2. **Document extraction** (`document_intelligence.py`, wraps
   `azure-ai-documentintelligence`) — pulls full text and lease terms
   (rent/renewal/termination/maintenance) out of an uploaded document. Real:
   calls the `prebuilt-document` model, used when
   `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` + `..._KEY` are set. Stub: treats
   the upload as plain text, splits it into paragraphs, and classifies each
   paragraph into a term type via a SHA256 hash of its content, deriving a
   plausible value (e.g. a dollar amount, a notice period) from the same hash.
3. **AI chat + embeddings** (`ai.py`, wraps Azure OpenAI via the `openai`
   package's `AzureOpenAI` client) — embeds lease chunks/questions and
   synthesizes answers. Real: used when `AZURE_OPENAI_ENDPOINT` +
   `AZURE_OPENAI_API_KEY` are set, with chat model `OPENAI_CHAT_MODEL`
   (default `gpt-5.4-mini`) and embedding model `OPENAI_EMBEDDING_MODEL`
   (default `text-embedding-3-large`, 1536 dimensions). Stub: deterministic
   SHA256-seeded 1536-float vectors for embeddings, and a deterministic
   templated reply for chat.
4. **Vector / hybrid search** (`search_store.py`, wraps
   `azure-search-documents`) — indexes lease chunks and retrieves the top-k
   most relevant ones for a question, scoped to one lease. Real: a real
   Azure AI Search index (`lease_chunks`), used when `AZURE_SEARCH_ENDPOINT` +
   `AZURE_SEARCH_KEY` are set. Stub: a process-local in-memory list of
   `{id, vector, payload}` with plain-Python cosine-similarity top-k search
   (similar to Qdrant's `:memory:` mode) — no persistence, rebuilt from the
   `LeaseChunk` table on every server start via the `resync_search_index`
   management command (wired to run automatically after `migrate`).
5. **Relational storage** — plain PostgreSQL (or SQLite in dev/test). No
   pgvector extension and no vector columns anywhere; all vectors live only
   in the search_store abstraction above.

### `USE_SQLITE` toggle

- `USE_SQLITE=True` (default): SQLite + every Azure service above stubbed.
  This is what `manage.py test` and CI always run under — zero external
  dependencies, fully reproducible.
- `USE_SQLITE=False`: real PostgreSQL via `POSTGRES_*` settings. Each Azure
  service independently stays stubbed if its own env vars are left blank —
  flipping `USE_SQLITE` to `False` does **not** by itself require any Azure
  credentials.

## Workflow

1. **Upload** — `POST /api/leases/` (multipart) stores the document via
   `blob_store.upload_document` and creates a `Lease` row with
   `status=uploaded`.
2. **Process** — `POST /api/leases/{id}/process/` runs
   `document_intelligence` to extract full text + `LeaseTerm` rows, chunks
   the text into `LeaseChunk` rows, embeds each chunk via `ai.embed_text`,
   upserts them into the `lease_chunks` search index (payload carries
   `lease_id`), and sets `Lease.status=processed`.
3. **Ask** — `POST /api/leases/{id}/queries/` embeds the question, retrieves
   the top-k chunks scoped to that lease via `search_store.search`,
   synthesizes an answer via `ai.chat_completion` citing the chunks/terms
   used, and saves a `LeaseQuery` row with `retrieved_chunk_ids`.
   `GET /api/leases/{id}/queries/` lists that lease's question history.

## Data model

`Property` → `Lease` (FK) → `LeaseTerm`, `LeaseChunk` (FK to Lease) and
`LeaseQuery` (FK to Lease + asked_by User).

## Permissions

- `property_manager`: create/process leases, upload documents, ask questions,
  manage properties.
- `admin`: everything above, plus delete properties/leases.

Enforced via a DRF permission class at the queryset/view level (not hidden
only in serializers or the frontend).

## Backend setup (Windows)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # a working .env with USE_SQLITE=True is already checked in for convenience
python manage.py migrate
python manage.py test
python manage.py runserver
```

`migrate` applies an idempotent seed-data migration (safe to re-run) that
creates 2 demo users, 6 properties, 8 leases (with terms + chunks already
extracted) and 3 sample question/answer history rows, all through the same
stub pipeline used at runtime.

### Running against real PostgreSQL

Set `USE_SQLITE=False` in `.env` with `POSTGRES_HOST=localhost`,
`POSTGRES_PORT=5432`, `POSTGRES_DB=lease_abstraction_tool`,
`POSTGRES_USER=lease_abstraction_tool`, `POSTGRES_PASSWORD=lease_abstraction_tool`
(native Postgres, no extensions required), then run `python manage.py migrate`
again. Azure services stay stubbed as long as their env vars are blank.

### Demo logins

| Role             | Email              | Password   |
|------------------|---------------------|-----------|
| Property Manager | pm@example.com       | Demo1234! |
| Admin            | admin@example.com    | Demo1234! |

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Reads the API base URL from `VITE_API_BASE_URL` (see `.env` /
`.env.example`, defaults to `http://localhost:8000/api`). Login page, a
properties list (create + drill into a property's leases), a leases list per
property (upload a document, trigger processing, delete as admin), and a
lease detail page (extracted terms table, ask-a-question box, and question
history).

## API surface

- `POST /api/auth/register/`, `POST /api/auth/login/`, `POST
  /api/auth/refresh/`, `GET /api/auth/me/`
- `GET|POST /api/properties/`, `GET|PUT|PATCH|DELETE /api/properties/{id}/`
- `GET|POST /api/leases/` (POST = multipart upload), `GET|PUT|PATCH|DELETE
  /api/leases/{id}/`
- `POST /api/leases/{id}/process/`
- `GET /api/leases/{id}/terms/`
- `GET|POST /api/leases/{id}/queries/` (POST = ask a question)

## Tests

`backend/apps/common/tests.py` covers each stub module in isolation
(determinism, round-tripping, cosine-similarity ranking, filtering).
`backend/apps/users/tests.py` and `backend/apps/leases/tests/` cover models,
permissions, and the API surface, plus a true end-to-end pipeline test
(`test_pipeline.py`) that exercises upload → extract → chunk/embed → index →
search → AI answer entirely through stub mode, including a test that two
different leases' chunks never cross-contaminate search results.
