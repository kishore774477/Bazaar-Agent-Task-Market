"""Bazaar: specialist agents bid for work under the Contract-Net protocol; a reputation system (per agent, per
category) learns who actually delivers, and the market routes around whoever does not — compared against a fixed-
role crew that never reconsiders who was hired.

    from bazaar import run
    r = run(n_tasks=240, seed=1)
    r.bazaar_metrics.success_rate, r.crew_metrics.success_rate
"""
from __future__ import annotations

from .simulate import SimResult, run

__version__ = "0.1.0"
__all__ = ["SimResult", "run", "__version__"]
