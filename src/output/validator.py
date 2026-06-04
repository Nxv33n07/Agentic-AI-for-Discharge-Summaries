from src.agent.state import AgentState, FactStatus


def validate_state(state: AgentState) -> list[str]:
    issues = []
    if not state.demographics:
        issues.append("[MISSING] demographics — no patient demographics found.")
    else:
        for k, fact in state.demographics.items():
            if fact.status in (FactStatus.MISSING,):
                issues.append(f"[MISSING] demographics.{k} — not documented.")

    fact_fields = {
        "admission_date": state.admission_date,
        "discharge_date": state.discharge_date,
        "hospital_course": state.hospital_course,
        "discharge_condition": state.discharge_condition,
    }
    for name, fact in fact_fields.items():
        if fact is None:
            issues.append(f"[MISSING] {name} — no data found in source documents. Requires clinician input.")
        elif fact.status == FactStatus.MISSING:
            issues.append(f"[MISSING] {name} — not documented. Requires clinician input.")
        elif fact.status == FactStatus.PENDING:
            issues.append(f"[PENDING] {name} — result not yet available.")
        elif fact.status == FactStatus.CONFLICT:
            issues.append(f"[CONFLICT] {name} — conflicting information across sources: {fact.note}")
        elif fact.status == FactStatus.UNCLEAR_OCR:
            issues.append(f"[UNCLEAR] {name} — OCR quality insufficient for reliable extraction: {fact.note}")
    if not state.diagnoses:
        issues.append("[MISSING] Diagnoses — no diagnoses found in source documents.")
    else:
        for dx in state.diagnoses:
            if dx.status == FactStatus.CONFLICT:
                issues.append(f"[CONFLICT] Diagnosis conflict: {dx.note}")
    for mc in state.med_changes:
        if mc.flagged_for_review:
            issues.append(f"[REVIEW] Medication reconciliation: {mc.drug} ({mc.change_type}) — {mc.note}")
    for esc in state.escalations:
        issues.append(esc)
    return issues
