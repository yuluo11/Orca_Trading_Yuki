# Reflection Agents

This package is reserved for post-decision reflection agents.

The reflection layer should sit after `analysts` and `decision`:

1. consume the analyst context and final advisory output
2. compare the setup against historical decision memories
3. ingest the realized outcome or later feedback
4. produce reusable lessons, adjustments, and candidate postmortem memories

Keep retrieval and persistence concerns in `services/reflection` so the agent
layer can focus on reasoning and iteration logic.
