# Eval fixtures

Committed repo bundles for the review evals. Reproducible on purpose: a live fetch would make
the score depend on whatever the repo looks like today, and the one variable an eval of the
*prompt* must hold still is the input.

| File | What it is | Expected |
|---|---|---|
| `strong_repo.json` | the real demo repo, exactly as `fetch_repo` returns it — 10 files, 26,991 chars | scores high (>= 75% of max) |
| `weak_repo.json` | a synthetic two-file Express app that meets none of the criteria | scores low (<= 34% of max) |

The injected variant is built from `weak_repo.json` at runtime by `bundles.injected()`, so the
attack text lives in one place. It is injected into the **weak** repo deliberately: injecting
into the strong one proves nothing, because a repo already scoring maximum cannot be inflated.

`strong_repo.json` was captured with `fetch_repo` against the live repo. Note that an
unauthenticated fetch silently drops files whose raw request fails — the first capture returned
8 of 10 — so regenerate it with `GITHUB_TOKEN` set and check the file count before committing.
