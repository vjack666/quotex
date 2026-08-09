# Requirements — Fabrica de Herramientas del Edificio

Este SPEC cumple el Laboratory Charter (docs/LAB_CHARTER.md). No modifica ninguno de sus principios.

> Contexto: el Edificio de Contratación YA es una linea de produccion secuencial
> (P1 Recepción → P2 Cerebro → P3 Sala Espera → CONTRATADO). Lo que este SPEC
> formaliza es el *reframe operativo* acordado con el trader: cada experimento
> (EXP-XXX) con identidad experimental previa se convierte en una HERRAMIENTA que
> emite EVIDENCIA, no una orden; y se anaden tres estaciones que hoy faltan
> explicitas — ENSAMBLADOR, INSPECTOR, GOBERNADOR — mas el gap de produccion de
> medir la COMPOSICION (n combinado) en lugar de asumirla.
>
> REVISIÓN 2026-08-09 (trader-humano): la unidad de decisión humana NO es el
> experimento aislado sino el CICLO EXPERIMENTAL. El trader-humano NO decide entre
> experimentos individuales salvo condición de seguridad previamente congelada;
> decide al CIERRE del ciclo, tras ejecutar todos los EXP congelados del lote y
> producir la síntesis conjunta.

## R0 (Unidad de decisión = ciclo, no experimento)
EL trader-humano NO DEBE emitir una decisión de dirección entre experimentos
individuales del mismo ciclo. El sistema DEBE presentar UN dictamen global al
cierre del ciclo experimental (todos los EXP del lote ejecutados y auditados),
y la decisión humana ordinaria DEBE ocurrir solo entonces.

## R12 (Orquestador del ciclo experimental)
CUANDO se inicia un ciclo, el sistema DEBE ejecutar un ORQUESTADOR que planea el
lote completo (hipótesis principal + EXP-076..080), congela parámetros/dataset/
métrica/criterio de cada EXP ANTES de ejecutar, ejecuta todos los EXP sin
modificar reglas entre ellos, y NO DEBE adaptar parámetros tras ver resultados
parciales (prohibido el re-ajuste adaptativo).

## R14 (Reporte individual obligatorio por EXP)
CUANDO un experimento del ciclo termina (o falla de forma registrada), el sistema
DEBE generar un reporte individual `EXP-NNN_reporte.md` en su carpeta propia
(`reports/CICLO-XXX/EXP-NNN/`) con: hipótesis, configuración congelada, dataset,
período, parámetros, n, WR, OOS/holdout, timing (si aplica), anomalías, evidencia,
conclusión DEL experimento (no decisión del director) y referencia al commit. Este
reporte es la evidencia PRIMARIA y NO DEBE eliminarse por existir la matriz global.

## R15 (Persistencia Git del reporte)
CUANDO se genera un reporte individual (R14) o la matriz global (R13), el sistema
DEBE hacer `git add` + `git commit` de ese artefacto y empujarlo al remoto, para
que quede disponible en GitHub para revisión externa (incl. ChatGPT). El commit del
experimento y el commit del ciclo DEBEN ser distinguibles (mensaje prefijado
`EXP-NNN:` vs `CYCLE-XXX:`).

## R16 (Cierre del ciclo condicionado a reportes completos)
SI falta el reporte individual (R14) de alguno de los EXP del lote, ENTONCES el
sistema NO DEBE considerar el ciclo cerrado ni producir la matriz global (R13)
salvo que el EXP conste con un estado de error explícitamente registrado. El cierre
del ciclo requiere evidencia primaria completa de todos los EXP congelados.

## R1 (Identidad de herramienta)
TODO experimento promovido al Edificio DEBE registrarse como HERRAMIENTA con
referencia obligatoria a su EXP-XXX de origen, su WR pooled, su n, su veredicto
Charter y el dominio donde obtuvo evidencia.

## R2 (Contrato de evidencia)
CUANDO una herramienta emite su veredicto, el sistema DEBE producir un objeto
de evidencia con los campos `direction` (LONG/SHORT/NONE), `strength` (0..1),
`confidence` (0..1) y `stage` (P1/P2/P3/CONTRATADO) — y NO DEBE contener ningun
campo de orden (BUY/SELL) ni emitir orden por si misma.

## R3 (Linea de produccion = pisos)
MIENTRAS el material (EURUSD/activo) transita P1→P2→P3, el sistema DEBE exigir
que cada piso emita evidencia de su herramienta correspondiente antes de
permitir el ascenso al piso superior; el ascenso NO DEBE depender de una sola
herramienta aislada.

## R4 (Ensamblador)
CUANDO el activo alcanza estado CONTRATABLE (evidencia acumulada en P3), el
sistema DEBE invocar al ENSAMBLADOR, que DEBE producir exactamente uno de
tres estados: BUY, SELL o NO_TRADE, combinando la evidencia de todas las
herramientas activas segun una regla declarada y congelada.

## R5 (Inspector — guard de conflictos)
SI dos o mas herramientas activas emiten `direction` opuesta con `confidence`
>= 0.5, ENTONCES el sistema DEBE marcar la oportunidad como CONFLICTO y el
ENSAMBLADOR DEBE producir NO_TRADE (la inspeccion precede a la contratacion).

## R6 (Gobernador — riesgo/sizing)
CUANDO el ENSAMBLADOR produce BUY o SELL, el sistema DEBE invocar al
GOBERNADOR antes de enviar la orden, y el GOBERNADOR DEBE calcular el tamano de
lote via Massaniello usando la frecuencia y racha de la SERIE FILTRADA (no de
todo el universo P3), y DEBE vetar la orden si el DD proyectado excede el limite.

## R7 (Gap de produccion — n combinado)
CUANDO se proponga una composicion de dos o mas herramientas como gate, el
sistema DEBE medir el n COMBINADO y la WR sobre ese n, y NO DEBE asumir que la
composicion hereda el edge de las herramientas por separado (requiere experimento
propio: EXP-077).

## R8 (Trazabilidad a experimento)
TODO estado BUY/SELL/NO_TRADE DEBE ser reproducible hasta el conjunto de
herramientas y sus EXP-XXX que lo produjeron, con sus WR/n individuales y
combinados registrados en el reporte inmutable.

## R9 (Dominio — Charter Art. 10/13)
SI una herramienta solo tiene evidencia en EURUSD REAL, ENTONCES el sistema NO
DEBE promoverla a operacion OTC sin validacion OTC previa del propio laboratorio;
el REAL es microscopio, el OTC es ensayo clinico.

## R10 (No promocion por WR aislada)
EL sistema NO DEBE promover una herramienta a produccion usando unicamente su
WR individual; DEBE exigir ademas el n, el holdout/OOS, y (para composiciones) el
n combinado del R7.

## R11 (Experimentos del ciclo congelados)
EL SPEC DEBE declarar explicitamente EXP-076 (validacion de timing de broker:
¿el edge 57% sobrevive al openPrice real ~300s?) y EXP-077 (composicion
arcoiris 7-EMA + valvula K/D medida con n combinado, holdout, OOS) como parte del
ciclo de vida antes de cualquier promocion a REAL.
