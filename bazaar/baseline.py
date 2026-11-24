"""The comparison: a fixed-role crew (how CrewAI- or AutoGen-style tooling is usually set up).

Once, at "onboarding", every agent bids on a representative task for each category with nobody's reputation known
yet (trust 0.5 across the board) — hiring on the strength of the pitch, which is all there is to go on. The winner
of that one interview keeps every task in that category forever after: there is no feedback loop, so nothing here
ever reconsiders the hire, however it performs. It is given the identical task stream and outcome draws as the
Bazaar run it is compared against.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .agents import Agent, CATEGORIES
from .execution import execute
from .market import AuctionResult
from .scoring import WEIGHTS, pick_winner, score_bids
from .tasks import Task


@dataclass
class Hire:
    category: str
    agent: str
    score: float


def interview(agents: list[Agent], categories: tuple, weights: tuple = WEIGHTS, complexity: float = 5.0, seed: int = 0) -> list[Hire]:
    rng = random.Random(seed)
    by_name = {a.name: a for a in agents}
    hires = []
    for cat in categories:
        role_task = Task(id=-1, category=cat, complexity=complexity, tick=-1)
        bidders = [a for a in agents if a.wants_to_bid(role_task)] or list(agents)
        bids = [a.bid(role_task, rng) for a in bidders]
        scored = score_bids(bids, {b.agent: 0.5 for b in bids}, weights)     # nobody has a track record on day one
        winner_bid, score = pick_winner(scored)
        hires.append(Hire(cat, winner_bid.agent, score))
    return hires


class FixedCrew:
    def __init__(self, agents: list[Agent], categories: tuple = CATEGORIES, weights: tuple = WEIGHTS, seed: int = 0):
        self.agents = {a.name: a for a in agents}
        self.categories = categories
        self.hires = interview(agents, categories, weights, seed=seed)
        self.assignment = {h.category: h.agent for h in self.hires}

    def run(self, tasks: list[Task], outcome_draws: list[float], price_seed: int = 1) -> list[AuctionResult]:
        price_rng = random.Random(price_seed)
        out = []
        for t, u in zip(tasks, outcome_draws):
            name = self.assignment.get(t.category)
            if name is None:
                out.append(AuctionResult(t, [], {}, None, None, "no role for this category"))
                continue
            agent = self.agents[name]
            quote = agent.bid(t, price_rng)                     # a price/eta quote, for cost bookkeeping only — it plays no part in who does the work
            outcome = execute(agent, t, u)
            out.append(AuctionResult(t, [quote], {name: 1.0}, name, outcome, "fixed role"))
        return out
