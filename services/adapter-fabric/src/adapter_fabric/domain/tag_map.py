"""Tag-map compounding — pure, testable, no I/O."""
from __future__ import annotations

import ast
import math
from typing import Any, Dict, Optional

from .models import TagMapping


# Allowed names for formula evaluation (math + builtins).
_ALLOWED_NAMES: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "pow": pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(expr: str, variables: Dict[str, float]) -> float:
    """Safely evaluate arithmetic expression over variables.

    Only allows: BinOp, UnaryOp, Call (whitelisted), Name, Constant/Num.
    No attribute access, no imports.
    """
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.FloorDiv,
    )
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Disallowed expression node: {type(node).__name__}: {expr!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_NAMES:
                raise ValueError(f"Disallowed call: {ast.dump(node)}")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in _ALLOWED_NAMES:
                raise ValueError(f"Unknown variable: {node.id!r} in {expr!r}")
    env: dict[str, Any] = {**_ALLOWED_NAMES, **variables}
    code = compile(tree, "<tag_formula>", "eval")
    result = eval(code, {"__builtins__": {}}, env)
    return float(result)


def apply_tag_mapping(raw: float, mapping: TagMapping) -> float:
    """Apply scale/offset for a single-tag mapping."""
    return raw * mapping.scale + mapping.offset


def compound(raw_by_var: Dict[str, float], mapping: TagMapping) -> float:
    """Evaluate a compound_formula over raw_by_var.

    If compound_formula is None, expects single var mapping and uses scale/offset.
    If compound_formula is set, eval formula with variables = raw_by_var keys
    (optionally pre-scaled — caller decides).
    """
    if mapping.compound_formula is None:
        # single var: key is the lone entry
        if len(raw_by_var) == 1:
            v = next(iter(raw_by_var.values()))
            return apply_tag_mapping(v, mapping)
        # multi but no formula: average scaled
        return sum(apply_tag_mapping(v, mapping) for v in raw_by_var.values()) / max(1, len(raw_by_var))
    return _safe_eval(mapping.compound_formula, raw_by_var)


def normalize_raw_value(raw: Any, mapping: TagMapping) -> float:
    """Coerce raw wire value to float respecting data_type."""
    dt = mapping.data_type.lower()
    if dt == "bool":
        return 1.0 if bool(raw) else 0.0
    if dt in ("int16", "int32", "int"):
        return float(int(raw))
    if dt in ("uint16", "uint32"):
        v = int(raw)
        if v < 0:
            # interpret as unsigned wrap
            bits = 16 if "16" in dt else 32
            v = v & ((1 << bits) - 1)
        return float(v)
    if dt == "float32":
        return float(raw)
    # float default
    return float(raw)


def evaluate_compound_formula(formula: str, variables: Dict[str, float]) -> float:
    """Public helper for callers/tests that just want formula eval."""
    return _safe_eval(formula, variables)


__all__ = [
    "apply_tag_mapping",
    "compound",
    "normalize_raw_value",
    "evaluate_compound_formula",
]
