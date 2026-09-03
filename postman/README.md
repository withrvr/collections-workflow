# Postman collection

Verified against the live backend via Newman: 13 requests, 25
assertions, 0 failures — this isn't a hand-written guess at what the
API returns, every request and test script actually ran.

## Import

1. Postman -> Import -> select all three files:
   - `collections-workflow.postman_collection.json`
   - `local.postman_environment.json`
   - `ngrok.postman_environment.json`
2. Top-right environment dropdown -> **Collections Workflow - Local**.

## Test flow with the given Excel file

1. **Health > Health Check** — run it, confirm `true`.
2. **Runs > Create Run - Dataset A (Blocks)** — click into the Body tab,
   click **Select File** next to `file`, choose
   `backend/app/collections/fixtures/dataset_a_original.xlsx` (or your
   own copy of the sample workbook). Send. The test script saves the
   returned run's id into `{{run_id}}` automatically — nothing else to
   configure.
3. Open **Reports** folder, run every request top to bottom against that
   same run: timeline, overdue, exceptions (cause/impact/fix/owner per
   row), regions, summary (the block banner + AI narrative).
4. **Runs > Create Run - Dataset B (Passes)** — same idea, attach
   `dataset_b_clean.xlsx`. Re-run **Reports** to see a `PASSED` run
   instead.
5. **Error Handling** folder — run both requests any time to see the
   error contract live: attach `postman/fixtures/corrupt.xlsx` (a real,
   deliberately-invalid file committed here for this test) to the first
   request — never 500s, comes back `FAILED` with a readable reason. The
   second needs no file — an unknown run id 404s cleanly.

To upload your own workbook instead: **Runs > Create Run - Your Own
File**, attach any `.xlsx` with the same four sheets
(Customers/Invoices/Payments/Region_Mapping). Everything downstream
follows `{{run_id}}` automatically.

## Why file fields are empty on import

Postman strips local file paths (`src`) out of form-data file fields
when importing a collection someone sent you — a JSON file silently
reading a path off your disk is a real attack vector, so Postman
refuses it by design. Every "Create Run" request's pre-request script
prints the exact path to attach in the Postman Console (View -> Show
Postman Console) as a reminder. You only select it once per request;
Postman remembers it after that.

## Testing against the public tunnel instead

Switch the environment dropdown to **Collections Workflow - Ngrok**
(`base_url` becomes the ngrok URL) — same requests, same test scripts,
nothing else changes. Useful for demoing from a phone or another
machine without touching this one's `localhost`.
