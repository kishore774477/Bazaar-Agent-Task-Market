"""What actually happens once an agent is handed a task: a function of its *real* skill, never of its bid.

Complexity hurts an unskilled agent more than a skilled one (an expert's skill barely dents on hard tasks; a
novice's success chance falls off faster), which is what makes a claim like Flex's ("I can do this") cash out as
more failures than a genuinely skilled rival's, once the task is hard enough.
"""
from __future__ import annotations

from dataclasses import dataclass

from .tasks import Task

MAX_COMPLEXITY = 10.0
COMPLEXITY_PENALTY = 0.65


def success_probability(skill: float, complexity: float) -> float:
    c = complexity / MAX_COMPLEXITY
    p = skill - c * (1.0 - skill) * COMPLEXITY_PENALTY
    return max(0.04, min(0.97, p))


@dataclass(frozen=True)
class Outcome:
    task_id: int
    agent: str
    success: bool
    true_probability: float      # never shown to the agent or the auctioneer; for the calibration view only


def execute(agent, task: Task, u: float) -> Outcome:
    """``u`` is the one random draw for this task, shared by whichever agent ends up doing it (see tasks.py)."""
    p = success_probability(agent.skill.get(task.category, 0.05), task.complexity)
    return Outcome(task.id, agent.name, u < p, round(p, 4))
