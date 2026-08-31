# Architecture

Owns: components, data flow, why each decision was made, trade-offs, what
breaks at scale. Does not own: how to run anything (see `DEVELOPMENT.md`),
endpoint payloads (see `API.md`).

Status: **Phase 0 skeleton.** Populated phase by phase as components land.

## Components

_Filled in as each phase lands (ingest, validate, calculate, control, ai,
export, observability, api)._

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
