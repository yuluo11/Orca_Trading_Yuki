from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.policy import KnowledgePolicy
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeIngestorTests(unittest.TestCase):
    def test_ingest_text_cleans_content_and_infers_default_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)

            record_path = ingestor.ingest_text(
                "foundation",
                "nvda-market-note",
                "  Disclaimer: internal draft only  \n\nAlpha   signal\t\tremains active.\r\n\r\n\r\nPage 1 of 3\n",
            )

            record = repository.load_processed_record("foundation", record_path.stem)

        self.assertEqual("Alpha signal remains active.", record["text"])
        self.assertEqual("Nvda Market Note", record["metadata"]["title"])
        self.assertEqual("medium", record["metadata"]["reliability"])
        self.assertEqual("low", record["metadata"]["time_sensitivity"])
        self.assertEqual("foundation", record["metadata"]["dataset"])

    def test_ingest_text_skips_exact_duplicate_content_in_same_dataset(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)

            first_path = ingestor.ingest_text(
                "dynamic",
                "nvda_first_note",
                "Momentum remains constructive.\n\nFollow-through still needs work.",
            )
            second_outcome = ingestor.ingest_text_with_outcome(
                "dynamic",
                "nvda_second_note",
                "  Momentum remains constructive.\n\nFollow-through still needs work.  ",
            )

            processed_files = repository.list_processed_record_paths("dynamic")

        self.assertEqual("skipped_duplicate", second_outcome.status)
        self.assertEqual(first_path, second_outcome.record_path)
        self.assertEqual(1, len(processed_files))

    def test_ingest_raw_text_directory_batches_files_and_reports_counts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            raw_dir = data_root / "foundation" / "raw" / "batch"
            raw_dir.mkdir(parents=True)
            (raw_dir / "alpha_note.txt").write_text(
                "Copyright 2026\n\nAlpha catalyst remains active.\n",
                encoding="utf-8",
            )
            (raw_dir / "beta_note.md").write_text(
                "Beta setup needs confirmation.\n",
                encoding="utf-8",
            )
            (raw_dir / "alpha_duplicate.md").write_text(
                "Alpha catalyst remains active.\n",
                encoding="utf-8",
            )

            repository = KnowledgeRepository(data_root=data_root)
            ingestor = KnowledgeIngestor(repository)

            summary = ingestor.ingest_raw_text_directory("foundation", raw_dir)
            processed_files = repository.list_processed_record_paths("foundation")
            manifest = repository.load_manifest()

        self.assertEqual(2, summary.imported_count)
        self.assertEqual(1, summary.skipped_count)
        self.assertEqual(2, summary.created_count)
        self.assertEqual(0, summary.updated_count)
        self.assertEqual(2, len(processed_files))
        raw_entries = manifest["datasets"]["foundation"]["raw"]
        processed_entries = manifest["datasets"]["foundation"]["processed"]
        self.assertEqual(3, len(raw_entries))
        self.assertEqual(2, len(processed_entries))
        self.assertTrue(all("text_hash" in entry for entry in processed_entries))

    def test_ingest_raw_text_file_infers_category_symbol_and_topic(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            raw_dir = data_root / "dynamic" / "raw" / "news"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "nvda_ai_supply_chain_note.md"
            raw_file.write_text("Supply chain commentary remains supportive.", encoding="utf-8")

            repository = KnowledgeRepository(data_root=data_root)
            ingestor = KnowledgeIngestor(repository)

            record_path = ingestor.ingest_raw_text_file("dynamic", raw_file)
            record = repository.load_processed_record("dynamic", record_path.stem)

        self.assertEqual("news", record["metadata"]["category"])
        self.assertEqual("NVDA", record["metadata"]["symbol"])
        self.assertEqual("ai supply chain note", record["metadata"]["topic"])
        self.assertTrue(record["metadata"]["source"].endswith("nvda_ai_supply_chain_note.md"))

    def test_ingest_raw_text_file_does_not_treat_common_words_as_symbols(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            raw_dir = data_root / "foundation" / "raw" / "research"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "macro_setup_note.md"
            raw_file.write_text("Macro setup commentary remains mixed.", encoding="utf-8")

            repository = KnowledgeRepository(data_root=data_root)
            ingestor = KnowledgeIngestor(repository)

            record_path = ingestor.ingest_raw_text_file("foundation", raw_file)
            record = repository.load_processed_record("foundation", record_path.stem)

        self.assertNotIn("symbol", record["metadata"])
        self.assertEqual("setup note", record["metadata"]["topic"])

    def test_ingest_text_skips_similar_content_when_policy_enables_similarity_detection(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            policy = KnowledgePolicy()
            policy.deduplication.similar_text_detection_enabled = True
            policy.deduplication.similar_text_threshold = 0.9
            ingestor = KnowledgeIngestor(repository, policy=policy)

            first_path = ingestor.ingest_text(
                "dynamic",
                "nvda_note_a",
                "Momentum remains constructive and confirmation is improving every day.",
            )
            second_outcome = ingestor.ingest_text_with_outcome(
                "dynamic",
                "nvda_note_b",
                "Momentum remains constructive and confirmation is improving day by day.",
            )

        self.assertEqual("skipped_duplicate", second_outcome.status)
        self.assertEqual(first_path, second_outcome.record_path)
        self.assertIn("similar", second_outcome.reason.lower())

    def test_ingest_text_can_auto_refresh_index_snapshot_when_policy_enables_it(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            policy = KnowledgePolicy()
            policy.indexing.rebuild_after_processed_updates = True
            policy.indexing.snapshot_enabled = True
            ingestor = KnowledgeIngestor(repository, policy=policy)

            outcome = ingestor.ingest_text_with_outcome(
                "foundation",
                "nvda_auto_index_note",
                "Auto index refresh should rebuild the current dataset snapshot.",
            )

            index_snapshot_path = repository.indexes / "foundation_auto_index.json"
            self.assertEqual(index_snapshot_path, outcome.index_snapshot_path)
            self.assertTrue(index_snapshot_path.exists())
            snapshot = json.loads(index_snapshot_path.read_text(encoding="utf-8"))

        self.assertEqual("foundation_auto_index", snapshot["name"])
        self.assertEqual(["foundation"], snapshot["datasets"])
        self.assertEqual(1, snapshot["document_count"])


if __name__ == "__main__":
    unittest.main()
