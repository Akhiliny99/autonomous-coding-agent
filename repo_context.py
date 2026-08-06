"""Repo-wide context retrieval using tree-sitter.

Builds a lightweight symbol index (function/class name -> file + line) so the
agent can find relevant files by matching issue text against real code
symbols, instead of dumping the entire repo into the LLM prompt.
"""
import os
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)


def index_repo(repo_path: str) -> dict:
    """Builds a lightweight symbol map: function/class name -> file + line."""
    index = {}
    for root, _, files in os.walk(repo_path):
        if ".git" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "rb") as fh:
                    code = fh.read()
            except OSError:
                continue
            tree = parser.parse(code)
            for node in tree.root_node.children:
                if node.type in ("function_definition", "class_definition"):
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        name = code[name_node.start_byte:name_node.end_byte].decode()
                        index[name] = {"file": path, "line": node.start_point[0] + 1}
    return index


def get_relevant_files(repo_path: str, issue_text: str, index: dict, top_k: int = 5) -> list:
    """Naive keyword match against symbol index — swap for embedding search if
    you want it fancier (e.g. sentence-transformers + FAISS over docstrings).
    """
    scores = {}
    words = set(issue_text.lower().split())
    for name, meta in index.items():
        name_lower = name.lower()
        if name_lower in words or any(w in name_lower for w in words if len(w) > 2):
            scores[meta["file"]] = scores.get(meta["file"], 0) + 1
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    files = [f for f, _ in ranked[:top_k]]

    # Fallback: if keyword match finds nothing, just grab the smallest set of
    # top-level .py files so the agent always has something to work with.
    if not files:
        all_files = []
        for root, _, fnames in os.walk(repo_path):
            if ".git" in root:
                continue
            for fn in fnames:
                if fn.endswith(".py"):
                    all_files.append(os.path.join(root, fn))
        files = all_files[:top_k]

    return files
