# Índice EXP-075 — Duración/tipo de Fase A como variable continua

| Campo | Valor |
|---|---|
| ID | EXP-075 |
| Título | ¿La duración (y descriptores continuos) de la Fase A predicen la dirección/calidad del breakout como variable continua? |
| Dominio | REAL (descubrimiento, Art. 13) |
| Activo / TF | EURUSD / M15 |
| Período datos | 2022-01-02 → 2026-08-06 (114,237 velas) |
| n Fases A | 3307 |
| Hypótesis | H1: duración continua predice monotonamente la resolución de la fase |
| Veredicto | **REFUTADA** (H1 rechazada; 0/36 descriptivos significativos FDR; OR_Q4≈1.0; OOS plano) |
| Cumple Charter | Sí |

## Archivos
- `hypothesis_exp075.md` — contrato congelado (Art. 6)
- `risks_exp075.md` — amenazas + mitigaciones
- `validation_exp075.md` — veredicto del tribunal
- `scripts/lab_exp075_phaseA_continuous.py` — experimento reproducible (seed=42)
- `reports/EXP-075/summary.txt` — salida inmutable
- `reports/EXP-075/protocol_frozen.json` — protocolo congelado
- `data/strategy_lab/exp075_phaseA_features.parquet` — features con etiqueta

## Relación con el hilo del lab
- EXP-074: K=2 sugirió población mixta (sil 0.2185).
- EXP-074b (freno): RECHAZÓ la partición GMM → duración = continuo, no 2 cajas.
- **EXP-075**: ese continuo TAMPOCO predice el breakout (REFUTADA). Cierra el hilo:
  la duración de la Fase A es ruido respecto a la resolución, en muestra y OOS.
