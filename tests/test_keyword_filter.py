from ai_model_watch.llm.keyword import KeywordRelevanceFilter


def test_keyword_filter_returns_structured_result() -> None:
    result = KeywordRelevanceFilter().classify(
        "New reasoning model", "The model improves coding and agent workflows."
    )
    assert result.relevant is True
    assert "model" in result.topics
