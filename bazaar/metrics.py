"""Turning a run (a list of ``AuctionResult``) into numbers: success rate, cost, who won, and a rolling view for charts."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


def _cost(r) -> float:
    if not r.bids:
        return 0.0
    b = next((x for x in r.bids if x.agent == r.winner), r.bids[0])
    return b.price


@dataclass
class RunMetrics:
    n_tasks: int
    n_awarded: int
    n_success: int
    total_cost: float
    win_count: dict            # agent -> int
    bid_count: dict            # agent -> int ([] / unused for the baseline)
    success_count: dict        # agent -> int
    category_success: dict     # category -> (success, total)
    rolling: list               # [{"tick", "success_rate", "window"}]

    @property
    def success_rate(self) -> float:
        return self.n_success / self.n_awarded if self.n_awarded else 0.0

    def win_share(self, agent: str, tasks=None) -> float:
        denom = self.n_awarded if tasks is None else tasks
        return self.win_count.get(agent, 0) / denom if denom else 0.0

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["success_rate"] = round(self.success_rate, 4)
        d["category_success"] = {k: {"success": s, "total": t, "rate": round(s / t, 4) if t else None} for k, (s, t) in self.category_success.items()}
        return d


def rolling_success(results: list, window: int = 20) -> list:
    out, buf = [], []
    for r in results:
        if r.outcome is not None:
            buf.append(r.outcome.success)
        if len(buf) > window:
            buf.pop(0)
        if r.outcome is not None:
            out.append({"tick": r.task.tick, "success_rate": round(sum(buf) / len(buf), 4), "window": len(buf)})
    return out


def summarize(results: list, window: int = 20) -> RunMetrics:
    win_count, bid_count, success_count = Counter(), Counter(), Counter()
    cat_success = defaultdict(lambda: [0, 0])
    n_success = total_cost = 0
    n_awarded = 0
    for r in results:
        for b in r.bids:
            bid_count[b.agent] += 1
        if r.winner is None:
            continue
        n_awarded += 1
        win_count[r.winner] += 1
        total_cost += _cost(r)
        cat_success[r.task.category][1] += 1
        if r.outcome and r.outcome.success:
            n_success += 1
            success_count[r.winner] += 1
            cat_success[r.task.category][0] += 1
    return RunMetrics(len(results), n_awarded, n_success, round(total_cost, 2), dict(win_count), dict(bid_count), dict(success_count),
                       {k: tuple(v) for k, v in cat_success.items()}, rolling_success(results, window))


def win_share_by_phase(results: list, agent: str, category: str | None = None, phases: int = 3) -> list:
    """``agent``'s share of the awarded tasks (optionally restricted to one category), split into ``phases`` equal chunks in time."""
    rel = [r for r in results if r.winner is not None and (category is None or r.task.category == category)]
    if not rel:
        return [0.0] * phases
    chunk = max(1, len(rel) // phases)
    out = []
    for i in range(phases):
        part = rel[i * chunk: (i + 1) * chunk] if i < phases - 1 else rel[i * chunk:]
        out.append(sum(1 for r in part if r.winner == agent) / len(part) if part else 0.0)
    return out
