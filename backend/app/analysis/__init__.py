"""The AI lane's public surface. Nothing outside this package imports anything deeper.

Three call types, per invariant #2 in the root CLAUDE.md:

    parsed, raw                      = run_analysis(student, courses)
    project, raw                     = generate_project(role_title, one_liner, skills)
    review, total, max_total, passed = review_repo(project, bundle)

`run_analysis` is the name, not `run` (DECISIONS #40, closing #11). TDD 4.8 writes `run` and
the root CLAUDE.md writes `run_analysis`; Salman's `routers/analyze.py` resolves either at call
time, so exporting the one agreed name is enough and the ambiguity ends here.

Everything raises `AnalysisFailed` after one retry. `ProviderError` is a subclass, so a caller
that catches `AnalysisFailed` catches transport failures too and the router contract is
unchanged.
"""

from app.analysis import demo
from app.analysis.client import AnalysisFailed, ProviderError, complete_validated
from app.analysis.demo import load as load_demo
from app.analysis.demo import load_project as load_demo_project
from app.analysis.demo import load_review as load_demo_review
from app.analysis.project import ProjectOut, SkillState, generate_project
from app.analysis.prompt import build_prompt
from app.analysis.review import ReviewOut, review_repo
from app.analysis.schema import AnalysisOut

__all__ = [
    "run_analysis",
    "generate_project",
    "review_repo",
    "build_prompt",
    "load_demo",
    "load_demo_project",
    "load_demo_review",
    "AnalysisOut",
    "ProjectOut",
    "SkillState",
    "ReviewOut",
    "AnalysisFailed",
    "ProviderError",
]


def run_analysis(student, courses, *, client=None) -> tuple[AnalysisOut, str]:
    """The one analysis call. Returns `(validated AnalysisOut, raw JSON text)`.

    `raw` is returned alongside the parsed object because it is what gets stored in
    `Analysis.raw_json` and what gets committed as `contracts/fixtures/demo_analysis.json` --
    re-serialising the parsed model would silently reorder keys and lose the exact bytes the
    model produced.

    Temperature 0.3: low enough that two runs on the same student are broadly comparable while
    tuning, high enough that role selection is not degenerate.

    `client` is injected only by tests and the CLI. In the app it is `None` and the configured
    provider is used.

    DEMO_MODE is handled here rather than in Salman's router, per TDD 4.8: `analyze.py` is
    thin and every decision about prompts, retries and caching belongs to this package. The
    gate is DEMO_MODE **and** the student's name -- never DEMO_MODE alone -- so any other
    student still gets a real call and judges can try their own input (DECISIONS #7).
    """
    if demo.applies(student):
        return demo.load()

    return complete_validated(
        AnalysisOut,
        build_prompt(student, courses),
        client=client,
        temperature=0.3,
    )
