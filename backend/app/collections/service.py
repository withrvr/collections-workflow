"""The orchestrator: load -> map -> validate -> calculate -> control -> summarise -> persist, top to bottom.

A plain Python function calling each stage in a fixed order, deliberately
not an autonomous agent (see QA_PREP.md, question 16). Built in Phase 3+
(MASTER_PLAN.md).
"""
