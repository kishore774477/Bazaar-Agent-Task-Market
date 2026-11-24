"""How the auctioneer picks a winner from a round of bids: Contract-Net's award step.

Price and ETA are scored *relative to the field* for this one auction (cheapest and fastest bid in the round score
1.0, the priciest/slowest scores 0.0) — an auction with only expensive bidders should not look bad against one
with only cheap ones. Confidence is discounted by the bidder's reputation in that category, which is the only
place a track record enters the decision: nothing here reads what an agent claims about its own honesty.
"""
from __future__ import annotations

from .agents import Bid

WEIGHTS = (0.15, 0.10, 0.75)      # (price, eta, confidence); must sum to 1.0


def _relative(values: list, pick) -> list[float]:
    xs = [pick(v) for v in values]
    lo, hi = min(xs), max(xs)
    if hi == lo:
        return [1.0] * len(xs)
    return [(hi - x) / (hi - lo) for x in xs]           # lower raw value -> higher score


def score_bids(bids: list[Bid], trust: dict, weights: tuple = WEIGHTS) -> list[tuple]:
    """Returns ``[(bid, score), ...]`` in the order given. ``trust``: agent name -> reputation mean in [0, 1]."""
    if not bids:
        return []
    wp, we, wc = weights
    price_s = _relative(bids, lambda b: b.price)
    eta_s = _relative(bids, lambda b: b.eta)
    out = []
    for b, ps, es in zip(bids, price_s, eta_s):
        cs = b.confidence * trust.get(b.agent, 0.5)
        out.append((b, round(wp * ps + we * es + wc * cs, 5)))
    return out


def pick_winner(scored: list[tuple]) -> tuple:
    """Highest score; ties broken by the lower price (a tie should not be an arbitrary coin flip)."""
    return max(scored, key=lambda t: (t[1], -t[0].price))
