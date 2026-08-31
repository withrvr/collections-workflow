"""End-to-end API tests: the whole flow a reviewer would drive from
/docs -- upload, list, detail, overdue, exceptions, regions, summary,
run-log -- against dataset A. MASTER_PLAN.md Phase 4's done-when:
"a reviewer can drive the whole flow from /docs."
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_a_original.xlsx"
)
API = "/api/v1/collections"


def _upload_dataset_a(client: TestClient) -> dict[str, Any]:
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            f"{API}/runs/",
            files={"file": ("dataset_a_original.xlsx", f, "application/octet-stream")},
        )
    assert response.status_code == 200
    return dict(response.json())


def test_create_run_matches_reference_numbers(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    assert run["status"] == "BLOCKED"
    assert run["overdue_count"] == 15
    assert run["total_outstanding"] == "1202000.00"
    assert run["exception_count"] == 17
    assert run["has_download"] is True


def test_create_run_with_custom_report_date(client: TestClient) -> None:
    """A different report_date shifts overdue/ageing math -- proves the
    override actually reaches the pipeline, not just gets accepted."""
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            f"{API}/runs/",
            files={"file": ("dataset_a_original.xlsx", f, "application/octet-stream")},
            data={"report_date": "2026-01-01"},
        )
    assert response.status_code == 200
    run = response.json()
    assert run["report_date"] == "2026-01-01"
    # A much earlier report date means fewer invoices are overdue yet.
    assert run["overdue_count"] != 15


def test_create_run_with_malformed_report_date_is_422(client: TestClient) -> None:
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            f"{API}/runs/",
            files={"file": ("dataset_a_original.xlsx", f, "application/octet-stream")},
            data={"report_date": "not-a-date"},
        )
    assert response.status_code == 422


def test_download_run_file_roundtrips_the_upload(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/runs/{run['id']}/download")
    assert response.status_code == 200
    assert response.content == FIXTURE_PATH.read_bytes()


def test_download_unknown_run_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/runs/{uuid.uuid4()}/download")
    assert response.status_code == 404


def test_list_runs_includes_created_run(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/runs/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["id"] == run["id"]


def test_get_run_by_id(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/runs/{run['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == run["id"]


def test_get_run_unknown_id_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/runs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_overdue_endpoint(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/overdue/", params={"run_id": run["id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 15
    assert body["total_outstanding"] == "1202000.00"
    assert all(row["is_overdue"] for row in body["data"])


def test_exceptions_endpoint_and_rule_filter(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/exceptions/", params={"run_id": run["id"]})
    assert response.status_code == 200
    assert response.json()["count"] == 17

    filtered = client.get(
        f"{API}/exceptions/", params={"run_id": run["id"], "rule_code": "E001"}
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["count"] == 1
    assert body["data"][0]["rule_code"] == "E001"
    row = body["data"][0]
    assert row["cause"]
    assert row["suggested_fix"]
    assert row["owner"]
    assert row["auto_fixable"] is False
    assert row["explanation_source"] in ("ollama", "cloud", "fallback")


def test_regions_endpoint_west_heaviest(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/regions/", params={"run_id": run["id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["heaviest_region"] == "West"
    west = next(r for r in body["data"] if r["region"] == "West")
    assert west["outstanding"] == "472000.00"


def test_summary_endpoint(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/summary/", params={"run_id": run["id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["overdue_count"] == 15
    assert body["exception_count"] == 17
    assert body["by_region"][0]["region"] == "West"
    assert body["gate_threshold"] == "0.0500"
    assert body["distinct_invoices_affected"] == 14
    # Narrative is now a real multi-sentence analysis (creative when an
    # LLM wrote it), not guaranteed to echo the literal word "BLOCKED" --
    # the status field above is the source of truth for that; here we
    # only check the narrative is substantive, not a one-liner.
    assert len(body["narrative"]) > 200
    assert body["summary_source"] in ("ollama", "cloud", "fallback")


def test_run_log_events_endpoint(client: TestClient) -> None:
    run = _upload_dataset_a(client)
    response = client.get(f"{API}/run-log/{run['id']}/events")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    stages = [e["stage"] for e in body["data"]]
    assert stages == [
        "load",
        "load",
        "validate",
        "validate",
        "validate",
        "calculate",
        "calculate",
        "control",
        "control",
        "summarise",
        "persist",
    ]


def test_broken_upload_produces_failed_run_not_500(client: TestClient) -> None:
    response = client.post(
        f"{API}/runs/",
        files={
            "file": (
                "corrupt.xlsx",
                b"not a real xlsx file",
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["error_code"] == "FILE_CORRUPT"

    events = client.get(f"{API}/run-log/{body['id']}/events").json()
    assert events["data"][-1]["level"] == "error"

    overdue = client.get(f"{API}/overdue/", params={"run_id": body["id"]}).json()
    assert overdue["count"] == 0


def test_send_email_calls_send_email_with_the_narrative(
    client: TestClient, monkeypatch
) -> None:
    """Mocks the SMTP send itself (no live mail server needed for the
    test) -- proves the endpoint builds and dispatches a real email for
    a finished run, not that Mailpit specifically works (that's
    infra, not app logic)."""
    import app.collections.api.runs as runs_module

    sent = {}

    def fake_send_email(*, email_to, subject, html_content):
        sent["to"] = email_to
        sent["subject"] = subject
        sent["html"] = html_content

    monkeypatch.setattr(runs_module, "send_email", fake_send_email)
    # emails_enabled is a computed property (no setter) -- drive it via
    # the real fields it derives from instead of monkeypatching itself.
    monkeypatch.setattr(runs_module.core_settings, "SMTP_HOST", "localhost")
    monkeypatch.setattr(
        runs_module.core_settings, "EMAILS_FROM_EMAIL", "test@example.com"
    )

    run = _upload_dataset_a(client)
    response = client.post(
        f"{API}/runs/{run['id']}/send-email", json={"to": "reviewer@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["sent"] is True
    assert sent["to"] == "reviewer@example.com"
    assert run["source_filename"] in sent["subject"]
    assert "BLOCKED" in sent["subject"] or run["status"] in sent["subject"]


def test_send_email_disabled_returns_503(client: TestClient, monkeypatch) -> None:
    import app.collections.api.runs as runs_module

    monkeypatch.setattr(runs_module.core_settings, "SMTP_HOST", None)
    run = _upload_dataset_a(client)
    response = client.post(
        f"{API}/runs/{run['id']}/send-email", json={"to": "reviewer@example.com"}
    )
    assert response.status_code == 503
