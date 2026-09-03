# Design Rationale: Twenty Questions and Answers

Each entry: a question worth asking about this design, the answer, and the
design decision that makes the answer true. If a design decision here is not
in `MASTER_PLAN.md`, one of the two documents is wrong.

---

## Business logic

**1. Why is the report date 2026-07-31 and not today?**

Because the workbook's README sheet fixes it. A collection position is always
stated as of a date. If it moved with the clock, the same file would produce
different numbers tomorrow and nothing could be reconciled or audited.

*Design:* `REPORT_DATE` in config, parsed from the workbook README sheet when
present, overridable per run, never `datetime.now()`. Recorded on the run record
with its source.

---

**2. Is tax included in the outstanding amount?**

No. The workbook defines Outstanding as Invoice Amount minus valid payments.
`Tax_Amount_INR` is carried through to the output for reference but never added.
If they intend tax-inclusive ageing, it is a one-line config change and the
assumption is documented.

*Design:* stated in README assumptions. `include_tax` is a config flag defaulting
to false so the answer is demonstrable, not just claimed.

---

**3. An invoice is due exactly on the report date. Overdue or not?**

Not overdue. The rule says Due Date *before* the report date, so the comparison
is strictly less-than. An invoice due today is current.

*Design:* explicit boundary test in `tests/calculate/`.

---

**4. A payment lands exactly on the report date. Does it count?**

Yes. The rule says payments received *on or before* the report date. Inclusive on
that side, exclusive on the due-date side. The asymmetry is deliberate and both
directions are tested.

---

**5. Why is INV-1007 not showing as overpaid customer credit?**

It is flagged as E014, payments exceeding the invoice amount, and outstanding is
floored at zero rather than going negative. Netting an overpayment against that
customer's other invoices would be a business decision the workbook does not
define, so it is surfaced rather than assumed.

*Design:* E014 is not on their required list. Adding it and saying so proves the
data was read, not just the brief.

---

**6. Why not net Credit Notes against that customer's open invoices?**

The workbook says exclude them from the overdue report and show them in
exceptions. It does not define netting rules. Netting would change the reported
position based on an assumption nobody authorised.

*Design:* named explicitly in the README assumptions list as a judgement call.

---

## Validation and exceptions

**7. Why did the management summary get blocked?**

Because the control rule fired as designed. Dataset A has roughly 16 to 19
exception rows against 36 invoice records, about 45%, far above the 5% threshold.
Blocking is the correct output, not a failure.

*Design:* the gate is never tuned to pass. The blocked payload reports the rate,
both denominators, the threshold, and the count.

---

**8. Exception records over invoice records: which denominator did you use?**

Invoice record count, 36, as the brief words it. Because the wording is
ambiguous, the response reports both that rate and a distinct-invoices-affected
rate, and the README says which one drives the gate and why.

*Design:* turning an ambiguity into a documented decision, rather than picking
silently, is the whole point.

---

**9. How do you know you caught every data quality issue?**

Two ways. A coverage test asserts every rule E001 to E014 fires at least once on
dataset A, so a rule that never triggers is treated as a bug rather than good
news. And a reconciliation test proves invoice totals equal outstanding plus
valid payments plus excluded amounts, so no value silently vanishes.

---

**10. Why not just fix the bad rows automatically?**

The workbook says do not silently delete problematic rows. The same logic applies
to silent fixes. Auto-correcting a customer mismatch would move cash between
ledgers on a guess. The explainer proposes a fix and names the owner;
`auto_fixable` is hardcoded false. Shipping auto-remediation would need a human
approval queue first.

---

**11. Walk me through one exception end to end.**

PAY-2026 is recorded against customer C003, but INV-1002 belongs to C002. Rule
E007 fires. The payment is excluded from the paid total, so C002 correctly still
shows as overdue rather than being credited with someone else's cash. The
exception row carries the cause, the business impact on both ledgers, the
suggested fix, and Accounts Receivable as owner. Nothing was deleted or moved.

---

## AI usage

**12. How do I know the LLM did not compute any of these numbers?**

Three layers. The calculator produces a frozen metrics dictionary before any LLM
is invoked. The narrator receives only that dictionary, never the raw sheets.
Then a post-generation guard extracts every numeric token from the output and
asserts each appears in the input dictionary, rejecting and falling back if not.
The constraint is enforced in code, not requested in a prompt.

*Design:* `ai/guard.py`, with a test that a response containing a foreign number
is rejected.

---

**13. What happens if the LLM is unavailable?**

The chain degrades: local Ollama, then a cloud provider if a key is set, then a
deterministic Jinja template. The pipeline never fails because a model is down,
and every run records which rung produced the text in `summary_source`. Being
honest about degradation is itself a control.

---

**14. Does this send our financial data to a third party?**

Not on the default path. The default provider is a local Ollama model on the
machine, so no data leaves it. The pipeline was demonstrated running with the
network disconnected. Cloud providers are a one-env-var switch if the client
prefers them, and that boundary is documented rather than buried.

---

**15. Why a 4B local model instead of GPT or Claude?**

Because of what the model is asked to do. It narrates pre-computed figures,
explains a rule violation, and returns a small JSON column mapping. None needs
reasoning depth, all need format discipline, and small instruct models handle
structured output reliably. It also removes the data-residency question entirely,
which for financial data matters more than prose quality.

---

**16. Why not build an autonomous agent for this?**

The brief requires financial numbers to come from code. An agent with planning
latitude and tool access cannot be *proven* not to have touched a number, whereas
four typed single-purpose roles can. Financial reporting also needs the same
input to produce the same output on every run, and agent loops are
nondeterministic by construction. The orchestrator is a plain Python function
calling four stages in a fixed order.

---

## Engineering

**17. What happens when you get a workbook with different column names?**

Three tiers. Exact match against an alias table, then fuzzy token matching, then
an LLM mapper for whatever the first two missed. Anything below 0.80 confidence
stops the run at `AWAITING_SCHEMA_CONFIRMATION` and asks a human, because
guessing at which column is money is not acceptable. Once confirmed, the mapping
is cached against the workbook fingerprint, so the same ERP export never costs a
second LLM call.

---

**18. Our team cannot read server logs. How do they know what went wrong?**

Logs and user feedback are separate channels by design. Every stage writes to a
`run_events` table with a stable code and a message written for a finance person,
surfaced as a timeline in the UI and at `GET /run-log/{id}/events`. A bad input
file never returns a 500 or a traceback; it produces a run with status FAILED and
readable events. A 500 would mean our code broke, which is a different problem
with a different owner.

---

**19. Why did you use the official FastAPI template rather than starting clean?**

It supplies the parts that aren't the point of this project and would otherwise consume the
timeline: Postgres with SQLModel and Alembic, Docker Compose, auth, CI, and a
React frontend with shadcn/ui. All collections code lives in one folder,
`app/collections`, with a single line wiring the router in. The initial commit is
the unmodified template, so every subsequent commit is our own work and the diff
is the deliverable.

---

**20. If this went to production, what would you change?**

Four things, in order. APScheduler moves to Celery Beat or a Kubernetes CronJob
once more than one worker exists. Structural checks today are type coercion at
load time plus declarative schema-shape constants (see ARCHITECTURE.md for why
that's Pandera-shaped work without the Pandera dependency); a managed
observability layer would replace bespoke trend detection, and Pandera would be
the natural upgrade if ingestion ever moved to a DataFrame-based pipeline. The
exception explainer gains a human approval queue and becomes remediation rather
than advice. And payment application moves from invoice-level to a proper cash
application matcher, which is the hardest and most valuable piece in commercial
AR platforms and where E007 actually comes from.

---

## Two worth hoping someone asks

**How did you use AI to build this, not just inside it?**

The build ran with two agent skills. Ponytail enforces a YAGNI ladder so the
agent stops before over-building, and its published benchmark was measured on a
headless agent editing this exact FastAPI template. Caveman compresses agent
prose while leaving code byte-exact. Every phase ended with a review pass that
produced a delete-list. Anydoc converts workbooks to Markdown for LLM context in
single-digit milliseconds, and is deliberately barred from the calculation path
because a Markdown cell is a formatted string that has lost its type.

**What is the weakest part of this?**

Pick one and answer honestly. The candid options: GSTIN validation is
format-only with no checksum. Payments are applied at invoice level rather than
FIFO across a customer ledger. The 5% denominator remains ambiguous in the brief
and was resolved by documented assumption rather than confirmation. Any of these
answered plainly beats a claim that there is no weak part.
