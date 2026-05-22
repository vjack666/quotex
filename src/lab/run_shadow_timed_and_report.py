#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
REPORT_SCRIPT = ROOT / "src" / "lab" / "journal_performance_report.py"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _run_report(json_out: Path, days: int) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPORT_SCRIPT),
        "--days",
        str(days),
        "--json-out",
        str(json_out),
    ]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=60)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print("[report stderr]\n" + res.stderr)
    if res.returncode != 0:
        raise RuntimeError(f"report failed with code {res.returncode}")
    return json.loads(json_out.read_text(encoding="utf-8"))


def _start_bot_process(cmd: list[str], env: Dict[str, str]) -> subprocess.Popen[Any]:
    if os.name == "nt":
        # Separate process group lets us send CTRL_BREAK only to child process tree.
        return subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def _stop_bot_process(proc: subprocess.Popen[Any]) -> int:
    if os.name == "nt":
        proc.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        proc.terminate()

    try:
        return proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        print(f"[{_ts()}] Graceful stop timeout; killing process")
        proc.kill()
        return proc.wait(timeout=10)


def _spawn_bot(
    minutes: int,
    min_payout: int,
    score_base: int,
    score_low: int,
    score_high: int,
    force_any_candidate: bool,
    scan_top_n: int,
) -> int:
    env = os.environ.copy()
    env["SHADOW_MODE_ENABLED"] = "true"
    env["SHADOW_AUDIT_MODE"] = "true"
    env["SHADOW_PERSIST_ENABLED"] = "true"
    if force_any_candidate:
        env["FORCE_EXECUTE_ANY_CANDIDATE"] = "true"

    cmd = [
        sys.executable,
        "main.py",
        "--min-payout",
        str(min_payout),
        "--adaptive-threshold-base",
        str(score_base),
        "--adaptive-threshold-low",
        str(score_low),
        "--adaptive-threshold-high",
        str(score_high),
        "--scan-top-n",
        str(scan_top_n),
    ]

    print(f"[{_ts()}] Starting timed shadow session")
    print(f"  minutes={minutes} min_payout={min_payout} score(base/low/high)={score_base}/{score_low}/{score_high}")
    print(f"  force_any_candidate={str(force_any_candidate).lower()}")
    print(f"  cmd: {' '.join(cmd)}")

    proc = _start_bot_process(cmd, env)
    start = time.time()
    stop_at = start + max(1, minutes) * 60
    last_print = 0.0

    try:
        while True:
            rc = proc.poll()
            now = time.time()

            if rc is not None:
                print(f"[{_ts()}] Bot finished by itself with code={rc}")
                return rc

            remaining = int(stop_at - now)
            if remaining <= 0:
                print(f"[{_ts()}] Timebox reached. Stopping bot...")
                break

            if now - last_print >= 15:
                mm = remaining // 60
                ss = remaining % 60
                print(f"[{_ts()}] Countdown {mm:02d}:{ss:02d}")
                last_print = now

            time.sleep(1)

        return _stop_bot_process(proc)
    except KeyboardInterrupt:
        print(f"[{_ts()}] Interrupted by user. Stopping bot...")
        try:
            return _stop_bot_process(proc)
        except Exception:
            proc.kill()
            return proc.wait(timeout=10)


def main() -> int:
    p = argparse.ArgumentParser(description="Run timed shadow collection and auto-analyze")
    p.add_argument("--minutes", type=int, default=20, help="session duration in minutes")
    p.add_argument("--days", type=int, default=7, help="lookback days for report")
    p.add_argument("--min-payout", type=int, default=84)
    p.add_argument("--score-base", type=int, default=50)
    p.add_argument("--score-low", type=int, default=48)
    p.add_argument("--score-high", type=int, default=54)
    p.add_argument("--scan-top-n", type=int, default=8, help="limit assets per cycle for diagnostics")
    p.add_argument(
        "--force-any-candidate",
        action="store_true",
        help="temporarily force execution for every detected candidate",
    )
    p.add_argument("--fallback-relaxed", action="store_true", help="if no shadow rows, run second pass with relaxed filters")
    args = p.parse_args()

    report_path = ROOT / "data" / "exports" / f"shadow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rc = _spawn_bot(
        minutes=args.minutes,
        min_payout=args.min_payout,
        score_base=args.score_base,
        score_low=args.score_low,
        score_high=args.score_high,
        force_any_candidate=args.force_any_candidate,
        scan_top_n=args.scan_top_n,
    )
    print(f"[{_ts()}] Session exit code: {rc}")

    print(f"[{_ts()}] Running report...")
    data = _run_report(report_path, days=args.days)
    shadow_rows = int(data.get("shadow_coverage", {}).get("shadow_rows_total", 0) or 0)
    resolved = int(data.get("shadow_coverage", {}).get("with_resolved_outcome", 0) or 0)
    total = int(data.get("summary", {}).get("total", 0) or 0)
    wins = int(data.get("summary", {}).get("wins", 0) or 0)
    losses = int(data.get("summary", {}).get("losses", 0) or 0)

    print(f"[{_ts()}] Report saved: {report_path}")
    print(f"[{_ts()}] shadow_rows_total={shadow_rows} with_resolved_outcome={resolved} total={total} wins={wins} losses={losses}")

    if total <= 0 and resolved <= 0:
        print(
            f"[{_ts()}] RESULTADO: SIN METRICAS DE EJECUCION. "
            "Pasar al siguiente paso: diagnostico de logica/estrategia (no solo escaneo)."
        )
    else:
        print(
            f"[{_ts()}] RESULTADO: CON METRICAS DE EJECUCION. "
            "Continuar con validacion estadistica (Fase 4)."
        )

    if shadow_rows == 0 and args.fallback_relaxed:
        print(f"[{_ts()}] No shadow rows. Launching fallback relaxed run...")
        rc2 = _spawn_bot(
            minutes=max(10, args.minutes),
            min_payout=80,
            score_base=48,
            score_low=46,
            score_high=52,
            force_any_candidate=args.force_any_candidate,
            scan_top_n=args.scan_top_n,
        )
        print(f"[{_ts()}] Fallback session exit code: {rc2}")
        report_path2 = ROOT / "data" / "exports" / f"shadow_report_relaxed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data2 = _run_report(report_path2, days=args.days)
        shadow_rows2 = int(data2.get("shadow_coverage", {}).get("shadow_rows_total", 0) or 0)
        resolved2 = int(data2.get("shadow_coverage", {}).get("with_resolved_outcome", 0) or 0)
        print(f"[{_ts()}] Fallback report saved: {report_path2}")
        print(f"[{_ts()}] fallback shadow_rows_total={shadow_rows2} with_resolved_outcome={resolved2}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
