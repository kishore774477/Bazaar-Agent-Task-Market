"""One call that builds the roster, generates the task stream, and runs both the market and the fixed-role baseline
against it, so a seed is reproducible end to end."""
from __future__ import annotations

from dataclasses import dataclass

from .agents import CATEGORIES, Agent, default_roster
from .baseline import FixedCrew, Hire
from .market import AuctionResult, Bazaar
from .metrics import RunMetrics, summarize
from .tasks import Task, generate_outcome_draws, generate_tasks


@dataclass
class SimResult:
    seed: int
    n_tasks: int
    tasks: list
    bazaar_results: list
    crew_results: list
    bazaar_metrics: RunMetrics
    crew_metrics: RunMetrics
    hires: list
    reputation: dict            # agent -> category -> Reputation (end of run)
    roster: list


def run(n_tasks: int = 240, seed: int = 1, agents: list[Agent] | None = None, categories: tuple = CATEGORIES, window: int = 20) -> SimResult:
    agents = agents if agents is not None else default_roster()
    tasks = generate_tasks(n_tasks, seed, categories)
    draws = generate_outcome_draws(n_tasks, seed + 1)
    bz = Bazaar([a for a in agents], categories)
    bz_results = bz.run(tasks, draws, seed + 2)
    crew = FixedCrew([a for a in agents], categories, seed=seed)
    crew_results = crew.run(tasks, draws, price_seed=seed + 3)
    return SimResult(seed, n_tasks, tasks, bz_results, crew_results, summarize(bz_results, window), summarize(crew_results, window),
                      crew.hires, bz.rep, agents)
