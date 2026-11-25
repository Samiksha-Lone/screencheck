import pytest

from src.factory.true_fit import calculate_true_fit, true_fit


def test_full_must_have_match():
    score = calculate_true_fit(
        ["Python", "SQL", "Git"],
        ["Python", "SQL", "Git"],
        [],
        0,
    )
    assert score == 70.0


def test_partial_must_have_match():
    score = calculate_true_fit(
        ["Python"],
        ["Python", "SQL", "Git"],
        [],
        0,
    )
    assert score == 23.33


def test_nice_to_have_contribution():
    score = calculate_true_fit(
        ["Python", "Docker"],
        ["Python"],
        ["Docker", "AWS"],
        0,
    )
    assert score == 80.0


@pytest.mark.parametrize(
    ("project_evidence", "expected"),
    [(0, 70.0), (5, 75.0), (10, 80.0)],
)
def test_project_evidence_values(project_evidence, expected):
    score = calculate_true_fit(
        ["Python"],
        ["Python"],
        [],
        project_evidence,
    )
    assert score == expected


def test_aliases_in_candidate_and_job_skills():
    score = calculate_true_fit(
        ["JS", "Node", "Postgres"],
        ["JavaScript", "Node.js", "PostgreSQL"],
        [],
        10,
    )
    assert score == 80.0


def test_duplicate_skills_are_not_double_counted():
    score = calculate_true_fit(
        ["Python", "Python", "SQL", "Docker"],
        ["Python", "Python", "SQL", "SQL"],
        ["Docker", "Docker"],
        0,
    )
    assert score == 90.0


def test_empty_skill_lists():
    assert calculate_true_fit([], [], [], 0) == 0.0
    assert calculate_true_fit([], [], [], 10) == 10.0
    assert calculate_true_fit(None, None, None, 5) == 5.0


@pytest.mark.parametrize("project_evidence", [-1, 1, 3, 6, 11, 100, True, None])
def test_invalid_project_evidence(project_evidence):
    with pytest.raises(ValueError):
        calculate_true_fit(["Python"], ["Python"], [], project_evidence)


def test_nice_to_have_keyword_alias():
    score = calculate_true_fit(
        ["Docker"],
        [],
        nice_to_have_skills=["Docker"],
        project_evidence=5,
    )
    assert score == 25.0


def test_true_fit_alias():
    assert true_fit(["Python"], ["Python"], [], 10) == 80.0
