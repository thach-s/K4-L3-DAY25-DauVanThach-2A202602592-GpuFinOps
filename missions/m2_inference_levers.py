"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    stages = {"baseline": 0.0, "cascade": 0.0, "cache": 0.0, "batch": 0.0}
    groups = {False: {"requests": 0, "cost": 0.0, "wh": 0.0},
              True: {"requests": 0, "cost": 0.0, "wh": 0.0}}
    reasoning_candidates = []
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        opt_cost += cost
        stages["baseline"] += pricing.request_cost(inp, out, lin, lout)
        stages["cascade"] += pricing.request_cost(inp, out, pin, pout)
        stages["cache"] += pricing.request_cost(inp, out, pin, pout, cached_in=cached)
        stages["batch"] += cost
        reasoning = bool(int(num(r["is_reasoning"])))
        wh = sustainability.wh_per_query(inp + out, is_reasoning=reasoning)
        groups[reasoning]["requests"] += 1
        groups[reasoning]["cost"] += cost
        groups[reasoning]["wh"] += wh
        if reasoning:
            # Generator models reasoning output as six times ordinary output.
            ordinary_out = out // 6
            ordinary_cost = pricing.request_cost(inp, ordinary_out, pin, pout,
                                                  cached_in=cached, batch=is_batch)
            ordinary_wh = sustainability.wh_per_query(inp + ordinary_out)
            reasoning_candidates.append((cost - ordinary_cost, wh - ordinary_wh))

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    # Cap preserves the request count; selects an expected random fraction to reroute.
    # A 10% cap can be a no-op: also measure a stricter 5% scenario.
    cap_scenarios = {}
    for cap in (0.10, 0.05):
        rerouted = max(0, groups[True]["requests"] - int(len(rows) * cap))
        fraction = rerouted / groups[True]["requests"] if groups[True]["requests"] else 0
        cap_scenarios[str(cap)] = {
            "rerouted_requests": rerouted,
            "saved_usd": sum(x[0] for x in reasoning_candidates) * fraction,
            "saved_wh": sum(x[1] for x in reasoning_candidates) * fraction,
        }
    reasoning_budget = {"groups": groups, "caps": cap_scenarios,
                        "traffic_share": groups[True]["requests"] / len(rows),
                        "cost_share": groups[True]["cost"] / opt_cost,
                        "energy_share": groups[True]["wh"] / sum(g["wh"] for g in groups.values())}
    if verbose:
        print("Sequential lever costs ($/day):", stages)
        print("Reasoning budget:", reasoning_budget)
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "stages": stages, "reasoning_budget": reasoning_budget,
    }


if __name__ == "__main__":
    run()
