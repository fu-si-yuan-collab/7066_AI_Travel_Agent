from app.recommendations.feature_engineering import (
    budget_fit_feature,
    build_ranking_features,
    season_match_feature,
)
from app.recommendations.online_ranker import (
    get_model_weights,
    score_with_online_model,
    update_model_weights,
)


def test_budget_fit_feature_monotonic_behavior():
    in_range = budget_fit_feature(price=500, low=300, high=800)
    above = budget_fit_feature(price=1200, low=300, high=800)
    below = budget_fit_feature(price=100, low=300, high=800)

    assert in_range == 1.0
    assert 0.0 <= above < 1.0
    assert 0.0 <= below < 1.0


def test_build_ranking_features_has_expected_keys():
    features = build_ranking_features(
        content=0.8,
        learned_tags=0.7,
        profile_similarity=0.6,
        self_affinity=0.4,
        collaborative=0.5,
        popularity=0.3,
        budget_fit=0.9,
        season_match=0.7,
        rating=4.5,
    )

    assert "bias" in features
    assert "rating_norm" in features
    assert 0.0 <= features["rating_norm"] <= 1.0


def test_online_ranker_score_and_update():
    features = {
        "content": 0.9,
        "learned_tags": 0.8,
        "profile_similarity": 0.6,
        "self_affinity": 0.4,
        "collaborative": 0.5,
        "popularity": 0.2,
        "budget_fit": 0.85,
        "season_match": 0.6,
        "rating_norm": 0.9,
        "bias": 1.0,
    }

    initial_score = score_with_online_model(features, learned_tags={})
    updated_tags = update_model_weights(
        learned_tags={},
        features=features,
        label=1.0,
    )
    updated_score = score_with_online_model(features, learned_tags=updated_tags)

    assert 0.0 <= initial_score <= 1.0
    assert 0.0 <= updated_score <= 1.0
    assert updated_score >= initial_score

    weights = get_model_weights(updated_tags)
    assert any(abs(v) > 0 for v in weights.values())


def test_season_match_feature_safe_fallback():
    assert season_match_feature("", "museum") == 0.5
    assert season_match_feature("invalid-date", "beach") == 0.5
