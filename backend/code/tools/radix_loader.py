from pathlib import Path
import json
from typing import Any, Dict, List, Iterator, Tuple, Optional
"""
Optimized file loading: Radix Tree [Geoffrey Duncan Opiyo]

Radix-tree loader + streaming generator for AskImmigrate 2.0
-----------------------------------------------------------
Usage
-----
from tools.radix_loader import build_kb, search_prefix, stream_nodes
root = build_kb(DATA_DIR)
docs = search_prefix(root, "EB-")        # list of dicts
for key, doc in stream_nodes(root):      # lazy DFS
    ...
"""

# Internal radix nodes
def _common_prefix(a: str, b: str) -> int:
    i, n = 0, min(len(a), len(b))
    while i < n and a[i] == b[i]:
        i += 1
    return i

class _Node:
    __slots__ = ("children", "value")

    def __init__(self):
        self.children: Dict[str, "_Node"] = {}
        self.value: Optional[Any] = None

def _insert(root: _Node, key: str, value: Any) -> None:
    node, rest = root, key
    while rest:
        for edge, child in node.children.items():
            cp = _common_prefix(edge, rest)
            if cp:
                if cp < len(edge):  # split the edge
                    mid = _Node()
                    mid.children[edge[cp:]] = child
                    node.children[edge[:cp]] = mid
                    del node.children[edge]
                    child = mid
                node, rest = child, rest[cp:]
                break
        else:
            new = _Node()
            node.children[rest] = new
            node, rest = new, ""
    node.value = value

def _collect(node: _Node, out: list) -> None:
    if node.value is not None:
        out.append(node.value)
    for child in node.children.values():
        _collect(child, out)

def _search(root: _Node, prefix: str) -> List[Any]:
    node, rest = root, prefix
    while rest:
        for edge, child in node.children.items():
            cp = _common_prefix(edge, rest)
            if cp:
                if cp == len(rest):
                    node, rest = child, ""
                    break
                if cp == len(edge):
                    node, rest = child, rest[cp:]
                    break
        else:
            return []
    out: list = []
    _collect(node, out)
    return out

# Public helpers
def build_kb(data_dir: Path) -> _Node:
    root = _Node()
    for p in data_dir.rglob("*.json"):
        _insert(root, p.stem, json.loads(p.read_text(encoding="utf-8")))
    return root


def search_prefix(root: _Node, prefix: str = "") -> List[Any]:
    return _search(root, prefix)


def stream_nodes(root: _Node, prefix: str = "") -> Iterator[Tuple[str, Any]]:
    """Depth-first streaming generator of (key, value)."""
    stack: list[Tuple[str, _Node]] = [("", root)]
    while stack:
        key_so_far, node = stack.pop()
        if node.value is not None and key_so_far.startswith(prefix):
            yield key_so_far, node.value
        for edge, child in node.children.items():
            stack.append((key_so_far + edge, child))
