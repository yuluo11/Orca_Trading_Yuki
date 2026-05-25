from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.indexing import KnowledgeIndexer, PersistedTokenVectorIndex
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeIndexerTests(unittest.TestCase):
    def test_save_and_load_persisted_token_vector_index_supports_similarity_search(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "foundation",
                "nvda_supply_chain_note",
                "NVIDIA supply chain strength remains supportive for AI demand.",
                metadata={"symbol": "NVDA", "category": "research"},
            )
            ingestor.ingest_text(
                "foundation",
                "btc_liquidity_note",
                "Bitcoin liquidity remains volatile and risk appetite is mixed.",
                metadata={"symbol": "BTC", "category": "market"},
            )

            indexer = KnowledgeIndexer(repository)
            snapshot_path = indexer.save_persisted_token_vector_index(
                "foundation_vector_index",
                datasets=("foundation",),
            )
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            backend = indexer.load_persisted_token_vector_index("foundation_vector_index")
            results = backend.similarity_search(
                "AI supply chain demand",
                k=1,
                filter={"symbol": "NVDA"},
            )

        self.assertEqual("persisted_token_vector", snapshot["backend"])
        self.assertEqual(2, snapshot["document_count"])
        self.assertEqual(1, len(results))
        self.assertEqual("NVDA", results[0].metadata["symbol"])
        self.assertIn("supply chain", results[0].page_content.lower())

    def test_load_or_build_default_backend_prefers_auto_index_snapshots(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "foundation",
                "nvda_supply_chain_note",
                "NVIDIA supply chain strength remains supportive for AI demand.",
                metadata={"symbol": "NVDA", "category": "research"},
            )
            ingestor.ingest_text(
                "dynamic",
                "btc_liquidity_note",
                "Bitcoin liquidity remains volatile and risk appetite is mixed.",
                metadata={"symbol": "BTC", "category": "market"},
            )

            indexer = KnowledgeIndexer(repository)
            indexer.save_persisted_token_vector_index("foundation_auto_index", datasets=("foundation",))
            indexer.save_persisted_token_vector_index("dynamic_auto_index", datasets=("dynamic",))

            backend = indexer.load_or_build_default_backend(("foundation", "dynamic"))
            results = backend.similarity_search(
                "AI supply chain demand",
                k=1,
                filter={"symbol": "NVDA"},
            )

        self.assertIsInstance(backend, PersistedTokenVectorIndex)
        self.assertEqual(1, len(results))
        self.assertEqual("NVDA", results[0].metadata["symbol"])

    def test_load_or_build_default_backend_can_mix_snapshot_and_live_documents(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "foundation",
                "nvda_supply_chain_note",
                "NVIDIA supply chain strength remains supportive for AI demand.",
                metadata={"symbol": "NVDA", "category": "research"},
            )
            ingestor.ingest_text(
                "dynamic",
                "btc_liquidity_note",
                "Bitcoin liquidity remains volatile and risk appetite is mixed.",
                metadata={"symbol": "BTC", "category": "market"},
            )

            indexer = KnowledgeIndexer(repository)
            indexer.save_persisted_token_vector_index("foundation_auto_index", datasets=("foundation",))

            backend = indexer.load_or_build_default_backend(("foundation", "dynamic"))
            foundation_results = backend.similarity_search(
                "AI supply chain demand",
                k=1,
                filter={"symbol": "NVDA"},
            )
            dynamic_results = backend.similarity_search(
                "Bitcoin liquidity risk appetite",
                k=1,
                filter={"symbol": "BTC"},
            )

        self.assertIsInstance(backend, PersistedTokenVectorIndex)
        self.assertEqual("NVDA", foundation_results[0].metadata["symbol"])
        self.assertEqual("BTC", dynamic_results[0].metadata["symbol"])


if __name__ == "__main__":
    unittest.main()
