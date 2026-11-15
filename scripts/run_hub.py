"""Load ignored local configuration and start the single demo hub."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
config = ROOT / ".env"
if config.exists():
    for line in config.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"LOS_EXTRACTION_MODE", "LOS_FIXTURE_CONTENT", "LOS_EXTRACTION_PROVIDER", "OPENAI_API_KEY", "LOS_OPENAI_MODEL", "GEMINI_API_KEY", "LOS_GEMINI_MODEL"}:
            os.environ.setdefault(key.strip(), value.strip())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.hub.app:app", host="0.0.0.0", port=8000, workers=1)
