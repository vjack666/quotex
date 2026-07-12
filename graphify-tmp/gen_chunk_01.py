# -*- coding: utf-8 -*-
import json, os

BASE = r"C:\Users\v_jac\Desktop\QUOTEX"
OUT = r"C:\Users\v_jac\Desktop\QUOTEX\graphify-tmp\chunk_01.json"

# Absolute file paths (verbatim)
FASE2   = BASE + r"\Documentos\fase 2\FASE 2 — CHECKLIST OPERATIVO PARA COPILOT.md"
EDGE    = BASE + r"\Documentos\files\EDGE_REAL.md"
ESTADO  = BASE + r"\Documentos\files\ESTADO_REAL_SISTEMA.md"
FILTROS = BASE + r"\Documentos\files\FILTROS_CRITICOS.md"
HALLAZ  = BASE + r"\Documentos\files\HALLAZGOS_OPERATIVOS.md"
INDICE  = BASE + r"\Documentos\files\INDICE.md"
MATRIZ  = BASE + r"\Documentos\files\MATRIZ_DE_CALIDAD.md"
METRIC  = BASE + r"\Documentos\files\METRICAS_REALES.md"
PLAN    = BASE + r"\Documentos\files\PLAN_MAESTRO.md"
PLANMAS = BASE + r"\Documentos\files\PLAN_MASANIELLO.md"
QUANT   = BASE + r"\Documentos\files\QUANT_ENGINE_ARQUITECTURA.md"
ROADMAP = BASE + r"\Documentos\files\ROADMAP_TECNICO.md"

AG = BASE + r"\agent"
CHANGELOG = AG + r"\CHANGELOG.md"
CONTEXT   = AG + r"\CONTEXT.md"
DECISIONS = AG + r"\DECISIONS.md"
HANDOFF   = AG + r"\HANDOFF.md"
PROJECT   = AG + r"\PROJECT_STATE.md"
SESSION   = AG + r"\SESSION_PROTOCOL.md"
START     = AG + r"\START.md"
TASKS     = AG + r"\TASKS.md"

nodes = []
edges = []

def add_node(nid, label, ftype, src, loc, author=None):
    nodes.append({
        "id": nid,
        "label": label,
        "file_type": ftype,
        "source_file": src,
        "source_location": loc,
        "source_url": None,
        "captured_at": None,
        "author": author,
        "contributor": None,
    })

def add_edge(s, t, rel, conf, cs, src, loc, weight=1.0):
    edges.append({
        "source": s,
        "target": t,
        "relation": rel,
        "confidence": conf,
        "confidence_score": cs,
        "source_file": src,
        "source_location": loc,
        "weight": weight,
    })

# ---------------- DOCUMENT NODES ----------------
docs = [
    ("documentos_fase_2_fase_2_checklist_operativo_para_copilot_document", "Fase 2 Checklist Operativo (Copilot)", FASE2, None),
    ("documentos_files_edge_real_document", "Edge Real del Sistema", EDGE, None),
    ("documentos_files_estado_real_sistema_document", "Estado Real del Sistema", ESTADO, None),
    ("documentos_files_filtros_criticos_document", "Filtros Críticos (Vetos Binarios)", FILTROS, None),
    ("documentos_files_hallazgos_operativos_document", "Hallazgos Operativos y Riesgos", HALLAZ, None),
    ("documentos_files_indice_document", "Índice de Documentación", INDICE, None),
    ("documentos_files_matriz_de_calidad_document", "Matriz de Calidad A/B/C/D", MATRIZ, None),
    ("documentos_files_metricas_reales_document", "Métricas Reales a Medir", METRIC, None),
    ("documentos_files_plan_maestro_document", "Plan Maestro del Sistema", PLAN, None),
    ("documentos_files_plan_masaniello_document", "Plan Masaniello (Gestión de Riesgo)", PLANMAS, None),
    ("documentos_files_quant_engine_arquitectura_document", "Quant Engine — Arquitectura Operativa", QUANT, None),
    ("documentos_files_roadmap_tecnico_document", "Roadmap Técnico por Fases", ROADMAP, None),
    ("agent_changelog_document", "CHANGELOG (agent memory)", CHANGELOG, None),
    ("agent_context_document", "CONTEXT (conocimiento técnico persistente)", CONTEXT, None),
    ("agent_decisions_document", "DECISIONS (registro de decisiones)", DECISIONS, None),
    ("agent_handoff_document", "HANDOFF (transferencia de sesión)", HANDOFF, None),
    ("agent_project_state_document", "PROJECT_STATE (estado del proyecto)", PROJECT, None),
    ("agent_session_protocol_document", "SESSION_PROTOCOL (protocolo de trabajo)", SESSION, None),
    ("agent_start_document", "START (punto de entrada autónomo)", START, None),
    ("agent_tasks_document", "TASKS (lista de tareas)", TASKS, None),
]
for nid, label, src, loc in docs:
    add_node(nid, label, "document", src, loc)

# ---------------- CONCEPT NODES ----------------
concepts = [
    ("documentos_files_edge_real_edge_confluence", "Edge de Confluencia (HTF × Zona × Patrón 1m)", EDGE, 195),
    ("documentos_files_filtros_criticos_htf_alignment_gate", "Veto HTF_ALIGNMENT_GATE", FILTROS, 21),
    ("documentos_files_filtros_criticos_pattern_1m_gate", "Veto PATTERN_1M_GATE", FILTROS, 56),
    ("documentos_files_filtros_criticos_zone_age_gate", "Veto ZONE_AGE_GATE", FILTROS, 88),
    ("documentos_files_filtros_criticos_payout_gate", "Veto PAYOUT_GATE", FILTROS, 115),
    ("documentos_files_filtros_criticos_spike_gate", "Veto SPIKE_GATE", FILTROS, 149),
    ("documentos_files_filtros_criticos_zone_memory_wall_gate", "Veto ZONE_MEMORY_WALL_GATE", FILTROS, 180),
    ("documentos_files_filtros_criticos_session_limit_gate", "Veto SESSION_LIMIT_GATE", FILTROS, 212),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "_pre_validate_entry (gate de riesgo)", ESTADO, 46),
    ("documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", "Fase 2 — 9 Vetos de Entrada", FASE2, 28),
    ("documentos_fase_2_fase_2_checklist_operativo_para_copilot_strat_b_bug", "Bug STRAT-B silenciosamente bloqueado (Fase 2)", FASE2, 16),
    ("documentos_files_matriz_de_calidad_quality_matrix_abcd", "Matriz de Calidad A/B/C/D", MATRIZ, 17),
    ("documentos_files_plan_masaniello_masaniello_engine", "Motor Masaniello 5/2", PLANMAS, 8),
    ("documentos_files_plan_masaniello_conservative_mode", "Modo Conservador Post-Pérdida (Masaniello)", PLANMAS, 109),
    ("documentos_files_hallazgos_operativos_credential_risk", "Riesgo: Credenciales en texto plano", HALLAZ, 174),
    ("documentos_files_hallazgos_operativos_order_timeout_risk", "Riesgo RT-01: Ambigüedad de orden en timeout", HALLAZ, 117),
    ("documentos_files_hallazgos_operativos_reconnect_risk", "Riesgo RT-02: Reconexión concurrente", HALLAZ, 139),
    ("documentos_files_estado_real_sistema_shadow_mode", "Modo Shadow NEW vs OLD (observador)", ESTADO, 79),
    ("documentos_files_estado_real_sistema_gonogo_framework", "Framework GO/NO-GO de promoción", ESTADO, 106),
    ("documentos_files_metricas_reales_metrics", "Métricas M1–M12 (winrate, gale, filtros)", METRIC, 27),
    ("documentos_files_quant_engine_arquitectura_layers", "Capas del Quant Engine (6 capas)", QUANT, 1),
    ("documentos_files_plan_maestro_strat_a_strat_b", "Estrategias STRAT-A (consolidación) / STRAT-B (Wyckoff)", PLAN, 35),
    ("documentos_files_plan_maestro_reject_first_principle", "Principio Rector: buscar razones para NO operar", PLAN, 111),
    ("agent_context_massaniello_risk", "MassanielloRiskManager (gestor de riesgo activo)", CONTEXT, 79),
    ("agent_project_state_four_layer_architecture", "Arquitectura de 4 capas (connection→scanner→strats→executor)", PROJECT, 21),
    ("agent_decisions_agent_autonomous_workflow", "Decisión: workflow autónomo /agent", DECISIONS, 8),
    ("agent_decisions_sdd_harness", "Decisión: harness SDD (Spec Driven Development)", DECISIONS, 57),
    ("agent_decisions_roadmap_dual_representation", "Decisión: roadmap dual (JSON + Markdown)", DECISIONS, 78),
    ("agent_project_state_roadmap_complete", "Roadmap completo: 22/22 features done", PROJECT, 4),
    ("agent_context_strategy_a_consolidation", "Strategy A — Consolidation (5m)", CONTEXT, 28),
    ("agent_context_strategy_b_wyckoff", "Strategy B — Wyckoff Spring/Upthrust", CONTEXT, 44),
    ("agent_decisions_demo_only_enforcement", "Decisión: demo-only para fase Masaniello", DECISIONS, 70),
]
for nid, label, src, loc in concepts:
    add_node(nid, label, "concept", src, loc)

# ---------------- RATIONALE NODES ----------------
rationales = [
    ("agent_decisions_massaniello_replaces_martingale_rationale", "Rationale: Massaniello reemplaza Martingale", DECISIONS, 21),
    ("agent_decisions_monolith_refactor_rationale", "Rationale: refactor del monolito en 4 capas", DECISIONS, 44),
    ("agent_decisions_demo_only_enforcement_rationale", "Rationale: solo PRACTICE para Masaniello", DECISIONS, 70),
    ("agent_decisions_sdd_harness_rationale", "Rationale: adoptar harness SDD", DECISIONS, 57),
    ("agent_decisions_agent_autonomous_workflow_rationale", "Rationale: carpeta /agent para resumen cross-machine", DECISIONS, 8),
    ("agent_decisions_roadmap_dual_representation_rationale", "Rationale: feature_list.json + docs/ROADMAP.md", DECISIONS, 78),
    ("documentos_files_plan_maestro_reject_first_rationale", "Rationale: principio reject-first", PLAN, 111),
    ("documentos_files_plan_masaniello_not_problem_rationale", "Rationale: el Masaniello no es el problema (son las entradas)", PLANMAS, 6),
]
for nid, label, src, loc in rationales:
    add_node(nid, label, "rationale", src, loc)

# ---------------- EDGES ----------------
# Document -> Concept (references, EXTRACTED 1.0)
doc_refs = [
    (docs[1][0], "documentos_files_edge_real_edge_confluence", EDGE, 195),
    (docs[1][0], "documentos_files_filtros_criticos_htf_alignment_gate", EDGE, 22),
    (docs[1][0], "documentos_files_filtros_criticos_pattern_1m_gate", EDGE, 64),
    (docs[1][0], "documentos_files_filtros_criticos_spike_gate", EDGE, 88),
    (docs[1][0], "documentos_files_filtros_criticos_zone_memory_wall_gate", EDGE, 107),
    (docs[1][0], "documentos_files_plan_masaniello_masaniello_engine", EDGE, 11),
    (docs[2][0], "documentos_files_estado_real_sistema_pre_validate_entry", ESTADO, 46),
    (docs[2][0], "documentos_files_estado_real_sistema_shadow_mode", ESTADO, 79),
    (docs[2][0], "documentos_files_estado_real_sistema_gonogo_framework", ESTADO, 106),
    (docs[3][0], "documentos_files_filtros_criticos_htf_alignment_gate", FILTROS, 21),
    (docs[3][0], "documentos_files_filtros_criticos_pattern_1m_gate", FILTROS, 56),
    (docs[3][0], "documentos_files_filtros_criticos_zone_age_gate", FILTROS, 88),
    (docs[3][0], "documentos_files_filtros_criticos_payout_gate", FILTROS, 115),
    (docs[3][0], "documentos_files_filtros_criticos_spike_gate", FILTROS, 149),
    (docs[3][0], "documentos_files_filtros_criticos_zone_memory_wall_gate", FILTROS, 180),
    (docs[3][0], "documentos_files_filtros_criticos_session_limit_gate", FILTROS, 212),
    (docs[3][0], "documentos_files_estado_real_sistema_pre_validate_entry", FILTROS, 256),
    (docs[4][0], "documentos_files_hallazgos_operativos_credential_risk", HALLAZ, 174),
    (docs[4][0], "documentos_files_hallazgos_operativos_order_timeout_risk", HALLAZ, 117),
    (docs[4][0], "documentos_files_hallazgos_operativos_reconnect_risk", HALLAZ, 139),
    (docs[4][0], "documentos_files_plan_masaniello_masaniello_engine", HALLAZ, 92),
    (docs[4][0], "documentos_files_plan_maestro_strat_a_strat_b", HALLAZ, 73),
    (docs[6][0], "documentos_files_matriz_de_calidad_quality_matrix_abcd", MATRIZ, 17),
    (docs[6][0], "documentos_files_estado_real_sistema_pre_validate_entry", MATRIZ, 174),
    (docs[7][0], "documentos_files_metricas_reales_metrics", METRIC, 27),
    (docs[8][0], "documentos_files_plan_maestro_strat_a_strat_b", PLAN, 35),
    (docs[8][0], "documentos_files_plan_maestro_reject_first_principle", PLAN, 111),
    (docs[8][0], "documentos_files_edge_real_edge_confluence", PLAN, 35),
    (docs[9][0], "documentos_files_plan_masaniello_masaniello_engine", PLANMAS, 8),
    (docs[9][0], "documentos_files_plan_masaniello_conservative_mode", PLANMAS, 109),
    (docs[10][0], "documentos_files_quant_engine_arquitectura_layers", QUANT, 1),
    (docs[11][0], "documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", ROADMAP, 109),
    (docs[11][0], "documentos_files_estado_real_sistema_shadow_mode", ROADMAP, 163),
    (docs[11][0], "documentos_files_plan_masaniello_conservative_mode", ROADMAP, 372),
    (docs[0][0], "documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", FASE2, 28),
    (docs[0][0], "documentos_fase_2_fase_2_checklist_operativo_para_copilot_strat_b_bug", FASE2, 16),
    (docs[0][0], "documentos_files_estado_real_sistema_pre_validate_entry", FASE2, 13),
    # INDICE references its sibling documents (TOC)
    (docs[5][0], docs[8][0], INDICE, 8),
    (docs[5][0], docs[1][0], INDICE, 13),
    (docs[5][0], docs[6][0], INDICE, 18),
    (docs[5][0], docs[3][0], INDICE, 23),
    (docs[5][0], docs[11][0], INDICE, 27),
    (docs[5][0], docs[9][0], INDICE, 31),
    (docs[5][0], docs[7][0], INDICE, 35),
    (docs[5][0], docs[4][0], INDICE, 39),
    (docs[5][0], docs[2][0], INDICE, 43),
    # agent documents
    (docs[13][0], "agent_context_massaniello_risk", CONTEXT, 79),
    (docs[13][0], "agent_context_strategy_a_consolidation", CONTEXT, 28),
    (docs[13][0], "agent_context_strategy_b_wyckoff", CONTEXT, 44),
    (docs[14][0], "agent_decisions_massaniello_replaces_martingale_rationale", DECISIONS, 21),
    (docs[14][0], "agent_decisions_monolith_refactor_rationale", DECISIONS, 44),
    (docs[14][0], "agent_decisions_demo_only_enforcement_rationale", DECISIONS, 70),
    (docs[14][0], "agent_decisions_sdd_harness_rationale", DECISIONS, 57),
    (docs[14][0], "agent_decisions_agent_autonomous_workflow_rationale", DECISIONS, 8),
    (docs[14][0], "agent_decisions_roadmap_dual_representation_rationale", DECISIONS, 78),
    (docs[16][0], "agent_project_state_four_layer_architecture", PROJECT, 21),
    (docs[16][0], "agent_project_state_roadmap_complete", PROJECT, 4),
    (docs[16][0], "agent_context_massaniello_risk", PROJECT, 15),
    (docs[16][0], "agent_context_strategy_a_consolidation", PROJECT, 64),
    (docs[16][0], "agent_context_strategy_b_wyckoff", PROJECT, 65),
    (docs[15][0], "agent_project_state_roadmap_complete", HANDOFF, 5),
    (docs[19][0], "agent_project_state_roadmap_complete", TASKS, 4),
    (docs[12][0], "agent_context_massaniello_risk", CHANGELOG, 34),
    (docs[12][0], "agent_project_state_four_layer_architecture", CHANGELOG, 44),
    (docs[12][0], "agent_project_state_roadmap_complete", CHANGELOG, 23),
    (docs[18][0], docs[16][0], START, 37),
    (docs[18][0], docs[15][0], START, 38),
    (docs[18][0], docs[19][0], START, 39),
    (docs[18][0], docs[14][0], START, 40),
    (docs[18][0], docs[12][0], START, 41),
    (docs[18][0], docs[13][0], START, 42),
    (docs[18][0], docs[17][0], START, 43),
    (docs[17][0], "agent_project_state_four_layer_architecture", SESSION, 39),
    (docs[17][0], "agent_context_massaniello_risk", SESSION, 41),
]
for s, t, src, loc in doc_refs:
    add_edge(s, t, "references", "EXTRACTED", 1.0, src, loc)

# Concept -> Concept
# pre_validate implements each gate (EXTRACTED)
gate_impl = [
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_htf_alignment_gate", FASE2, 6687),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_pattern_1m_gate", FASE2, 6722),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_zone_age_gate", FASE2, 6731),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_payout_gate", FASE2, 6645),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_spike_gate", FASE2, 6667),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_zone_memory_wall_gate", FASE2, 6735),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_files_filtros_criticos_session_limit_gate", FASE2, 6638),
]
for s, t, src, loc in gate_impl:
    add_edge(s, t, "references", "EXTRACTED", 1.0, src, loc)

# semantically_similar_to (INFERRED)
sim = [
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_htf_alignment_gate", 0.85),
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_pattern_1m_gate", 0.85),
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_zone_age_gate", 0.75),
    ("documentos_files_plan_masaniello_masaniello_engine", "agent_context_massaniello_risk", 0.95),
    ("documentos_files_plan_masaniello_conservative_mode", "documentos_files_plan_masaniello_masaniello_engine", 0.85),
    ("documentos_files_matriz_de_calidad_quality_matrix_abcd", "documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", 0.75),
    ("documentos_files_estado_real_sistema_shadow_mode", "documentos_files_estado_real_sistema_gonogo_framework", 0.85),
    ("documentos_files_quant_engine_arquitectura_layers", "agent_project_state_four_layer_architecture", 0.95),
    ("documentos_files_plan_maestro_strat_a_strat_b", "agent_context_strategy_a_consolidation", 0.85),
    ("documentos_files_plan_maestro_strat_a_strat_b", "agent_context_strategy_b_wyckoff", 0.85),
    ("documentos_files_estado_real_sistema_pre_validate_entry", "documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", 0.95),
    ("documentos_files_plan_maestro_reject_first_principle", "documentos_fase_2_fase_2_checklist_operativo_para_copilot_phase2_vetos", 0.85),
    ("documentos_files_hallazgos_operativos_order_timeout_risk", "documentos_files_hallazgos_operativos_reconnect_risk", 0.75),
    ("documentos_files_plan_masaniello_conservative_mode", "agent_context_massaniello_risk", 0.85),
    ("documentos_files_metricas_reales_metrics", "documentos_files_matriz_de_calidad_quality_matrix_abcd", 0.65),
    ("agent_decisions_sdd_harness", "agent_decisions_roadmap_dual_representation", 0.65),
]
for s, t, cs in sim:
    add_edge(s, t, "semantically_similar_to", "INFERRED", cs, None, None)

# conceptually_related_to (INFERRED)
rel = [
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_htf_alignment_gate", 0.85),
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_pattern_1m_gate", 0.85),
    ("documentos_files_edge_real_edge_confluence", "documentos_files_filtros_criticos_zone_age_gate", 0.75),
    ("documentos_files_plan_maestro_strat_a_strat_b", "documentos_files_estado_real_sistema_pre_validate_entry", 0.75),
    ("documentos_files_estado_real_sistema_shadow_mode", "documentos_files_estado_real_sistema_pre_validate_entry", 0.75),
    ("documentos_files_plan_maestro_reject_first_principle", "documentos_files_matriz_de_calidad_quality_matrix_abcd", 0.75),
    ("agent_project_state_four_layer_architecture", "agent_context_strategy_a_consolidation", 0.75),
    ("agent_project_state_four_layer_architecture", "agent_context_strategy_b_wyckoff", 0.75),
    ("documentos_files_filtros_criticos_session_limit_gate", "documentos_files_plan_masaniello_masaniello_engine", 0.75),
]
for s, t, cs in rel:
    add_edge(s, t, "conceptually_related_to", "INFERRED", cs, None, None)

# rationale_for (EXTRACTED 1.0)
rat = [
    ("agent_decisions_massaniello_replaces_martingale_rationale", "agent_context_massaniello_risk", DECISIONS, 21),
    ("agent_decisions_monolith_refactor_rationale", "agent_project_state_four_layer_architecture", DECISIONS, 44),
    ("agent_decisions_demo_only_enforcement_rationale", "agent_decisions_demo_only_enforcement", DECISIONS, 70),
    ("agent_decisions_sdd_harness_rationale", "agent_decisions_sdd_harness", DECISIONS, 57),
    ("agent_decisions_agent_autonomous_workflow_rationale", "agent_decisions_agent_autonomous_workflow", DECISIONS, 8),
    ("agent_decisions_roadmap_dual_representation_rationale", "agent_decisions_roadmap_dual_representation", DECISIONS, 78),
    ("documentos_files_plan_maestro_reject_first_rationale", "documentos_files_plan_maestro_reject_first_principle", PLAN, 111),
    ("documentos_files_plan_masaniello_not_problem_rationale", "documentos_files_plan_masaniello_masaniello_engine", PLANMAS, 6),
]
for s, t, src, loc in rat:
    add_edge(s, t, "rationale_for", "EXTRACTED", 1.0, src, loc)

# ---------------- OUTPUT ----------------
out = {
    "nodes": nodes,
    "edges": edges,
    "hyperedges": [],
    "input_tokens": 0,
    "output_tokens": 0,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("nodes:", len(nodes))
print("edges:", len(edges))
print("wrote:", OUT)
