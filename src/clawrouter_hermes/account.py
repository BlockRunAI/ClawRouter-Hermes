"""Read-only shared BlockRun account credential state."""
import os
from pathlib import Path
PORTAL="https://user.blockrun.ai"
def resolve_api_key():
    if "BLOCKRUN_API_KEY" in os.environ:
        key=os.environ["BLOCKRUN_API_KEY"].strip();source="env"
    else:
        path=Path.home()/".blockrun"/".api-key"
        if not path.is_file(): return None
        key=path.read_text(encoding="utf-8").strip();source=str(path)
    if not key.startswith("brk_") or any(c.isspace() for c in key):
        raise ValueError(f"Invalid BlockRun API key; create one at {PORTAL}/dashboard/keys. Wallet fallback refused.")
    return {"source":source,"portal":f"{PORTAL}/dashboard/credits"}
