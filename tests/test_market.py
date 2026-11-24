import pytest

from bazaar.agents import Agent
from bazaar.baseline import FixedCrew, interview
from bazaar.evaluate import sweep
from bazaar.market import Bazaar
from bazaar.metrics import summarize, win_share_by_phase
from bazaar.tasks import generate_outcome_draws, generate_tasks


CATS = ("x", "y")


def _roster():
    return [Agent("Skilled", {"x": 0.9, "y": 0.5}, price_rate=12),
            Agent("Weak", {"x": 0.3, "y": 0.5}, price_rate=10, honesty=2.0, price_aggression=0.7, bids_outside_skill=True),
            Agent("Generalist", {"x": 0.5, "y": 0.5}, price_rate=8)]


# ---------------------------------------------------------------------------- Bazaar market
def test_a_market_run_awards_every_task_with_bidders_and_updates_reputation():
    bz = Bazaar(_roster(), CATS)
    tasks = generate_tasks(60, seed=1, categories=CATS)
    draws = generate_outcome_draws(60, seed=2)
    results = bz.run(tasks, draws, seed=3)
    assert len(results) == 60
    assert all(r.winner is not None for r in results)                 # everyone bids on x and y here, so nothing goes unawarded
    assert all(r.outcome is not None and r.outcome.task_id == r.task.id for r in results)
    assert any(cats["x"].observations > 0 for cats in bz.rep.values())


def test_no_bidders_is_reported_not_crashed():
    narrow = [Agent("Only", {"x": 0.8}, participation_threshold=0.9)]            # will not clear its own bar
    bz = Bazaar(narrow, CATS)
    tasks = generate_tasks(10, seed=1, categories=CATS)
    draws = generate_outcome_draws(10, seed=2)
    results = bz.run(tasks, draws, seed=3)
    assert all(r.winner is None and r.note == "no bids" for r in results)


def test_market_run_is_deterministic_given_a_seed():
    tasks = generate_tasks(40, seed=5, categories=CATS)
    draws = generate_outcome_draws(40, seed=6)
    a = Bazaar(_roster(), CATS).run(tasks, draws, seed=9)
    b = Bazaar(_roster(), CATS).run(tasks, draws, seed=9)
    assert [r.winner for r in a] == [r.winner for r in b]
    assert [r.outcome.success for r in a] == [r.outcome.success for r in b]


def test_reputation_discount_eventually_shifts_the_winner():
    """Weak overclaims and can win early (nobody has a track record); as it fails, the skilled rival should take over."""
    bz = Bazaar(_roster(), CATS)
    tasks = generate_tasks(300, seed=1, categories=("x",) * 300)
    draws = generate_outcome_draws(300, seed=2)
    results = bz.run(tasks, draws, seed=4)
    early = [r.winner for r in results[:40]]
    late = [r.winner for r in results[-40:]]
    assert early.count("Weak") > late.count("Weak")
    assert late.count("Skilled") >= early.count("Skilled")


# ---------------------------------------------------------------------------- fixed-role crew
def test_interview_hires_exactly_one_agent_per_category():
    hires = interview(_roster(), CATS, seed=0)
    assert {h.category for h in hires} == set(CATS)
    assert len({h.category for h in hires}) == len(hires)


def test_fixed_crew_never_changes_its_mind():
    crew = FixedCrew(_roster(), CATS, seed=0)
    tasks = generate_tasks(100, seed=1, categories=("x",) * 100)
    draws = generate_outcome_draws(100, seed=2)
    results = crew.run(tasks, draws)
    winners = {r.winner for r in results}
    assert len(winners) == 1                                       # one agent does every "x" task, success or failure
    assert all(r.note == "fixed role" for r in results)
    assert all(len(r.bids) == 1 for r in results)                   # a price/eta quote for cost tracking, not a competition


def test_fixed_crew_and_bazaar_see_identical_tasks_and_outcome_draws():
    tasks = generate_tasks(50, seed=7, categories=CATS)
    draws = generate_outcome_draws(50, seed=8)
    crew = FixedCrew(_roster(), CATS, seed=0)
    bz = Bazaar(_roster(), CATS)
    cr = crew.run(tasks, draws)
    bzr = bz.run(tasks, draws, seed=1)
    assert [r.task for r in cr] == [r.task for r in bzr]            # the common task stream
    name = crew.assignment["x"]
    for r_crew, r_bz, t, u in zip(cr, bzr, tasks, draws):
        if t.category == "x" and r_bz.winner == name:
            assert r_crew.outcome.success == r_bz.outcome.success    # same agent, same draw -> same outcome


def test_unassigned_category_is_reported():
    crew = FixedCrew(_roster(), CATS, seed=0)
    crew.assignment.pop("y")
    tasks = generate_tasks(5, seed=1, categories=("y",) * 5)
    results = crew.run(tasks, generate_outcome_draws(5, seed=2))
    assert all(r.winner is None and r.note == "no role for this category" for r in results)


# ---------------------------------------------------------------------------- metrics
def test_summarize_counts_match_the_run():
    bz = Bazaar(_roster(), CATS)
    tasks = generate_tasks(80, seed=1, categories=CATS)
    results = bz.run(tasks, generate_outcome_draws(80, seed=2), seed=3)
    m = summarize(results)
    assert m.n_tasks == 80 and m.n_awarded == sum(1 for r in results if r.winner)
    assert sum(m.win_count.values()) == m.n_awarded
    assert m.n_success == sum(1 for r in results if r.outcome and r.outcome.success)
    assert m.success_rate == pytest.approx(m.n_success / m.n_awarded)
    assert sum(t for _, t in m.category_success.values()) == m.n_awarded
    d = m.to_dict()
    assert d["success_rate"] == round(m.success_rate, 4)


def test_rolling_window_never_exceeds_its_size_and_covers_every_awarded_task():
    bz = Bazaar(_roster(), CATS)
    tasks = generate_tasks(60, seed=1, categories=CATS)
    results = bz.run(tasks, generate_outcome_draws(60, seed=2), seed=3)
    m = summarize(results, window=10)
    assert all(p["window"] <= 10 for p in m.rolling)
    assert len(m.rolling) == sum(1 for r in results if r.outcome is not None)


def test_win_share_by_phase_sums_sensibly():
    bz = Bazaar(_roster(), CATS)
    tasks = generate_tasks(90, seed=1, categories=("x",) * 90)
    results = bz.run(tasks, generate_outcome_draws(90, seed=2), seed=3)
    shares = win_share_by_phase(results, "Skilled", "x", phases=3)
    assert len(shares) == 3 and all(0.0 <= s <= 1.0 for s in shares)
    assert win_share_by_phase([], "Skilled") == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------- the headline, checked rather than asserted in prose
def test_sweep_shape_and_headline_on_a_small_sample():
    s = sweep(n_seeds=6, n_tasks=120, base_seed=500)
    d = s.to_dict()
    assert d["n_seeds"] == 6 and len(s.bazaar_success) == 6
    assert 0.0 <= d["bazaar_success"]["mean"] <= 1.0
    assert d["bazaar_beats_crew"]["seeds"] <= d["bazaar_beats_crew"]["of"] == 6


def test_full_roster_sweep_shows_the_market_beating_the_fixed_crew_most_of_the_time():
    """The default-roster headline, on held-out seeds distinct from the ones used to tune the scoring weights."""
    s = sweep(n_seeds=15, n_tasks=240, base_seed=9000).to_dict()
    assert s["bazaar_beats_crew"]["seeds"] >= 12                    # at least 80% of seeds
    assert s["bazaar_success"]["mean"] > s["crew_success"]["mean"] + 0.1
    fh = s["flex_hired_for_data"]
    if fh["seeds"] >= 3:
        assert s["data_rate_when_flex_hired"]["bazaar"]["mean"] > s["data_rate_when_flex_hired"]["crew"]["mean"]
