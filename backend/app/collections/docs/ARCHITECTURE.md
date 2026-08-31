# Architecture

Owns: components, data flow, why each decision was made, trade-offs, what
breaks at scale. Does not own: how to run anything (see `DEVELOPMENT.md`),
endpoint payloads (see `API.md`).

Status: **Phase 2 in progress.** Populated phase by phase as components land.

## Components

_Filled in as each phase lands (ingest, validate, calculate, control, ai,
export, observability, api)._

## Why `validate/schemas.py` is not Pandera

MASTER_PLAN.md section 9 names Pandera for Phase 2's "structural schemas."
We deliberately did not add it, and the reasoning belongs here rather than
silently deviating from the plan.

Pandera validates DataFrame-shaped data (`DataFrameSchema`/
`DataFrameModel`). This codebase has no DataFrame anywhere: `ingest/loader.py`
reads typed openpyxl cells straight into frozen dataclasses (`contracts.py`)
specifically to avoid a second, looser numeric-parsing path — the same
reasoning the anydoc boundary above uses (a DataFrame-inferred dtype for a
money column carries exactly the same "lost precision and type" risk as a
parsed Markdown cell).

By the time any `validate/rules.py` function receives a `CanonicalDataset`,
there is no dtype-mismatch state left for Pandera to catch:

- Required-sheet/required-column presence is already enforced by
  `ingest/resolver.py`'s `ColumnResolutionError`.
- Per-cell type coercion (string -> `Decimal`, string -> `date`) already
  happens in `ingest/loader.py`'s `_decimal`/`_date`/etc. helpers, which
  raise immediately on a bad cell — arguably stricter than a post-hoc
  DataFrame dtype check, since it operates on the real openpyxl typed
  value rather than an inferred column dtype.
- Empty sheet / corrupt file / missing sheet are pipeline **failures**
  (`PipelineError`, Phase 3), not per-row exceptions — out of scope for a
  structural-schema layer regardless of which library implements it.

Adding `pandas`/Pandera here would mean building a throwaway DataFrame
just to re-check a guarantee the type system already gives, plus a new
runtime dependency and a second numeric-parsing code path for money.
Instead, `validate/schemas.py` holds `SheetSchema` constants — a
declarative, dependency-free single source of truth re-exporting
`ingest/resolver.py`'s existing header dicts — plus `sheet_row_counts()`.
If ingestion ever moves to a DataFrame-based pipeline, Pandera would be
the natural upgrade at that point.

## Data flow

_Filled in Phase 3: the `service.py` orchestrator stage sequence — load,
map, validate, calculate, control, summarise, persist._

## The anydoc boundary

A hard rule, stated here explicitly because it is the kind of distinction
that reads as senior in review: anydoc converts workbooks to Markdown for
LLM context ONLY. Numbers for calculation always come from `openpyxl`
reading typed cells into `Decimal`, never from parsing a Markdown table
cell, which is a formatted string that has already lost precision and
type.

```
ALLOWED   workbook -> anydoc -> markdown -> LLM context
BANNED    workbook -> anydoc -> markdown -> parse -> financial calculation
```

## Trade-offs and what breaks at scale

_Filled in as decisions are made; see QA_PREP.md question 20 for the
production-hardening answer this section will expand on._
