"""Test T8 — adversarial: ningún .py de src/observador/ usa reloj de pared."""
import pathlib
import re

PATTERN = re.compile(r"time\.time\(|datetime\.now\(|datetime\.utcnow\(")

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "observador"


def test_no_wallclock_in_observador_sources():
    files = sorted(SRC.glob("**/*.py"))
    assert files, f"no se encontraron .py en {SRC}"
    offenders = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line):
                offenders.append(f"{f.name}:{i}: {line.strip()}")
    assert not offenders, "reloj de pared prohibido en src/observador/:\n" + "\n".join(offenders)
