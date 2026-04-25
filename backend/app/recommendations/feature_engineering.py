"""Feature engineering helpers for recommendation ranking."""

from __future__ import annotations

from datetime import datetime


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def budget_fit_feature(price: float, low: float, high: float) -> float:
    """Return a smooth budget fit score in [0, 1]."""
    if price <= 0 or high <= 0:
        return 0.5
    if low <= price <= high:
        return 1.0
    if price < low:
        gap = max(1.0, low)
        return max(0.0, 1.0 - (low - price) / gap)
    gap = max(1.0, high)
    return max(0.0, 1.0 - (price - high) / gap)


def season_match_feature(start_date: str, text: str) -> float:
    if not start_date:
        return 0.5
    try:
        month = datetime.fromisoformat(start_date).month
    except Exception:
        return 0.5

    normalized_text = (text or "").lower()
    if month in {6, 7, 8}:
        return 1.0 if any(k in normalized_text for k in ["beach", "island", "outdoor", "water"]) else 0.4
    if month in {12, 1, 2}:
        return 1.0 if any(k in normalized_text for k in ["museum", "indoor", "onsen", "spa"]) else 0.4
    return 0.6


def build_ranking_features(
    *,
    content: float,
    learned_tags: float,
    profile_similarity: float,
    self_affinity: float,
    collaborative: float,
    popularity: float,
    budget_fit: float,
    season_match: float,
    rating: float,
) -> dict[str, float]:
    """Assemble a normalized feature dict for model scoring."""
    return {
        "content": round(max(0.0, content), 6),
        "learned_tags": round(max(0.0, learned_tags), 6),
        "profile_similarity": round(max(0.0, profile_similarity), 6),
        "self_affinity": round(max(0.0, self_affinity), 6),
        "collaborative": round(max(0.0, collaborative), 6),
        "popularity": round(max(0.0, popularity), 6),
        "budget_fit": round(max(0.0, min(1.0, budget_fit)), 6),
        "season_match": round(max(0.0, min(1.0, season_match)), 6),
        "rating_norm": round(max(0.0, min(1.0, rating / 5.0)), 6),
        "bias": 1.0,
    }
