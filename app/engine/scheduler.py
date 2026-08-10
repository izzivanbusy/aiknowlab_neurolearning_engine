"""
FSRS-inspired spaced repetition scheduler.

This is a planning model — it answers "when should we review this item next?"
It does NOT model brain processes or claim to measure memory directly.

Rating scale (from evaluator → mapped here):
    1 = Again   (retrieval failed / performance < 0.3)
    2 = Hard    (retrieved with significant errors, 0.3–0.6)
    3 = Good    (retrieved correctly, 0.6–0.85)
    4 = Easy    (retrieved fluently, > 0.85)
"""

from datetime import datetime, timedelta, timezone


# Stability multipliers per rating
STABILITY_FACTOR: dict[int, float] = {
    1: 0.4,   # Again  — significant forgetting, reset
    2: 0.8,   # Hard   — partial recall
    3: 1.6,   # Good   — normal spacing increase
    4: 2.5,   # Easy   — large spacing increase
}

# Difficulty deltas per rating (difficulty ∈ [0.1, 1.0])
DIFFICULTY_DELTA: dict[int, float] = {
    1: +0.20,
    2: +0.10,
    3:  0.00,
    4: -0.10,
}


def performance_to_rating(performance_score: float, retrieval_success: bool) -> int:
    """Map evaluator signals to a 1–4 FSRS rating."""
    if not retrieval_success:
        return 1
    if performance_score < 0.3:
        return 1
    if performance_score < 0.6:
        return 2
    if performance_score < 0.85:
        return 3
    return 4


def fsrs_update(
    stability: float,
    difficulty: float,
    repetitions: int,
    lapses: int,
    rating: int,
) -> tuple[float, float, int, int, datetime]:
    """
    Returns: (new_stability, new_difficulty, new_repetitions, new_lapses, next_review)
    """
    new_stability = max(0.1, stability * STABILITY_FACTOR[rating])
    new_difficulty = max(0.1, min(1.0, difficulty + DIFFICULTY_DELTA[rating]))

    if rating == 1:
        # Failed retrieval — counts as a lapse
        new_repetitions = 0
        new_lapses = lapses + 1
        # After a lapse, reset to short interval
        new_stability = max(0.1, stability * 0.2)
    else:
        new_repetitions = repetitions + 1
        new_lapses = lapses

    next_review = datetime.now(tz=timezone.utc) + timedelta(days=new_stability)

    return new_stability, new_difficulty, new_repetitions, new_lapses, next_review


def due_items_query_fragment() -> str:
    """
    SQL fragment for selecting due items — for reference in route code.

    Full query lives in the route, but the logic is:
      WHERE next_review <= NOW()
      ORDER BY next_review ASC, stability ASC
      — with interference filter: max 1 item per family_id per session batch
    """
    return "next_review <= NOW() ORDER BY next_review ASC, stability ASC"
