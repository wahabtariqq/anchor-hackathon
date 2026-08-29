"""build_prompt, and the guard that stops the mirrored prompt text from rotting.

The canonical prompt lives in ai-working/prompts/analysis.md; app/analysis/prompt.py mirrors it
in a constant so the deployed backend has no runtime dependency on a docs directory outside
backend/. A mirror nobody checks is a mirror that drifts, so the first test here is the whole
reason the mirror is safe.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.analysis import run_analysis
from app.analysis.prompt import ANALYSIS_PROMPT, build_prompt, render_courses
from app.analysis.schema import AnalysisOut
from tests.test_validation import valid_payload

CANONICAL = Path(__file__).resolve().parents[2] / "ai-working" / "prompts" / "analysis.md"

PLACEHOLDERS = ["{semester}", "{interests}", "{courses}", "{course_codes}", "{postings_block}"]


def student(semester: int = 4, interests: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(semester=semester, interests=interests or ["Databases", "Security"])


def course(code: str, name: str, text: str, tag: str = "past") -> SimpleNamespace:
    return SimpleNamespace(code=code, name=name, curriculum_text=text, semester_tag=tag)


COURSES = [
    course("CS201", "Data Structures", "Arrays, trees, graphs."),
    course("CUSTOM-1", "Human-Computer Interaction", "Wireframing, usability.", "current"),
]


def test_the_mirrored_prompt_matches_the_canonical_markdown() -> None:
    """If this fails, someone edited one copy. The .md is the source; update prompt.py from it."""
    block = re.search(r"```text\n(.*?)\n```", CANONICAL.read_text(encoding="utf-8"), re.S)
    assert block, f"no ```text block in {CANONICAL}"
    assert ANALYSIS_PROMPT == block.group(1), (
        "prompt.py has drifted from ai-working/prompts/analysis.md -- "
        "edit the .md first, then regenerate the constant"
    )


def test_the_template_still_has_every_placeholder() -> None:
    for token in PLACEHOLDERS:
        assert token in ANALYSIS_PROMPT, f"{token} vanished from the template"


@pytest.mark.parametrize("token", PLACEHOLDERS)
def test_no_placeholder_survives_rendering(token: str) -> None:
    """An unsubstituted token would be sent to the model verbatim and quietly degrade output."""
    assert token not in build_prompt(student(), COURSES)


def test_student_facts_reach_the_prompt() -> None:
    rendered = build_prompt(student(semester=6, interests=["Databases", "Mobile"]), COURSES)
    assert "Semester: 6" in rendered
    assert "Databases, Mobile" in rendered


def test_course_codes_include_custom_courses() -> None:
    """CUSTOM-1 is a real code the server assigns; coverage rows are validated against it."""
    rendered = build_prompt(student(), COURSES)
    assert "CS201, CUSTOM-1" in rendered


def test_courses_render_with_code_name_tag_and_syllabus() -> None:
    rendered = render_courses(COURSES)
    assert "CS201 - Data Structures (past)" in rendered
    assert "Arrays, trees, graphs." in rendered
    assert "CUSTOM-1 - Human-Computer Interaction (current)" in rendered


def test_postings_block_is_empty_unless_supplied() -> None:
    """PRD 8.6: the seed set is out unless it is in the prompt from the start of Day-2 tuning."""
    assert "GROUNDING" not in build_prompt(student(), COURSES).upper()
    with_block = build_prompt(student(), COURSES, postings_block="\n\n## Grounding\nexcerpt")
    assert with_block.rstrip().endswith("excerpt")


def test_run_analysis_returns_parsed_and_raw_without_touching_the_network() -> None:
    """The seam Salman's routers/analyze.py calls: run(student, courses) -> (parsed, raw)."""
    import json

    payload = json.dumps(valid_payload())

    class Fake:
        def __init__(self) -> None:
            self.prompt = ""

        def complete_json(self, prompt, schema, *, max_tokens, temperature):
            self.prompt = prompt
            return payload, "stop"

    fake = Fake()
    parsed, raw = run_analysis(student(), COURSES, client=fake)

    assert isinstance(parsed, AnalysisOut)
    assert raw == payload, "raw must be the model's exact bytes, not a re-serialisation"
    assert "Semester: 4" in fake.prompt, "the rendered prompt is what reaches the client"
