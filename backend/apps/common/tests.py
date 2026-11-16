from django.test import TestCase, override_settings

from apps.common import ai, blob_store, document_intelligence, search_store


class BlobStoreStubTests(TestCase):
    def test_upload_and_download_roundtrip(self):
        path = blob_store.upload_document(b"hello lease world", "test-container", "doc1.txt")
        self.assertTrue(path.startswith("stub://"))
        data = blob_store.download_document(path)
        self.assertEqual(data, b"hello lease world")

    def test_upload_auto_generates_blob_name(self):
        path = blob_store.upload_document(b"content", "test-container")
        self.assertIn("test-container/", path)
        self.assertEqual(blob_store.download_document(path), b"content")


class DocumentIntelligenceStubTests(TestCase):
    def test_extract_text_decodes_bytes(self):
        text = document_intelligence.extract_text(b"Hello\n\nWorld")
        self.assertEqual(text, "Hello\n\nWorld")

    def test_extract_lease_terms_is_deterministic(self):
        raw = b"RENT. Pay monthly.\n\nRENEWAL. Renew in writing.\n\nTERMINATION. Notice required."
        terms_a = document_intelligence.extract_lease_terms(raw)
        terms_b = document_intelligence.extract_lease_terms(raw)
        self.assertEqual(terms_a, terms_b)
        self.assertGreaterEqual(len(terms_a), 1)
        for term in terms_a:
            self.assertIn(term["term_type"], document_intelligence.TERM_TYPES)
            self.assertIsInstance(term["source_page"], int)

    def test_extract_lease_terms_changes_with_content(self):
        terms_a = document_intelligence.extract_lease_terms(b"Paragraph one content.")
        terms_b = document_intelligence.extract_lease_terms(b"Totally different paragraph.")
        self.assertNotEqual(terms_a, terms_b)


class AiStubTests(TestCase):
    def test_embed_text_is_deterministic_and_correct_length(self):
        vec_a = ai.embed_text("the rent is due monthly")
        vec_b = ai.embed_text("the rent is due monthly")
        self.assertEqual(vec_a, vec_b)
        self.assertEqual(len(vec_a), 1536)
        self.assertTrue(all(isinstance(v, float) for v in vec_a))

    def test_embed_text_differs_for_different_input(self):
        vec_a = ai.embed_text("question one")
        vec_b = ai.embed_text("question two")
        self.assertNotEqual(vec_a, vec_b)

    def test_chat_completion_is_deterministic(self):
        messages = [{"role": "user", "content": "What is the rent?"}]
        reply_a = ai.chat_completion(messages)
        reply_b = ai.chat_completion(messages)
        self.assertEqual(reply_a, reply_b)
        self.assertIn("stub-answer", reply_a)

    def test_pad_vector_length(self):
        vec = ai.pad_vector(b"seed", 1536)
        self.assertEqual(len(vec), 1536)


class SearchStoreStubTests(TestCase):
    def setUp(self):
        search_store.reset_index("test_index")

    def test_upsert_and_search_top_k(self):
        items = [
            {"id": "a", "vector": [1.0, 0.0, 0.0], "payload": {"lease_id": 1}},
            {"id": "b", "vector": [0.0, 1.0, 0.0], "payload": {"lease_id": 1}},
            {"id": "c", "vector": [1.0, 0.01, 0.0], "payload": {"lease_id": 2}},
        ]
        search_store.upsert_chunks("test_index", items)
        results = search_store.search("test_index", [1.0, 0.0, 0.0], top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "a")

    def test_search_respects_filter_fn(self):
        items = [
            {"id": "a", "vector": [1.0, 0.0], "payload": {"lease_id": 1}},
            {"id": "b", "vector": [1.0, 0.0], "payload": {"lease_id": 2}},
        ]
        search_store.upsert_chunks("test_index", items)
        results = search_store.search(
            "test_index", [1.0, 0.0], top_k=5, filter_fn=lambda p: p["lease_id"] == 2
        )
        self.assertEqual([r["id"] for r in results], ["b"])

    def test_upsert_is_idempotent_by_id(self):
        search_store.upsert_chunks(
            "test_index", [{"id": "a", "vector": [1.0], "payload": {"v": 1}}]
        )
        search_store.upsert_chunks(
            "test_index", [{"id": "a", "vector": [1.0], "payload": {"v": 2}}]
        )
        results = search_store.search("test_index", [1.0], top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["payload"]["v"], 2)
