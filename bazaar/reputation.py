"""Reputation as a Beta distribution per agent per category: it is what the *auctioneer* learns from outcomes,
never from what an agent claims about itself.

A weak prior (``alpha0 = beta0 = 2``, equivalent to two pseudo-observations split evenly) starts everyone at a
neutral 0.5 rather than 0 or 1 on day one, and lets a track record of a handful of tasks move the mean a long way.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0


@dataclass
class Reputation:
    alpha: float = PRIOR_ALPHA
    beta: float = PRIOR_BETA
    history: list = field(default_factory=list)      # bool outcomes, oldest first — for the calibration view only

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def observations(self) -> int:
        return len(self.history)

    def update(self, success: bool) -> "Reputation":
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0
        self.history.append(bool(success))
        return self

    def to_dict(self) -> dict:
        return {"mean": round(self.mean, 4), "variance": round(self.variance, 5), "observations": self.observations, "alpha": self.alpha, "beta": self.beta}
