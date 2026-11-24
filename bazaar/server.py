"""FastAPI app: the market simulation API and the dashboard."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .agents import CATEGORIES, Agent, default_roster
from .evaluate import sweep
from .scoring import WEIGHTS
from .simulate import run

ROOT = Path(__file__).resolve().parent.parent
PRESETS = [40, 80, 120, 240, 480, 960]


class RunReq(BaseModel):
    seed: int = 1
    n_tasks: int = 240
    weights: list | None = None


def create_app(precompute: bool = True) -> FastAPI:
    state: dict = {"sweep": None, "computing": False}

    def set_run(seed: int, n_tasks: int, weights) -> dict:
        w = tuple(weights) if weights else WEIGHTS
        if abs(sum(w) - 1.0) > 1e-6 or len(w) != 3:
            raise HTTPException(400, "weights must be three numbers that sum to 1.0")
        state["result"] = run(n_tasks=n_tasks, seed=seed, agents=default_roster())
        state["seed"], state["n_tasks"], state["weights"] = seed, n_tasks, w
        return {"seed": seed, "n_tasks": n_tasks}

    set_run(int(os.getenv("BAZAAR_SEED", "1")), 240, None)

    if precompute:
        def work():
            state["computing"] = True
            try:
                state["sweep"] = sweep(40, 240, 100).to_dict()
            finally:
                state["computing"] = False
        threading.Thread(target=work, daemon=True).start()

    app = FastAPI(title="Bazaar", version=__version__, description="A market where agents bid for work, versus a fixed-role crew that never reconsiders a hire.")
    app.state.get = lambda: state

    def R():
        return state["result"]

    @app.get("/api/meta")
    def meta():
        return {"version": __version__, "categories": list(CATEGORIES), "presets": PRESETS, "seed": state["seed"], "n_tasks": state["n_tasks"],
                "weights": list(state["weights"]), "roster": [{"name": a.name, "skill": a.skill, "price_rate": a.price_rate, "speed": a.speed,
                 "honesty": a.honesty, "price_aggression": a.price_aggression, "bids_outside_skill": a.bids_outside_skill} for a in R().roster],
                "sweep_ready": state["sweep"] is not None}

    @app.post("/api/run")
    def run_(req: RunReq):
        if not 10 <= req.n_tasks <= 2000:
            raise HTTPException(400, "n_tasks must be between 10 and 2,000")
        return set_run(req.seed, req.n_tasks, req.weights)

    @app.get("/api/summary")
    def summary():
        r = R()
        return {"seed": r.seed, "n_tasks": r.n_tasks, "bazaar": r.bazaar_metrics.to_dict(), "crew": r.crew_metrics.to_dict(),
                "hires": [{"category": h.category, "agent": h.agent, "score": round(h.score, 3)} for h in r.hires]}

    @app.get("/api/reputation")
    def reputation():
        r = R()
        return {name: {cat: rep.to_dict() for cat, rep in cats.items()} for name, cats in r.reputation.items()}

    @app.get("/api/auctions")
    def auctions(system: str = "bazaar", category: str | None = None, limit: int = 400, offset: int = 0):
        if system not in ("bazaar", "crew"):
            raise HTTPException(400, "system must be 'bazaar' or 'crew'")
        r = R()
        results = r.bazaar_results if system == "bazaar" else r.crew_results
        if category:
            results = [x for x in results if x.task.category == category]
        return {"total": len(results), "items": [x.to_dict() for x in results[offset: offset + min(limit, 500)]]}

    @app.get("/api/sweep")
    def sweep_():
        return {"result": state["sweep"], "computing": state["computing"]}

    @app.post("/api/sweep")
    def sweep_run(n_seeds: int = 40, n_tasks: int = 240, base_seed: int = 100):
        if not 2 <= n_seeds <= 200:
            raise HTTPException(400, "n_seeds must be between 2 and 200")
        if not 10 <= n_tasks <= 2000:
            raise HTTPException(400, "n_tasks must be between 10 and 2,000")
        state["sweep"] = sweep(n_seeds, n_tasks, base_seed).to_dict()
        return state["sweep"]

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    return app
