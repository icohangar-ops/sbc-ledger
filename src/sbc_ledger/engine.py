"""ASC 718 share-based compensation.

Grant register, Black-Scholes when grant-date FV is not supplied, straight-line
accrual over the service period with a forfeiture estimate, and true-up for
actual forfeitures.

It does not choose volatility, the risk-free rate, or expected term. Those
are inputs. The control owner signs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from math import erf, exp, log, sqrt


CENTS = Decimal("0.01")
FOUR = Decimal("0.0001")


def money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def black_scholes_call(
    spot: Decimal,
    strike: Decimal,
    years: Decimal,
    rate: Decimal,
    volatility: Decimal,
    dividend_yield: Decimal = Decimal("0"),
) -> Decimal:
    S, K, T, r, sig, q = map(float, (spot, strike, years, rate, volatility, dividend_yield))
    if T <= 0 or sig <= 0 or S <= 0 or K <= 0:
        return money(max(S - K, 0))
    d1 = (log(S / K) + (r - q + sig * sig / 2.0) * T) / (sig * sqrt(T))
    d2 = d1 - sig * sqrt(T)
    call = exp(-q * T) * S * _ncdf(d1) - exp(-r * T) * K * _ncdf(d2)
    return money(call)


class AwardType(str, Enum):
    OPTION = "option"
    RSU = "rsu"


@dataclass(frozen=True)
class Grant:
    grant_id: str
    award_type: AwardType
    grant_date: date
    shares: int
    service_years: Decimal
    grant_date_fv: Decimal | None
    strike: Decimal | None = None
    spot: Decimal | None = None
    expected_term_years: Decimal | None = None
    risk_free_rate: Decimal | None = None
    volatility: Decimal | None = None
    dividend_yield: Decimal = Decimal("0")
    expected_forfeiture_rate: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_years", Decimal(str(self.service_years)))
        object.__setattr__(self, "expected_forfeiture_rate", Decimal(str(self.expected_forfeiture_rate)))
        object.__setattr__(self, "dividend_yield", Decimal(str(self.dividend_yield)))
        if self.grant_date_fv is not None:
            object.__setattr__(self, "grant_date_fv", money(self.grant_date_fv))
        for name in ("strike", "spot"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, money(value))
        for name in ("expected_term_years", "risk_free_rate", "volatility"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, Decimal(str(value)))


@dataclass(frozen=True)
class PeriodExpense:
    grant_id: str
    unit_fv: Decimal
    expected_to_vest: Decimal
    total_cost: Decimal
    years_elapsed: Decimal
    cumulative_before: Decimal
    period_cost: Decimal
    remaining: Decimal
    forfeited_this_period: int


def unit_fair_value(grant: Grant) -> Decimal:
    if grant.grant_date_fv is not None:
        return grant.grant_date_fv
    if grant.award_type is AwardType.RSU:
        if grant.spot is None:
            raise ValueError(f"{grant.grant_id}: RSU needs grant_date_fv or spot")
        return grant.spot
    if None in (grant.spot, grant.strike, grant.expected_term_years, grant.risk_free_rate, grant.volatility):
        raise ValueError(f"{grant.grant_id}: option needs FV or Black-Scholes inputs")
    return black_scholes_call(
        grant.spot,
        grant.strike,
        grant.expected_term_years,
        grant.risk_free_rate,
        grant.volatility,
        grant.dividend_yield,
    )


def _years_between(start: date, end: date) -> Decimal:
    return (Decimal((end - start).days) / Decimal("365")).quantize(FOUR, rounding=ROUND_HALF_UP)


def period_expense(
    grant: Grant,
    period_start: date,
    period_end: date,
    actual_forfeitures: int = 0,
) -> PeriodExpense:
    if period_end < period_start:
        raise ValueError("period_end before period_start")
    fv = unit_fair_value(grant)
    remaining_shares = max(grant.shares - actual_forfeitures, 0)
    expected_to_vest = money(
        Decimal(remaining_shares) * (Decimal("1") - grant.expected_forfeiture_rate)
    )
    total_cost = money(expected_to_vest * fv)

    elapsed_end = min(_years_between(grant.grant_date, period_end), grant.service_years)
    elapsed_start = min(
        max(_years_between(grant.grant_date, period_start), Decimal("0")),
        grant.service_years,
    )
    if elapsed_start < 0:
        elapsed_start = Decimal("0")
    frac_end = elapsed_end / grant.service_years if grant.service_years else Decimal("1")
    frac_start = elapsed_start / grant.service_years if grant.service_years else Decimal("0")
    cumulative_end = money(total_cost * frac_end)
    cumulative_before = money(total_cost * frac_start)
    cost = money(cumulative_end - cumulative_before)
    remaining = money(total_cost - cumulative_end)
    return PeriodExpense(
        grant_id=grant.grant_id,
        unit_fv=fv,
        expected_to_vest=expected_to_vest,
        total_cost=total_cost,
        years_elapsed=elapsed_end,
        cumulative_before=cumulative_before,
        period_cost=cost,
        remaining=remaining,
        forfeited_this_period=actual_forfeitures,
    )
