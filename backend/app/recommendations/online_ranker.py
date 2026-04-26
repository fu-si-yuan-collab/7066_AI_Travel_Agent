"""Lightweight online ranking model (logistic scorer + SGD updates).

This keeps model state inside learned_tags using keys prefixed with 'model:w:'.
"""

from __future__ import annotations

import math

FEATURE_KEYS = [
    "content",
    "learned_tags",
    "profile_similarity",
    "self_affinity",
    "collaborative",
    "popularity",
    "budget_fit",
    "season_match",
    "rating_norm",
    "bias",
]

DEFAULT_WEIGHTS = {
    "content": 0.55,
    "learned_tags": 0.75,
    "profile_similarity": 0.65,
    "self_affinity": 0.45,
    "collaborative": 0.5,
    "popularity": 0.2,
    "budget_fit": 0.35,
    "season_match": 0.15,
    "rating_norm": 0.25,
    "bias": -0.05,
}


def _clip(value: float, lo: float = -3.0, hi: float = 3.0) -> float:
    return max(lo, min(hi, value))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _model_key(feature: str) -> str:
    return f"model:w:{feature}"


def get_model_weights(learned_tags: dict | None) -> dict[str, float]:
    learned_tags = learned_tags or {}
    weights: dict[str, float] = {}
    for key in FEATURE_KEYS:
        w = learned_tags.get(_model_key(key), DEFAULT_WEIGHTS.get(key, 0.0))
        try:
            weights[key] = float(w)
        except Exception:
            weights[key] = float(DEFAULT_WEIGHTS.get(key, 0.0))
    return weights


def score_with_online_model(features: dict[str, float], learned_tags: dict | None) -> float:
    weights = get_model_weights(learned_tags)
    z = 0.0
    for key in FEATURE_KEYS:
        z += weights.get(key, 0.0) * float(features.get(key, 0.0))
    return round(_sigmoid(z), 6)


def update_model_weights(
    *,
    learned_tags: dict | None,
    features: dict[str, float],
    label: float,
    learning_rate: float = 0.08,
    l2: float = 0.002,
) -> dict[str, float]:
    """Single-step SGD update for logistic regression.

    label should be in [0, 1].
    """
    tags: dict[str, float] = {str(k): float(v) for k, v in (learned_tags or {}).items() if isinstance(v, (int, float))}
    weights = get_model_weights(tags)

    pred = score_with_online_model(features, tags)
    error = float(label) - pred

    for key in FEATURE_KEYS:
        x = float(features.get(key, 0.0))
        w = weights.get(key, 0.0)
        grad = error * x - l2 * w
        new_w = w + learning_rate * grad
        weights[key] = _clip(new_w)
        tags[_model_key(key)] = round(weights[key], 6)

    return tags
