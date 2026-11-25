"""Run the three ScreenCheck screeners over 300 generated candidates."""

import json
import random
from pathlib import Path

from src.factory.resume_renderer import extract_pdf_text
from src.screeners.screeners import (
    EmbeddingScreener,
    KeywordScreener,
    LLMJudge,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "private" / "screeners"

JOB_FILES = {
    "backend": "backend_software_engineer.json",
    "full_stack": "full_stack_developer.json",
    "data_analyst": "data_analyst.json",
}


def load_jobs() -> dict:
    jobs = {}
    for job_key, filename in JOB_FILES.items():
        with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
            jobs[job_key] = json.load(file)
    return jobs


def load_candidates() -> list[dict]:
    candidates = []
    for path in sorted((DATA_DIR / "generated").glob("*_candidates.json")):
        with path.open("r", encoding="utf-8") as file:
            candidates.extend(json.load(file)["candidates"])
    return candidates


def _average_ranks(values: list[float]) -> list[float]:
    ranked = [0.0] * len(values)
    indexed = sorted(range(len(values)), key=lambda index: values[index])
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and values[indexed[end]] == values[indexed[position]]:
            end += 1
        rank = (position + 1 + end) / 2
        for index in indexed[position:end]:
            ranked[index] = rank
        position = end
    return ranked


def spearman_correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    left_mean = sum(left_ranks) / len(left_ranks)
    right_mean = sum(right_ranks) / len(right_ranks)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_ranks, right_ranks)
    )
    left_variance = sum((value - left_mean) ** 2 for value in left_ranks)
    right_variance = sum((value - right_mean) ** 2 for value in right_ranks)
    denominator = (left_variance * right_variance) ** 0.5
    if denominator == 0:
        return 1.0 if left_ranks == right_ranks else 0.0
    return round(numerator / denominator, 6)


def get_candidate_resume_text(candidate: dict) -> str:
    path = (
        DATA_DIR
        / "private"
        / "rendered"
        / candidate["job_id"]
        / "one-column"
        / f"{candidate['candidate_id']}.pdf"
    )
    if path.exists():
        return extract_pdf_text(path)

    from src.factory.resume_renderer import resume_text

    return resume_text(candidate)


def run_pipeline(output_dir: str | Path = OUTPUT_DIR) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs()
    candidates = load_candidates()

    keyword = KeywordScreener()
    embedding = EmbeddingScreener(cache_dir=output_dir)
    llm = LLMJudge(cache_path=output_dir / "llm_cache.json")
    results = []
    similarities = []
    llm_errors = []

    for candidate in candidates:
        job = jobs[candidate["job_id"]]
        resume_text = get_candidate_resume_text(candidate)
        keyword_result = keyword.score(resume_text, job)
        similarity = embedding.similarity(resume_text, job["original_job_description"])
        similarities.append(similarity)

        try:
            llm_result = llm.score(resume_text, job)
        except Exception as error:
            llm_result = {"status": "error", "error": str(error), "score": None}
            llm_errors.append(
                {"candidate_id": candidate["candidate_id"], "error": str(error)}
            )

        results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "job_id": candidate["job_id"],
                "job_title": candidate["job_title"],
                "true_fit": candidate["true_fit"],
                "keyword": keyword_result,
                "embedding": {
                    "similarity": similarity,
                    "scaled_score": None,
                    "model": embedding.model_name,
                },
                "llm": llm_result,
            }
        )

    scaled = embedding.scale_scores(similarities)
    for result, score in zip(results, scaled):
        result["embedding"]["scaled_score"] = score

    true_fit_scores = [result["true_fit"] for result in results]
    keyword_scores = [result["keyword"]["score"] for result in results]
    embedding_scores = [result["embedding"]["scaled_score"] for result in results]
    rng = random.Random(42)
    random_scores = [rng.random() * 100 for _ in results]

    repeat_scores = []
    repeat = KeywordScreener()
    for candidate in candidates:
        job = jobs[candidate["job_id"]]
        text = get_candidate_resume_text(candidate)
        repeat_scores.append(repeat.score(text, job)["score"])

    llm_evaluated = sum(
        1
        for result in results
        if result["llm"].get("status") != "error"
        and result["llm"].get("score") is not None
    )
    manifest = {
        "candidate_count": len(results),
        "embedding_model": embedding.model_name,
        "llm": {
            "evaluated": llm_evaluated,
            "errors": len(llm_errors),
            "failure_details": llm_errors[:20],
            "model": llm.model or "not-configured",
            "temperature": 0,
        },
        "repeatability": {
            "keyword_identical": repeat_scores == keyword_scores,
        },
        "rank_quality": {
            "keyword_vs_true_fit_spearman": spearman_correlation(
                keyword_scores, true_fit_scores
            ),
            "embedding_vs_true_fit_spearman": spearman_correlation(
                embedding_scores, true_fit_scores
            ),
            "random_vs_true_fit_spearman": spearman_correlation(
                random_scores, true_fit_scores
            ),
            "true_fit_baseline_spearman": spearman_correlation(
                true_fit_scores, true_fit_scores
            ),
        },
    }

    with (output_dir / "screening_results.json").open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
    with (output_dir / "screening_manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
    return manifest


if __name__ == "__main__":
    print(json.dumps(run_pipeline(), indent=2))
