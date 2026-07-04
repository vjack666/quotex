"""Parse STRAT-A live validation session from consolidation_bot.log."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "consolidation_bot.log"
SESSION_MARKER_LINE = 489254  # 2026-07-02 STRAT-A validation run #2


def load_session() -> list[str]:
    with LOG.open(encoding="utf-8", errors="replace") as f:
        for _ in range(SESSION_MARKER_LINE - 1):
            next(f, None)
        return f.readlines()


def main() -> int:
    session = load_session()
    info = [l for l in session if "[INFO]" in l]
    rejects = [
        l
        for l in session
        if "⛔ [STRAT-A]" in l
        or ("zona demasiado joven" in l and "— skip" in l)
    ]
    fase3 = [l for l in session if "[FASE 3/5]" in l]
    strat_only = [l for l in session if "[STRAT-A-ONLY]" in l]
    scans = [l for l in session if "SCAN #" in l and "[INFO]" in l]
    errors = [l for l in session if "[ERROR]" in l or "[CRITICAL]" in l]
    entries = [
        l
        for l in session
        if re.search(
            r"(ORDEN enviada|✅ ORDEN|sesión cumplida|Massaniello.*cumplida|3 ITM)",
            l,
            re.I,
        )
    ]

    reasons: Counter[str] = Counter()
    for line in rejects:
        if "zona demasiado joven" in line:
            reasons["zone_age"] += 1
        elif "payout=" in line:
            reasons["payout"] += 1
        elif "score=" in line:
            reasons["score"] += 1
        elif "patrón" in line or "patron" in line:
            reasons["pattern"] += 1
        elif "htf" in line.lower() or "tendencia" in line.lower():
            reasons["htf"] += 1
        elif "zone_memory" in line:
            reasons["zone_memory"] += 1
        else:
            reasons["other"] += 1

    start = info[0].split()[0] if info else "?"
    end = info[-1].split()[0] if info else "?"

    print("=== STRAT-A LIVE VALIDATION SESSION ===")
    print(f"marker_line: {SESSION_MARKER_LINE}")
    print(f"time_range: {start} -> {end}")
    print(f"session_lines: {len(session)}")
    print(f"scan_cycles: {len(scans)}")
    print(f"fase3_cycles: {len(fase3)}")
    print(f"strat_a_only_cycles: {len(strat_only)}")
    print(f"rejections: {len(rejects)}")
    print(f"entries: {len(entries)}")
    print(f"errors: {len(errors)}")
    print(f"rejection_reasons: {dict(reasons)}")
    print("--- scans ---")
    for s in scans:
        print(s.rstrip())
    print("--- fase3 ---")
    for s in fase3:
        print(s.rstrip())
    print("--- rejections ---")
    for r in rejects:
        print(r.rstrip())
    print("--- entries ---")
    for e in entries:
        print(e.rstrip())
    criterion = len(rejects) >= 10 or any("sesión cumplida" in e.lower() for e in entries)
    print(f"criterion_met: {criterion}")
    return 0 if criterion else 1


if __name__ == "__main__":
    raise SystemExit(main())