# EXP-077 — Composición arcoíris + válvula K/D (n combinado)

**Hipótesis:** la composición apilada arcoíris(7-EMA)+válvula K/D produce edge con su n COMBINADO (no asume suma de edges).
**Config congelada:** stoch 14,3,3; DESVIO=5; arcoíris progresión x2 [5,10,20,40,80,160,320]; WR i+1/i+2 close M15.
**Resultados:**
```json
[
  {
    "comp": [
      {
        "n": 2599,
        "w": 1590,
        "wr": 61.2,
        "p": 0.0,
        "exp": "EURUSD_2023_24_COMP_CALL",
        "ok": true
      },
      {
        "n": 2765,
        "w": 1680,
        "wr": 60.8,
        "p": 0.0,
        "exp": "EURUSD_2023_24_COMP_PUT",
        "ok": true
      }
    ],
    "valve": [
      {
        "n": 22802,
        "w": 11035,
        "wr": 48.4,
        "p": 0.0,
        "exp": "EURUSD_2023_24_VALV_CALL",
        "ok": true
      },
      {
        "n": 23145,
        "w": 10972,
        "wr": 47.4,
        "p": 0.0,
        "exp": "EURUSD_2023_24_VALV_PUT",
        "ok": true
      }
    ],
    "label": "EURUSD_2023_24"
  },
  {
    "comp": [
      {
        "n": 16176,
        "w": 9698,
        "wr": 60.0,
        "p": 0.0,
        "exp": "EURUSD_OOS_2012_2022_COMP_CALL",
        "ok": true
      },
      {
        "n": 17053,
        "w": 10121,
        "wr": 59.4,
        "p": 0.0,
        "exp": "EURUSD_OOS_2012_2022_COMP_PUT",
        "ok": true
      }
    ],
    "valve": [
      {
        "n": 138623,
        "w": 66942,
        "wr": 48.3,
        "p": 0.0,
        "exp": "EURUSD_OOS_2012_2022_VALV_CALL",
        "ok": true
      },
      {
        "n": 138283,
        "w": 66935,
        "wr": 48.4,
        "p": 0.0,
        "exp": "EURUSD_OOS_2012_2022_VALV_PUT",
        "ok": true
      }
    ],
    "label": "EURUSD_OOS_2012_2022"
  },
  {
    "comp": [
      {
        "n": 22610,
        "w": 13824,
        "wr": 61.1,
        "p": 0.0,
        "exp": "XAUUSD_COMP_CALL",
        "ok": true
      },
      {
        "n": 19168,
        "w": 11370,
        "wr": 59.3,
        "p": 0.0,
        "exp": "XAUUSD_COMP_PUT",
        "ok": true
      }
    ],
    "valve": [
      {
        "n": 171961,
        "w": 83683,
        "wr": 48.7,
        "p": 0.0,
        "exp": "XAUUSD_VALV_CALL",
        "ok": true
      },
      {
        "n": 175467,
        "w": 85156,
        "wr": 48.5,
        "p": 0.0,
        "exp": "XAUUSD_VALV_PUT",
        "ok": true
      }
    ],
    "label": "XAUUSD"
  }
]
```
**Conclusión del EXP:** medible; reporte n combinado por dataset. Veredicto final en matriz global.
