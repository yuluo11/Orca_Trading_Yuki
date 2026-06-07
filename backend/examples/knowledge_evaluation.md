# Knowledge evaluation set

Knowledge evaluation is optional and user-fixed. If you want a query to become a
regression check, add it to a JSON eval set and enable it.

Start from:

```text
backend/data/manifests/knowledge_eval_set_template.json
```

Each case can define what “good retrieval” means for that query:

```json
{
  "case_id": "nvda_event_fade_risk",
  "enabled": true,
  "query": "NVDA event fade risk",
  "datasets": ["dynamic"],
  "k": 3,
  "min_results": 1,
  "expected_symbols": ["NVDA"],
  "expected_categories": ["news"],
  "must_include_terms": ["fade", "risk"]
}
```

Run it from Python:

```python
from backend.src.knowledge.evaluation import KnowledgeRetrievalEvaluator

summary = KnowledgeRetrievalEvaluator().evaluate_file(
    "backend/data/manifests/knowledge_eval_set_template.json"
)
print(summary.to_dict())
```

Or run it from the CLI:

```bash
python -m backend.src.knowledge.evaluation_cli \
  --data-root backend/data \
  --eval-set backend/data/manifests/knowledge_eval_set_template.json
```

Disabled cases are skipped by default, so the user decides exactly which checks
are fixed at any point in the project.
