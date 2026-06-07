# Foundation Knowledge Title

Write the durable rule, playbook, boundary, or principle here. Keep it stable,
specific, and reusable across market conditions.

## Metadata To Provide During Import

- foundation_category: risk_framework
- principle_type: rule
- applies_to: ["decision_agent", "position_sizing"]
- valid_when: ["risk budget is constrained", "setup has clear invalidation"]
- invalid_when: ["market data is stale", "setup invalidation is unknown"]
- priority: high
- status: draft
- rule_direction: reduce
- owner_defined: true
- rule_id: risk_position_sizing_001
- conflicts_with: []

## Guidance

Prefer explicit boundaries:

- What this rule allows or blocks.
- When it applies.
- When it must not be used.
- Which agent or service should consume it.
