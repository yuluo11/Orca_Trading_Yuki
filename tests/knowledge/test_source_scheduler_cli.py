from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import json

from backend.src.knowledge.source_scheduler_cli import run_cli
from backend.src.knowledge.repository import KnowledgeRepository


class DynamicKnowledgeSchedulerCliTests(unittest.TestCase):
    def test_cli_register_list_and_due_dry_run(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)

            registered = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "register",
                    "--source-id",
                    "nvda_demo_feed",
                    "--source-type",
                    "rss_feed",
                    "--url",
                    "https://example.com/feed.xml",
                    "--symbol",
                    "NVDA",
                    "--max-items",
                    "2",
                ]
            )
            listed = run_cli(["--data-root", str(data_root), "list"])
            due = run_cli(["--data-root", str(data_root), "run-due", "--dry-run"])

        self.assertEqual("nvda_demo_feed", registered["source"]["source_id"])
        self.assertTrue(registered["schedulePath"].endswith("dynamic_source_schedule.json"))
        self.assertEqual(1, listed["count"])
        self.assertEqual("NVDA", listed["sources"][0]["symbol"])
        self.assertTrue(due["dryRun"])
        self.assertEqual(1, due["count"])

    def test_cli_can_hide_disabled_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)

            run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "register",
                    "--source-id",
                    "disabled_feed",
                    "--source-type",
                    "rss_feed",
                    "--url",
                    "https://example.com/feed.xml",
                    "--disabled",
                ]
            )
            all_sources = run_cli(["--data-root", str(data_root), "list"])
            active_sources = run_cli(["--data-root", str(data_root), "list", "--active-only"])

        self.assertEqual(1, all_sources["count"])
        self.assertEqual(0, active_sources["count"])

    def test_cli_run_source_dry_run_reports_selected_source(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)

            run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "register",
                    "--source-id",
                    "single_feed",
                    "--source-type",
                    "rss_feed",
                    "--url",
                    "https://example.com/feed.xml",
                ]
            )
            result = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "run-source",
                    "--source-id",
                    "single_feed",
                    "--dry-run",
                ]
            )

        self.assertTrue(result["dryRun"])
        self.assertEqual(1, result["count"])
        self.assertEqual("single_feed", result["sources"][0]["source_id"])

    def test_cli_import_config_supports_dry_run_and_register(self) -> None:
        config_payload = {
            "version": 1,
            "sources": [
                {
                    "source_id": "config_feed",
                    "source_type": "rss_feed",
                    "url": "https://example.com/feed.xml",
                    "symbol": "NVDA",
                    "max_items": 3,
                },
                {
                    "source_id": "config_page",
                    "source_type": "web_page",
                    "url": "https://example.com/article",
                    "category": "news",
                    "title": "Example article",
                },
            ],
        }
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text(json.dumps(config_payload), encoding="utf-8")

            dry_run = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "import-config",
                    "--config",
                    str(config_path),
                    "--dry-run",
                ]
            )
            before_import = run_cli(["--data-root", str(data_root), "list"])
            imported = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "import-config",
                    "--config",
                    str(config_path),
                ]
            )
            listed = run_cli(["--data-root", str(data_root), "list"])

        self.assertTrue(dry_run["dryRun"])
        self.assertEqual(2, dry_run["count"])
        self.assertEqual(0, before_import["count"])
        self.assertFalse(imported["dryRun"])
        self.assertEqual(2, listed["count"])

    def test_cli_run_due_can_use_fixture_file_to_smoke_test_crawler_flow(self) -> None:
        rss_fixture = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>NVDA fixture crawl update</title>
              <link>https://example.com/nvda-fixture</link>
              <description>Fixture crawl proves the scheduler ingest path works.</description>
            </item>
          </channel>
        </rss>
        """
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            fixture_path = Path(tmpdir) / "fixture.xml"
            fixture_path.write_text(rss_fixture, encoding="utf-8")

            run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "register",
                    "--source-id",
                    "fixture_feed",
                    "--source-type",
                    "rss_feed",
                    "--url",
                    "https://example.com/feed.xml",
                    "--symbol",
                    "NVDA",
                ]
            )
            result = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "run-due",
                    "--fixture-file",
                    str(fixture_path),
                ]
            )
            repository = KnowledgeRepository(data_root=data_root)
            records = repository.load_all_processed_records("dynamic")

        self.assertEqual(1, result["count"])
        self.assertEqual("success", result["results"][0]["status"])
        self.assertEqual(1, result["results"][0]["imported_count"])
        self.assertEqual(1, len(records))
        self.assertIn("Fixture crawl", records[0]["text"])


if __name__ == "__main__":
    unittest.main()
