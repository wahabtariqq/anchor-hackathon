"""Write `contracts/analysis.schema.json` -- the JSON Schema of AnalysisOut.

    python -m app.analysis.export_schema

Reference material for the other lanes, and optional frontend validation of fixtures
(CONTRACT 4). Regenerate whenever `schema.py` changes: a stale copy is worse than none,
because it still looks authoritative.

Both forms are written. The raw Pydantic schema is the honest description of the contract;
the transformed one is what the provider actually receives, and seeing them side by side is
what makes the stripped keywords (`pattern`, the length bounds) obvious rather than surprising.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.analysis.client import transform_schema
from app.analysis.schema import AnalysisOut

# backend/app/analysis/export_schema.py -> repo root
CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"


def main() -> None:
    CONTRACTS.mkdir(parents=True, exist_ok=True)

    full = AnalysisOut.model_json_schema()
    target = CONTRACTS / "analysis.schema.json"
    target.write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target}")

    sent = transform_schema(full)
    sent_target = CONTRACTS / "analysis.provider-schema.json"
    sent_target.write_text(json.dumps(sent, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {sent_target}  (what the provider is actually sent)")


if __name__ == "__main__":
    main()
