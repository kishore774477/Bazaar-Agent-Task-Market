# Bazaar: a market where agents bid for work, so reputation can route around a bad one

Most multi-agent tooling (CrewAI, AutoGen) assigns a fixed role to a fixed agent: you decide once, by hand, who does
"backend work" or "the data pipeline", and that is who does it from then on, however it performs. **Bazaar allocates
work by a market instead.** Every task is a Contract-Net auction — agents bid a price, an ETA and a claimed
confidence; the highest-scoring bid wins, discounted by that agent's track record in that exact category. Nobody
has to notice that an agent keeps missing; the next auction's score already knows.

```
 task (category, complexity)
        │  broadcast to every agent whose real skill clears its own bar (or who bids broadly anyway)
        ▼
 bid    price · eta · claimed confidence  — confidence tracks real skill for an honest agent, inflates it for one that isn't
        ▼
 score  price & eta scored against the field in *this* auction; confidence x reputation(agent, category)   ->   highest wins
        ▼
 work   done by the *real* skill, never the bid — a success or a failure updates the winner's Beta-distributed reputation
        ▼
 next auction: the same bid now scores differently
```

## What makes it different

| Idea | What it does | Fixed-role crews (CrewAI / AutoGen-style) |
|---|---|---|
| **Allocation is a market, not a hire** | Every task is its own auction; nothing is decided once and left alone. | One role, one agent, decided up front. |
| **Reputation is earned, not claimed** | A Beta distribution per agent *per category*, built only from outcomes. What an agent says about itself never touches the number. | No feedback loop at all once assigned. |
| **The claim and the real skill are different things** | Bids come from a claimed confidence; execution runs on a private, separate real skill. An agent that overclaims wins early (nobody has a track record yet) and then loses as it fails more than it promised. | A convincing pitch at hiring time is the only signal there ever is. |
| **Scored, not asserted** | A fixed-role baseline runs the identical task stream and the identical outcome draws, so the comparison is apples to apples, and the result is a measured number across many seeds, not a demo run once. | — |
| **Every auction is inspectable** | The dashboard's auction log shows every bid, every score, and the real (hidden) success probability behind the outcome. | A role, not a decision. |

## See it work (no API key needed — it is a self-contained simulation)

Ten named agents, eight categories, one designed rivalry: **Bolt** is a genuine data specialist (skill 0.87); **Flex** claims
roughly the same confidence in "data" while its real skill there is 0.35, because its `honesty` factor inflates confidence
most exactly where its skill is weakest, and it bids outside its skill at all. Run it (`python -m bazaar run`) and the
demo plays out: Flex wins some of the earliest "data" auctions on price and claimed confidence — nobody has a track
record yet — then fails more than it promised, and Bolt takes over.

**On 60 held-out seeds (not the ones used to pick the scoring weights), 240 tasks each:**

| | Bazaar (market) | Fixed-role crew |
|---|---:|---:|
| Success rate | **73.4%** (62.5–80.4%) | 55.7% (36.7–74.2%) |
| Total cost | $13,627 | $12,827 |

* **Bazaar beats the fixed crew in 59 of 60 seeds**, by 17.7 points of success rate on average; the one loss was by 7 points.
* **The fixed crew's one-time "interview" hires Flex for the `data` role in 52 of 60 seeds** (it looks great on paper when nobody
  has a track record to check it against). In those 52 seeds, the crew's `data` tasks succeed **14.4%** of the time against
  Bazaar's **73.6%** on the identical tasks.
* **In the market, Flex's share of the `data` auctions it enters falls from 18.7% in the first third of a run to 1.9% in the
  last third** — the mechanism visibly routing around it as reputation catches up.
* **The market is not free.** It costs about 6% more on average ($13,627 vs $12,827) — paying a specialist's higher
  price is itself part of what makes the market right more often. Report both numbers, not just the win.

### What those numbers do and do not say

* **This is a designed scenario**, like the earlier projects' synthetic benchmarks: ten agents and the Bolt/Flex rivalry were
  hand-built so the mechanism's point is visible in under 240 tasks. It demonstrates that the mechanism *can* route around
  overclaiming given a rival with a genuine track record to route *to* — it is not a claim about how often real contractor
  or agent marketplaces look like this.
* **The weights (price 15% / ETA 10% / confidence×reputation 75%) were chosen, by looking at one auction's numbers, so that
  an untested claim can win early and a bad track record can lose later** — a different weighting could blunt the effect or
  sharpen it. `python -m bazaar run` with different `--weights` via the dashboard's Market tab shows this directly: push the
  price weight up enough and the market stops caring who delivers.
* **Reputation is per category**, not global — an agent who fails at `data` is judged only on that history the next time
  `data` comes up, exactly as badly or as well as it has actually done there.
* **One seed in 60 had the market losing to the crew**, by 7 points. "Routes around dishonesty" is a strong tendency here,
  not a guarantee — report the distribution, not the best run.

## Run it

```powershell
start.bat                        # creates .venv, installs, opens http://127.0.0.1:8160
# or
python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt ; .venv\Scripts\python run.py
```

Dashboard tabs: **Market** (re-run with a new seed, task count or scoring weights; who won the work; rolling success rate vs the fixed crew; success by category), **Agents** (skill, price, flagged overclaiming/cautious agents, reputation by category),
**Auction log** (every bid in every auction, the score, the real hidden success probability behind each outcome), **Market vs fixed crew** (one run's head-to-head, plus a live sweep across many seeds), **How it works**.

```powershell
python -m bazaar run --seed 1                      # one seed, bazaar vs the fixed crew, and the one-time hires
python -m bazaar sweep --seeds 40                   # the distribution across 40 seeds
python examples\compare_market_vs_crew.py           # the library in 30 lines
python examples\compare_market_vs_crew.py --sweep 30
```

```python
from bazaar import run
r = run(n_tasks=240, seed=1)
r.bazaar_metrics.success_rate, r.crew_metrics.success_rate
r.hires                              # [Hire(category, agent, score), ...] — the fixed crew's one-time hires
r.reputation["Flex"]["data"].mean    # the auctioneer's learned trust, never the agent's own claim
```

| HTTP | |
|---|---|
| `GET /api/meta` `/api/summary` `/api/reputation` | the roster and config; the current run's metrics and hires; end-of-run reputation per agent per category |
| `GET /api/auctions` | `?system=bazaar\|crew&category=&limit=&offset=` → every auction, its bids and its outcome |
| `POST /api/run` | `{seed, n_tasks, weights}` → re-run with new parameters |
| `GET /api/sweep` · `POST /api/sweep` | the cached sweep (computed in the background on startup); force a fresh one with `?n_seeds=&n_tasks=` |

Configure with `BAZAAR_PORT`, `BAZAAR_SEED` (see `.env.example`). There is nothing here an LLM would read or write — bids
are numbers, not prose — so unlike the earlier projects in this series there is no optional real-model integration.

## Tests

```powershell
.venv\Scripts\python -m pytest -q        # 34 tests, ~1 s, no network, no API key
```

They check: an agent never bids outside its skill unless explicitly flagged to; price falls with skill and rises with complexity; an overclaiming agent's confidence inflates more at low skill than at high skill; the Beta-reputation prior, update and shrinking variance; scoring rewards cheap/fast/confident/trusted bids and breaks ties on price; a market run is deterministic given a seed and updates reputation; the fixed crew never reconsiders a hire and is fed the identical task stream and outcome draws as the market it is compared against (checked by replaying the same draw through both); metrics arithmetic (success rate, rolling window, win share by phase); the headline sweep on 15 held-out seeds; the API and CLI.

## Limitations

* Ten agents and eight categories are hand-designed, not learned or sampled from real data, so this is a mechanism demo, not a market-design study.
* Reputation only ever discounts a bid's score; it never excludes an agent outright, however bad its record — an agent with a terrible reputation can still win if it is cheap and fast enough, which is a modelling choice, not a law of the mechanism.
* Execution is a one-shot success/failure per task; there is no partial credit, no rework, and ETA is not checked against how long the task actually took.
* The "cost" figure is the winning bid's price, not what the work was actually worth — a cheap failure still costs its price and delivers nothing.
