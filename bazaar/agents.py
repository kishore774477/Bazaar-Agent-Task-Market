"""The bidders: specialist, generalist, cautious and dishonest agents with private skill and cost profiles.

Each agent's *real* skill (used when the task is actually executed, in :mod:`bazaar.execution`) is private: the
auctioneer never sees it, only the bid. ``honesty`` is how closely a claimed confidence tracks that real skill
(1.0 = honest; above 1.0 inflates confidence beyond what the skill warrants, especially at low skill — that is what
"overbidding confidence" means here). ``price_aggression`` below 1.0 undercuts the price an honest quote would ask.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

CATEGORIES = ("backend", "frontend", "data", "ml", "infra", "security", "docs", "qa")


@dataclass(frozen=True)
class Bid:
    agent: str
    task_id: int
    price: float
    eta: float
    confidence: float


@dataclass
class Agent:
    name: str
    skill: dict               # category -> true capability in (0, 1]; a missing category means "won't touch it"
    price_rate: float = 10.0  # currency per complexity point, before the skill and aggression adjustments
    speed: float = 1.0        # days per complexity point, before the skill adjustment
    honesty: float = 1.0      # 1.0 = claimed confidence tracks real skill; >1.0 inflates it, most at low skill
    price_aggression: float = 1.0   # <1.0 undercuts; >1.0 charges a premium
    participation_threshold: float = 0.30   # will not bid on a category below this true skill...
    bids_outside_skill: bool = False        # ...unless this is set, which is what makes an agent bid broadly

    def wants_to_bid(self, task) -> bool:
        s = self.skill.get(task.category, 0.0)
        return s > 0 and (self.bids_outside_skill or s >= self.participation_threshold)

    def bid(self, task, rng: random.Random) -> Bid:
        s = self.skill.get(task.category, 0.05)
        price = max(1.0, self.price_rate * task.complexity * (1.15 - 0.30 * s) * self.price_aggression * (1 + rng.gauss(0, 0.05)))
        eta = max(0.5, self.speed * task.complexity * (1.30 - 0.40 * s) * (1 + rng.gauss(0, 0.06)))
        raw = 0.15 + 0.80 * s                                           # what an honest agent with this skill would claim
        if self.honesty <= 1.0:
            claimed = raw * self.honesty                                # a cautious agent (honesty < 1) underclaims uniformly
        else:
            claimed = raw + (self.honesty - 1.0) * (1.0 - s) * 0.9       # an overclaiming agent inflates most exactly where skill is low
        confidence = _clip(claimed + rng.gauss(0, 0.03), 0.05, 0.98)
        return Bid(self.name, task.id, round(price, 2), round(eta, 2), round(confidence, 3))


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def default_roster() -> list[Agent]:
    """Ten agents, fixed and named so the story is reproducible: five specialists, two generalists, one cautious
    agent, and two rivals for the ``data`` category — one genuinely skilled, one that overclaims. Nobody here is
    malicious; "dishonest" means its *claimed* confidence does not track its *real* skill."""
    return [
        Agent("Atlas", {"backend": 0.90, "infra": 0.55, "docs": 0.30}, price_rate=11, speed=0.9),
        Agent("Lumen", {"frontend": 0.88, "docs": 0.45, "qa": 0.35}, price_rate=10, speed=0.95),
        Agent("Quark", {"ml": 0.92, "data": 0.60, "backend": 0.25}, price_rate=16, speed=1.1),
        Agent("Vault", {"security": 0.90, "infra": 0.50, "backend": 0.30}, price_rate=15, speed=1.0),
        Agent("Nimbus", {"infra": 0.88, "backend": 0.50, "security": 0.35}, price_rate=12, speed=0.85),
        Agent("Pivot", {c: 0.58 for c in CATEGORIES}, price_rate=9, speed=0.8),
        Agent("Sable", {c: 0.50 for c in CATEGORIES}, price_rate=7, speed=1.2),
        Agent("Haze", {"qa": 0.85, "docs": 0.60, "security": 0.40}, price_rate=10, speed=1.0, honesty=0.85),      # cautious: underclaims a little, not dishonest
        Agent("Bolt", {"data": 0.87, "ml": 0.45, "backend": 0.25}, price_rate=14, speed=1.0),                      # the genuine data specialist
        Agent("Flex", {"data": 0.35, "ml": 0.30, "backend": 0.25}, price_rate=14, speed=1.0,
              honesty=2.1, price_aggression=0.72, participation_threshold=0.0, bids_outside_skill=True),           # the overclaiming rival
    ]
