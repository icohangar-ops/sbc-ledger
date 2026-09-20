"""MCP server for the sbc-ledger engine.

Exposes deterministic ASC 718 share-based-compensation measurement as Model
Context Protocol tools. Thin wrapper — all measurement logic lives in
``sbc_ledger.engine`` and ``sbc_ledger.evidence`` and is reused verbatim;
nothing here touches the network, and volatility / risk-free rate / expected
term stay owner-supplied inputs, never model estimates.

Follows the same publishing path proven by invoice-audit-engine /
codesentinel: namespace ``io.github.Cubiczan``, stdio transport, published
via the ``mcp-publisher`` CLI.

Run it:

    uvx --from sbc-ledger sbc-ledger-mcp
    # or, from a checkout:
    python -m sbc_ledger.mcp_server
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from mcp.server.fastmcp import FastMCP

from sbc_ledger.engine import AwardType, Grant, period_expense, unit_fair_value
from sbc_ledger.evidence import evidence_pack

mcp = FastMCP(
    "sbc-ledger",
    instructions=(
        "Deterministic ASC 718 share-based-compensation measurement. Supply "
        "grant terms and a period; the tools compute unit fair value "
        "(grant-date FV or Black-Scholes on supplied inputs), straight-line "
        "accrual over the service period with a forfeiture estimate, and "
        "render the evidence pack a tester can reperform. Volatility, "
        "risk-free rate, and expected term are inputs — the model never "
        "chooses them."
    ),
)


def _grant_from_dict(item: dict[str, Any]) -> Grant:
    """Build a Grant from the CLI/JSON shape (same keys as the CLI's input file)."""
    return Grant(
        grant_id=item["grant_id"],
        award_type=AwardType(item["award_type"]),
        grant_date=date.fromisoformat(item["grant_date"]),
        shares=item["shares"],
        service_years=item["service_years"],
        grant_date_fv=item.get("grant_date_fv"),
        strike=item.get("strike"),
        spot=item.get("spot"),
        expected_term_years=item.get("expected_term_years"),
        risk_free_rate=item.get("risk_free_rate"),
        volatility=item.get("volatility"),
        dividend_yield=item.get("dividend_yield", 0),
        expected_forfeiture_rate=item.get("expected_forfeiture_rate", 0),
    )


def _jsonify(value: Any) -> Any:
    """JSON-safe conversion: Decimals become strings so cents survive exactly."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


@mcp.tool()
def measure_grant_expense(
    grant: dict[str, Any],
    period_start: str,
    period_end: str,
    actual_forfeitures: int = 0,
) -> dict[str, Any]:
    """Accrue one grant's ASC 718 expense over a period (straight-line, forfeiture-adjusted).

    Returns unit fair value, expected-to-vest shares, total cost, cumulative
    cost before the period, the period cost, and the remaining unrecognized
    balance. Amounts are exact decimal strings.

    Args:
        grant: Grant terms. Expected keys mirror the CLI input file:
            grant_id, award_type ("option" | "rsu"), grant_date (ISO date),
            shares, service_years, grant_date_fv, strike, spot,
            expected_term_years, risk_free_rate, volatility, dividend_yield,
            expected_forfeiture_rate.
        period_start: ISO date the accrual period starts.
        period_end: ISO date the accrual period ends.
        actual_forfeitures: Shares forfeited in the period (drives the true-up).
    """
    row = period_expense(
        _grant_from_dict(grant),
        date.fromisoformat(period_start),
        date.fromisoformat(period_end),
        actual_forfeitures,
    )
    return _jsonify(asdict(row))


@mcp.tool()
def grant_unit_fair_value(grant: dict[str, Any]) -> str:
    """Compute a grant's unit fair value.

    Uses grant-date FV when supplied; otherwise spot for RSUs or
    Black-Scholes for options on the supplied inputs. Returns an exact
    decimal string.

    Args:
        grant: Grant terms, same shape as measure_grant_expense's input.
    """
    return str(unit_fair_value(_grant_from_dict(grant)))


@mcp.tool()
def sbc_evidence_pack(
    grants: list[dict[str, Any]],
    period_start: str,
    period_end: str,
    period_label: str = "",
    owner: str = "",
) -> dict[str, Any]:
    """Build the ASC 718 evidence pack a tester can reperform without the source code.

    Accrues every supplied grant over the period and aggregates the
    population into the control-spine pack (period cost, unrecognized
    remainder, per-grant detail, owner sign-off).

    Args:
        grants: Grant terms, same shape as measure_grant_expense's input;
            each may carry actual_forfeitures.
        period_start: ISO date the accrual period starts.
        period_end: ISO date the accrual period ends.
        period_label: Close period label; defaults to "<start> to <end>".
        owner: Named owner for sign-off. Must not be the engine.
    """
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    rows = tuple(
        period_expense(
            _grant_from_dict(item), start, end, item.get("actual_forfeitures", 0)
        )
        for item in grants
    )
    return _jsonify(evidence_pack(rows, period_label or f"{period_start} to {period_end}", owner))


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
