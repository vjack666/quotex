"""Renderer del panel HUB para STRAT-F.

Dibuja el resultado de un ciclo: aceptadas vs rechazadas con la razón
de cada rechazo. Es lo que Ruben pidió ver: el bot como portero que
dice "NO" de forma explicable.

Usa Rich para color semántico (verde=aceptada, rojo=rechazada) y
barras de aceptación. Si Rich no está instalado, cae a texto plano.
"""

from __future__ import annotations

from .strat_f_state import StratFHubState

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    _RICH = True
except Exception:  # pragma: no cover — Rich opcional
    _RICH = False


_REJECT_LABELS = {
    "M1 no rechaza la banda (cierra fuera)": "M1 no rebota (cierra fuera)",
    "M15 rango roto: no operar rebotes": "Rango M15 roto",
    "zona muy joven": "Zona muy joven",
    "CALL contra tendencia M15": "CALL vs tendencia M15",
    "PUT contra tendencia M15": "PUT vs tendencia M15",
    "payout insuficiente": "Payout < mínimo",
    "score insuficiente": "Score < mínimo",
}


def _shorten(reason: str) -> str:
    for k, v in _REJECT_LABELS.items():
        if reason.startswith(k):
            return v
    return reason[:34]


def _bar(n: int, total: int) -> str:
    if total <= 0:
        return "[..........]"
    filled = int(round((n / total) * 10))
    return "[" + "#" * filled + "." * (10 - filled) + "]"


def _plain(state: StratFHubState) -> str:
    total = state.total or 1
    accepted = len(state.accepted)
    rejected = len(state.rejected)
    pct = int(round((accepted / total) * 100)) if total else 0
    lines: list[str] = []
    lines.append("STRAT-F — QUALITY DASHBOARD")
    lines.append("")
    lines.append(f"  Activos evaluados : {state.total_assets or total}")
    lines.append(f"  Señales aceptadas: {accepted}  {_bar(accepted, total)} {pct}%")
    lines.append(f"  Rechazadas       : {rejected}  {_bar(rejected, total)} {100 - pct}%")
    lines.append("")
    lines.append("ACEPTADAS")
    if state.accepted:
        for c in state.accepted:
            lines.append(
                f"  {c.asset:<14} {c.direction.upper():<4} "
                f"fuerza={c.strength:>3}  payout={c.payout:>3}%"
            )
    else:
        lines.append("  (ninguna pasó los filtros)")
    lines.append("")
    lines.append("RECHAZADAS (y por qué)")
    if state.rejected:
        for c in state.rejected:
            lines.append(f"  {c.asset:<14} {_shorten(c.skip_reason)}")
    else:
        lines.append("  (ninguna rechazada)")
    lines.append("")
    lines.append("Principio: el bot prefiere NO operar a entrar mal.")
    return "\n".join(lines)


def _rich(state: StratFHubState) -> str:
    total = state.total or 1
    accepted = len(state.accepted)
    rejected = len(state.rejected)
    pct = int(round((accepted / total) * 100)) if total else 0

    title = Text("STRAT-F — QUALITY DASHBOARD", style="bold cyan")
    table = Table.grid(padding=(0, 2))
    table.add_row(
        Text("Activos evaluados", style="bold"),
        Text(str(state.total_assets or total), style="white"),
    )
    table.add_row(
        Text("Aceptadas", style="bold green"),
        Text(f"{accepted}  {_bar(accepted, total)} {pct}%", style="green"),
    )
    table.add_row(
        Text("Rechazadas", style="bold red"),
        Text(f"{rejected}  {_bar(rejected, total)} {100 - pct}%", style="red"),
    )

    acc_panel = Table(show_header=True, header_style="bold green")
    acc_panel.add_column("Activo", style="cyan", no_wrap=True)
    acc_panel.add_column("Dir", style="white")
    acc_panel.add_column("Fuerza", style="green")
    acc_panel.add_column("Payout", style="white")
    if state.accepted:
        for c in state.accepted:
            acc_panel.add_row(
                c.asset, c.direction.upper(), str(c.strength), f"{c.payout}%"
            )
    else:
        acc_panel.add_row("(ninguna pasó los filtros)", "", "", "")

    rej_panel = Table(show_header=True, header_style="bold red")
    rej_panel.add_column("Activo", style="cyan", no_wrap=True)
    rej_panel.add_column("Razón del rechazo", style="red")
    if state.rejected:
        for c in state.rejected:
            rej_panel.add_row(c.asset, _shorten(c.skip_reason))
    else:
        rej_panel.add_row("(ninguna rechazada)", "")

    console = Console(width=72, record=True)
    console.print(title)
    console.print(table)
    console.print(Text("✅ ACEPTADAS", style="bold green"))
    console.print(acc_panel)
    console.print(Text("❌ RECHAZADAS (y por qué)", style="bold red"))
    console.print(rej_panel)
    console.print(
        Text("Principio: el bot prefiere NO operar a entrar mal.", style="dim")
    )
    return console.export_text()


def render_dashboard(state: StratFHubState) -> str:
    if _RICH:
        try:
            return _rich(state)
        except Exception:
            return _plain(state)
    return _plain(state)
