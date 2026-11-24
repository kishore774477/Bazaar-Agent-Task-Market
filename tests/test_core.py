import random

import pytest

from bazaar.agents import Agent, CATEGORIES, default_roster
from bazaar.execution import execute, success_probability
from bazaar.reputation import PRIOR_ALPHA, PRIOR_BETA, Reputation
from bazaar.scoring import score_bids, pick_winner
from bazaar.tasks import Task, generate_outcome_draws, generate_tasks


# ---------------------------------------------------------------------------- tasks
def test_tasks_are_deterministic_and_in_range():
    a, b = generate_tasks(50, seed=3), generate_tasks(50, seed=3)
    assert [t.__dict__ for t in a] == [t.__dict__ for t in b]
    assert generate_tasks(50, seed=4) != a
    assert all(1.0 <= t.complexity <= 10.0 for t in a) and all(t.category in CATEGORIES for t in a)
    assert [t.id for t in a] == list(range(50))


def test_outcome_draws_are_deterministic_uniforms():
    u = generate_outcome_draws(500, seed=9)
    assert len(u) == 500 and all(0.0 <= x <= 1.0 for x in u)
    assert generate_outcome_draws(500, seed=9) == u
    assert abs(sum(u) / len(u) - 0.5) < 0.05           # roughly uniform


# ---------------------------------------------------------------------------- agents
def test_an_agent_never_bids_outside_its_skill_unless_flagged():
    specialist = Agent("S", {"backend": 0.9}, participation_threshold=0.3)
    assert not specialist.wants_to_bid(Task(0, "frontend", 5, 0))        # no skill at all in this category
    assert specialist.wants_to_bid(Task(0, "backend", 5, 0))
    cautious = Agent("C", {"qa": 0.2}, participation_threshold=0.3)
    assert not cautious.wants_to_bid(Task(0, "qa", 5, 0))                 # below its own bar
    bold = Agent("B", {"qa": 0.2}, participation_threshold=0.3, bids_outside_skill=True)
    assert bold.wants_to_bid(Task(0, "qa", 5, 0))                         # the flag overrides the bar


def test_price_and_eta_rise_with_complexity_and_fall_with_skill():
    rng = random.Random(0)
    weak, strong = Agent("W", {"x": 0.2}), Agent("S", {"x": 0.9})
    small, big = Task(0, "x", 1.0, 0), Task(1, "x", 9.0, 0)
    assert weak.bid(big, rng).price > weak.bid(small, rng).price
    assert weak.bid(small, rng).price > strong.bid(small, rng).price


def test_price_aggression_undercuts_and_claims_track_honesty():
    rng1, rng2 = random.Random(1), random.Random(1)
    cheap = Agent("Cheap", {"x": 0.5}, price_aggression=0.5)
    normal = Agent("Normal", {"x": 0.5}, price_aggression=1.0)
    t = Task(0, "x", 5.0, 0)
    assert cheap.bid(t, rng1).price < normal.bid(t, rng2).price

    honest = Agent("Honest", {"x": 0.3}, honesty=1.0)
    overclaim = Agent("Over", {"x": 0.3}, honesty=2.0)
    confs = [overclaim.bid(t, random.Random(k)).confidence for k in range(40)]
    honest_confs = [honest.bid(t, random.Random(k)).confidence for k in range(40)]
    assert sum(confs) / len(confs) > sum(honest_confs) / len(honest_confs)      # low skill (0.3): overclaiming inflates the most here

    high_skill = Task(0, "x", 5.0, 0)
    honest_hi = Agent("HonestHi", {"x": 0.9}, honesty=1.0)
    over_hi = Agent("OverHi", {"x": 0.9}, honesty=2.0)
    gap_low = (sum(confs) / len(confs)) - (sum(honest_confs) / len(honest_confs))
    confs_hi = [over_hi.bid(high_skill, random.Random(k)).confidence for k in range(40)]
    honest_hi_confs = [honest_hi.bid(high_skill, random.Random(k)).confidence for k in range(40)]
    gap_hi = (sum(confs_hi) / len(confs_hi)) - (sum(honest_hi_confs) / len(honest_hi_confs))
    assert gap_low > gap_hi                                                      # inflation bites less when skill is already high


def test_default_roster_has_ten_named_agents_with_valid_skills():
    r = default_roster()
    assert len(r) == 10 and len({a.name for a in r}) == 10
    for a in r:
        assert all(0.0 < v <= 1.0 for v in a.skill.values())
        assert all(c in CATEGORIES for c in a.skill)
    flex = next(a for a in r if a.name == "Flex")
    bolt = next(a for a in r if a.name == "Bolt")
    assert flex.honesty > 1.0 and flex.bids_outside_skill and flex.skill["data"] < bolt.skill["data"]


# ---------------------------------------------------------------------------- execution
def test_success_probability_increases_with_skill_and_the_gap_widens_with_complexity():
    assert success_probability(0.9, 1.0) > success_probability(0.3, 1.0)
    gap_easy = success_probability(0.9, 1.0) - success_probability(0.3, 1.0)
    gap_hard = success_probability(0.9, 10.0) - success_probability(0.3, 10.0)
    assert gap_hard > gap_easy                          # complexity punishes the unskilled agent more
    assert 0.04 <= success_probability(0.0, 10.0) and success_probability(1.0, 0.0) <= 0.97


def test_execute_uses_the_shared_draw_not_a_private_roll():
    a = Agent("A", {"x": 0.5})
    p = success_probability(0.5, 5.0)
    assert execute(a, Task(0, "x", 5.0, 0), p - 0.001).success
    assert not execute(a, Task(0, "x", 5.0, 0), p + 0.001).success


# ---------------------------------------------------------------------------- reputation
def test_reputation_prior_and_updates():
    r = Reputation()
    assert r.mean == pytest.approx(0.5) and r.observations == 0
    r.update(True)
    assert r.alpha == PRIOR_ALPHA + 1 and r.mean > 0.5 and r.observations == 1
    for _ in range(20):
        r.update(False)
    assert r.mean < 0.3 and r.history == [True] + [False] * 20


def test_reputation_variance_shrinks_with_more_observations():
    a, b = Reputation(), Reputation()
    for _ in range(3):
        a.update(True)
    for _ in range(30):
        b.update(True)
    assert b.variance < a.variance


# ---------------------------------------------------------------------------- scoring
def test_score_bids_rewards_cheap_fast_confident_trusted():
    from bazaar.agents import Bid

    bids = [Bid("A", 0, price=10, eta=1, confidence=0.9), Bid("B", 0, price=100, eta=10, confidence=0.9)]
    scored = score_bids(bids, {"A": 0.9, "B": 0.9})
    sa = dict((b.agent, s) for b, s in scored)
    assert sa["A"] > sa["B"]
    bids2 = [Bid("A", 0, price=10, eta=1, confidence=0.9), Bid("B", 0, price=10, eta=1, confidence=0.9)]
    trusted = {b.agent: s for b, s in score_bids(bids2, {"A": 0.9, "B": 0.1})}
    assert trusted["A"] > trusted["B"]


def test_score_bids_handles_a_tied_field_and_empty_input():
    from bazaar.agents import Bid

    bids = [Bid("A", 0, 10, 1, 0.5), Bid("B", 0, 10, 1, 0.5)]
    scored = score_bids(bids, {"A": 0.5, "B": 0.5})
    assert scored[0][1] == pytest.approx(scored[1][1])
    assert score_bids([], {}) == []


def test_pick_winner_breaks_ties_on_lower_price():
    from bazaar.agents import Bid

    bids = [Bid("A", 0, 20, 1, 0.5), Bid("B", 0, 10, 1, 0.5)]
    scored = score_bids(bids, {"A": 0.5, "B": 0.5})
    winner, _ = pick_winner(scored)
    assert winner.agent == "B"


def test_weights_must_sum_appropriately_for_a_meaningful_comparison():
    from bazaar.scoring import WEIGHTS
    assert sum(WEIGHTS) == pytest.approx(1.0)
