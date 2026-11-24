"""Run the market and the fixed-role baseline on the same task stream and print the gap.

    python examples/compare_market_vs_crew.py                 # one seed
    python examples/compare_market_vs_crew.py --sweep 30       # the distribution over 30 seeds
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bazaar import run              # noqa: E402
from bazaar.evaluate import sweep   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--tasks", type=int, default=240)
ap.add_argument("--sweep", type=int, default=0, help="run this many seeds instead of one")
a = ap.parse_args()

if a.sweep:
    s = sweep(a.sweep, a.tasks).to_dict()
    print(f"{a.sweep} seeds x {a.tasks} tasks")
    print(f"bazaar success: {s['bazaar_success']['mean']:.1%} mean   crew success: {s['crew_success']['mean']:.1%} mean")
    print(f"bazaar beats crew in {s['bazaar_beats_crew']['seeds']}/{s['bazaar_beats_crew']['of']} seeds")
else:
    r = run(n_tasks=a.tasks, seed=a.seed)
    print(f"seed {a.seed}, {a.tasks} tasks")
    print(f"bazaar: {r.bazaar_metrics.success_rate:.1%} success, ${r.bazaar_metrics.total_cost:,.0f} spent")
    print(f"crew:   {r.crew_metrics.success_rate:.1%} success, ${r.crew_metrics.total_cost:,.0f} spent")
    print("\nthe crew's one-time hires:")
    for h in r.hires:
        print(f"  {h.category:<10} {h.agent}")
    print("\nreputation at the end of the run (agents with a track record):")
    for name, cats in r.reputation.items():
        for cat, rep in cats.items():
            if rep.observations:
                print(f"  {name:<10} {cat:<10} {rep.mean:.1%} over {rep.observations} tasks")
