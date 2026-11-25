import pytest

from src.factory.skill_normalizer import normalize_skill


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("JS", "JavaScript"),
        ("java script", "JavaScript"),
        ("Node", "Node.js"),
        ("node JS", "Node.js"),
        ("Postgres", "PostgreSQL"),
        ("RESTful services", "REST APIs"),
        ("React JS", "React"),
        ("Express JS", "Express.js"),
    ],
)
def test_aliases_are_normalized(skill, expected):
    assert normalize_skill(skill) == expected


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("JavaScript", "JavaScript"),
        ("Node.js", "Node.js"),
        ("PostgreSQL", "PostgreSQL"),
        ("REST APIs", "REST APIs"),
        ("React", "React"),
        ("Express.js", "Express.js"),
    ],
)
def test_canonical_names_are_unchanged(skill, expected):
    assert normalize_skill(skill) == expected


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("aws", "AWS"),
        ("SQL", "SQL"),
        ("typesCRIPT", "TypeScript"),
        ("power BI", "Power BI"),
        ("javascript", "JavaScript"),
        ("postgresql", "PostgreSQL"),
        ("NODE.JS", "Node.js"),
        ("react", "React"),
        ("GIT", "Git"),
        ("PYTHON", "Python"),
        ("java", "Java"),
        ("Docker", "Docker"),
        ("REDIS", "Redis"),
        ("KUBERNETES", "Kubernetes"),
        ("tableau", "Tableau"),
        ("EXCEL", "Excel"),
    ],
)
def test_common_technology_names_use_canonical_formatting(skill, expected):
    assert normalize_skill(skill) == expected


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("python", "Python"),
        ("MACHINE learning", "Machine Learning"),
        ("  data   analysis  ", "Data Analysis"),
    ],
)
def test_unknown_skills_use_consistent_capitalization(skill, expected):
    assert normalize_skill(skill) == expected


def test_case_and_whitespace_are_normalized():
    assert normalize_skill("  jS  ") == "JavaScript"
    assert normalize_skill(" POSTGRES ") == "PostgreSQL"


@pytest.mark.parametrize("skill", ["", " ", "   \t"])
def test_empty_input_is_safe(skill):
    assert normalize_skill(skill) == ""
