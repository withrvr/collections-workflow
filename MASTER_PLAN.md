# ERP Collection Reporting Workflow: Project Plan
Companion document: `QA_PREP.md` (a design-rationale FAQ this plan answers).
---
## 1. Goal, restated from the source of truth
The email lists deliverables. The **README sheet inside the workbook** defines the
actual specification and is stricter. Where they differ, the workbook wins.
Non-negotiables extracted from the workbook:
| Rule | Consequence in code |
|---|---|
| Report date is `2026-07-31` | A config value read from the workbook. Never `datetime.now()` |
| Only `Approved` invoices in the overdue report | Status filter at the calculator boundary |
| `Cancelled` and `Credit Note` excluded from overdue, shown in exceptions | Two different code paths, both required |
| Outstanding = Invoice Amount − valid payments on or before report date | Tax is NOT added |
| Overdue = Due Date < report date AND Outstanding > 0 | Strict less-than |
| Payments after report date do not reduce the position | Date filter before aggregation |
| **Do not silently delete problematic rows** | Every exclusion emits an exception row |
| Blank Region derived from Region_Mapping via State | Enrichment step, never a blank output |
Design priorities: business understanding, validation approach, exception
handling, code structure, responsible AI use, clarity of explanation.
**This is an MVP for a walkthrough, not a platform.** Optimise for what
someone can see, click, and understand in fifteen minutes.
---
## 2. Two phases of scope: core and extended
| Milestone | Scope |
|---|---|
| **Core** | Phases 0 to 8. Code, README, working API, minimal UI |
| **Extended** | Phases 9 to 13. Handling a second, differently-shaped workbook live |
Design every phase so that stopping at the end of it still leaves a demoable
system. Never leave a phase half-finished.
---
## 3. The second-workbook problem
At the presentation they will hand over a different file. Three ways that file
can differ, and the required behaviour for each:
| Difference | Required behaviour |
|---|---|
| Same schema, different data | Runs clean. Different numbers, same report shapes |
| Different column names | Schema mapping screen. Confirm, then run. **Never crash** |
| Missing sheet or corrupt file | Run recorded as `FAILED` with a readable reason in the UI |
A live crash loses the room. A live "I found 4 sheets and mapped 22 of 25
columns, these 3 need your confirmation" wins it. Budget real time for this.
### Fixture set to build
The given workbook always blocks the control gate (roughly 45% exception rate),
so the happy path is invisible with it alone. Build four fixtures:
| Fixture | Purpose |
|---|---|
| `dataset_a_original.xlsx` | The given file. Demonstrates the gate **blocking** |
| `dataset_b_clean.xlsx` | Hand-built, under 5% exceptions. Demonstrates the gate **passing** and the LLM summary rendering |
| `dataset_c_renamed.xlsx` | Same data, different column headers. Demonstrates schema mapping |
| `dataset_d_broken.xlsx` | Missing sheet, corrupt rows. Demonstrates graceful failure |
Generate B, C and D with a script committed under `scripts/make_fixtures.py` so
they are reproducible and you can explain how they were built.
---
## 4. Repo layout
Base: `git clone https://github.com/fastapi/full-stack-fastapi-template`, commit
unchanged as `chore: initial commit from full-stack-fastapi-template`. Everything
after that is your diff, which is exactly what a reviewer wants to see.
The frontend that was dead weight in v2 is now an asset, since a team needs to
view results without reading logs. Keep it.
```
backend/app/collections/           # the entire collections service, one folder
  __init__.py
  config.py                        # report date, thresholds, LLM settings
  contracts.py                     # CanonicalCustomer/Invoice/Payment/RegionMap
  ingest/
    loader.py                      # xlsx -> DataFrames, Decimal-typed
    resolver.py                    # 3-tier column resolution
    fingerprint.py                 # workbook hash + mapping cache
  validate/
    rules.py                       # E001..E014, one function each
    schemas.py                     # Pandera structural schemas
    engine.py                      # runs all rules, emits ExceptionRow[]
  calculate/
    outstanding.py
    overdue.py
    regions.py
    ageing.py
  control/
    gate.py                        # the 5% rule
  ai/
    provider.py                    # LiteLLM seam
    context.py                     # anydoc -> markdown for LLM context ONLY
    roles/
      schema_mapper.py
      exception_explainer.py
      summary_narrator.py
      run_triage.py
    guard.py                       # numeric containment check
    fallback.py                    # deterministic templates
  export/
    csv.py
    pdf.py
  observability/
    logging.py                     # structlog config
    metrics.py                     # prometheus collectors
    events.py                      # user-visible run events
  models.py                        # SQLModel tables
  service.py                       # the orchestrator, top to bottom
  scheduler.py
  api/
    runs.py  overdue.py  exceptions.py  regions.py  summary.py  runlog.py  mappings.py
  docs/                            # see section 5
  fixtures/
  tests/
frontend/src/routes/collections/   # the collections UI
  runs.tsx  run-detail.tsx  exceptions.tsx  summary.tsx  upload.tsx  mapping.tsx
```
One folder, one concern, no collections code leaking into the template's own
modules. A reviewer can `ls backend/app/collections` and see the whole design.
Wire the router into the template's `app/api/main.py` with a single include line.
That one-line touch is the only template file you modify.
---
## 5. Documentation set
Six files, strict ownership. A fact lives in exactly one file; others link to it.
| File | Owns | Never contains |
|---|---|---|
| `README.md` (service root) | **The primary deliverable.** What it does, how to run, business rules, assumptions, AI tooling used, validation performed | Architecture internals, endpoint schemas |
| `docs/ARCHITECTURE.md` | Components, data flow, why each decision was made, trade-offs, what breaks at scale | How to run, endpoint payloads |
| `docs/API.md` | Every endpoint: method, path, params, response schema, status codes, error codes | Business rationale, setup |
| `docs/RULES.md` | The exception rule catalogue. Single source of truth for E001 to E014 | Anything not a rule |
| `docs/DEVELOPMENT.md` | Local setup, commands, git workflow, commit format, testing, release process | Business logic |
| `docs/DEMO.md` | Presentation runbook, click order, fallback if something fails | Everything else |
Rule for the agent building this: **when a phase changes behaviour, update the
owning doc in the same commit.** A doc update is not a separate task.
Add `docs/CHANGELOG.md` at repo root in Keep a Changelog format.
---
## 6. Development tooling
These are agent-side tools that shape how the code gets written. They are **not
project dependencies** and do not go in `requirements.txt`. anydoc is the
exception: it ships as a runtime dependency for the LLM context path.
### ponytail
```
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```
A YAGNI ladder that stops the agent before it writes code: does this need to
exist, is it already in the codebase, does stdlib do it, is it one line. Its own
benchmark was run on a headless agent editing this exact template, reporting
roughly 54% less code and 20% lower cost against a no-skill baseline, with
validation, error handling and security explicitly off the chopping block.
Use `/ponytail-review` at the end of every phase before opening the MR. It hands
back a delete-list. On a 2-day MVP, the code you do not write is the schedule you
do not blow.
### caveman
```
npx skills add JuliusBrussee/caveman
```
Shrinks what the agent says while leaving code and errors byte-exact. Its own
FAQ recommends pairing with ponytail: caveman shrinks the prose, ponytail shrinks
the build, no overlap. Note the honest caveat in its README, that the skill cuts
output tokens only and adds roughly 1 to 1.5k input tokens per turn, so on
already-terse work it can go net negative. Use it for the long build phases, not
for the design conversations.
`/caveman-commit` produces terse Conventional Commit messages, which fits the
commit discipline in section 8.
### anydoc
```
pip install firecrawl-anydoc
```
Converts xlsx, pdf, docx and csv to clean GitHub-Flavored Markdown in single-digit
milliseconds, pure Rust, no ML models, no external service. Scores highest on
every judged format in its own benchmark against libreoffice, unstructured,
markitdown, pandoc, docling and mammoth.
**Where it is used and where it is banned.**
```
ALLOWED   workbook -> anydoc -> markdown -> LLM context
          (schema mapper sees structure, explainer sees offending rows)
BANNED    workbook -> anydoc -> markdown -> parse -> financial calculation
```
Numbers come from openpyxl reading typed cells into `Decimal`. A Markdown table
cell is a formatted string that has already lost precision and type. State this
boundary in `ARCHITECTURE.md` explicitly. It is the kind of distinction that
reads as senior.
Practical benefit: sending the workbook README sheet and headers as compact
Markdown instead of raw JSON keeps the schema-mapper prompt small enough for a
4B local model to handle reliably.
---
## 7. Observability for people who cannot see logs
This is the requirement that most changes the design. The person running a file
is not the person who can read `docker logs`. Server logs are for you. The
**run event stream** is for them.
### Three separate channels
| Channel | Audience | Medium |
|---|---|---|
| `structlog` JSON to stdout | You, debugging | Terminal, log aggregator |
| `run_events` table | The user | Timeline in the UI, `GET /run-log/{id}/events` |
| Prometheus `/metrics` | Ops | Scrape endpoint |
### The run_events table
```sql
run_events (
  id, run_id, ts, stage, level, code, message, detail_json
)
```
Every stage writes events. `stage` is one of `load`, `map`, `validate`,
`calculate`, `control`, `summarise`, `persist`. `level` is `info`, `warning`,
`error`. `code` is a stable machine code, `message` is written for a finance
person, not an engineer.
Bad: `KeyError: 'Due_Date'`
Good: `code: SHEET_COLUMN_MISSING, message: "The Invoices sheet has no Due Date column. 3 of 25 columns need mapping before this file can run."`
### Error contract
Never let a traceback reach the user. Every failure maps to a typed error:
```python
class PipelineError(Exception):
    code: str              # SHEET_MISSING, COLUMN_UNMAPPED, FILE_CORRUPT, ...
    user_message: str      # plain English, actionable
    stage: str
    detail: dict           # for the log, not the UI
```
`POST /run` never returns 500 for a bad input file. It returns 200 with a run
record whose status is `FAILED` and whose events explain why. A 500 means *your
code* broke, and that distinction is itself worth explaining in the debrief.
### What the UI shows per run
A vertical timeline: stage, duration, event count, expandable detail. Green
through `calculate`, amber at `control` when the gate blocks, red on failure.
Someone with no terminal access can answer "what happened to my file" unaided.
---
## 8. Git workflow
### Commits
Conventional Commits. Title under 72 characters, body explains *why*.
```
feat(validate): add E007 payment-to-invoice customer mismatch rule
Payments can reference an invoice belonging to a different customer.
PAY-2026 pays INV-1002 under C003 while the invoice belongs to C002.
The payment is excluded from the paid total and flagged rather than
reassigned, since reassignment would be a silent data correction.
Refs: docs/RULES.md
```
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`.
Scopes: `ingest`, `validate`, `calculate`, `control`, `ai`, `api`, `ui`,
`obs`, `docs`, `infra`.
One logical change per commit. If the body needs the word "and", split it.
### Branches and MRs
```
main                    always demoable, tagged
  phase/01-domain-core
  phase/02-validation
  ...
```
One MR per phase. MR description template lives in
`.github/pull_request_template.md`:
```markdown
## Phase N: <name>
### What this adds
### Requirement served
### Docs updated
- [ ] README.md   - [ ] ARCHITECTURE.md   - [ ] API.md
- [ ] RULES.md    - [ ] DEVELOPMENT.md    - [ ] CHANGELOG.md
### Verification
<commands run, expected output>
### Known gaps carried to next phase
```
Self-review every MR before merge. Run `/ponytail-review` on the diff first and
delete what it flags.
### Versioning
SemVer, tagged on merge to `main`.
| Tag | Phase |
|---|---|
| `v0.1.0` | Foundation |
| `v0.2.0` | Domain core |
| `v0.3.0` | Validation |
| ... | one minor per phase |
| `v1.0.0` | Core scope complete |
| `v1.1.0`+ | Presentation hardening |
`CHANGELOG.md` updated in the same MR, never retrofitted.
---
## 9. Phases
Each phase: branch, build, docs, `/ponytail-review`, MR, tag, merge.
### Core scope
**Phase 0: Foundation** `v0.1.0`
Clone template, init commit. Add `collections` package skeleton and docs
skeleton. Docker Compose up with Postgres. Health endpoint returns green.
*Done when:* `docker compose up` works and `/health` is 200.
**Phase 1: Domain core** `v0.2.0`
Contracts with `Decimal`. Loader with exact-match column resolution. Calculator:
outstanding, overdue, days, ageing, region enrichment. Pure functions, no DB, no
API. Unit tests against the reference numbers.
*Done when:* a script prints 15 overdue invoices, ~₹12.02L, West heaviest.
**Phase 2: Validation and exceptions** `v0.3.0` ← **the most important phase**
Pandera structural schemas. All 14 rules as individual, individually-tested
functions. `RULES.md` written. Assert every rule fires at least once on
dataset A.
*Done when:* rule coverage test passes and `RULES.md` matches the code.
**Phase 3: Persistence and run events** `v0.4.0`
SQLModel tables, Alembic migration. Run lifecycle. `run_events` table. Typed
`PipelineError`. Every stage emits events.
*Done when:* a deliberately broken file produces a FAILED run with readable
events and no traceback.
**Phase 4: API** `v0.5.0`
The six required endpoints plus `/health`, `/run-log/{id}/events`. Pydantic
response models. `API.md` written. Swagger clean.
*Done when:* a reviewer can drive the whole flow from `/docs`.
**Phase 5: Control gate and deterministic summary** `v0.6.0`
The 5% rule. Blocked payload with both rate denominators. Jinja template
summary. No LLM yet.
*Done when:* dataset A blocks, dataset B passes, both visible via API.
**Phase 6: LLM layer** `v0.7.0`
LiteLLM seam. Ollama with Phi-4-mini. anydoc context builder. Numeric guard.
Three-rung fallback. `summary_source` recorded.
*Done when:* the pipeline completes with the network disconnected, and
`llm_calls_total` shows local calls succeeding.
**Phase 7: Exception Explainer** `v0.8.0`
Batched by rule code. Cause, impact, suggested fix, owner. `auto_fixable`
hardcoded false. Guarded and cached.
*Done when:* every exception row carries an explanation, and the explainer never
invents an ID absent from its input.
**Phase 8: Frontend** `v0.9.0` then `v1.0.0` on core-scope completion
Five routes: runs list, run detail with timeline, exceptions table with filters,
summary with block banner, upload. Template's shadcn/ui components throughout.
*Done when:* someone who has never seen the terminal can upload a file and read
every output.
**Core scope cut line — everything above is the core build.**
### Extended scope
**Phase 9: Exports** `v1.1.0`
CSV per report, PDF management pack. Download buttons on every view.
**Phase 10: Multi-workbook** `v1.2.0`
Fuzzy tier 2 resolution, LLM tier 3 mapping, fingerprint cache,
`AWAITING_SCHEMA_CONFIRMATION` status, mapping confirmation UI. Fixtures C and D.
*This is the phase that saves the live demo.*
**Phase 11: Scheduler** `v1.3.0`
APScheduler in lifespan, `max_instances=1`, `coalesce=True`, file-hash dedup,
`trigger_source` on runs, `GET /schedule`. Disabled by default.
**Phase 12: Observability** `v1.4.0`
structlog JSON, Prometheus counters and histograms, `/metrics`, Run Triage role.
**Phase 13: A/B compare and rehearsal** `v1.5.0`
`GET /run/compare?a=&b=` returning a side-by-side delta of two runs. Rehearse
the demo three times against fixtures A, B and C. Write `DEMO.md`.
---
## 10. Testing, weighted toward exceptions
The brief grades exception handling. Test accordingly.
| Layer | What it covers | Where |
|---|---|---|
| Rule unit tests | One test per rule, positive and negative | `tests/validate/` |
| Rule coverage | Every rule fires at least once on dataset A | `tests/test_coverage.py` |
| Boundary tests | Due exactly on report date is not overdue. Payment exactly on report date counts | `tests/calculate/` |
| Reconciliation | invoices = outstanding + valid payments + excluded. Must tie | `tests/test_reconcile.py` |
| Gate tests | A blocks, B passes, boundary at exactly 5% | `tests/control/` |
| Guard tests | Narrator output containing a foreign number is rejected | `tests/ai/` |
| Failure tests | Corrupt file, missing sheet, empty sheet, all produce FAILED with a code, never a 500 | `tests/test_failures.py` |
| Independent recompute | Headline figure verified by raw SQL over persisted tables | `tests/test_sql_crosscheck.py` |
The independent recompute deserves a paragraph in the README. Verifying the
pandas result with a second method is the most convincing possible answer to
"what validation did you perform".
---
## 11. Demo runbook outline
Fifteen minutes, in this order:
1. `docker compose up`, open the UI. Thirty seconds.
2. Upload dataset A. Watch the timeline stream. Land on the blocked summary.
3. Open Exceptions. Filter to E007. Read the LLM explanation aloud. **This is the
   moment that lands.**
4. Upload dataset B. Gate passes. LLM summary renders. Point at
   `summary_source: llm`.
5. Disconnect the network. Re-run B. Still works, still says `llm`, because the
   model is local.
6. Upload their file. If it maps cleanly, run it. If not, show the mapping
   screen, confirm three columns, run it.
7. Open `/docs`. Show the six endpoints they asked for.
8. Show `/run-log`. Every run from the session, with runtime and exception rate.
Fallbacks in `DEMO.md`: what to do if Ollama is cold, if their file is corrupt,
if the network is down when it should not be.
---
## 12. Standing instruction for the build agent
Put this in `AGENTS.md` at repo root so every session inherits it:
```
- Report date is config, never datetime.now().
- Money is Decimal, never float.
- Never drop a row silently. Every exclusion emits an exception with a rule code.
- The LLM never computes, chooses, or corrects a number. It narrates and explains.
- anydoc output is LLM context only, never a calculation source.
- Every user-facing failure is a typed error with a plain-English message.
- Update the owning doc in the same commit as the behaviour change.
- One logical change per commit, Conventional Commits format.
- Run /ponytail-review before opening any MR.
```
