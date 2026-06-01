# Foundation knowledge

Foundation knowledge is static, durable project knowledge: the user's trading
principles, playbooks, risk rules, indicator definitions, and agent boundaries.

Use the taxonomy template:

```text
backend/data/manifests/foundation_taxonomy.json
```

Use the raw record template:

```text
backend/data/foundation/raw/templates/foundation_record_template.md
```

Suggested import metadata:

```python
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.repository import KnowledgeRepository

repository = KnowledgeRepository()
ingestor = KnowledgeIngestor(repository)

ingestor.ingest_raw_text_file(
    "foundation",
    "backend/data/foundation/raw/risk_framework/position_sizing_rule.md",
    metadata={
        "foundation_category": "risk_framework",
        "principle_type": "rule",
        "applies_to": ["decision_agent", "position_sizing"],
        "valid_when": ["setup has clear invalidation"],
        "invalid_when": ["risk budget is unknown"],
        "priority": "high",
        "status": "active",
        "rule_direction": "reduce",
        "owner_defined": True,
        "rule_id": "risk_position_sizing_001"
    }
)
```

Run a static-only audit:

```python
from backend.src.routes.knowledge import audit_knowledge_payload

result = audit_knowledge_payload({"datasets": ["foundation"]})
```

Run static retrieval regression checks from:

```text
backend/data/manifests/foundation_eval_set_template.json
```
