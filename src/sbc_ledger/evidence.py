from __future__ import annotations

from decimal import Decimal

from control_spine import render_spine, seal
from sbc_ledger.engine import PeriodExpense, money

FOUNDATION = (
    "Volatility, risk-free rate, and expected term are owner inputs, not estimated here.",
    "Expense is straight-line over the service period on expected-to-vest shares.",
    "Grant-date FV is used when supplied; otherwise Black-Scholes on the supplied inputs.",
)

ENGINE_ID = "sbc-ledger-engine"
ENGINE_VERSION = "0.1.0"


def evidence_pack(rows: tuple[PeriodExpense, ...], period_label: str, owner: str) -> dict:
    total = money(sum((r.period_cost for r in rows), Decimal("0")))
    remaining = money(sum((r.remaining for r in rows), Decimal("0")))
    pack = {
        "control_id": "ICFR-ASC718-01",
        "control_objective": "Share-based payment cost is complete, measured at grant-date FV, and accrued over the service period.",
        "period": period_label,
        "population_count": len(rows),
        "threshold": "100% of grants outstanding or granted in the period.",
        "period_cost": str(total),
        "unrecognized_remaining": str(remaining),
        "grants": [
            {
                "grant_id": r.grant_id,
                "unit_fv": str(r.unit_fv),
                "expected_to_vest": str(r.expected_to_vest),
                "total_cost": str(r.total_cost),
                "period_cost": str(r.period_cost),
                "remaining": str(r.remaining),
                "forfeited_this_period": r.forfeited_this_period,
            }
            for r in rows
        ],
        "prepared_by": ENGINE_ID,
        "owner_signoff": owner,
        "conclusion": f"Period compensation cost {total}. Owner confirms grant population against the equity ledger.",
    }
    return seal(
        pack,
        engine_id=ENGINE_ID,
        engine_version=ENGINE_VERSION,
        inputs={"grant_ids": [r.grant_id for r in rows], "period": period_label},
        foundation=FOUNDATION,
    )


def evidence_markdown(pack: dict) -> str:
    lines = [
        f"# ASC 718 evidence pack — {pack['period']}",
        "",
        *render_spine(pack),
        f"**Control:** {pack['control_id']}",
        f"**Period cost:** {pack['period_cost']}  **Unrecognized:** {pack['unrecognized_remaining']}",
        f"**Owner sign-off:** {pack['owner_signoff'] or '_unsigned_'}",
        "",
        "| Grant | Unit FV | Expected to vest | Period cost | Remaining |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in pack["grants"]:
        lines.append(
            f"| {row['grant_id']} | {row['unit_fv']} | {row['expected_to_vest']} | {row['period_cost']} | {row['remaining']} |"
        )
    lines += ["", pack["conclusion"], ""]
    return "\n".join(lines)
