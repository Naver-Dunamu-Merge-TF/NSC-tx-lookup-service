from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_dlq(path: str, payload: Mapping[str, Any]) -> None:
    dlq_path = Path(path)
    dlq_path.parent.mkdir(parents=True, exist_ok=True)
    with dlq_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
