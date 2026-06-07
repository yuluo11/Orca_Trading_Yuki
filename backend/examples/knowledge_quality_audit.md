# Knowledge quality audit

The quality audit checks processed records for operational issues such as
missing required metadata, very short text, missing dynamic source fields,
stale dynamic records, and duplicated content hashes.

Run from Python:

```python
from backend.src.knowledge.quality import KnowledgeQualityAuditor

summary = KnowledgeQualityAuditor().audit(datasets=("dynamic",))
print(summary.to_dict())
```

The route-layer payload is also available for API or future frontend usage:

```python
from backend.src.routes.knowledge import audit_knowledge_payload

result = audit_knowledge_payload({
    "datasets": ["dynamic"],
    "dynamic_max_age_days": 45
})
```

Warnings do not fail the audit. Errors fail it. This lets the project separate
hard data-shape problems from softer quality reminders.
