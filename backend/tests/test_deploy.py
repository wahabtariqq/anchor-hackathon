"""The deploy config and the readiness probe.

These exist because the deployment failure this project is most exposed to is silent:
`contracts/fixtures/` lives *outside* `backend/`, so a host configured with a root directory
of `backend/` builds green, serves /health green, and fails only when the demo runs. Each
check below turns one variant of that into a test failure.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analysis.demo import FIXTURE as DEMO_ANALYSIS_FIXTURE
from app.readiness import (
    DEMO_FIXTURES,
    FIXTURES_DIR,
    is_configured,
    missing_demo_fixtures,
    readiness,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = {name: ROOT / name for name in ("Procfile", "render.yaml", "nixpacks.toml", "runtime.txt")}


# ---- the path duplication, pinned ----


def test_readiness_and_the_ai_lane_agree_on_where_fixtures_live() -> None:
    """readiness.py counts parents from app/, demo.py from app/analysis/. If either module
    moves, this fails here rather than at pitch time."""
    assert FIXTURES_DIR == DEMO_ANALYSIS_FIXTURE.parent


def test_the_fixtures_directory_is_outside_backend() -> None:
    # the whole reason the deploy has to be rooted at the repo root
    assert not FIXTURES_DIR.is_relative_to(ROOT / "backend")
    assert FIXTURES_DIR == ROOT / "contracts" / "fixtures"


def test_every_demo_fixture_is_present_and_not_a_placeholder() -> None:
    assert missing_demo_fixtures() == []
    for name in DEMO_FIXTURES:
        body = (FIXTURES_DIR / name).read_text(encoding="utf-8")
        assert "_todo" not in body, f"{name} is still the placeholder"


# ---- deploy config ----


@pytest.mark.parametrize("name", list(CONFIGS))
def test_deploy_config_exists(name: str) -> None:
    assert CONFIGS[name].is_file(), f"{name} missing — TDD §10 wants the API deployable"


@pytest.mark.parametrize("name", ["Procfile", "render.yaml", "nixpacks.toml"])
def test_start_command_runs_from_backend_with_the_root_intact(name: str) -> None:
    """`cd backend && uvicorn ...` — not a root directory of backend/, which would leave
    contracts/fixtures/ off the disk."""
    body = CONFIGS[name].read_text(encoding="utf-8")
    assert "cd backend" in body
    assert "uvicorn app.main:app" in body
    assert "--host 0.0.0.0" in body


def test_render_installs_requirements_from_backend() -> None:
    body = CONFIGS["render.yaml"].read_text(encoding="utf-8")
    assert "pip install -r backend/requirements.txt" in body
    assert "healthCheckPath: /health" in body


def test_runtime_pins_python_312() -> None:
    assert CONFIGS["runtime.txt"].read_text(encoding="utf-8").strip().startswith("python-3.12")


# ---- the probe itself ----


def test_readiness_reports_the_deploy_critical_flags() -> None:
    body = readiness()
    assert body["ok"] is True
    for key in (
        "database", "demo_mode", "demo_fixtures_present", "missing_demo_fixtures",
        "demo_repo_url_set", "llm_key_set", "github_token_set", "cors_origins",
    ):
        assert key in body, f"/health lost {key}, which the smoke test reads"
    assert body["demo_fixtures_present"] is True


@pytest.mark.parametrize("value", ["", "   ", "sk-ant-...", "ghp_...", "<pw>", "AIza...",
                                   "https://github.com/<you>/anchor-demo-project"])
def test_placeholders_do_not_count_as_configured(value: str) -> None:
    """.env.example ships these verbatim; copying it must not turn the probe green."""
    assert is_configured(value) is False


@pytest.mark.parametrize("value", ["AIzaSyReal", "ghp_realtoken", "https://github.com/o/r"])
def test_real_values_count_as_configured(value: str) -> None:
    assert is_configured(value) is True


def test_copying_env_example_does_not_fake_a_ready_deploy(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import readiness as module

    monkeypatch.setattr(module.settings, "GEMINI_API_KEY", "", raising=False)
    monkeypatch.setattr(module.settings, "ANTHROPIC_API_KEY", "sk-ant-...", raising=False)
    monkeypatch.setattr(module.settings, "GITHUB_TOKEN", "ghp_...", raising=False)
    body = readiness()
    assert body["llm_key_set"] is False
    assert body["github_token_set"] is False


def test_readiness_never_leaks_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import readiness as module

    monkeypatch.setattr(module.settings, "GITHUB_TOKEN", "ghp_supersecret", raising=False)
    monkeypatch.setattr(module.settings, "GEMINI_API_KEY", "AIza_supersecret", raising=False)
    body = readiness()
    assert body["github_token_set"] is True and body["llm_key_set"] is True
    assert "supersecret" not in repr(body)


def test_health_endpoint_serves_the_probe(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["demo_fixtures_present"] is True
