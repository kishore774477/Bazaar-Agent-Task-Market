"""The task stream: what the market and the fixed-role baseline are both fed.

Both systems see the *same* tasks and the *same* execution-outcome draws (one uniform random number per task,
``generate_outcome_draws``), so a lucky or unlucky task lands the same way for whichever agent ends up doing it —
the usual "common random numbers" trick for a fair comparison, not independent randomness per system.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .agents import CATEGORIES


@dataclass(frozen=True)
class Task:
    id: int
    category: str
    complexity: float    # 1..10
    tick: int


def generate_tasks(n: int, seed: int, categories: tuple = CATEGORIES, weights: list | None = None) -> list[Task]:
    rng = random.Random(seed)
    return [Task(i, rng.choices(categories, weights=weights)[0], round(rng.uniform(1.0, 10.0), 2), i) for i in range(n)]


def generate_outcome_draws(n: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]
