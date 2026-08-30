"""`ProjectOut`, the `verifies` cross-check, and the project prompt mirror.

Governing docs: CONTRACT §1b · PRD §8.2 · TDD §4.12 · `ai-working/prompts/project.md`.

Nothing here touches the network. `generate_project` is driven through a scripted `LLMClient`,
the same seam `test_client.py` uses, so this suite costs nothing, needs no key and passes
offline. The live path is `scripts/run_project_cli.py` (TDD §12).
"""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.analysis.client import AnalysisFailed
from app.analysis.project import (
    PROJECT_MAX_TOKENS,
    PROJECT_PROMPT,
    PROJECT_RETRY_MAX_TOKENS,
    PROJECT_TEMPERATURE,
    ProjectOut,
    SkillState,
    build_project_prompt,
    generate_project,
)

CANONICAL = Path(__file__).resolve().parents[2] / "ai-working" / "prompts" / "project.md"

PLACEHOLDERS = ["{role_title}", "{one_liner}", "{skill_lines}"]

STATES = [
    SkillState(slug="etl-pipelines", name="ETL Pipelines", weight="core", state="missing"),
    SkillState(
        slug="sql-query-optimization",
        name="SQL Query Optimization",
        weight="core",
        state="ticked",
    ),
    SkillState(
        slug="containerization",
        name="Containerization",
        weight="supporting",
        state="covered:partial",
    ),
    SkillState(slug="unit-testing", name="Unit Testing", weight="supporting", state="verified"),
]

ROLE_TITLE = "Data Engineer"
ONE_LINER = "Builds the pipelines that move and reshape a company's data."

GOOD: dict[str, Any] = {
    "title": "Build a log-ingestion pipeline with replay",
    "spec": (
        "Ingest newline-delimited log files, normalise them, and store them so they can be "
        "queried. Done when one command replays a day of logs and a query returns yesterday's "
        "errors."
    ),
    "criteria": [
        "Ingestion and storage are separate modules with a defined interface between them.",
        "The README documents the replay procedure, including how duplicates are handled.",
        "Malformed lines are handled explicitly rather than crashing the run.",
    ],
    "verifies": ["etl-pipelines", "sql-query-optimization"],
}


def payload(**overrides: Any) -> dict[str, Any]:
    """A valid ProjectOut dict with targeted damage. Never mutates GOOD."""
    return {**GOOD, **overrides}


class FakeClient:
    """Scripted LLMClient. Each entry is (raw, finish_reason) or an Exception to raise."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.budgets: list[int] = []
        self.temperatures: list[float] = []

    def complete_json(self, prompt, schema, *, max_tokens, temperature):
        self.prompts.append(prompt)
        self.budgets.append(max_tokens)
        self.temperatures.append(temperature)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def calls(self) -> int:
        return len(self.prompts)


def ok(**overrides: Any) -> tuple[str, str]:
    return json.dumps(payload(**overrides)), "stop"


# --------------------------------------------------------------------------- the prompt mirror


def test_the_mirrored_prompt_matches_the_canonical_markdown() -> None:
    """If this fails, someone edited one copy. The .md is the source; update project.py from it."""
    block = re.search(r"```text\n(.*?)\n```", CANONICAL.read_text(encoding="utf-8"), re.S)
    assert block, f"no ```text block in {CANONICAL}"
    assert PROJECT_PROMPT == block.group(1), (
        "project.py has drifted from ai-working/prompts/project.md -- "
        "edit the .md first, then regenerate the constant"
    )


def test_the_template_still_has_every_placeholder() -> None:
    for token in PLACEHOLDERS:
        assert token in PROJECT_PROMPT, f"{token} vanished from the template"


@pytest.mark.parametrize("token", PLACEHOLDERS)
def test_no_placeholder_survives_rendering(token: str) -> None:
    """An unsubstituted token would be sent to the model verbatim and quietly degrade output."""
    assert token not in build_project_prompt(ROLE_TITLE, ONE_LINER, STATES)


def test_every_skill_reaches_the_prompt_with_all_four_of_its_fields() -> None:
    """The state labels are the whole reason this call is separate from the analysis."""
    rendered = build_project_prompt(ROLE_TITLE, ONE_LINER, STATES)
    assert ROLE_TITLE in rendered and ONE_LINER in rendered
    for state in STATES:
        line = next(
            (ln for ln in rendered.splitlines() if ln.startswith(state.slug)), ""
        )
        assert line, f"{state.slug} is missing from the rendered prompt"
        for field in (state.slug, state.name, state.weight, state.state):
            assert field in line, f"{field} missing from the line for {state.slug}"


# ------------------------------------------------------------------- the SkillState field names


def test_skill_state_field_names_match_the_copy_in_salmans_router() -> None:
    """DECISIONS #33: `SkillState` is duplicated, not imported, and matched by field NAME only.

    Renaming a field on either side breaks his caller at runtime with no other test failing --
    `skill_states_for_role` builds his dataclass and `generate_project` reads mine. This is the
    one test that turns that silent break into a loud one, so it compares the real classes
    rather than a remembered list, and pins the literal names as well in case both drift
    together.
    """
    from app.routers.project import SkillState as TheirSkillState

    ours = [f.name for f in fields(SkillState)]
    theirs = [f.name for f in fields(TheirSkillState)]
    assert ours == theirs, (
        f"SkillState drifted: app.analysis.project has {ours}, "
        f"app.routers.project has {theirs} -- this breaks GET /api/project silently"
    )
    assert ours == ["slug", "name", "weight", "state"]


# ------------------------------------------------------------------------- ProjectOut validators


def test_a_good_project_validates() -> None:
    """Without this, every rejection below could be `reject everything` and still pass."""
    project = ProjectOut.model_validate(GOOD)
    assert project.verifies == ["etl-pipelines", "sql-query-optimization"]
    assert len(project.criteria) == 3


@pytest.mark.parametrize("n", [2, 5])
def test_criteria_must_be_three_or_four(n: int) -> None:
    criteria = [f"Criterion number {i} is checkable by reading." for i in range(n)]
    with pytest.raises(ValidationError, match="criteria"):
        ProjectOut.model_validate(payload(criteria=criteria))


@pytest.mark.parametrize("n", [1, 5])
def test_verifies_must_be_two_to_four(n: int) -> None:
    with pytest.raises(ValidationError, match="verifies"):
        ProjectOut.model_validate(payload(verifies=[f"skill-{i}" for i in range(n)]))


def test_duplicate_verifies_are_rejected() -> None:
    """Two identical slugs resolve to one id, so the project claims to verify more than it does."""
    with pytest.raises(ValidationError, match="verifies"):
        ProjectOut.model_validate(payload(verifies=["etl-pipelines", "etl-pipelines"]))


def test_duplicate_criteria_are_rejected() -> None:
    """A repeated criterion is scored twice, quietly doubling its weight in the total."""
    with pytest.raises(ValidationError, match="criteri"):
        ProjectOut.model_validate(
            payload(criteria=[GOOD["criteria"][0], GOOD["criteria"][0], GOOD["criteria"][1]])
        )


@pytest.mark.parametrize("field", ["title", "spec"])
def test_a_blank_title_or_spec_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        ProjectOut.model_validate(payload(**{field: "   "}))


def test_a_blank_criterion_is_rejected() -> None:
    """An empty criterion still counts toward max_total, so it lowers every score silently."""
    with pytest.raises(ValidationError, match="criteri"):
        ProjectOut.model_validate(payload(criteria=[GOOD["criteria"][0], "  ", "Has a README."]))


# ------------------------------------------------------------- generate_project + the cross-check


def test_generate_project_returns_the_parsed_model_and_the_raw_text() -> None:
    raw_text, _ = ok()
    client = FakeClient((raw_text, "stop"))
    project, raw = generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)

    assert isinstance(project, ProjectOut)
    assert raw == raw_text, "raw must be the model's exact bytes, not a re-serialisation"
    assert client.calls == 1


def test_generate_project_uses_the_project_budget_and_temperature() -> None:
    client = FakeClient(ok())
    generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)
    assert client.budgets == [PROJECT_MAX_TOKENS]
    assert client.temperatures == [PROJECT_TEMPERATURE]


def test_a_slug_outside_the_role_is_rejected_and_retried() -> None:
    """The grammar cannot express set membership (CONTRACT §1b, DECISIONS #35).

    A `Project` row whose verifies resolve to nothing verifies nothing forever, silently, so
    this must trigger the retry rather than reach the caller. Salman 502s it independently.
    """
    client = FakeClient(
        ok(verifies=["etl-pipelines", "not-in-this-role"]),
        ok(),
    )
    project, _ = generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)

    assert client.calls == 2, "the bad payload must be retried, not returned"
    assert set(project.verifies) <= {s.slug for s in STATES}


def test_a_slug_outside_the_role_twice_fails_the_call() -> None:
    client = FakeClient(
        ok(verifies=["etl-pipelines", "not-in-this-role"]),
        ok(verifies=["still-not-in-this-role", "etl-pipelines"]),
    )
    with pytest.raises(AnalysisFailed, match="not-in-this-role|still-not-in-this-role"):
        generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)
    assert client.calls == 2, "exactly two attempts, ever"


def test_truncation_retries_with_the_larger_budget() -> None:
    client = FakeClient(("{", "max_tokens"), ok())
    generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)
    assert client.budgets == [PROJECT_MAX_TOKENS, PROJECT_RETRY_MAX_TOKENS]


def test_the_role_slugs_are_the_only_allowed_vocabulary() -> None:
    """Case and whitespace are not normalised away: `ETL-Pipelines` is not `etl-pipelines`.

    Salman resolves slugs by exact dictionary lookup, so a near-miss 502s. Rejecting it here
    buys a retry that might come back right.
    """
    client = FakeClient(ok(verifies=["ETL-Pipelines", "unit-testing"]), ok())
    project, _ = generate_project(ROLE_TITLE, ONE_LINER, STATES, client=client)
    assert client.calls == 2
    assert project.verifies == GOOD["verifies"]
