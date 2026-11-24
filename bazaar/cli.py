"""Command line: python -m bazaar <command>"""
from __future__ import annotations

import argparse
import sys

from .evaluate import sweep
from .simulate import run


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="bazaar", description="A market where agents bid for work, versus a fixed-role crew")
    ap.add_argument("--tasks", type=int, default=240)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="run one seed and print the comparison")
    p.add_argument("--seed", type=int, default=1)
    p = sub.add_parser("sweep", help="run many seeds and report the distribution")
    p.add_argument("--seeds", type=int, default=40)
    p.add_argument("--base-seed", type=int, default=100)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        r = run(n_tasks=a.tasks, seed=a.seed)
        bm, cm = r.bazaar_metrics, r.crew_metrics
        print(f"{a.tasks} tasks, seed {a.seed}\n")
        print(f"{'':<10}{'success':>10}{'cost':>12}")
        print(f"{'bazaar':<10}{bm.success_rate:>10.1%}{bm.total_cost:>12,.0f}")
        print(f"{'crew':<10}{cm.success_rate:>10.1%}{cm.total_cost:>12,.0f}\n")
        print("the crew hired, once, for each category:")
        for h in r.hires:
            print(f"  {h.category:<10} {h.agent}")
        print(f"\nbazaar win counts: {dict(sorted(bm.win_count.items(), key=lambda kv: -kv[1]))}")
    elif a.cmd == "sweep":
        s = sweep(a.seeds, a.tasks, a.base_seed).to_dict()
        print(f"{s['n_seeds']} seeds x {s['n_tasks']} tasks\n")
        print(f"bazaar success: mean {s['bazaar_success']['mean']:.1%} (min {s['bazaar_success']['min']:.1%}, max {s['bazaar_success']['max']:.1%})")
        print(f"crew success:   mean {s['crew_success']['mean']:.1%} (min {s['crew_success']['min']:.1%}, max {s['crew_success']['max']:.1%})")
        print(f"bazaar beats crew in {s['bazaar_beats_crew']['seeds']}/{s['bazaar_beats_crew']['of']} seeds, by {s['bazaar_beats_crew']['mean_diff']:.1%} on average")
        print(f"bazaar cost: mean {s['bazaar_cost']['mean']:,.0f}   crew cost: mean {s['crew_cost']['mean']:,.0f}")
        fh = s["flex_hired_for_data"]
        print(f"\nFlex was hired for 'data' by the fixed crew in {fh['seeds']}/{fh['of']} seeds; when it was:")
        d = s["data_rate_when_flex_hired"]
        if d["crew"]:
            print(f"  crew success on 'data' tasks:   {d['crew']['mean']:.1%}")
            print(f"  bazaar success on 'data' tasks: {d['bazaar']['mean']:.1%}")
        f = s["flex_win_share_in_data"]
        print(f"\nFlex's share of 'data' auctions in Bazaar: {f['phase1_mean']:.1%} early -> {f['phase3_mean']:.1%} late")


if __name__ == "__main__":
    main()
