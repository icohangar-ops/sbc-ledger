from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from control_spine import exit_code
from sbc_ledger.engine import AwardType, Grant, period_expense
from sbc_ledger.evidence import evidence_markdown, evidence_pack


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC 718 grant ledger + evidence pack")
    p.add_argument("grants_json")
    p.add_argument("--period-start", required=True)
    p.add_argument("--period-end", required=True)
    p.add_argument("--period-label", default="")
    p.add_argument("--owner", default="")
    args = p.parse_args(argv)
    raw = json.loads(Path(args.grants_json).read_text())
    start = date.fromisoformat(args.period_start)
    end = date.fromisoformat(args.period_end)
    rows = []
    for item in raw["grants"]:
        grant = Grant(
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
        rows.append(period_expense(grant, start, end, item.get("actual_forfeitures", 0)))
    pack = evidence_pack(
        tuple(rows), args.period_label or f"{args.period_start} to {args.period_end}", args.owner
    )
    print(evidence_markdown(pack))
    print(pack["lock_state"], file=sys.stderr)
    return exit_code(pack)


if __name__ == "__main__":
    raise SystemExit(main())
