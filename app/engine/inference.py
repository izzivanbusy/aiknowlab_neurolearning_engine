"""
Bayesian acquisition inference engine.

Updates P(skill sufficiently acquired | observed evidence).

This is a model estimate — not a measured property of the learner.
acquisition_probability = 0.82 means: given the evidence so far,
the model estimates 82% probability that this skill is sufficiently acquired.

Separate from FSRS scheduling. The two systems share evidence but serve
different purposes:
- inference.py → answers "has the skill been acquired?"
- scheduler.py → answers "when should we review this item next?"
"""

import math
from typing import Any


def _clamp(value: float, lo: float = 0.05, hi: float = 0.95) -> float:
    return max(lo, min(hi, value))


def estimate_likelihood_acquired(
    skill_demonstration: dict[str, Any],
    signals: dict[str, Any],
) -> float:
    """
    P(this observation | skill IS acquired)

    If the skill is acquired, we expect:
    - functional=True (communicative function achieved)
    - independent=True (no scaffolding needed)
    - generalized=True (if transfer context)
    - high performance_score
    - few errors
    """
    score = 0.35  # base rate

    sd = skill_demonstration
    if sd.get("functional"):
        score += 0.25
    if sd.get("independent"):
        score += 0.15
    if sd.get("generalized"):
        score += 0.20
    if sd.get("context_appropriate"):
        score += 0.10

    perf = signals.get("performance_score", 0.0)
    score += perf * 0.10

    # Penalise errors
    error_count = (
        len(signals.get("lexical_errors", []))
        + len(signals.get("morphological_errors", []))
        + len(signals.get("pragmatic_errors", []))
    )
    score -= min(error_count * 0.04, 0.15)

    return _clamp(score, 0.05, 0.99)


def estimate_likelihood_not_acquired(
    skill_demonstration: dict[str, Any],
    signals: dict[str, Any],
) -> float:
    """
    P(this observation | skill is NOT acquired)

    If the skill is not acquired, we expect:
    - functional=False
    - independent=False
    - errors present
    - low performance_score
    """
    score = 0.35  # base rate

    sd = skill_demonstration
    if not sd.get("functional"):
        score += 0.25
    if not sd.get("independent"):
        score += 0.15

    perf = signals.get("performance_score", 0.0)
    score += (1.0 - perf) * 0.10

    error_count = (
        len(signals.get("lexical_errors", []))
        + len(signals.get("morphological_errors", []))
        + len(signals.get("pragmatic_errors", []))
    )
    score += min(error_count * 0.04, 0.20)

    if not signals.get("retrieval_success"):
        score += 0.10

    return _clamp(score, 0.05, 0.99)


def update_acquisition_probability(
    prior_p: float,
    skill_demonstration: dict[str, Any],
    signals: dict[str, Any],
    evidence_strength: float,
) -> float:
    """
    Bayesian posterior update via log-odds.

    evidence_strength scales how much this evidence moves the estimate.
    Strong evidence (distance=3, unexpected transfer) → large update.
    Weak evidence (distance=0, controlled exercise) → small update.
    """
    p_obs_acquired = estimate_likelihood_acquired(skill_demonstration, signals)
    p_obs_not_acquired = estimate_likelihood_not_acquired(skill_demonstration, signals)

    # Log-odds update (numerically stable)
    prior_log_odds = math.log(prior_p / (1.0 - prior_p + 1e-9) + 1e-9)
    log_likelihood_ratio = math.log(p_obs_acquired / (p_obs_not_acquired + 1e-9) + 1e-9)

    # Weight update by evidence_strength
    posterior_log_odds = prior_log_odds + evidence_strength * log_likelihood_ratio
    posterior_p = 1.0 / (1.0 + math.exp(-posterior_log_odds))

    return _clamp(posterior_p)


def update_confidence(
    current_confidence: float,
    evidence_strength: float,
    evidence_count: int,
) -> float:
    """
    Confidence in our estimate grows with evidence count and strength.
    Asymptotically approaches 1.0, never reaches it.

    Low confidence + high acquisition_probability means:
    "Looks like acquisition, but we haven't seen enough to be sure."
    """
    # Sigmoid-like growth based on evidence count
    count_factor = evidence_count / (evidence_count + 10.0)
    # 10 items → 0.5 confidence ceiling
    # 20 items → 0.67 ceiling
    # 40 items → 0.8 ceiling

    incremental = evidence_strength * (1.0 - current_confidence) * 0.25
    new_confidence = (current_confidence + incremental) * count_factor

    return _clamp(new_confidence, 0.0, 0.99)


def is_acquired(state_acquisition_p: float, state_confidence: float) -> bool:
    """
    Conservative acquisition gate:
    - acquisition_probability > 0.75
    - confidence_in_estimate > 0.6
    Both must hold. A weak estimate does not unlock the next skill.
    """
    return state_acquisition_p > 0.75 and state_confidence > 0.6
