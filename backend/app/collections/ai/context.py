"""anydoc workbook-to-markdown conversion for LLM context ONLY, never a calculation source.

See docs/ARCHITECTURE.md for the allowed/banned boundary. Built in Phase 6
(MASTER_PLAN.md). No Phase 6 role calls this yet -- `summary_narrator`
narrates the already-computed metrics dictionary, never raw sheets (see
its own docstring). This exists for Phase 7's exception_explainer (sees
the offending rows) and Phase 10's schema_mapper (sees the workbook's
real header structure) to build on.
"""

from __future__ import annotations

from pathlib import Path

import anydoc


def workbook_readme_markdown(path: Path) -> str:
    """The workbook's README sheet only, as Markdown -- not the whole
    workbook. Keeps the prompt small enough for a local 4B model to
    handle reliably (MASTER_PLAN.md section 6), and there is no reason
    an LLM narrating or explaining needs to see every data sheet's
    literal cells when the numbers themselves already came from
    `ingest/loader.py`, not from this markdown."""
    full_markdown = anydoc.to_markdown(path)
    readme_start = full_markdown.find("## README")
    if readme_start == -1:
        return full_markdown
    next_heading = full_markdown.find("\n## ", readme_start + 1)
    return full_markdown[
        readme_start : next_heading if next_heading != -1 else None
    ].strip()
