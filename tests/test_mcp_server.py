"""The MCP server registers the engine's deterministic measurement as callable tools.

Pins the test suite's canonical RSU case (10,000 shares at FV 12, two-year
service, first year = 60,000.00) through the MCP tool path. Skipped cleanly
when the optional ``mcp`` SDK is not installed.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp")

from sbc_ledger import mcp_server  # noqa: E402


def _tool_names() -> set[str]:
    tools = asyncio.run(mcp_server.mcp.list_tools())
    return {t.name for t in tools}


def _grant() -> dict:
    return {
        "grant_id": "RSU-1",
        "award_type": "rsu",
        "grant_date": "2026-01-01",
        "shares": 10000,
        "service_years": "2",
        "grant_date_fv": "12",
    }


def test_expected_tools_registered() -> None:
    assert _tool_names() >= {
        "measure_grant_expense",
        "grant_unit_fair_value",
        "sbc_evidence_pack",
    }


def test_measure_grant_expense_pins_the_suite_number() -> None:
    row = mcp_server.measure_grant_expense(
        _grant(), period_start="2026-01-01", period_end="2027-01-01"
    )
    assert row["unit_fv"] == "12.00"
    assert row["total_cost"] == "120000.00"
    assert row["period_cost"] == "60000.00"
    assert row["remaining"] == "60000.00"


def test_evidence_pack_totals_population() -> None:
    pack = mcp_server.sbc_evidence_pack(
        [_grant()],
        period_start="2026-01-01",
        period_end="2027-01-01",
        period_label="H1 2026",
    )
    assert pack["population_count"] == 1
    assert pack["lock_state"] == "EXPLORING"
    assert pack["is_evidence"] is False
    assert pack["invoked_via"] == "mcp"
    assert pack["period_cost"] == "60000.00"
