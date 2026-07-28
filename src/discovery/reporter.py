"""Reporter del Discovery Engine (T8) + Lifecycle (T12) — Agente C.

- emit_lab_doc(law, path): genera docs/LAB_0XX_<slug>.md canónico con los campos
  R7 (variables, efecto, IC, walk-forward, p, frecuencia, markets, sources,
  state) y referencia script_ref.
- record_law(law, store): delega a store.save_law (NO sobrescribe si ya existe).
- add_transition(store, law_id, new_state, version, motivo): actualiza el state
  de la ley en el store (si SQLiteLawStore -> UPDATE; si InMemory -> replace).
  La ley OBSOLETA/VALIDADA NO se borra, solo cambia de state.
- transition_log(store, law_id): registro de transiciones (opcional).

NO importa de scanner/strat_fractal/bot. NO usa time.now(). Determinista.
"""

from __future__ import annotations

import os
import re
from typing import Any

from .types import Law
from .storage import InMemoryLawStore, LawStorage

__all__ = ["emit_lab_doc", "record_law", "add_transition", "transition_log", "slugify"]


def slugify(name: str) -> str:
    """Convierte un nombre de ley en slug de archivo (sin acentos, "-" separa)."""
    s = (name or "").lower()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i")
    s = s.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "ley"


def _law_to_doc(law: Law) -> str:
    """Construye el markdown canónico del LAB con campos R7 + markets/sources/state."""
    lo, hi = law.ci if law.ci else (0.0, 0.0)
    lines: list[str] = []
    lines.append(f"# LAB {law.id} — {law.name}")
    lines.append("")
    lines.append(f"> script_ref: `{law.script_ref or 'N/A'}`  ")
    lines.append(f"> discovery_version: `{law.discovery_version}`  ")
    lines.append(f"> state: `{law.state}`")
    lines.append("")
    lines.append("## R7 — Métricas de la ley")
    lines.append("")
    lines.append(f"- **variables**: {law.conditions}")
    lines.append(f"- **efecto**: probabilidad de rebote = {law.probability:.4f}")
    lines.append(f"- **IC**: [{lo:.4f}, {hi:.4f}]")
    lines.append(f"- **walk-forward**: estado validado por hold-out "
                 f"(train/test por split_year); n={law.cases_studied}")
    lines.append(f"- **p**: {law.p_value:.6f}")
    lines.append(f"- **frecuencia**: {law.cases_studied} casos estudiados "
                 f"(confianza {law.confidence})")
    lines.append(f"- **markets**: {', '.join(law.markets) if law.markets else '-'}")
    lines.append(f"- **sources**: {', '.join(law.sources) if law.sources else '-'}")
    lines.append(f"- **timeframes**: {', '.join(law.timeframes) if law.timeframes else '-'}")
    lines.append(f"- **state**: {law.state}")
    lines.append("")
    lines.append("## Explicabilidad")
    lines.append("")
    lines.append(f"Ley `{law.id}` (`{law.name}`) describe una relación estadística "
                 f"observada en el Atlas y validada por walk-forward. Su state actual "
                 f"es `{law.state}`.")
    lines.append("")
    lines.append("---")
    lines.append("Documento generado por `discovery.reporter.emit_lab_doc` "
                 "(Discovery Engine, Agente C).")
    return "\n".join(lines) + "\n"


def emit_lab_doc(law: Law, path: str) -> str:
    """Genera el .md canónico en `path` (docs/LAB_0XX_<slug>.md). Devuelve path."""
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    doc = _law_to_doc(law)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


def record_law(law: Law, store: LawStorage) -> None:
    """Delega a store.save_law. NO sobrescribe si la ley ya existe (R5/R12)."""
    store.save_law(law)


def _upsert(store: LawStorage, law: Law) -> None:
    """Actualiza una ley existente en el store (lifecycle T12).

    La ley NO se borra: solo cambia de state (u otros campos). Soporta:
    - InMemoryLawStore: reemplaza en el dict (no borra).
    - SQLiteLawStore (B): emite un UPDATE sobre la tabla `leyes`.
    - Cualquier otro LawStorage: intenta replace_law; si no, fuerza el
      reemplazo por reflección del diccionario interno `_laws` cuando exista.
    """
    # 1) SQLiteLawStore (B): UPDATE explícito sobre la tabla `leyes`.
    conn = getattr(store, "conn", None)
    if conn is not None:
        try:
            cur = conn.execute(
                "UPDATE leyes SET state = ?, probability = ?, confidence = ?, "
                "conditions = ?, script_ref = ?, discovery_version = ? WHERE id = ?",
                (law.state, law.probability, law.confidence, law.conditions,
                 law.script_ref, law.discovery_version, law.id),
            )
            if cur.rowcount >= 0:
                conn.commit()
                return
        except Exception:
            # si falla el UPDATE (p.ej. tabla sin columna), caer a replace_law.
            pass

    # 2) InMemoryLawStore / cualquier store con replace_law.
    if hasattr(store, "replace_law"):
        store.replace_law(law)  # type: ignore[attr-defined]
        return

    # 3) Fallback genérico por reflección del dict interno.
    existing = store.get_law(law.id)
    if existing is None:
        store.save_law(law)
    else:
        inner = getattr(store, "_laws", None)
        if isinstance(inner, dict):
            inner[law.id] = law
        else:
            store.save_law(law)


def _log_transition(store: LawStorage, law_id: str, new_state: str,
                    version: str, motivo: str) -> None:
    log = getattr(store, "_transitions", None)
    if log is None:
        log = {}
        try:
            store._transitions = log  # type: ignore[attr-defined]
        except Exception:
            pass
    if isinstance(log, dict):
        log.setdefault(law_id, []).append(
            {"state": new_state, "version": version, "motivo": motivo}
        )


def add_transition(store: LawStorage, law_id: str, new_state: str,
                  version: str, motivo: str) -> Law | None:
    """Cambia el state de la ley `law_id` a `new_state`. La ley NO se borra.

    Devuelve la ley actualizada, o None si no existía.
    """
    if new_state not in Law.VALID_STATES:
        raise ValueError(f"state inválido para lifecycle: {new_state!r}")
    law = store.get_law(law_id)
    if law is None:
        return None
    updated = Law(
        id=law.id,
        name=law.name,
        conditions=law.conditions,
        probability=law.probability,
        confidence=law.confidence,
        markets=law.markets,
        sources=law.sources,
        timeframes=law.timeframes,
        cases_studied=law.cases_studied,
        state=new_state,
        discovery_version=law.discovery_version,
        script_ref=law.script_ref,
        p_value=law.p_value,
        ci=law.ci,
    )
    _upsert(store, updated)
    _log_transition(store, law_id, new_state, version, motivo)
    return updated


def transition_log(store: LawStorage, law_id: str) -> list[dict[str, Any]]:
    """Registro de transiciones de lifecycle para una ley (opcional)."""
    log = getattr(store, "_transitions", None)
    if isinstance(log, dict):
        return list(log.get(law_id, []))
    return []


# Re-export para conveniencia de tests / ensamblaje.
__all__ = ["emit_lab_doc", "record_law", "add_transition", "transition_log",
           "slugify", "InMemoryLawStore"]
