from src.agent.state import AgentState, Fact, FactStatus, MedicationChange
from src.output.schema import DRAFT_TEMPLATE
import re


def _looks_like_ocr_fragment(value: str, raw_text: str) -> bool:
    """Heuristic: returns True if `value` looks like raw OCR noise rather than real content."""
    if not value or not isinstance(value, str):
        return True
    val = value.strip()
    if not val:
        return True
    if val.startswith("[") and val.endswith("]"):
        return False
    words = re.findall(r"\b[A-Za-z0-9]{2,}\b", val)
    if not words:
        return True
    if len(words) == 1 and len(val) <= 3 and val.isalpha() and val.islower():
        return True
    raw_lower = (raw_text or "").lower()
    matches = sum(1 for w in words if w.lower() in raw_lower)
    return matches == 0


def _guard_facts(facts: list, raw_text: str) -> list:
    """Re-tag facts that look like OCR fragments so the composer renders them safely."""
    guarded = []
    for f in facts:
        if f.status == FactStatus.FOUND and _looks_like_ocr_fragment(f.value, raw_text):
            guarded.append(Fact(
                value=f.value,
                status=FactStatus.UNCLEAR_OCR,
                source=f.source,
                page=f.page,
                note=(f.note or "") + " Guard: no word overlap with source text.",
                confidence=f.confidence,
            ))
        else:
            guarded.append(f)
    return guarded


def _fmt_fact(fact) -> str:
    if fact is None:
        return "[NOT DOCUMENTED]"
    if fact.status == FactStatus.MISSING:
        return "[NOT DOCUMENTED]"
    if fact.status == FactStatus.PENDING:
        return f"[PENDING] {fact.value}" if fact.value else "[PENDING]"
    if fact.status == FactStatus.CONFLICT:
        return f"[CONFLICT] {fact.value} (Note: {fact.note})"
    if fact.status == FactStatus.UNCLEAR_OCR:
        return f"[UNCLEAR — OCR insufficient]"
    return fact.value


def compose_draft(state: AgentState) -> str:
    raw_text = state.raw_text or ""

    guarded_procedures = _guard_facts(state.procedures, raw_text)
    guarded_allergies = _guard_facts(state.allergies, raw_text)
    guarded_follow_up = _guard_facts(state.follow_up_instructions, raw_text)
    guarded_pending = _guard_facts(state.pending_results, raw_text)
    guarded_dx = _guard_facts(state.diagnoses, raw_text)
    guarded_demo = {}
    for k, v in state.demographics.items():
        if v.status == FactStatus.FOUND and _looks_like_ocr_fragment(v.value, raw_text):
            guarded_demo[k] = Fact(
                value=v.value, status=FactStatus.UNCLEAR_OCR, source=v.source,
                page=v.page, note=(v.note or "") + " Guard: no word overlap with source.",
                confidence=v.confidence,
            )
        else:
            guarded_demo[k] = v
    guarded_hc = state.hospital_course
    if (guarded_hc and guarded_hc.status == FactStatus.FOUND
            and _looks_like_ocr_fragment(guarded_hc.value, raw_text)):
        guarded_hc = Fact(
            value=guarded_hc.value, status=FactStatus.UNCLEAR_OCR, source=guarded_hc.source,
            page=guarded_hc.page, note=(guarded_hc.note or "") + " Guard: no word overlap.",
            confidence=guarded_hc.confidence,
        )
    guarded_dc = state.discharge_condition
    if (guarded_dc and guarded_dc.status == FactStatus.FOUND
            and _looks_like_ocr_fragment(guarded_dc.value, raw_text)):
        guarded_dc = Fact(
            value=guarded_dc.value, status=FactStatus.UNCLEAR_OCR, source=guarded_dc.source,
            page=guarded_dc.page, note=(guarded_dc.note or "") + " Guard: no word overlap.",
            confidence=guarded_dc.confidence,
        )

    patient_name = _fmt_fact(guarded_demo.get("name")) if "name" in guarded_demo else "[MISSING]"
    mrn = _fmt_fact(guarded_demo.get("mrn")) if "mrn" in guarded_demo else "[MISSING]"

    demo_lines = []
    for key in ["name", "age", "gender", "mrn", "address"]:
        if key in guarded_demo:
            demo_lines.append(f"- **{key.capitalize()}**: {_fmt_fact(guarded_demo[key])}")
    demographics = "\n".join(demo_lines) if demo_lines else "[MISSING]"

    if guarded_dx:
        principal = _fmt_fact(guarded_dx[0])
        secondary = ""
        if len(guarded_dx) > 1:
            sec_lines = [f"- {_fmt_fact(dx)}" for dx in guarded_dx[1:]]
            secondary = "\n" + "\n".join(sec_lines) if sec_lines else "[MISSING — no secondary diagnoses documented]"
        else:
            secondary = "[MISSING — no secondary diagnoses documented]"
    else:
        principal = "[MISSING]"
        secondary = "[MISSING]"

    med_lines = []
    for med in state.discharge_medications:
        val = _fmt_fact(med)
        if med.note and val and not val.startswith("["):
            line = f"- {val} ({med.note})"
        else:
            line = f"- {val}"
        med_lines.append(line)
    discharge_meds = "\n".join(med_lines) if med_lines else "[MISSING — no discharge medications documented]"

    med_recon_lines = []
    for mc in state.med_changes:
        if isinstance(mc, dict):
            mc = MedicationChange(
                drug=mc.get("drug", "?"),
                change_type=mc.get("change_type", "?"),
                reason=mc.get("reason", ""),
                reason_documented=mc.get("reason_documented", False),
                flagged_for_review=mc.get("flagged_for_review", False),
            )
        flag = " ⚠️ FLAGGED FOR REVIEW" if mc.flagged_for_review else ""
        reason = f" (reason documented)" if mc.reason_documented else " (no reason documented)"
        med_recon_lines.append(f"- {mc.drug}: {mc.change_type}{reason}{flag}")
    med_reconciliation = "\n".join(med_recon_lines) if med_recon_lines else "No medication changes identified."

    allergy_lines = [f"- {_fmt_fact(a)}" for a in guarded_allergies] if guarded_allergies else ["[MISSING — not documented]"]
    allergies_text = "\n".join(allergy_lines)

    follow_lines = [f"- {_fmt_fact(f)}" for f in guarded_follow_up] if guarded_follow_up else ["[MISSING — not documented]"]
    follow_up = "\n".join(follow_lines)

    pending_lines = [f"- {_fmt_fact(p)}" for p in guarded_pending] if guarded_pending else ["No pending results."]
    pending_results = "\n".join(pending_lines)

    from src.output.validator import validate_state
    issues = validate_state(state)
    escalations = "\n".join(f"- {i}" for i in issues) if issues else "None"

    conflicts_lines = []
    for c in state.conflicts:
        srcs = c.sources if c.sources else ["unknown source"]
        conflicts_lines.append(f"- **{c.field.capitalize()} Conflict**: '{c.value1}' vs '{c.value2}' (sources: {', '.join(srcs)})")
    conflicts = "\n".join(conflicts_lines) if conflicts_lines else "None"

    return DRAFT_TEMPLATE.format(
        patient_name=patient_name,
        mrn=mrn,
        admission_date=_fmt_fact(state.admission_date),
        discharge_date=_fmt_fact(state.discharge_date),
        demographics=demographics,
        principal_diagnosis=principal,
        secondary_diagnoses=secondary,
        hospital_course=_fmt_fact(guarded_hc),
        procedures="\n".join(f"- {_fmt_fact(p)}" for p in guarded_procedures) if guarded_procedures else "[NOT DOCUMENTED]",
        discharge_medications=discharge_meds,
        med_reconciliation=med_reconciliation,
        allergies=allergies_text,
        follow_up=follow_up,
        pending_results=pending_results,
        discharge_condition=_fmt_fact(guarded_dc),
        conflicts=conflicts,
        escalations=escalations,
    )


LOW_CONFIDENCE_TEMPLATE = """

## Low-Confidence Fields
*The following fields have low confidence and may require clinician verification:"""


def render_confidence_warnings(state: AgentState) -> str:
    seen = set()
    warnings = []
    for f in state.facts:
        if f.confidence < 0.8 and f.value not in seen:
            seen.add(f.value)
            warnings.append(f"- {f.value} (confidence: {f.confidence:.0%}, source: {f.source})")

    if warnings:
        return LOW_CONFIDENCE_TEMPLATE + "\n" + "\n".join(warnings)
    return ""
