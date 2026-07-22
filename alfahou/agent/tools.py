from __future__ import annotations

import ast
import math
import operator
import re
from datetime import datetime, timedelta, timezone

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name in {"sqrt", "sin", "cos", "tan", "log", "abs", "round"} and len(node.args) == 1:
            fn = getattr(math, name) if name not in {"abs", "round"} else (abs if name == "abs" else round)
            return fn(_eval_node(node.args[0]))
    raise ValueError("expression non autorisée")


def safe_calculate(expr: str) -> str:
    cleaned = expr.strip().replace("^", "**").replace(",", ".")
    cleaned = re.sub(r"[^0-9+\-*/().%\sA-Za-z_]", "", cleaned)
    try:
        tree = ast.parse(cleaned, mode="eval")
        value = _eval_node(tree)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)
    except Exception:
        return ""


def now_paris() -> str:
    utc = datetime.now(timezone.utc)
    offset = 2 if 3 < utc.month < 11 else 1
    local = utc + timedelta(hours=offset)
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    months = [
        "",
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    return (
        f"{days[local.weekday()]} {local.day} {months[local.month]} {local.year} "
        f"· {local.strftime('%H:%M')} (Paris)"
    )


def convert_units(text: str) -> str | None:
    t = text.lower().replace(",", ".")
    m = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(km|m|cm|kg|g|celsius|°c|c|fahrenheit|°f|f|miles?|lbs?)\b",
        t,
    )
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "km":
        return f"{val} km = {val * 1000:g} m = {val * 0.621371:g} miles"
    if unit == "m":
        return f"{val} m = {val / 1000:g} km = {val * 100:g} cm"
    if unit == "cm":
        return f"{val} cm = {val / 100:g} m"
    if unit == "kg":
        return f"{val} kg = {val * 1000:g} g = {val * 2.20462:g} lb"
    if unit == "g":
        return f"{val} g = {val / 1000:g} kg"
    if unit in {"celsius", "°c", "c"}:
        return f"{val:g} °C = {val * 9 / 5 + 32:g} °F"
    if unit in {"fahrenheit", "°f", "f"}:
        return f"{val:g} °F = {(val - 32) * 5 / 9:g} °C"
    if unit.startswith("mile"):
        return f"{val} miles = {val * 1.60934:g} km"
    if unit.startswith("lb"):
        return f"{val} lb = {val * 0.453592:g} kg"
    return None
