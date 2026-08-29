"""The provider seam: one small protocol, one implementation per vendor, one retry policy.

Everything vendor-specific in this lane sits behind `LLMClient`. Swapping providers is a new
~40-line class and one env var -- which is why LangChain was rejected (DECISIONS #39): the
abstraction already existed in the three public functions, and a framework would normalise away
the one thing the retry policy actually needs, the raw finish reason.

Gemini is called over raw REST, NOT the `google-genai` SDK (DECISIONS #45). Measured in S0: the
SDK returns 403 PERMISSION_DENIED with our key while the identical key succeeds against
generativelanguage.googleapis.com with an `x-goog-api-key` header. `httpx` was already a
dependency, so the provider costs nothing extra.

`complete_json` returns `(raw_text, finish_reason)` with the reason normalised to
`stop` / `max_tokens` / `other`. That normalisation is the point of the seam: every provider
spells truncation differently, and getting it wrong fails silently -- a truncated response looks
exactly like a bad prompt.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

import httpx
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT = 240.0  # the analysis call measured 55 s in S0; headroom, not a target


class AnalysisFailed(Exception):
    """A model call that did not produce a valid payload after its retry.

    Routers turn this into a 502. It is the only exception this package raises outward.
    """


class ProviderError(AnalysisFailed):
    """Transport or HTTP-level failure. Retryable -- the free tier really does return 503."""


# --------------------------------------------------------------------------------------
# Schema transform
# --------------------------------------------------------------------------------------

# Keywords Gemini's responseSchema rejects or ignores, verified against a live call in S0.
# minItems/maxItems ARE supported but are dropped anyway: schema.py's validators own every
# length rule, and two sources of truth that can silently disagree is worse than one.
_DROP_KEYWORDS = frozenset(
    {
        "pattern",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "additionalProperties",
        "title",
        "description",
        "default",
        "$schema",
    }
)


def transform_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic's JSON Schema -> the subset Gemini's responseSchema accepts.

    1. $ref/$defs are inlined -- the grammar compiler does not follow references.
    2. Unsupported keywords are stripped (_DROP_KEYWORDS).
    3. `const` becomes a single-item `enum` -- Pydantic emits `const` for one-value Literals
       and Gemini only understands `enum`.
    """
    defs = schema.get("$defs", {})
    root = {k: v for k, v in schema.items() if k != "$defs"}
    return _walk(root, defs)


def _walk(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_walk(n, defs) for n in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        return _walk(defs[node["$ref"].rsplit("/", 1)[-1]], defs)

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _DROP_KEYWORDS:
            continue
        if key == "const":
            out["enum"] = [value]
            continue
        if key == "properties":
            # Keys here are FIELD NAMES, not schema keywords. Filtering them against
            # _DROP_KEYWORDS deletes real fields: RoleOut.title vanished from `properties`
            # while staying in `required`, and Gemini rejected the request with
            # "required[1]: property is not defined". Caught in S0; DECISIONS #47.
            out["properties"] = {name: _walk(sub, defs) for name, sub in value.items()}
            continue
        out[key] = _walk(value, defs)
    return out


# --------------------------------------------------------------------------------------
# The seam
# --------------------------------------------------------------------------------------


class LLMClient(Protocol):
    """The entire vendor surface. A new provider implements this and nothing else."""

    def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, str]:
        """Return (raw_text, finish_reason): `stop` / `max_tokens` / `other`.

        Raises ProviderError on transport or HTTP failure.
        """
        ...


class GeminiClient:
    """Google Gemini over the REST API. See the module docstring for why not the SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        # Injected for tests, exactly as Salman's fetch_repo does it (DECISIONS #37): the whole
        # path is driven through MockTransport with no monkeypatching and no network.
        self._client = client

    def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, str]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        url = GEMINI_ENDPOINT.format(model=self.model)

        client = self._client or httpx.Client(timeout=REQUEST_TIMEOUT)
        try:
            response = client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini transport error: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        if response.status_code != 200:
            raise ProviderError(f"gemini HTTP {response.status_code}: {response.text[:300]}")

        return self._unpack(response.json())

    @staticmethod
    def _unpack(payload: dict[str, Any]) -> tuple[str, str]:
        candidates = payload.get("candidates") or []
        if not candidates:
            # A safety filter blocking the whole response leaves no text at all. That is a
            # provider failure, not a validation failure -- retrying the prompt is right.
            raise ProviderError(f"gemini returned no candidates: {str(payload)[:300]}")

        candidate = candidates[0]
        raw = "".join(
            part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
        )
        reason = {"STOP": "stop", "MAX_TOKENS": "max_tokens"}.get(
            candidate.get("finishReason", ""), "other"
        )
        return raw, reason


def get_client() -> LLMClient:
    """The configured provider. LLM_PROVIDER is the only thing that selects it."""
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider == "gemini":
        return GeminiClient()
    raise AnalysisFailed(
        f"unknown LLM_PROVIDER {provider!r} -- add a client class in app/analysis/client.py"
    )


# --------------------------------------------------------------------------------------
# Retry policy -- shared by all three call types
# --------------------------------------------------------------------------------------


def complete_validated(
    model_cls: type[BaseModel],
    prompt: str,
    *,
    client: LLMClient | None = None,
    max_tokens: int | None = None,
    retry_max_tokens: int | None = None,
    temperature: float = 0.3,
    cross_check: Callable[[Any], None] | None = None,
) -> tuple[Any, str]:
    """Call the model, validate, retry once, then give up. Returns (parsed, raw_text).

    Exactly two attempts, ever. A third would triple the worst case of a call the Analyzing
    screen is already masking for a minute.

    Three retryable failures, handled the same way:
      * transport / HTTP (ProviderError) -- the free tier returns 503 under load
      * finish_reason == "max_tokens" -- retried with the larger budget
      * validation failure -- the semantic rules the grammar cannot express

    cross_check(parsed) is an optional extra assertion that must raise to reject. It exists for
    the `verifies` subset-of-role-slugs rule and the criteria-echo rule: neither is expressible
    in a schema, and both must trigger the retry rather than reach the caller.
    """
    client = client or get_client()
    schema = transform_schema(model_cls.model_json_schema())
    budget = max_tokens if max_tokens is not None else settings.ANALYSIS_MAX_TOKENS
    retry_budget = (
        retry_max_tokens if retry_max_tokens is not None else settings.ANALYSIS_RETRY_MAX_TOKENS
    )

    last_error: Exception | None = None

    for attempt in (1, 2):
        try:
            raw, finish = client.complete_json(
                prompt, schema, max_tokens=budget, temperature=temperature
            )
        except ProviderError as exc:
            last_error = exc
            log.warning("attempt %s: %s", attempt, exc)
            continue

        if finish == "max_tokens":
            last_error = AnalysisFailed(f"truncated at {budget} tokens")
            log.warning("attempt %s: %s", attempt, last_error)
            budget = retry_budget
            continue

        try:
            parsed = model_cls.model_validate_json(raw)
            if cross_check is not None:
                cross_check(parsed)
            return parsed, raw
        except Exception as exc:  # ValidationError, or a cross_check rejection
            last_error = exc
            log.warning("attempt %s failed validation: %s", attempt, exc)

    raise AnalysisFailed(f"{model_cls.__name__} failed after 2 attempts: {last_error}")
