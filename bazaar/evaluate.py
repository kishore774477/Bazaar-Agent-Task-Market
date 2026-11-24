"""Aggregate the comparison across many seeds, so a single run is never mistaken for the whole story."""
from __future__ import annotations

import statistics as st
from dataclasses import dataclass

from .agents import default_roster
from .simulate import run


@dataclass
class SweepResult:
    n_seeds: int
    n_tasks: int
    bazaar_success: list
    crew_success: list
    bazaar_cost: list
    crew_cost: list
    flex_hired_data: int
    data_rate_when_hired: list       # [(crew_rate, bazaar_rate), ...] for seeds where the crew hired Flex for "data"
    flex_phase_share: list           # [[phase1, phase2, phase3], ...] in the "data" category, Bazaar only

    def to_dict(self) -> dict:
        wins = sum(1 for b, c in zip(self.bazaar_success, self.crew_success) if b > c)
        diffs = [b - c for b, c in zip(self.bazaar_success, self.crew_success)]
        return {
            "n_seeds": self.n_seeds, "n_tasks": self.n_tasks,
            "bazaar_success": _stats(self.bazaar_success), "crew_success": _stats(self.crew_success),
            "bazaar_cost": _stats(self.bazaar_cost), "crew_cost": _stats(self.crew_cost),
            "bazaar_beats_crew": {"seeds": wins, "of": self.n_seeds, "mean_diff": round(st.mean(diffs), 4) if diffs else None, "min_diff": round(min(diffs), 4) if diffs else None},
            "flex_hired_for_data": {"seeds": self.flex_hired_data, "of": self.n_seeds},
            "data_rate_when_flex_hired": {"crew": _stats([c for c, _ in self.data_rate_when_hired]), "bazaar": _stats([b for _, b in self.data_rate_when_hired]),
                                           "n": len(self.data_rate_when_hired)},
            "flex_win_share_in_data": {"phase1_mean": round(st.mean(p[0] for p in self.flex_phase_share), 4) if self.flex_phase_share else None,
                                        "phase3_mean": round(st.mean(p[-1] for p in self.flex_phase_share), 4) if self.flex_phase_share else None},
        }


def _stats(xs: list) -> dict | None:
    if not xs:
        return None
    return {"mean": round(st.mean(xs), 4), "min": round(min(xs), 4), "max": round(max(xs), 4)}


def sweep(n_seeds: int = 40, n_tasks: int = 240, base_seed: int = 100) -> SweepResult:
    from .metrics import win_share_by_phase
    bz_s, cr_s, bz_c, cr_c, rates, phases = [], [], [], [], [], []
    flex_hired = 0
    for i in range(n_seeds):
        r = run(n_tasks=n_tasks, seed=base_seed + i, agents=default_roster())
        bz_s.append(r.bazaar_metrics.success_rate)
        cr_s.append(r.crew_metrics.success_rate)
        bz_c.append(r.bazaar_metrics.total_cost)
        cr_c.append(r.crew_metrics.total_cost)
        hires = {h.category: h.agent for h in r.hires}
        phases.append(win_share_by_phase(r.bazaar_results, "Flex", "data"))
        if hires.get("data") == "Flex":
            flex_hired += 1
            cd = r.crew_metrics.to_dict()["category_success"].get("data")
            bd = r.bazaar_metrics.to_dict()["category_success"].get("data")
            if cd and bd and cd["total"] and bd["total"]:
                rates.append((cd["rate"], bd["rate"]))
    return SweepResult(n_seeds, n_tasks, bz_s, cr_s, bz_c, cr_c, flex_hired, rates, phases)
