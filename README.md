# sbc-ledger

> **Cubiczan stack** — [CHP](https://github.com/Cubiczan/consensus-hardening-protocol) · [control-spine](https://github.com/Cubiczan/control-spine) · **You are here:** `sbc-ledger`

**ASC 718 share-based compensation.** Grant register, Black-Scholes when grant-date FV is not supplied, straight-line service-period expense, forfeiture estimate and actual-forfeiture true-up, evidence pack. Koil Energy's origin weakness was share-based payments. There was no repo. Now there is.

The engine does not choose volatility, the risk-free rate, or expected term. Those stay with the control owner. The number is recomputable.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What it produces

| Artefact | What a tester samples |
|---|---|
| Grant register | Award type, shares, grant-date FV, service period, forfeiture assumption |
| Period cost | Straight-line over service years on expected-to-vest shares |
| Remaining unrecognized cost | Total cost minus cumulative to period-end |
| Option FV | Black-Scholes call pinned in tests (ATM, 4-year, 40% vol, 5% rate = **3.82**) |

## Quick start

```bash
pip install -e ".[dev]"
pytest -q
sbc-ledger examples/grants.json \
  --period-start 2026-01-01 --period-end 2026-12-31 \
  --period-label "FY2026" --owner "Controller"
```

Not a substitute for a signed valuation memo on a novel award (market conditions, modifications, liability-classified plans). Those still need a person.

## Compliance spine

Vendored `control-spine`. Volatility, term, and the risk-free rate are committed as foundation assumptions, not estimated here. Unsigned packs stay `EXPLORING`. Only a named owner reaches `LOCKED`.
