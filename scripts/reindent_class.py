"""Añade 4 espacios a todo el cuerpo de cada método de clase."""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def fix_class_bodies(text: str, class_name: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_target_class = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(f"class {class_name}"):
            in_target_class = True
            out.append(line)
            i += 1
            continue
        if in_target_class and line.startswith("class ") and not line.startswith(f"class {class_name}"):
            in_target_class = False

        if in_target_class and (
            line.startswith("    def ") or line.startswith("    async def ") or line.startswith("    @")
        ):
            # decorators
            while line.startswith("    @"):
                out.append(line)
                i += 1
                if i >= len(lines):
                    break
                line = lines[i]
            if i < len(lines) and (lines[i].startswith("    def ") or lines[i].startswith("    async def ")):
                out.append(lines[i])
                i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("    def ") or nxt.startswith("    async def "):
                    break
                if nxt.strip() == "":
                    out.append(nxt)
                else:
                    out.append("    " + nxt)
                i += 1
            continue

        out.append(line)
        i += 1

    result = "".join(out)
    result = result.replace("await await ", "await ")
    result = result.replace("self.bot._round_up_to_cents", "self._round_up_to_cents")
    return result


for fname, cls in [("executor.py", "TradeExecutor"), ("scanner.py", "AssetScanner")]:
    path = SRC / fname
    # Reload from git? Can't. Re-read current and only fix if needed
    path.write_text(fix_class_bodies(path.read_text(encoding="utf-8"), cls), encoding="utf-8")
    print("fixed", fname)