# Dynamic Knowledge Scheduler CLI

The scheduler can be run manually or from cron/launchd without starting a web server.

Register a source:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  register \
  --source-id nvda_news_feed \
  --source-type rss_feed \
  --url https://example.com/feed.xml \
  --symbol NVDA \
  --category news \
  --refresh-interval-minutes 60
```

Import sources from a reviewed JSON config:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  import-config \
  --config backend/data/manifests/dynamic_source_template.json \
  --dry-run
```

Check due sources without fetching:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  run-due \
  --dry-run
```

Run all due sources:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  run-due
```

Run the full scheduler -> collector -> ingest flow with a local fixture instead
of a real network fetch:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  run-due \
  --fixture-file backend/data/fixtures/example_feed.xml
```

Run one source immediately:

```bash
python -m backend.src.knowledge.source_scheduler_cli \
  --data-root backend/data \
  run-source \
  --source-id nvda_news_feed \
  --force
```

The schedule state is stored at `backend/data/manifests/dynamic_source_schedule.json`.

Use `backend/data/manifests/dynamic_source_template.json` as the starting point
for user-approved source lists. Keep placeholder sources disabled until the URL
and crawling permission have been reviewed.
