"""Write the JSON Schema of every model this lane returns, into `contracts/`.

    python -m app.analysis.export_schema

Reference material for the other lanes, and optional frontend validation of fixtures
(CONTRACT 4). Regenerate whenever a schema changes: a stale copy is worse than none, because
it still looks authoritative.

Both forms are written for each model. The raw Pydantic schema is the honest description of the
contract; the transformed one is what the provider actually receives, and seeing them side by
side is what makes the stripped keywords (`pattern`, the length bounds) obvious rather than
surprising.

`ProjectOut` and `ReviewOut` were added once S6/S7 landed. CONTRACT 1b and 1c describe them in
prose and nothing published their actual shape, which left the two newest models the only ones
another lane had to take on trust.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.analysis.client import transform_schema
from app.analysis.project import ProjectOut
from app.analysis.review import ReviewOut
from app.analysis.schema import AnalysisOut

# backend/app/analysis/export_schema.py -> repo root
CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"

MODELS = [
    ("analysis", AnalysisOut),
    ("project", ProjectOut),
    ("review", ReviewOut),
]


def main() -> None:
    CONTRACTS.mkdir(parents=True, exist_ok=True)

    for name, model_cls in MODELS:
        full = model_cls.model_json_schema()
        target = CONTRACTS / (name + ".schema.json")
        target.write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
        print("wrote " + str(target))

        sent = transform_schema(full)
        sent_target = CONTRACTS / (name + ".provider-schema.json")
        sent_target.write_text(json.dumps(sent, indent=2) + "\n", encoding="utf-8")
        print("wrote " + str(sent_target) + "  (what the provider is actually sent)")


if __name__ == "__main__":
    main()
