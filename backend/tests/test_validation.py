"""AnalysisOut's semantic validators (docs/TDD.md §4.5, CONTRACT.md §1.1).

Structured outputs guarantee the shape; these rules are what the grammar cannot express, and
every one of them corresponds to a way the roadmap breaks silently — a role referencing a
skill that does not exist means a card whose fit % is computed from nothing.

app/analysis/schema.py is Dev B's lane. Until it lands this module skips; the moment it
appears these assertions start running with no edit here.
"""

import copy
from typing import Any

import pytest

schema = pytest.importorskip(
    "app.analysis.schema",
    reason="app/analysis/schema.py is Dev B's lane and is not written yet",
)
# The file exists but is empty until Dev B fills it, so importing is not enough of a check.
AnalysisOut = getattr(schema, "AnalysisOut", None)
if AnalysisOut is None:
    pytest.skip(
        "app/analysis/schema.py does not define AnalysisOut yet (Dev B's lane)",
        allow_module_level=True,
    )

N_SKILLS = 40
CODES = ("CS201", "CS301", "CS401", "CS402")


def valid_payload(n_skills: int = N_SKILLS) -> dict[str, Any]:
    """A payload that breaks exactly one rule at a time — every other rule stays satisfied,
    including 8-16 skills per role, so a rejection can only come from the rule under test.
    """
    return {
        "skills": [
            {"id": f"skill-{i:02d}", "name": f"Skill {i:02d}", "real_world": f"Matters when {i}."}
            for i in range(n_skills)
        ],
        "coverage": [
            {"skill_id": f"skill-{i:02d}", "course_code": CODES[i % 4], "depth": "full" if i % 3 else "partial"}
            for i in range(12)
        ],
        "roles": [
            {
                "id": f"role-{r}",
                "title": f"Role {r}",
                "one_liner": f"Does the {r} work.",
                "proximity": "adjacent" if r >= 6 else "core",
                "bridge": "Your coursework converges here." if r >= 6 else "",
                "rank": r + 1,
                "skills": [
                    {"skill_id": f"skill-{(r * 5 + k) % n_skills:02d}", "weight": "core" if k < 5 else "supporting"}
                    for k in range(11)
                ],
            }
            for r in range(8)
        ],
    }


def rejects(payload: dict[str, Any]) -> str:
    with pytest.raises(Exception) as caught:      # ValidationError, whatever pydantic raises
        AnalysisOut.model_validate(payload)
    return str(caught.value)


def test_the_baseline_payload_is_valid() -> None:
    parsed = AnalysisOut.model_validate(valid_payload())
    assert len(parsed.skills) == N_SKILLS
    assert len(parsed.roles) == 8
    assert sum(r.proximity == "core" for r in parsed.roles) == 6


# V1 — skills


def test_rejects_too_few_skills() -> None:
    assert "34" in rejects(valid_payload(n_skills=34))


def test_rejects_too_many_skills() -> None:
    assert "71" in rejects(valid_payload(n_skills=71))


def test_rejects_duplicate_skill_ids() -> None:
    p = valid_payload()
    p["skills"][1] = copy.deepcopy(p["skills"][0])
    assert "duplicate" in rejects(p).lower()


def test_rejects_a_non_kebab_case_skill_id() -> None:
    p = valid_payload()
    p["skills"][0]["id"] = "SQL Query Optimization"
    p["roles"] = [
        {**r, "skills": [s for s in r["skills"] if s["skill_id"] != "skill-00"]} for r in p["roles"]
    ]
    p["coverage"] = [c for c in p["coverage"] if c["skill_id"] != "skill-00"]
    assert rejects(p)


# V2 — roles


@pytest.mark.parametrize("n", [7, 9])
def test_rejects_the_wrong_number_of_roles(n: int) -> None:
    p = valid_payload()
    roles = p["roles"]
    p["roles"] = roles[:n] if n < 8 else roles + [{**copy.deepcopy(roles[0]), "id": "role-8", "rank": 9}]
    assert str(n) in rejects(p)


@pytest.mark.parametrize("n_core", [4, 7])
def test_rejects_the_wrong_number_of_core_roles(n_core: int) -> None:
    p = valid_payload()
    for i, role in enumerate(p["roles"]):
        core = i < n_core
        role["proximity"] = "core" if core else "adjacent"
        role["bridge"] = "" if core else "Your coursework converges here."
    assert str(n_core) in rejects(p)


# V3 / V4 — dangling references


def test_rejects_a_role_referencing_an_unknown_skill() -> None:
    p = valid_payload()
    p["roles"][2]["skills"][0]["skill_id"] = "skill-does-not-exist"
    assert "skill-does-not-exist" in rejects(p)


def test_rejects_coverage_referencing_an_unknown_skill() -> None:
    p = valid_payload()
    p["coverage"][0]["skill_id"] = "skill-does-not-exist"
    assert "skill-does-not-exist" in rejects(p)


# V5 — role membership


def test_rejects_a_skill_repeated_within_one_role() -> None:
    p = valid_payload()
    p["roles"][0]["skills"][1]["skill_id"] = p["roles"][0]["skills"][0]["skill_id"]
    assert rejects(p)


@pytest.mark.parametrize("n", [7, 17])
def test_rejects_a_role_with_the_wrong_number_of_skills(n: int) -> None:
    p = valid_payload()
    p["roles"][0]["skills"] = [
        {"skill_id": f"skill-{i:02d}", "weight": "core" if i < 5 else "supporting"} for i in range(n)
    ]
    assert str(n) in rejects(p)


# V6 — adjacent roles


@pytest.mark.parametrize("bridge", ["", "   "])
def test_rejects_an_adjacent_role_without_a_bridge(bridge: str) -> None:
    p = valid_payload()
    p["roles"][6]["bridge"] = bridge
    assert "bridge" in rejects(p)


# Soft rules — CONTRACT.md §1.1 "Soft (warn + skip)".
#
# These two must NOT raise. persist_analysis drops them with a log warning (TDD §4.9), because
# a soft data-quality issue is the wrong thing to fail a live analysis over. Hardening either
# one into a hard failure would turn a shrug into a 502 in front of a judge, and nothing else
# in the suite would notice — hence these.


def test_tolerates_a_coverage_row_with_an_unknown_course_code() -> None:
    p = valid_payload()
    p["coverage"][0]["course_code"] = "CS999"
    parsed = AnalysisOut.model_validate(p)
    assert parsed.coverage[0].course_code == "CS999"


def test_tolerates_a_duplicate_skill_course_coverage_pair() -> None:
    p = valid_payload()
    p["coverage"].append(copy.deepcopy(p["coverage"][0]))
    parsed = AnalysisOut.model_validate(p)
    assert len(parsed.coverage) == len(p["coverage"])
