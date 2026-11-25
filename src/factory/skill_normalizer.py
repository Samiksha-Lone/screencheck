"""Small utility for normalizing skill names."""


SKILL_ALIASES = {
    "js": "JavaScript",
    "java script": "JavaScript",
    "javascript": "JavaScript",
    "aws": "AWS",
    "sql": "SQL",
    "typescript": "TypeScript",
    "power bi": "Power BI",
    "git": "Git",
    "python": "Python",
    "java": "Java",
    "docker": "Docker",
    "redis": "Redis",
    "kubernetes": "Kubernetes",
    "tableau": "Tableau",
    "excel": "Excel",
    "data analysis": "Data Analysis",
    "data visualization": "Data Visualization",
    "statistics": "Statistics",
    "node": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "restful services": "REST APIs",
    "rest apis": "REST APIs",
    "react js": "React",
    "react": "React",
    "express js": "Express.js",
    "express.js": "Express.js",
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name, or capitalize an unknown skill consistently."""
    if not isinstance(skill, str):
        raise TypeError("skill must be a string")

    clean_skill = " ".join(skill.strip().split())
    if not clean_skill:
        return ""

    key = " ".join(clean_skill.lower().split())
    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]

    return clean_skill.title()
