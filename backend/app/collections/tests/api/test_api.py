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
    assert "BLOCKED" in body["narrative"]


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
