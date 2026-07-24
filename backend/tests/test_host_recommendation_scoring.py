"""Host recommendation scoring weights."""

from app.hosts.recommendations import constants as C


def test_recommendation_labels():
    from app.hosts.recommendations.scoring import recommendation_label

    assert recommendation_label(85) == C.LABEL_STRONG
    assert recommendation_label(65) == C.LABEL_GOOD
    assert recommendation_label(40) == C.LABEL_SIMILAR
    assert recommendation_label(20) is None
