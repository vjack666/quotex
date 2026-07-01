"""Script auxiliar para extraer módulos del monolito (uso único en refactor)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
MONOLITH = SRC / "consolidation_bot.py"


def read_monolith() -> str:
    return MONOLITH.read_text(encoding="utf-8")


def extract_function_block(text: str, name: str) -> str:
    pattern = rf"^(async )?def {name}\("
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i
            break
    if start is None:
        raise ValueError(f"Function {name} not found")
    # find end by next top-level def/class at column 0
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("def ") or lines[j].startswith("async def ") or lines[j].startswith("class "):
            end = j
            break
    return "".join(lines[start:end])


def extract_class_methods(text: str, method_names: list[str]) -> dict[str, str]:
    result = {}
    for name in method_names:
        pattern = rf"^    (async )?def {name}\("
        lines = text.splitlines(keepends=True)
        start = None
        for i, line in enumerate(lines):
            if re.match(pattern, line):
                start = i
                break
        if start is None:
            continue
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^    (async )?def ", lines[j]) or lines[j].startswith("class "):
                end = j
                break
        block = "".join(lines[start:end])
        # dedent one level
        dedented = []
        for line in block.splitlines(keepends=True):
            if line.startswith("    "):
                dedented.append(line[4:])
            else:
                dedented.append(line)
        result[name] = "".join(dedented)
    return result


if __name__ == "__main__":
    text = read_monolith()
    names = [
        "fetch_candles",
        "fetch_candles_with_retry",
        "get_open_assets",
        "looks_like_connection_issue",
        "place_order",
        "connect_with_retry",
        "detect_consolidation",
        "raw_to_candle",
    ]
    for n in names:
        try:
            block = extract_function_block(text, n)
            print(f"=== {n} ({len(block.splitlines())} lines) ===")
        except ValueError as e:
            print(e)