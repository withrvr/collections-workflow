# API

Owns: every endpoint — method, path, params, response schema, status
codes, error codes. Does not own: business rationale (see `README.md`),
setup (see `DEVELOPMENT.md`).

Status: **Phase 5 complete.** All endpoints mounted under
`/api/v1/collections`, no auth required. Response schemas:
`app/collections/api/schemas.py`.

## Health check

`GET /api/v1/utils/health-check/` — from the base template, returns `true`.

## Endpoints

### `POST /collections/runs/`

Upload a workbook and run the pipeline against it synchronously.
Multipart form field `file`. Always returns `200` with a `Run` — a bad
input file produces a `FAILED` run in the response body, never a `500`
(see `ARCHITECTURE.md`'s error contract). `error_code`/`error_message`
are set only when `status == "FAILED"`.

```json
{
  "id": "uuid", "status": "BLOCKED", "source_filename": "dataset_a.xlsx",
  "report_date": "2026-07-31", "created_at": "...", "completed_at": "...",
  "error_code": null, "error_message": null,
  "customer_count": 25, "invoice_count": 36, "payment_count": 29,
  "overdue_count": 15, "total_outstanding": "1202000.00", "exception_count": 17
}
```

### `GET /collections/runs/`

List runs, newest first. Query params: `skip` (default 0), `limit`
(default 100). Returns `{"data": [Run, ...], "count": <total>}`.

### `GET /collections/runs/{run_id}`

One run. `404` if `run_id` doesn't exist.

### `GET /collections/overdue/?run_id=`

Every overdue `RunInvoicePosition` for that run. `404` if `run_id`
doesn't exist; empty `data`/`count: 0` if the run failed before
`calculate` or genuinely has no overdue invoices.

```json
{"run_id": "uuid", "count": 15, "total_outstanding": "1202000.00", "data": [...]}
```

### `GET /collections/exceptions/?run_id=&rule_code=&severity=`

Every `RunException` for that run. `rule_code` (e.g. `E001`) and
`severity` (`error`/`warning`) are optional filters.

### `GET /collections/regions/?run_id=`

Overdue outstanding grouped by region, sorted heaviest first.

```json
{"run_id": "uuid", "heaviest_region": "West", "data": [{"region": "West", "outstanding": "472000.00", "overdue_count": 5}, ...]}
```

### `GET /collections/summary/?run_id=`

The run's numeric summary, region breakdown, and the control gate's
"blocked payload" (QA_PREP.md Q7): `gate_threshold` (`0.05`),
`exception_row_rate` (drives the gate), `distinct_invoices_affected` and
`distinct_invoice_rate` (the alternate denominator, reported for
transparency — see `ARCHITECTURE.md`'s control gate section), and
`narrative`, the deterministic plain-English summary. All `null` if the
run failed before `control` ran. `status` is `"PASSED"`, `"BLOCKED"`, or
`"FAILED"`.

```json
{
  "run_id": "uuid", "status": "BLOCKED", "report_date": "2026-07-31",
  "customer_count": 25, "invoice_count": 36, "payment_count": 29,
  "overdue_count": 15, "total_outstanding": "1202000.00", "exception_count": 17,
  "gate_threshold": "0.0500", "exception_row_rate": "0.4722",
  "distinct_invoices_affected": 14, "distinct_invoice_rate": "0.3889",
  "narrative": "Run against dataset_a_original.xlsx as of 2026-07-31: 36 invoice(s) processed, 15 overdue totaling Rs 1,202,000.00 (West heaviest). 17 exception(s) found (47.2% of invoices, 14 distinct invoice(s) affected, 38.9%) -- BLOCKED: exceeds the 5% control threshold.",
  "by_region": [{"region": "West", "outstanding": "472000.00", "overdue_count": 5}, "..."]
}
```

### `GET /collections/run-log/{run_id}/events`

The run's full event timeline, oldest first — `stage`, `level`, `code`,
`message`, `detail`. This is what a `FAILED` run's readable error
actually comes from; `data[-1]` on a failed run is always the `error`-level
event that explains why.

## Error codes

Set on a `FAILED` `Run.error_code`, and on that run's final `run_events`
row. See `ARCHITECTURE.md`'s error contract for the full mapping.

| Code | Meaning |
|---|---|
| `SHEET_MISSING` | A required sheet (Customers/Invoices/Payments/Region_Mapping) is absent |
| `SHEET_COLUMN_MISSING` | A present sheet is missing one or more required columns |
| `FILE_CORRUPT` | The uploaded file isn't a valid Excel workbook |
| `ROW_DATA_INVALID` | A cell couldn't be parsed (e.g. text in a money/date column) |
| `UNEXPECTED_ERROR` | A genuine bug, not a bad input file — logged with a full traceback server-side, never shown to the user |
