from dataclasses import dataclass

# Calibrated from real all-MiniLM-L6-v2 cosine similarity scores observed
# manually during Milestones 5-6: genuinely relevant chunk-to-question matches
# scored ~0.51-0.64, an unrelated chunk scored ~0.19. This is a starting
# point, not a tuned value — revisit once there's a hand-labeled eval set.
LOW_SIMILARITY_THRESHOLD = 0.35

# If the top two matches are this close, it's ambiguous which chunk is
# actually authoritative for the answer.
AMBIGUOUS_GAP_THRESHOLD = 0.03


@dataclass(frozen=True)
class ConfidenceResult:
    needs_review: bool
    reason: str | None


def assess_confidence(scores: list[float]) -> ConfidenceResult:
    """Decides whether an answer needs human review, from retrieval
    similarity scores alone. `scores` must be pre-sorted descending by
    relevance (as retrieval.retrieve_relevant_chunks already returns them) —
    this function doesn't sort them itself.
    """
    if not scores:
        return ConfidenceResult(
            needs_review=True,
            reason="No relevant passages were found in the document.",
        )

    top_score = scores[0]
    if top_score < LOW_SIMILARITY_THRESHOLD:
        return ConfidenceResult(
            needs_review=True,
            reason=(
                f"The best-matching passage had low similarity "
                f"({top_score:.2f} < {LOW_SIMILARITY_THRESHOLD})."
            ),
        )

    if len(scores) >= 2:
        gap = scores[0] - scores[1]
        if gap < AMBIGUOUS_GAP_THRESHOLD:
            return ConfidenceResult(
                needs_review=True,
                reason=(
                    f"The top two matching passages had very similar relevance "
                    f"scores ({scores[0]:.2f} vs {scores[1]:.2f}), making it "
                    f"unclear which is authoritative."
                ),
            )

    return ConfidenceResult(needs_review=False, reason=None)
