"""Deterministic and local screening implementations for ScreenCheck."""

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from src.factory.skill_normalizer import SKILL_ALIASES, normalize_skill


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


class KeywordScreener:
    name = "keyword"

    def score(self, resume_text: str, job: dict) -> dict:
        resume = _clean_text(resume_text)
        must_have = list(dict.fromkeys(job["must_have_skills"]))
        nice_have = list(dict.fromkeys(job["nice_to_have_skills"]))

        def match(skill: str) -> bool:
            canonical = normalize_skill(skill)
            names = {canonical.lower(), skill.lower()}
            for alias, target in SKILL_ALIASES.items():
                if target == canonical:
                    names.add(alias)
            if len(canonical) <= 3:
                return any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", resume) for name in names)
            return any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", resume) for name in names)

        matched_must = [skill for skill in must_have if match(skill)]
        matched_nice = [skill for skill in nice_have if match(skill)]
        missing = [skill for skill in must_have if skill not in matched_must]
        matched_weight = len(matched_must) * 2 + len(matched_nice)
        maximum_weight = len(must_have) * 2 + len(nice_have)
        score = 0.0 if maximum_weight == 0 else round(100 * matched_weight / maximum_weight, 2)

        return {
            "score": score,
            "matched_skills": matched_must + matched_nice,
            "missing_skills": missing,
            "matched_must_have": matched_must,
            "matched_nice_to_have": matched_nice,
            "explanation": (
                f"Matched {len(matched_must)} of {len(must_have)} must-have skills "
                f"and {len(matched_nice)} of {len(nice_have)} nice-to-have skills."
            ),
        }


class EmbeddingScreener:
    name = "embedding"
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model_name: str | None = None, cache_dir: str | Path | None = None):
        self.model_name = model_name or self.MODEL_NAME
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._model = None
        self._similarity_cache = {}

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def similarity(self, resume_text: str, job_text: str) -> float:
        import numpy as np

        cache_key = (resume_text, job_text)
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        model = self._load_model()
        embeddings = model.encode(
            [resume_text, job_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        dot = float(np.dot(embeddings[0], embeddings[1]))
        similarity = round(max(-1.0, min(1.0, dot)), 6)
        self._similarity_cache[cache_key] = similarity
        return similarity

    @staticmethod
    def scale_scores(similarities: list[float]) -> list[float]:
        if not similarities:
            return []
        minimum = min(similarities)
        maximum = max(similarities)
        if maximum == minimum:
            return [50.0] * len(similarities)
        return [
            round(100 * (value - minimum) / (maximum - minimum), 2)
            for value in similarities
        ]

    def score(self, resume_text: str, job: dict) -> dict:
        similarity = self.similarity(resume_text, job["original_job_description"])
        return {
            "similarity": similarity,
            "scaled_score": 50.0,
            "model": self.model_name,
        }


class LLMOutputError(RuntimeError):
    pass


class LLMJudge:
    name = "llm"

    def __init__(
        self,
        model: str | None = None,
        cache_path: str | Path | None = None,
        local_url: str | None = None,
        hosted_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model or os.getenv("SCREENCHECK_LLM_MODEL", "")
        self.cache_path = (
            Path(cache_path)
            if cache_path
            else Path("data/private/screeners/llm_cache.json")
        )
        self.local_url = local_url or os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        )
        self.hosted_url = hosted_url or os.getenv("OPENAI_BASE_URL")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.cache_path.exists():
            with self.cache_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w", encoding="utf-8") as file:
            json.dump(self.cache, file, indent=2)

    @staticmethod
    def build_prompt(resume_text: str, job: dict) -> str:
        return (
            "Evaluate this synthetic resume using only the evidence in the resume. "
            "Do not invent missing evidence.\n\n"
            "Return one valid JSON object only with these fields:\n"
            "- score: integer from 0 to 100\n"
            "- must_have_skill_evidence: integer from 0 to 40\n"
            "- project_relevance: integer from 0 to 30\n"
            "- relevant_experience: integer from 0 to 20\n"
            "- clarity: integer from 0 to 10\n"
            "- reason: short string\n\n"
            "Rubric: must-have evidence 40, project relevance 30, relevant experience "
            "20, clarity 10. The score must equal the sum of the four numeric components.\n\n"
            f"Job title: {job['job_title']}\n"
            f"Job description: {job['original_job_description']}\n"
            f"Must-have skills: {', '.join(job['must_have_skills'])}\n"
            f"Nice-to-have skills: {', '.join(job['nice_to_have_skills'])}\n\n"
            f"Resume:\n{resume_text}"
        )

    def _parse_json(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise LLMOutputError("LLM response was not valid JSON") from error

        required = (
            "score",
            "must_have_skill_evidence",
            "project_relevance",
            "relevant_experience",
            "clarity",
            "reason",
        )
        if not isinstance(result, dict) or any(key not in result for key in required):
            raise LLMOutputError("LLM JSON omitted required fields")
        if not isinstance(result["reason"], str):
            raise LLMOutputError("LLM reason must be a string")

        values = [
            result["must_have_skill_evidence"],
            result["project_relevance"],
            result["relevant_experience"],
            result["clarity"],
        ]
        limits = (40, 30, 20, 10)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise LLMOutputError("LLM rubric values must be integers")
        if any(value < 0 or value > limit for value, limit in zip(values, limits)):
            raise LLMOutputError("LLM rubric value is outside its allowed range")
        if result["score"] != sum(values):
            raise LLMOutputError("LLM score does not equal the rubric components")
        if isinstance(result["score"], bool) or not isinstance(result["score"], int):
            raise LLMOutputError("LLM score must be an integer")
        if not 0 <= result["score"] <= 100:
            raise LLMOutputError("LLM score is outside 0-100")
        return result

    def _call_model(self, prompt: str) -> str:
        if self.api_key and self.hosted_url:
            payload = {
                "model": self.model or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
            request = urllib.request.Request(
                self.hosted_url.rstrip("/") + "/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": "Bearer " + self.api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
        else:
            if not self.model:
                raise RuntimeError(
                    "No LLM configured. Set SCREENCHECK_LLM_MODEL for Ollama "
                    "or OPENAI_API_KEY and OPENAI_BASE_URL for a hosted model."
                )
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0},
            }
            request = urllib.request.Request(
                self.local_url.rstrip("/") + "/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise RuntimeError("LLM request failed: " + str(error)) from error

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        if "message" in data:
            return data["message"]["content"]
        raise LLMOutputError("LLM response did not contain message content")

    def score(self, resume_text: str, job: dict) -> dict:
        prompt = self.build_prompt(resume_text, job)
        model_name = self.model or ("hosted:" + str(self.hosted_url))
        cache_key = hashlib.sha256(
            (model_name + "\n" + prompt).encode("utf-8")
        ).hexdigest()
        if cache_key in self.cache:
            return {**self.cache[cache_key], "cache_hit": True}

        raw = self._call_model(prompt)
        result = self._parse_json(raw)
        result["model"] = model_name
        result["temperature"] = 0
        result["cache_hit"] = False
        self.cache[cache_key] = result
        self._save_cache()
        return result


def get_screener(name: str, **kwargs):
    """Return one of the three supported screener implementations."""
    screeners = {
        "keyword": KeywordScreener,
        "embedding": EmbeddingScreener,
        "llm": LLMJudge,
    }
    if name not in screeners:
        raise ValueError("unknown screener: " + name)
    return screeners[name](**kwargs)
