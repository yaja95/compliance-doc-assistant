from compliance_doc_assistant.confidence import (
    AMBIGUOUS_GAP_THRESHOLD,
    LOW_SIMILARITY_THRESHOLD,
    assess_confidence,
)


def test_empty_scores_needs_review() -> None:
    result = assess_confidence([])

    assert result.needs_review is True
    assert "No relevant passages" in result.reason


def test_single_high_score_does_not_need_review() -> None:
    result = assess_confidence([0.6])

    assert result.needs_review is False
    assert result.reason is None


def test_single_low_score_needs_review() -> None:
    result = assess_confidence([0.2])

    assert result.needs_review is True
    assert "low similarity" in result.reason


def test_score_exactly_at_low_similarity_threshold_does_not_need_review() -> None:
    """The comparison is strict (<), so a score exactly at the threshold is
    the boundary between "passes" and "fails" — this pins down which side.
    """
    result = assess_confidence([LOW_SIMILARITY_THRESHOLD])

    assert result.needs_review is False


def test_score_just_below_low_similarity_threshold_needs_review() -> None:
    result = assess_confidence([LOW_SIMILARITY_THRESHOLD - 0.001])

    assert result.needs_review is True


def test_large_gap_between_top_two_does_not_need_review() -> None:
    result = assess_confidence([0.6, 0.3])

    assert result.needs_review is False


def test_small_gap_between_top_two_needs_review() -> None:
    result = assess_confidence([0.6, 0.6 - AMBIGUOUS_GAP_THRESHOLD + 0.001])

    assert result.needs_review is True
    assert "very similar relevance" in result.reason


def test_gap_exactly_at_threshold_does_not_need_review() -> None:
    """Strict (<) comparison again — a gap exactly equal to the threshold
    passes (is not "too small").
    """
    result = assess_confidence([0.6, 0.6 - AMBIGUOUS_GAP_THRESHOLD])

    assert result.needs_review is False


def test_low_top_score_takes_priority_over_gap_check() -> None:
    """Both conditions could technically apply here (low top score, and the
    two scores happen to be close together) — the low-similarity reason
    should win since it's checked first and is the more fundamental problem.
    """
    result = assess_confidence([0.1, 0.09])

    assert result.needs_review is True
    assert "low similarity" in result.reason


def test_three_scores_only_compares_top_two() -> None:
    result = assess_confidence([0.6, 0.3, 0.6])

    assert result.needs_review is False
