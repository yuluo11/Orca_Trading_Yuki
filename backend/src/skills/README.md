"""Skill layer layout for reusable backend capabilities.

This directory is intentionally separated from ``config``. Configuration should
only decide whether a skill is enabled or how it is parameterized; the skill
implementation itself lives here.

Structure:
- ``global_skills``: cross-domain reusable capabilities
- ``finskills``: finance-specific reusable capabilities

Skills should stay thinner than full services. A skill is best treated as a
reusable capability unit that can be called by analysts, decision logic,
reflection flows, or tools without owning end-to-end workflow orchestration.
"""
