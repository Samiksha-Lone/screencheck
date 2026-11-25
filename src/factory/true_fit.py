"""Simple true-fit skill and project-evidence scoring."""

from typing import Iterable

from src.factory.skill_normalizer import normalize_skill


def _normalized_skill_set(skills: Iterable[str] | None) -> set[str]:
    """Normalize skills and remove duplicates and empty values."""
    if skills is None:
        return set()

    normalized = set()
    for skill in skills:
        if isinstance(skill, str):
            clean_skill = normalize_skill(skill)
            if clean_skill:
                normalized.add(clean_skill)
    return normalized


def calculate_true_fit(
    candidate_skills: Iterable[str] | None,
    must_have_skills: Iterable[str] | None,
    nice_have_skills: Iterable[str] | None = None,
    project_evidence: int = 0,
    *,
    nice_to_have_skills: Iterable[str] | None = None,
) -> float:
    """Calculate a 0-100 true-fit score."""
    if isinstance(project_evidence, bool) or project_evidence not in (0, 5, 10):
        raise ValueError("project_evidence must be 0, 5, or 10")

    if nice_to_have_skills is not None:
        if nice_have_skills is not None:
            raise TypeError(
                "provide either nice_have_skills or nice_to_have_skills, not both"
            )
        nice_have_skills = nice_to_have_skills

    candidate = _normalized_skill_set(candidate_skills)
    must_have = _normalized_skill_set(must_have_skills)
    nice_have = _normalized_skill_set(nice_have_skills)

    must_have_contribution = 0.0
    if must_have:
        must_have_held = len(candidate.intersection(must_have))
        must_have_contribution = 70 * must_have_held / len(must_have)

    nice_have_contribution = 0.0
    if nice_have:
        nice_have_held = len(candidate.intersection(nice_have))
        nice_have_contribution = 20 * nice_have_held / len(nice_have)

    score = must_have_contribution + nice_have_contribution + project_evidence
    return round(min(100.0, max(0.0, score)), 2)


# A shorter name for callers that prefer the concept directly.
def true_fit(
    candidate_skills: Iterable[str] | None,
    must_have_skills: Iterable[str] | None,
    nice_have_skills: Iterable[str] | None = None,
    project_evidence: int = 0,
) -> float:
    return calculate_true_fit(
        candidate_skills,
        must_have_skills,
        nice_have_skills,
        project_evidence,
    )
