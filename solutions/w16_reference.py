"""Reference solution for the semantic cache drill.

The threshold is 0.88, and it was chosen on days 1-6, not on all eight. At 0.88 the cache serves
about three quarters of the traffic with about four percent wrong; 0.90 halves the hits to buy
one point of wrongness back; 0.80 serves more and answers the wrong question fifteen percent of
the time.

The lookup is a linear scan over the cache. With two hundred turns a day that is forty thousand
comparisons, which is nothing; at a million turns a day you would need an index, and the
threshold would stay exactly where it is.
"""

from __future__ import annotations

from drills.w16_semantic_cache.data import cosine

THRESHOLD = 0.88


def serve(day, model) -> dict:
    cache: list = []
    served: list[str | None] = []

    for turn in day.turns:
        best = None
        best_score = -1.0
        for cached in cache:
            score = cosine(turn.embedding, cached.embedding)
            if score > best_score:
                best, best_score = cached, score

        if best is not None and best_score >= THRESHOLD:
            served.append(best.id)
            continue

        model.complete(turn.text)
        cache.append(turn)
        served.append(None)

    return {"served": served}
