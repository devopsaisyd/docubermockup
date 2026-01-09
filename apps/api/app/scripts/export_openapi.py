from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    spec = app.openapi()
    out = Path(__file__).resolve().parents[2] / "openapi.json"  # apps/api/openapi.json
    out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

