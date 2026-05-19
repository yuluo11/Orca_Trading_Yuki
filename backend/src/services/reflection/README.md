# Reflection Services

This package is reserved for reflection-support services.

Expected responsibilities:

- gather current decision outputs and relevant context
- retrieve historical decision memories and postmortem references
- normalize realized outcomes and feedback signals
- prepare structured payloads for reflection agents
- optionally prepare candidate memory records for later persistence

Reasoning should remain in `agents/reflection`; service code should stay
focused on context preparation and data contracts.
