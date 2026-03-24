from __future__ import annotations

import ast
import math
import operator

from langchain_core.tools import tool


ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
    "abs": abs,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BIN_OPS:
        return ALLOWED_BIN_OPS[type(node.op)](
            _safe_eval(node.left), _safe_eval(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_UNARY_OPS:
        return ALLOWED_UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function_name = node.func.id
        if function_name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Unsupported function: {function_name}")
        if node.keywords:
            raise ValueError("Keyword arguments are not supported.")
        return float(
            ALLOWED_FUNCTIONS[function_name](*[_safe_eval(argument) for argument in node.args])
        )
    raise ValueError("Only arithmetic expressions and approved math functions are allowed.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression using safe arithmetic parsing."""
    try:
        parsed = ast.parse(expression, mode="eval")
        result = _safe_eval(parsed)
    except Exception as exc:  # noqa: BLE001
        return f"Calculator error: {exc}"

    if result.is_integer():
        return f"Result: {int(result)}"
    return f"Result: {result}"

