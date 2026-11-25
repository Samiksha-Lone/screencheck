import pytest

from src.screeners.run_screening import spearman_correlation
from src.screeners.screeners import (
    EmbeddingScreener,
    LLMJudge,
    LLMOutputError,
    get_screener,
)


JOB = {
    "job_title": "Backend Engineer",
    "original_job_description": "Build Python and PostgreSQL services.",
    "must_have_skills": ["Python", "PostgreSQL", "Git"],
    "nice_to_have_skills": ["Docker", "AWS"],
}


def test_keyword_complete_partial_and_empty():
    screener = get_screener("keyword")
    complete = screener.score("Python PostgreSQL Git Docker AWS", JOB)
    partial = screener.score("Python Docker", JOB)
    empty = screener.score("", JOB)

    assert complete["score"] == 100.0
    assert partial["score"] == 37.5
    assert partial["matched_must_have"] == ["Python"]
    assert partial["missing_skills"] == ["PostgreSQL", "Git"]
    assert empty["score"] == 0.0


def test_keyword_aliases():
    result = get_screener("keyword").score(
        "JS Node Postgres RESTful services",
        {
            "must_have_skills": ["JavaScript", "Node.js", "PostgreSQL", "REST APIs"],
            "nice_to_have_skills": [],
        },
    )
    assert result["score"] == 100.0


def test_embedding_scaling_and_identical_scores():
    assert EmbeddingScreener.scale_scores([0.2, 0.4, 0.8]) == [0.0, 33.33, 100.0]
    assert EmbeddingScreener.scale_scores([0.5, 0.5]) == [50.0, 50.0]
    assert EmbeddingScreener.scale_scores([]) == []


def test_embedding_similarity(monkeypatch):
    import numpy as np

    class FakeModel:
        def encode(self, texts, convert_to_numpy, normalize_embeddings):
            return np.array([[1.0, 0.0], [1.0, 0.0]])

    screener = EmbeddingScreener(model_name="test-model")
    monkeypatch.setattr(screener, "_load_model", lambda: FakeModel())
    assert screener.similarity("same", "same") == 1.0


def test_llm_json_parsing_and_invalid_output(tmp_path):
    judge = LLMJudge(cache_path=tmp_path / "cache.json")
    valid = judge._parse_json(
        '{"score":100,"must_have_skill_evidence":40,"project_relevance":30,'
        '"relevant_experience":20,"clarity":10,"reason":"Complete"}'
    )
    assert valid["score"] == 100
    with pytest.raises(LLMOutputError):
        judge._parse_json("not json")
    with pytest.raises(LLMOutputError):
        judge._parse_json(
            '{"score":100,"must_have_skill_evidence":40,"project_relevance":30,'
            '"relevant_experience":20,"clarity":10}'
        )


def test_llm_cache_hit(tmp_path, monkeypatch):
    judge = LLMJudge(model="test-model", cache_path=tmp_path / "cache.json")
    calls = []

    def fake_call(prompt):
        calls.append(prompt)
        return (
            '{"score":50,"must_have_skill_evidence":20,"project_relevance":15,'
            '"relevant_experience":10,"clarity":5,"reason":"Test"}'
        )

    monkeypatch.setattr(judge, "_call_model", fake_call)
    first = judge.score("Python project", JOB)
    second = judge.score("Python project", JOB)
    assert len(calls) == 1
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True


def test_llm_error_handling(tmp_path, monkeypatch):
    judge = LLMJudge(model="test-model", cache_path=tmp_path / "cache.json")
    monkeypatch.setattr(
        judge,
        "_call_model",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("network unavailable")),
    )
    with pytest.raises(RuntimeError, match="network unavailable"):
        judge.score("Python", JOB)


def test_screener_interface_consistency():
    for name in ("keyword", "embedding", "llm"):
        screener = get_screener(name)
        assert hasattr(screener, "score")
        assert screener.name == name


def test_spearman_baselines():
    assert spearman_correlation([1, 2, 3], [1, 2, 3]) == 1.0
    assert spearman_correlation([1, 2, 3], [3, 2, 1]) == -1.0
