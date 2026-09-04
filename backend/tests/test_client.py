"""The provider seam: schema transform, retry policy, and the Gemini REST client.

Nothing here touches the network. Every model call is a fake or an httpx MockTransport, so the
suite costs nothing, needs no key, burns no free-tier quota, and passes offline. The live
integration path is scripts/run_*_cli.py, which is what those exist for (TDD 12).
"""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
import pytest
from pydantic import BaseModel

import app.analysis.client as client_module
from app.analysis.client import (
    AnalysisFailed,
    GeminiClient,
    ProviderError,
    complete_validated,
    transform_schema,
)
from app.analysis.schema import AnalysisOut


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------


def walk_keys(node: Any):
    """Every schema-level key in the tree (property NAMES are not yielded)."""
    if isinstance(node, list):
        for n in node:
            yield from walk_keys(n)
    elif isinstance(node, dict):
        for k, v in node.items():
            yield k
            if k == "properties" and isinstance(v, dict):
                for sub in v.values():
                    yield from walk_keys(sub)
            else:
                yield from walk_keys(v)


def objects_with_properties(node: Any):
    """Every subschema that declares `properties`."""
    if isinstance(node, list):
        for n in node:
            yield from objects_with_properties(n)
    elif isinstance(node, dict):
        if "properties" in node:
            yield node
        for v in node.values():
            yield from objects_with_properties(v)


class Tiny(BaseModel):
    value: int


class Single(BaseModel):
    only: Literal["one"]


class FakeClient:
    """Scripted LLMClient. Each entry is (raw, finish_reason) or an Exception to raise."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.budgets: list[int] = []

    def complete_json(self, prompt, schema, *, max_tokens, temperature):
        self.budgets.append(max_tokens)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def calls(self) -> int:
        return len(self.budgets)


# ---------------------------------------------------------------------------------------
# transform_schema
# ---------------------------------------------------------------------------------------

SCHEMA = transform_schema(AnalysisOut.model_json_schema())


def test_refs_are_inlined() -> None:
    keys = set(walk_keys(SCHEMA))
    assert "$ref" not in keys and "$defs" not in keys


@pytest.mark.parametrize(
    "keyword", ["pattern", "minLength", "maxLength", "minItems", "maxItems", "additionalProperties"]
)
def test_unsupported_keywords_are_stripped(keyword: str) -> None:
    assert keyword not in set(walk_keys(SCHEMA))


def test_the_field_named_title_survives() -> None:
    """Regression for DECISIONS #47.

    `title` is both a JSON-Schema annotation and a real field on RoleOut. Filtering keys by
    name deleted the field from `properties` while leaving it in `required`, and Gemini
    rejected the whole request with "required[1]: property is not defined".
    """
    role = SCHEMA["properties"]["roles"]["items"]
    assert "title" in role["properties"], "RoleOut.title was stripped as if it were an annotation"
    assert role["properties"]["title"]["type"] == "string"


def test_every_required_name_exists_in_properties() -> None:
    """The invariant that would have caught #47 anywhere in the tree, not just on RoleOut."""
    for obj in objects_with_properties(SCHEMA):
        missing = set(obj.get("required", [])) - set(obj["properties"])
        assert not missing, f"required names with no property: {sorted(missing)}"


def test_required_is_preserved() -> None:
    assert set(SCHEMA["required"]) == {"skills", "coverage", "roles"}
    role = SCHEMA["properties"]["roles"]["items"]
    assert "bridge" in role["required"] and "proximity" in role["required"]


def test_literals_survive_as_enums() -> None:
    depth = SCHEMA["properties"]["coverage"]["items"]["properties"]["depth"]
    assert set(depth["enum"]) == {"full", "partial"}


def test_single_value_literal_becomes_a_one_item_enum() -> None:
    """Pydantic emits `const` for a one-value Literal; Gemini only understands `enum`."""
    out = transform_schema(Single.model_json_schema())
    assert out["properties"]["only"]["enum"] == ["one"]
    assert "const" not in set(walk_keys(out))


def test_nested_arrays_of_objects_are_preserved() -> None:
    role_skills = SCHEMA["properties"]["roles"]["items"]["properties"]["skills"]
    assert role_skills["type"] == "array"
    assert set(role_skills["items"]["properties"]) == {"skill_id", "weight"}


# ---------------------------------------------------------------------------------------
# complete_validated -- the retry policy
# ---------------------------------------------------------------------------------------

GOOD = ('{"value": 1}', "stop")
BAD_JSON = ("not json at all", "stop")
WRONG_TYPE = ('{"value": "not-an-int"}', "stop")


def test_first_attempt_success_makes_exactly_one_call() -> None:
    fake = FakeClient(GOOD)
    parsed, raw = complete_validated(Tiny, "p", client=fake)
    assert parsed.value == 1 and raw == GOOD[0]
    assert fake.calls == 1


def test_validation_failure_retries_once_then_succeeds() -> None:
    fake = FakeClient(WRONG_TYPE, GOOD)
    parsed, _ = complete_validated(Tiny, "p", client=fake)
    assert parsed.value == 1
    assert fake.calls == 2


def test_two_validation_failures_raise_and_stop_at_two_attempts() -> None:
    """A third attempt would triple the worst-case latency of an already slow call."""
    fake = FakeClient(BAD_JSON, WRONG_TYPE, GOOD)   # a third good response is queued
    with pytest.raises(AnalysisFailed) as caught:
        complete_validated(Tiny, "p", client=fake)
    assert fake.calls == 2, "must not reach the third response"
    assert "2 attempts" in str(caught.value)


def test_truncation_retries_with_the_larger_budget() -> None:
    fake = FakeClient(("{partial", "max_tokens"), GOOD)
    parsed, _ = complete_validated(
        Tiny, "p", client=fake, max_tokens=16000, retry_max_tokens=24000
    )
    assert parsed.value == 1
    assert fake.budgets == [16000, 24000], "second attempt must use the retry budget"


def test_truncation_twice_raises_and_names_truncation() -> None:
    fake = FakeClient(("{a", "max_tokens"), ("{b", "max_tokens"))
    with pytest.raises(AnalysisFailed) as caught:
        complete_validated(Tiny, "p", client=fake, max_tokens=16000, retry_max_tokens=24000)
    assert "truncated" in str(caught.value)


def test_provider_error_is_retried() -> None:
    """The free tier really does return 503 under load -- measured during S0."""
    fake = FakeClient(ProviderError("503 high demand"), GOOD)
    parsed, _ = complete_validated(Tiny, "p", client=fake)
    assert parsed.value == 1 and fake.calls == 2


def test_two_provider_errors_raise() -> None:
    fake = FakeClient(ProviderError("503 a"), ProviderError("503 b"))
    with pytest.raises(AnalysisFailed) as caught:
        complete_validated(Tiny, "p", client=fake)
    assert "503 b" in str(caught.value), "the LAST error should be reported"


def test_a_provider_error_waits_before_retrying(monkeypatch: pytest.MonkeyPatch) -> None:
    """503 means the provider is shedding load. Retrying in the same instant re-enters the
    window that just refused us -- measured live: an immediate retry failed 2 of 4 review
    calls, and the same key succeeded first try once a wait was introduced."""
    slept: list[float] = []
    monkeypatch.setattr(client_module, "PROVIDER_RETRY_BACKOFF_SECONDS", 5.0)
    monkeypatch.setattr(client_module.time, "sleep", lambda s: slept.append(s))

    fake = FakeClient(ProviderError("503 high demand"), GOOD)
    parsed, _ = complete_validated(Tiny, "p", client=fake)

    assert parsed.value == 1 and fake.calls == 2
    assert slept == [5.0], "exactly one pause, between the two attempts"


def test_only_a_provider_error_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Truncation and validation are deterministic faults of the prompt. Waiting on those
    would add latency to a call the student is watching, and fix nothing."""
    slept: list[float] = []
    monkeypatch.setattr(client_module, "PROVIDER_RETRY_BACKOFF_SECONDS", 5.0)
    monkeypatch.setattr(client_module.time, "sleep", lambda s: slept.append(s))

    truncated = FakeClient(("{a", "max_tokens"), GOOD)
    complete_validated(Tiny, "p", client=truncated, max_tokens=16000, retry_max_tokens=24000)
    assert slept == [], "a truncation retry must not pause"

    invalid = FakeClient(('{"value": "not-an-int"}', "stop"), GOOD)
    complete_validated(Tiny, "p", client=invalid)
    assert slept == [], "a validation retry must not pause"


def test_the_second_provider_error_does_not_wait_for_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """There is no third attempt, so pausing after the last one would delay the 502 the
    student is already waiting on."""
    slept: list[float] = []
    monkeypatch.setattr(client_module, "PROVIDER_RETRY_BACKOFF_SECONDS", 5.0)
    monkeypatch.setattr(client_module.time, "sleep", lambda s: slept.append(s))

    fake = FakeClient(ProviderError("503 a"), ProviderError("503 b"))
    with pytest.raises(AnalysisFailed):
        complete_validated(Tiny, "p", client=fake)

    assert slept == [5.0], "one pause total, not one per failure"


def test_cross_check_rejection_triggers_the_retry() -> None:
    """verifies-subset and criteria-echo are not expressible in a schema, so they retry here."""
    seen: list[int] = []

    def reject_ones(parsed: Tiny) -> None:
        seen.append(parsed.value)
        if parsed.value == 1:
            raise ValueError("value 1 is not allowed")

    fake = FakeClient(GOOD, ('{"value": 2}', "stop"))
    parsed, _ = complete_validated(Tiny, "p", client=fake, cross_check=reject_ones)
    assert parsed.value == 2 and seen == [1, 2] and fake.calls == 2


def test_cross_check_failing_twice_raises() -> None:
    def always_reject(parsed: Tiny) -> None:
        raise ValueError("nope")

    fake = FakeClient(GOOD, GOOD)
    with pytest.raises(AnalysisFailed):
        complete_validated(Tiny, "p", client=fake, cross_check=always_reject)


def test_swapping_the_provider_changes_nothing() -> None:
    """The point of the seam: two unrelated clients, identical behaviour."""
    class OtherProvider:
        def complete_json(self, prompt, schema, *, max_tokens, temperature):
            return GOOD

    a, _ = complete_validated(Tiny, "p", client=FakeClient(GOOD))
    b, _ = complete_validated(Tiny, "p", client=OtherProvider())
    assert a == b


# ---------------------------------------------------------------------------------------
# GeminiClient -- driven through MockTransport, exactly as app/github.py is (DECISIONS #37)
# ---------------------------------------------------------------------------------------


def gemini(handler) -> GeminiClient:
    transport = httpx.MockTransport(handler)
    return GeminiClient(api_key="test-key", model="gemini-3.6-flash",
                        client=httpx.Client(transport=transport))


def reply(text: str, finish: str = "STOP") -> httpx.Response:
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}]},
    )


def test_gemini_returns_text_and_normalises_stop() -> None:
    raw, finish = gemini(lambda r: reply('{"value": 1}')).complete_json(
        "p", {"type": "object"}, max_tokens=100, temperature=0.3
    )
    assert raw == '{"value": 1}' and finish == "stop"


@pytest.mark.parametrize(
    "reason,expected",
    [("STOP", "stop"), ("MAX_TOKENS", "max_tokens"), ("SAFETY", "other"), ("", "other")],
)
def test_finish_reasons_are_normalised(reason: str, expected: str) -> None:
    """The retry policy keys on this. Every provider spells truncation differently, and
    getting it wrong is silent -- a truncated response looks like a bad prompt."""
    _, finish = gemini(lambda r: reply("{}", reason)).complete_json(
        "p", {}, max_tokens=100, temperature=0.3
    )
    assert finish == expected


def test_multipart_responses_are_joined() -> None:
    def handler(request):
        return httpx.Response(200, json={"candidates": [{
            "content": {"parts": [{"text": '{"val'}, {"text": 'ue": 1}'}]},
            "finishReason": "STOP"}]})

    raw, _ = gemini(handler).complete_json("p", {}, max_tokens=100, temperature=0.3)
    assert json.loads(raw) == {"value": 1}


def test_the_request_carries_the_key_and_the_schema() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["key"] = request.headers.get("x-goog-api-key")
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return reply("{}")

    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    gemini(handler).complete_json("hello", schema, max_tokens=4321, temperature=0.7)

    assert captured["key"] == "test-key"
    assert "gemini-3.6-flash:generateContent" in captured["url"]
    cfg = captured["body"]["generationConfig"]
    assert cfg["responseSchema"] == schema
    assert cfg["responseMimeType"] == "application/json"
    assert cfg["maxOutputTokens"] == 4321 and cfg["temperature"] == 0.7
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "hello"


@pytest.mark.parametrize("status", [400, 403, 429, 503])
def test_http_errors_become_provider_errors(status: int) -> None:
    """ProviderError is retryable; a bare exception here would skip the retry entirely."""
    client = gemini(lambda r: httpx.Response(status, text="upstream said no"))
    with pytest.raises(ProviderError) as caught:
        client.complete_json("p", {}, max_tokens=100, temperature=0.3)
    assert str(status) in str(caught.value)


def test_a_blocked_response_with_no_candidates_is_a_provider_error() -> None:
    """A safety filter leaves no text at all -- retrying the prompt is the right move,
    and treating it as a validation failure would report a confusing parse error."""
    client = gemini(lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(ProviderError):
        client.complete_json("p", {}, max_tokens=100, temperature=0.3)


def test_transport_failures_become_provider_errors() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset")

    with pytest.raises(ProviderError):
        gemini(boom).complete_json("p", {}, max_tokens=100, temperature=0.3)


def test_gemini_plugs_into_the_retry_policy_end_to_end() -> None:
    """One 503, then a good payload -- the whole path with no network."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="high demand")
        return reply('{"value": 7}')

    parsed, _ = complete_validated(Tiny, "p", client=gemini(handler))
    assert parsed.value == 7 and calls["n"] == 2
