"""The Contract-Net market: broadcast a task, collect bids, award by score, execute, and learn.

One auction is: every agent that wants the task bids -> the auctioneer scores the bids against each bidder's
reputation *in that category* -> the highest score wins -> the task is actually done (``execution.execute``, which
knows nothing about the bid) -> the outcome updates the winner's reputation for next time. Nothing here is told
who is "dishonest"; the loop is the whole mechanism.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .agents import Agent, Bid, CATEGORIES
from .execution import Outcome, execute
from .reputation import Reputation
from .scoring import WEIGHTS, pick_winner, score_bids
from .tasks import Task


@dataclass
class AuctionResult:
    task: Task
    bids: list                     # [] for the fixed-role baseline, which never bids
    scores: dict                   # agent -> score, {} for the baseline
    winner: str | None
    outcome: Outcome | None
    note: str                      # "awarded" | "fixed role" | "no bids"

    def to_dict(self) -> dict:
        return {"task": {"id": self.task.id, "category": self.task.category, "complexity": self.task.complexity, "tick": self.task.tick},
                "bids": [b.__dict__ for b in self.bids], "scores": self.scores, "winner": self.winner,
                "outcome": None if self.outcome is None else self.outcome.__dict__, "note": self.note}


class Bazaar:
    """A market: ``run()`` holds one Contract-Net auction per task and carries reputation forward between them."""

    def __init__(self, agents: list[Agent], categories: tuple = CATEGORIES, weights: tuple = WEIGHTS):
        self.agents = {a.name: a for a in agents}
        self.categories = categories
        self.weights = weights
        self.rep = {a.name: {c: Reputation() for c in categories} for a in agents}

    def trust(self, category: str) -> dict:
        return {name: cats[category].mean for name, cats in self.rep.items()}

    def run_auction(self, task: Task, u: float, bid_rng: random.Random) -> AuctionResult:
        bidders = [a for a in self.agents.values() if a.wants_to_bid(task)]
        if not bidders:
            return AuctionResult(task, [], {}, None, None, "no bids")
        bids = [a.bid(task, bid_rng) for a in bidders]
        scored = score_bids(bids, self.trust(task.category), self.weights)
        winner_bid, _ = pick_winner(scored)
        outcome = execute(self.agents[winner_bid.agent], task, u)
        self.rep[winner_bid.agent][task.category].update(outcome.success)
        return AuctionResult(task, bids, {b.agent: s for b, s in scored}, winner_bid.agent, outcome, "awarded")

    def run(self, tasks: list[Task], outcome_draws: list[float], seed: int) -> list[AuctionResult]:
        bid_rng = random.Random(seed)
        return [self.run_auction(t, u, bid_rng) for t, u in zip(tasks, outcome_draws)]
