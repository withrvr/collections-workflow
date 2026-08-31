"""Tier-1 (exact-match) column resolution. Fuzzy and LLM tiers are Phase 10 (MASTER_PLAN.md)."""

from __future__ import annotations


class ColumnResolutionError(Exception):
    """A sheet is missing one or more required columns."""

    def __init__(self, sheet_name: str, missing_headers: list[str]) -> None:
        self.sheet_name = sheet_name
        self.missing_headers = missing_headers
        joined = ", ".join(missing_headers)
        super().__init__(f"Sheet '{sheet_name}' is missing required column(s): {joined}")


CUSTOMER_FIELDS: dict[str, str] = {
    "customer_id": "Customer_ID",
    "customer_name": "Customer_Name",
    "city": "City",
    "state": "State",
    "region": "Region",
    "gstin": "GSTIN",
    "credit_limit": "Credit_Limit_INR",
    "active_flag": "Active_Flag",
}

INVOICE_FIELDS: dict[str, str] = {
    "invoice_id": "Invoice_ID",
    "customer_id": "Customer_ID",
    "invoice_date": "Invoice_Date",
    "due_date": "Due_Date",
    "invoice_amount": "Invoice_Amount_INR",
    "tax_amount": "Tax_Amount_INR",
    "status": "Status",
    "salesperson": "Salesperson",
    "source_system_ref": "Source_System_Ref",
}

PAYMENT_FIELDS: dict[str, str] = {
    "payment_id": "Payment_ID",
    "customer_id": "Customer_ID",
    "invoice_id": "Invoice_ID",
    "payment_date": "Payment_Date",
    "payment_amount": "Payment_Amount_INR",
    "payment_mode": "Payment_Mode",
    "bank_ref": "Bank_Ref",
}

REGION_MAP_FIELDS: dict[str, str] = {
    "state": "State",
    "region": "Region",
}


def resolve_columns(
    sheet_name: str, header_row: tuple[object, ...], expected: dict[str, str]
) -> dict[str, int]:
    """Exact-match column resolution: canonical field name -> header column index.

    Raises ColumnResolutionError listing every missing header at once, not
    just the first, so a mismatched workbook only needs one round trip to
    diagnose.
    """
    header_index = {str(cell).strip(): i for i, cell in enumerate(header_row) if cell is not None}
    resolved: dict[str, int] = {}
    missing: list[str] = []
    for field_name, header_text in expected.items():
        if header_text in header_index:
            resolved[field_name] = header_index[header_text]
        else:
            missing.append(header_text)
    if missing:
        raise ColumnResolutionError(sheet_name, missing)
    return resolved
