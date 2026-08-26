"""Fetch a public GitHub repo's structure and a slice of its contents (docs/TDD.md §4.13).

Read-only, over the REST API and raw.githubusercontent.com. **No clone, no checkout, no
execution, no `git` binary** — the review scores what the code says, not what it does
(DECISIONS #22). Every failure a student can cause becomes a RepoError carrying a sentence
worth showing them; routers/submit.py turns that into a 422.

Budget per submission: 2 API calls + at most MAX_FILES raw fetches.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import settings

log = logging.getLogger(__name__)

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)

MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES = 10, 20_000, 60_000

SKIP_DIRS = (
    "node_modules/", "vendor/", "dist/", "build/", ".git/", "__pycache__/",
    ".venv/", "venv/", "target/", ".next/", "coverage/",
)
SKIP_NAMES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock")
SOURCE_EXT = (
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".rb",
    ".sql", ".sh", ".yml", ".yaml", ".toml", ".md",
)
SOURCE_NAMES = ("Dockerfile", "Makefile")

_REPO_PATH = re.compile(r"^/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$")
_warned_no_token = False


@dataclass(frozen=True)
class RepoBundle:
    owner: str
    repo: str
    default_branch: str
    tree: list[str]                  # every blob path, for structure
    files: dict[str, str]            # path -> content, README first, capped


class RepoError(Exception):
    """Something about the student's repo — always safe to show them verbatim."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


def parse_github_url(url: str) -> tuple[str, str]:
    parsed = urlparse((url or "").strip())
    host = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme not in ("http", "https") or host != "github.com":
        raise RepoError("That doesn't look like a public GitHub repo URL")
    # tolerate the URL people actually copy: /owner/repo/tree/main, /owner/repo.git, trailing /
    path = re.sub(r"/(tree|blob)/[^/]+/?.*$", "", parsed.path)
    match = _REPO_PATH.match(path)
    if not match:
        raise RepoError("That doesn't look like a public GitHub repo URL")
    return match.group("owner"), match.group("repo")


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "anchor-hackathon"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        return headers
    global _warned_no_token
    if not _warned_no_token:      # once per process, not once per request
        _warned_no_token = True
        log.warning("GITHUB_TOKEN is unset — GitHub allows only 60 requests/hour unauthenticated")
    return headers


def _raise_for(response: httpx.Response) -> None:
    if response.status_code == 404:
        raise RepoError("That repo isn't public or doesn't exist")
    if response.status_code in (403, 429):
        # 403 is both "rate limited" and "forbidden"; the remaining header tells them apart
        if response.headers.get("x-ratelimit-remaining") == "0" or "rate limit" in response.text.lower():
            raise RepoError("GitHub is rate-limiting us — try again in a minute")
        raise RepoError("That repo isn't public or doesn't exist")
    if response.status_code >= 400:
        log.warning("github %s -> %s", response.request.url, response.status_code)
        raise RepoError("GitHub wouldn't give us that repo — check the URL and try again")


def _skip(path: str) -> bool:
    if path.startswith(SKIP_DIRS) or any(part in path for part in SKIP_DIRS):
        return True
    name = path.rsplit("/", 1)[-1]
    return name in SKIP_NAMES


def _is_source(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.endswith(SOURCE_EXT) or name in SOURCE_NAMES


def _pick(paths: list[str]) -> list[str]:
    """README first, then the shallowest source files — the ones that describe the project."""
    readmes = sorted(
        (p for p in paths if p.rsplit("/", 1)[-1].lower().startswith("readme")),
        key=lambda p: (p.count("/"), len(p), p),
    )
    rest = sorted(
        (p for p in paths if p not in set(readmes) and _is_source(p)),
        key=lambda p: (p.count("/"), len(p), p),
    )
    return (readmes + rest)[:MAX_FILES]


def fetch_repo(url: str, *, client: httpx.Client | None = None) -> RepoBundle:
    owner, repo = parse_github_url(url)
    owned = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=True)
    try:
        meta = _get_json(client, f"{API}/repos/{owner}/{repo}")
        branch = meta.get("default_branch") or "main"

        tree_doc = _get_json(client, f"{API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        nodes = tree_doc.get("tree") or []
        tree = [n["path"] for n in nodes if n.get("type") == "blob"]
        candidates = [p for p in tree if not _skip(p)]
        if not candidates:
            raise RepoError("That repo has no files yet")

        files: dict[str, str] = {}
        used = 0
        for path in _pick(candidates):
            body = _get_raw(client, owner, repo, branch, path)
            if body is None:
                continue
            if len(body) > MAX_FILE_BYTES:
                body = body[:MAX_FILE_BYTES] + "\n…[truncated]"
            if used + len(body) > MAX_TOTAL_BYTES:
                break
            files[path] = body
            used += len(body)

        if not files:
            raise RepoError("That repo has no readable source files")
        return RepoBundle(owner=owner, repo=repo, default_branch=branch, tree=tree, files=files)
    finally:
        if owned:
            client.close()


def _get_json(client: httpx.Client, url: str) -> dict:
    try:
        response = client.get(url, headers=_headers())
    except httpx.HTTPError as e:
        log.warning("github request failed: %s", e)
        raise RepoError("Couldn't reach GitHub just now — try again in a minute") from e
    _raise_for(response)
    return response.json()


def _get_raw(client: httpx.Client, owner: str, repo: str, branch: str, path: str) -> str | None:
    """Text content, or None for anything binary or unreadable — one skipped file is not fatal."""
    try:
        response = client.get(f"{RAW}/{owner}/{repo}/{branch}/{path}", headers=_headers())
    except httpx.HTTPError as e:
        log.warning("raw fetch failed for %s: %s", path, e)
        return None
    if response.status_code != 200:
        return None
    if b"\x00" in response.content[:1024]:
        return None
    try:
        return response.content.decode("utf-8")
    except UnicodeDecodeError:
        return None
