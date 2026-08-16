from datetime import date
from decimal import Decimal

from sbc_ledger.engine import AwardType, Grant, black_scholes_call, period_expense, unit_fair_value
from sbc_ledger.evidence import evidence_pack


def test_black_scholes_atm_four_year() -> None:
    fv = black_scholes_call(
        Decimal("10"), Decimal("10"), Decimal("4"), Decimal("0.05"), Decimal("0.40")
    )
    assert fv == Decimal("3.82")


def test_rsu_straight_line_first_year_of_two() -> None:
    grant = Grant(
        grant_id="RSU-1",
        award_type=AwardType.RSU,
        grant_date=date(2026, 1, 1),
        shares=10000,
        service_years=Decimal("2"),
        grant_date_fv=Decimal("12"),
    )
    row = period_expense(grant, date(2026, 1, 1), date(2027, 1, 1))
    assert row.unit_fv == Decimal("12.00")
    assert row.total_cost == Decimal("120000.00")
    assert row.period_cost == Decimal("60000.00")
    assert row.remaining == Decimal("60000.00")


def test_forfeiture_estimate_reduces_cost() -> None:
    grant = Grant(
        grant_id="RSU-2",
        award_type=AwardType.RSU,
        grant_date=date(2026, 1, 1),
        shares=10000,
        service_years=Decimal("1"),
        grant_date_fv=Decimal("10"),
        expected_forfeiture_rate=Decimal("0.10"),
    )
    row = period_expense(grant, date(2026, 1, 1), date(2027, 1, 1))
    assert row.expected_to_vest == Decimal("9000.00")
    assert row.total_cost == Decimal("90000.00")


def test_option_uses_black_scholes_when_fv_omitted() -> None:
    grant = Grant(
        grant_id="OPT-1",
        award_type=AwardType.OPTION,
        grant_date=date(2026, 1, 1),
        shares=1000,
        service_years=Decimal("4"),
        grant_date_fv=None,
        strike=Decimal("10"),
        spot=Decimal("10"),
        expected_term_years=Decimal("4"),
        risk_free_rate=Decimal("0.05"),
        volatility=Decimal("0.40"),
    )
    assert unit_fair_value(grant) == Decimal("3.82")


def test_evidence_pack_totals() -> None:
    grant = Grant(
        "RSU-1", AwardType.RSU, date(2026, 1, 1), 100, Decimal("1"), Decimal("10")
    )
    row = period_expense(grant, date(2026, 1, 1), date(2027, 1, 1))
    pack = evidence_pack((row,), "FY2026", "Controller")
    assert pack["period_cost"] == "1000.00"
    assert pack["control_id"] == "ICFR-ASC718-01"
    assert pack["lock_state"] == "LOCKED"
    assert pack["is_evidence"] is True


def test_unsigned_pack_is_exploring_not_evidence() -> None:
    grant = Grant(
        "RSU-1", AwardType.RSU, date(2026, 1, 1), 100, Decimal("1"), Decimal("10")
    )
    row = period_expense(grant, date(2026, 1, 1), date(2027, 1, 1))
    pack = evidence_pack((row,), "FY2026", "")
    assert pack["lock_state"] == "EXPLORING"
    assert pack["is_evidence"] is False
