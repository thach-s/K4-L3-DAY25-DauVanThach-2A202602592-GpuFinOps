"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    # Use actual job days for this separate energy scenario, not the M3 30-day run-rate.
    carbon_jobs = []
    for j in jobs:
        if int(num(j["interruptible"])):
            wh = (num(j["hours_per_day"]) * num(j["days"]) * num(j["num_gpus"])
                  * num(cat[j["gpu_type"]]["watts"]))
            carbon_jobs.append({"job_id": j["job_id"], "wh": wh,
                               "baseline_g": sustainability.carbon_g(wh, "us-east-1"),
                               "clean_g": sustainability.carbon_g(wh, "europe-north1")})
    total_wh = sum(j["wh"] for j in carbon_jobs)
    regions = [{"region": region, "price_kwh": sustainability.REGION_PRICE_KWH[region],
                "carbon_kwh": intensity,
                "electricity_usd": sustainability.energy_cost_usd(total_wh, region),
                "carbon_g": sustainability.carbon_g(total_wh, region)}
               for region, intensity in sustainability.REGION_CARBON.items()]
    carbon_schedule = {"jobs": carbon_jobs, "regions": regions, "total_wh": total_wh}
    if verbose:
        print("Carbon scheduling (actual job duration, rated GPU power):", carbon_schedule)
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_schedule": carbon_schedule}


if __name__ == "__main__":
    run()
