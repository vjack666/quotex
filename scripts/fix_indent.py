"""Corrige indentación de métodos sueltos en executor.py y scanner.py."""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def fix_module(path: Path, class_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # find class line
    class_idx = next(i for i, l in enumerate(lines) if l.startswith(f"class {class_name}"))
    # find first module-level def/async def after class __init__ block
    body_start = None
    for i in range(class_idx + 1, len(lines)):
        line = lines[i]
        if line.startswith("def ") or line.startswith("async def "):
            body_start = i
            break
    if body_start is None:
        print(f"{path.name}: nothing to fix")
        return

    header = lines[:body_start]
    body = lines[body_start:]

    fixed_body = []
    for line in body:
        if line.strip() == "":
            fixed_body.append(line)
        elif line.startswith("    "):
            fixed_body.append(line)
        else:
            fixed_body.append("    " + line)

    new_text = "".join(header + fixed_body)
    new_text = new_text.replace("await await ", "await ")
    new_text = new_text.replace("self.bot._round_up_to_cents", "self._round_up_to_cents")
    path.write_text(new_text, encoding="utf-8")
    print(f"Fixed {path.name}: {len(fixed_body)} body lines indented")


fix_module(SRC / "executor.py", "TradeExecutor")
fix_module(SRC / "scanner.py", "AssetScanner")

# scanner: add loop_utils import if missing
scanner = (SRC / "scanner.py").read_text(encoding="utf-8")
if "loop_utils" not in scanner:
    scanner = scanner.replace(
        "from connection import fetch_candles_with_retry, get_open_assets\n",
        "from connection import fetch_candles_with_retry, get_open_assets\nfrom loop_utils import sleep_with_inline_countdown\n",
    )
    (SRC / "scanner.py").write_text(scanner, encoding="utf-8")

# add ma helper and extra methods to scanner if _compute_ma_state missing
if "def _compute_ma_state" not in scanner:
    helper = '''
    def _compute_ma_state(self, asset: str, candles_5m):
        from models import Candle
        prev = self.bot.ma_state_by_asset.get(asset)
        state = compute_ma_state(candles_5m, prev)
        if state is not None:
            self.bot.ma_state_by_asset[asset] = state
        return state

'''
    scanner = (SRC / "scanner.py").read_text(encoding="utf-8")
    scanner = scanner.replace(
        "class AssetScanner:\n    def __init__(self, bot: Any, executor: \"TradeExecutor\"):\n        self.bot = bot\n        self.executor = executor\n\n",
        "class AssetScanner:\n    def __init__(self, bot: Any, executor: \"TradeExecutor\"):\n        self.bot = bot\n        self.executor = executor\n" + helper,
    )
    (SRC / "scanner.py").write_text(scanner, encoding="utf-8")