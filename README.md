# sbc-ledger

> **Cubiczan stack** — [CHP](https://github.com/Cubiczan/consensus-hardening-protocol) · [control-spine](https://github.com/Cubiczan/control-spine) · **You are here:** `sbc-ledger`

**ASC 718 share-based compensation.** Grant register, Black-Scholes when grant-date FV is not supplied, straight-line service-period expense, forfeiture estimate and actual-forfeiture true-up, evidence pack. Built for any listed company whose share-based payment control cannot be reperformed from the equity ledger.

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

## MCP server

`src/sbc_ledger/mcp_server.py` publishes the engine over Model Context Protocol: a thin wrapper in the `io.github.icohangar-ops/sbc-ledger` namespace (stdio transport) whose tools — `measure_grant_expense`, `grant_unit_fair_value`, and `sbc_evidence_pack` — call `sbc_ledger.engine` and `sbc_ledger.evidence` verbatim. All measurement logic lives in the engine module; the wrapper adds no logic, touches no network, and never estimates volatility, rates, or expected term — those stay owner inputs. Evidence packs built through MCP are always unsigned — the tool takes no owner, so the spine renders `EXPLORING` and `is_evidence: false`; a named human signs via the CLI (`--owner`), never through MCP. MCP access is opt-in, keeping the deterministic core zero-dependency: the engine and CLI install with no runtime dependencies, and the MCP server ships behind the `mcp` extra (`pip install 'sbc-ledger[mcp]'`) — chosen over a hard dependency after prelint review, since a default install must stay dependency-free. CI installs `.[dev,mcp]` so the MCP tests still run.

```bash
uvx --from 'sbc-ledger[mcp]' sbc-ledger-mcp
# or from a checkout:
uv run --with 'mcp>=1.2,<2' --with . python -m sbc_ledger.mcp_server
```
