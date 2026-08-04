# Configuración parametrizable de P2 y P3
# Objetivo: exponer cada decisión del Edificio como variable para que el laboratorio y la red neuronal puedan experimentar.

## P2 — Parámetros

```yaml
p2:
  brake_eval:
    window: 15                  # Ventana de evaluación del impulso
    min_pips: 5.0               # Mínimo de pips para considerar extensión clara
    require_alternation: false  # Si requiere alternación de impulsos
    partial_confirm: true       # Si acepta freno parcialmente confirmado (no quiquilloso)

  stochastic:
    k_period: 14                # Período K del estocástico
    d_period: 3                 # Período D del estocástico
    overbought: 80              # Umbral sobrecompra para PUT
    oversold: 20                # Umbral sobreventa para CALL

  estadia:
    brake_ok_no_revoke: true    # Si brake_ok instantáneo no revoca tarjeta
    perder_extremo_baja_p1: true # Si perder extremo baja a P1

  poi:
    descarte_ruptura_sin_rebote: true  # Descarte solo si POI roto + sin rebote
    reevaluacion_poi_cercano: true      # Si hay rebote, reevalúa en POI cercano
    umbral_proximidad_poi_pips: 50      # Distancia máxima para considerar POI cercano
```

## P3 — Parámetros

```yaml
p3:
  entrada_desde_p2:
    requiere_freno_confirmado: true
    requiere_extremo_vigente: true
    requiere_separacion_kd_vela_cerrada: true

  filtro_sticky_cross:
    activo: true                # Si filtra cruces pegajosos
    min_separacion_kd: 2.0      # Separación mínima K/D para considerar cruce limpio

  permanencia:
    condiciones: [paga_bien, sigue_frenado, sigue_en_extremo]
    perder_freno_o_extremo_vuelve_p2: true

  cruce:
    max_cross_ago: 12           # Velas máximas de espera del cruce desde P2
    direccion_debe_coincidir_con_extremo: true  # CALL requiere extremo <=20, PUT >=80

  salida:
    perder_pago_sale_edificio: true  # Regla 1
```

## Uso

El laboratorio debe:
1. Cargar este archivo como config base.
2. Permitir variar cualquier parámetro por experimento.
3. Documentar en cada EXP-XXX.md qué parámetros se modificaron y sus valores.
4. Medir impacto en win rate, robustness y reproducibility por cada combinación.
