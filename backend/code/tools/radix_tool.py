from pathlib import Path
from langchain_core.tools import tool
from .radix_loader import build_kb, search_prefix

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_ROOT = build_kb(_DATA_DIR) # builds once at import

@tool
def radix_prefix_search(prefix: str) -> list[dict]:
    """
    Return ALL immigration JSON docs whose *filename* begins with `prefix`.
    Example prefixes: "E-", "EB-3", "F-1"
    """
    return search_prefix(_ROOT, prefix)
