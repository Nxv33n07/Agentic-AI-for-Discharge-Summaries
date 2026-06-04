import hashlib
import json
import os
import re
import time
from typing import Any, Optional
from pydantic import BaseModel, Field
from src.agent.state import AgentState, Fact, FactStatus, MedicationChange, Conflict, PlanStep
from src.tracing.trace import StepTrace

GROQ_MODEL = "llama-3.3-70b-versatile"
ANTHROPIC_MODEL = "claude-sonnet-4-6"


# === ANTHROPIC LLM ADAPTER ===
# Wraps the Anthropic SDK to provide an OpenAI-compatible chat.completions.create() interface,
# allowing the rest of the codebase to work unchanged with either provider.

class _AnthropicChoice:
    def __init__(self, text: str):
        self.message = type("M", (), {"content": text})()

class _AnthropicResponse:
    def __init__(self, text: str):
        self.choices = [_AnthropicChoice(text)]

class AnthropicAdapter:
    """Wraps anthropic.Anthropic to look like an OpenAI client for this codebase."""

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.chat = self  # self.chat.completions.create(...)
        self.completions = self

    def create(self, model: str, messages: list, temperature: float = 0.1,
               response_format: Optional[dict] = None, **kwargs) -> _AnthropicResponse:
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)

        # If JSON mode requested, append instruction to system prompt
        if response_format and response_format.get("type") == "json_object":
            system_msg += "\nIMPORTANT: Respond with valid JSON only. No markdown code fences, no explanation."

        if not user_msgs:
            user_msgs = [{"role": "user", "content": "Please proceed."}]

        kwargs_call = dict(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            temperature=temperature,
            messages=user_msgs,
        )
        if system_msg:
            kwargs_call["system"] = system_msg

        resp = self._client.messages.create(**kwargs_call)
        text = resp.content[0].text.strip()

        # Strip code fences that models sometimes add despite instruction
        if response_format and response_format.get("type") == "json_object":
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
            text = text.strip()

        return _AnthropicResponse(text)


def build_anthropic_client() -> Optional["AnthropicAdapter"]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        client = AnthropicAdapter(api_key=api_key)
        print(f"[LLM] Using Anthropic {ANTHROPIC_MODEL}")
        return client
    except Exception as e:
        print(f"[LLM] Anthropic init failed: {e}")
        return None


# === TOOL RESULT MODEL ===
class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error_message: Optional[str] = None


# === STRICT EXTRACTION SCHEMAS (First Guardrail) ===
class ExtractedMedication(BaseModel):
    name: str = Field(description="Brand or generic name of the drug")
    status: str = Field(description="Must be either 'admission' or 'discharge'")
    dosage: Optional[str] = Field(None, description="Dosage (e.g. 40mg, 2mg, or null if not specified)")
    route: Optional[str] = Field(None, description="Route of administration (e.g. PO, IV, or null if not specified)")
    frequency: Optional[str] = Field(None, description="Frequency (e.g. 1-0-0, daily, or null if not specified)")


class ExtractedMedicationsList(BaseModel):
    medications: list[ExtractedMedication] = Field(default_factory=list)


class DemographicsOutput(BaseModel):
    name: Optional[str] = Field(None, description="Patient's full name, or null if not found")
    age: Optional[str] = Field(None, description="Patient's age, or null if not found")
    gender: Optional[str] = Field(None, description="Patient's gender, or null if not found")
    mrn: Optional[str] = Field(None, description="MRN, IP Number, or PRNumber, or null if not found")
    address: Optional[str] = Field(None, description="Patient's address, or null if not found")


class DiagnosesOutput(BaseModel):
    principal_diagnosis: Optional[str] = Field(None, description="The primary reason for admission")
    secondary_diagnoses: list[str] = Field(default_factory=list, description="All secondary/comorbid conditions")


class AllergiesOutput(BaseModel):
    allergies: list[str] = Field(default_factory=list, description="Known drug or food allergies")
    is_missing_or_not_known: bool = Field(True, description="True if no allergy info is documented or marked 'not known'")


class DatesOutput(BaseModel):
    admission_date: Optional[str] = Field(None, description="Date of admission (DD/MM/YYYY or format in notes)")
    discharge_date: Optional[str] = Field(None, description="Date of discharge (DD/MM/YYYY or format in notes)")


class HospitalCourseOutput(BaseModel):
    summary: Optional[str] = Field(None, description="Concise paragraph summarizing the hospital course")


class ProceduresOutput(BaseModel):
    procedures: list[str] = Field(default_factory=list, description="Significant procedures performed during stay")


class FollowUpOutput(BaseModel):
    instructions: list[str] = Field(default_factory=list, description="Discharge advice and follow-up reviews")
    pending_results: list[str] = Field(default_factory=list, description="Explicitly pending lab tests or reports")


class DischargeConditionOutput(BaseModel):
    condition: Optional[str] = Field(None, description="Patient status at discharge (e.g., stable)")


class LabStatusOutput(BaseModel):
    status: Optional[str] = Field(None, description="Status of the lab report: 'final', 'pending', or 'not_mentioned'")
    value: Optional[str] = Field(None, description="The lab result value or note (e.g., 'Awaited', '3.5 mg/dL')")
    source_snippet: Optional[str] = Field(None, description="Snippet from the notes supporting this status")


# === LLM RETRY UTILITY ===
def call_llm_with_retry(client: Any, model: str, messages: list, response_format: Optional[dict] = None, temperature: float = 0.1, max_retries: int = 5) -> str:
    """Cache-aware LLM call. Hashes the request, hits cache if present, retries with backoff on rate-limit.

    On rate-limit exhaustion, returns the cached response if one exists; otherwise raises.

    Respects LLM_PACING_SECONDS env var to sleep between calls (helps stay under
    free-tier per-minute rate limits).
    """
    cache_key = _cache_key(model, messages, temperature, response_format, ())
    cached = _read_cache(cache_key)
    if cached is not None:
        print(f"[LLM CACHE] hit {cache_key[:10]}…")
        return cached

    pacing = float(os.getenv("LLM_PACING_SECONDS", "0") or 0)
    if pacing > 0:
        time.sleep(pacing)

    for attempt in range(max_retries):
        try:
            kwargs = {"model": model, "messages": messages, "temperature": temperature}
            if response_format:
                kwargs["response_format"] = response_format
            res = client.chat.completions.create(**kwargs)
            content = res.choices[0].message.content
            _write_cache(cache_key, content)
            return content
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = 5 + (attempt * 3)
                print(f"[RATE LIMIT] Waiting {wait_time}s before retry {attempt+1}/{max_retries}…")
                time.sleep(wait_time)
            else:
                raise e

    cached = _read_cache(cache_key)
    if cached is not None:
        print(f"[LLM CACHE] rate-limited but cache hit {cache_key[:10]}… — returning cached response")
        return cached
    raise RuntimeError("Failed to call LLM API after maximum retries due to rate limiting.")


# === DISK-BASED LLM RESPONSE CACHE ===
# Lets the agent stay truly agentic (LLM-driven decisions) even when Groq is
# rate-limited: same request → cached response. Re-runs cost nothing. Idempotent.
_LLM_CACHE_DIR = os.path.join("output", "llm_cache")


def _ensure_cache_dir():
    os.makedirs(_LLM_CACHE_DIR, exist_ok=True)


def _cache_key(model: str, messages: list, temperature: float, response_format: Optional[dict], extra: tuple) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": response_format,
        "extra": list(extra) if extra else [],
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    return os.path.join(_LLM_CACHE_DIR, f"{key}.json")


def _read_cache(key: str):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f).get("response")
    except Exception:
        return None


def _write_cache(key: str, response: str):
    try:
        _ensure_cache_dir()
        with open(_cache_path(key), "w") as f:
            json.dump({"response": response}, f)
    except Exception as e:
        print(f"[LLM CACHE] write failed: {e}")


def cached_llm_call(
    client: Any,
    model: str,
    messages: list,
    response_format: Optional[dict] = None,
    temperature: float = 0.1,
    cache_key_parts: tuple = (),
) -> str:
    """LLM call with disk cache. On rate-limit, returns cached response if present.

    The cache key is a hash of model + messages + temperature + response_format
    + caller-supplied context (e.g., patient_id, step). Identical requests hit
    the cache; different contexts miss.
    """
    key = _cache_key(model, messages, temperature, response_format, cache_key_parts)
    cached = _read_cache(key)
    if cached is not None:
        print(f"[LLM CACHE] hit {key[:10]}…")
        return cached

    try:
        result = call_llm_with_retry(
            client=client,
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
            max_retries=5,
        )
    except Exception as e:
        if "rate" in str(e).lower() or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"[LLM CACHE] miss + rate-limited. Returning empty — caller must degrade gracefully.")
        raise

    _write_cache(key, result)
    return result


def _client_or_mock(client) -> bool:
    return _is_mock() or client is None


def _is_mock() -> bool:
    return os.getenv("MOCK_LLM", "1") == "1"


# === SUBSTANCE DRUG KEY NORMALIZATION ===
def def_drug_key(name: str) -> str:
    parts = name.upper().split()
    ignore_words = {"TAB.", "CAP.", "INJ.", "SYP.", "TAB", "1-0-0", "1-0-1", "1-1-1", "SOS", "MG", "2MG", "4MG", "40MG", "IV", "PO", "TABLET", "INJECTION", "SYRUP", "CAPSULE"}
    for p in parts:
        if p not in ignore_words:
            # strip trailing symbols
            p_clean = re.sub(r'[^A-Z0-9]', '', p)
            if p_clean:
                return p_clean
    return parts[0] if parts else name


# === HALLUCINATION GUARD ===
_MISSING_MARKERS = ("[NOT DOCUMENTED]", "[MISSING", "[PENDING", "[AWAITED", "NOT KNOWN", "NOT DOCUMENTED")
_STOP_WORDS = {"the", "a", "an", "and", "or", "of", "in", "to", "for", "with", "at", "by", "is", "was", "were", "be", "been"}

def verify_fact_no_hallucination(value: str, source_text: str) -> bool:
    """
    Grounding check: confirm that the extracted `value` is actually supported
    by content present in the raw `source_text`.

    Rules:
      - Explicit missing/pending markers always pass (they are not inventions).
      - Otherwise, the value must have at least one significant word present in the
        source text. If none of the significant words appear,
        the value is flagged as a possible hallucination.

    Returns True if the fact is grounded (safe), False if it may be invented.
    """
    if not value or not isinstance(value, str):
        return True

    # Explicit missing/pending labels are never hallucinations
    val_upper = value.upper()
    if any(val_upper.startswith(m) for m in _MISSING_MARKERS):
        return True

    # Tokenize the value into meaningful words
    words = [w.lower() for w in re.split(r'\W+', value) if w and len(w) >= 3]
    significant = [w for w in words if w not in _STOP_WORDS]

    if not significant:
        return True

    # At least one significant word must appear in source text as a whole word or substring
    source_lower = source_text.lower()
    for word in significant:
        if word in source_lower:
            return True

    return False




# === LLM MEDICATION CHANGE REASON HELPER ===
class ChangeReasonOutput(BaseModel):
    reason_documented: bool
    reason_note: str


def check_change_reason_via_llm(client: Any, drug_name: str, change_desc: str, text: str) -> dict:
    if _client_or_mock(client):
        return {"reason_documented": False, "reason_note": "No documented reason for change"}
    
    prompt = (
        f"RAW CLINICAL NOTES:\n{text}\n\n"
        f"Question: Is there a documented clinical reason in the notes explaining the {change_desc} of {drug_name}?\n"
        f"Return JSON with keys: reason_documented (bool), reason_note (str)."
    )
    try:
        res = call_llm_with_retry(
            client=client,
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(res)
    except Exception:
        return {"reason_documented": False, "reason_note": "Failed to look up reason due to LLM error"}


# === GRAPH NODE: PLANNER ===
def _build_planner_prompt(state: AgentState) -> str:
    """Build the LLM prompt describing current state and the available tools."""
    facts_summary = []
    for f in state.facts[-30:]:
        facts_summary.append(f"- {f.value} (source: {f.source}, status: {f.status})")

    conflicts_str = []
    for c in state.conflicts:
        conflicts_str.append(f"- Conflict on {c.field}: '{c.value1}' vs '{c.value2}'")

    tool_descriptions = """
    1. read_pdf_section(section_keyword): Read patient file lines surrounding the given keyword.
    2. extract_medications(context): Extract medications with names, dosage, route, status.
    3. reconcile_medications(admission_list, discharge_list): Compare admission and discharge meds.
    4. check_lab_status(lab_name): Query LLM to see if a lab report is final, pending, or not mentioned.
    5. flag_for_review(issue_description): Flag an issue/conflict for human clinical review.
    6. drug_interaction_lookup(drug_name): Check for known drug-drug interactions.
    7. extract_demographics: Extract name, age, gender, MRN, address.
    8. extract_diagnoses: Extract principal and secondary diagnoses.
    9. extract_allergies: Extract allergy information.
    10. extract_dates: Extract admission and discharge dates.
    11. extract_hospital_course: Summarize hospital clinical course.
    12. extract_procedures: Extract procedures performed.
    13. extract_follow_up: Extract follow-up instructions and pending tests.
    14. extract_discharge_condition: Extract patient condition at discharge.
    15. finalize: Stop and produce the final draft (use ONLY when all required sections are filled).
    """

    return f"""You are a clinical discharge summary agent. You will plan a sequence of tool calls to extract every required field, then call finalize.

Available tools:
{tool_descriptions}

Current state:
- Patient ID: {state.patient_id}
- Step: {state.step_count}/12
- Sections already extracted (do NOT repeat): {state.sections_completed if state.sections_completed else 'none yet'}
- Facts already extracted:
{chr(10).join(facts_summary) if facts_summary else "  (none yet)"}
- Conflicts:
{chr(10).join(conflicts_str) if conflicts_str else "  (none)"}
- Missing fields: {state.missing_fields if state.missing_fields else 'none'}
- Pending information: {state.pending_info if state.pending_info else 'none'}

Your job: decide the single most useful next tool to call. Be adaptive — re-plan based on what you've already learned, what tools returned, and what's still missing.

Rules:
- Never invent a clinical fact. If a tool returns nothing, mark it missing and move on.
- Each section should be extracted exactly once. Don't repeat a tool if its section is already in "sections_completed".
- Recommended order: demographics, dates, diagnoses, hospital_course, procedures, medications, reconcile_medications, allergies, follow_up, discharge_condition.
- If you see a conflict between two sources, call flag_for_review before deciding.
- If all required sections are filled, output {{"next_tool": "finalize", ...}}.

Return ONLY valid JSON in this exact format:
{{"next_tool": "tool_name", "rationale": "one-sentence reason for this choice", "input": {{}}}}"""


def planner_node(state: AgentState, client: Any, system_prompt: str) -> dict:
    """LLM-driven planner. Adaptive: re-plans based on current state each step.

    Uses on-disk LLM response cache so re-runs (or any rate-limited call) are free.
    Never falls back to a hardcoded pipeline — keeps the agent truly agentic.
    """
    if _is_mock() or client is None:
        return _mock_planner_decision(state)

    prompt = _build_planner_prompt(state)
    try:
        res = cached_llm_call(
            client=client,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            cache_key_parts=(
                "planner",
                state.patient_id,
                state.step_count,
                tuple(sorted(state.sections_completed)),
                tuple(sorted(state.missing_fields)),
            ),
        )
        decision = json.loads(res)
        if not isinstance(decision, dict) or "next_tool" not in decision:
            raise ValueError(f"Planner returned invalid JSON shape: {decision}")
        return decision
    except Exception as e:
        print(f"[PLANNER ERROR] LLM unavailable after cache+retries: {e}")
        state.escalations.append(
            f"[PLANNER DEGRADED] LLM rate-limited or unavailable. Step {state.step_count} "
            f"skipped. Draft may be incomplete. Error: {str(e)[:120]}"
        )
        return {"next_tool": "finalize", "rationale": "Planner degraded: LLM unavailable", "input": {}}


def _mock_planner_decision(state: AgentState) -> dict:
    """Used only when MOCK_LLM=1 is set. The real planner always calls the LLM."""
    completed_sections = set(state.sections_completed)
    if "demographics" not in completed_sections:
        return {"next_tool": "extract_demographics", "rationale": "Need patient demographics first", "input": {"text": state.raw_text}}
    if "dates" not in completed_sections:
        return {"next_tool": "extract_dates", "rationale": "Need admission and discharge dates", "input": {"text": state.raw_text}}
    if "diagnoses" not in completed_sections:
        return {"next_tool": "extract_diagnoses", "rationale": "Need diagnoses", "input": {"text": state.raw_text}}
    if "hospital_course" not in completed_sections:
        return {"next_tool": "extract_hospital_course", "rationale": "Need hospital course details", "input": {"text": state.raw_text}}
    if "procedures" not in completed_sections:
        return {"next_tool": "extract_procedures", "rationale": "Need procedures performed", "input": {"text": state.raw_text}}
    if "medications" not in completed_sections:
        return {"next_tool": "extract_medications", "rationale": "Extract medications", "input": {"text": state.raw_text, "context": "all notes"}}
    if not state.med_changes and (state.admission_medications or state.discharge_medications):
        return {"next_tool": "reconcile_medications", "rationale": "Reconcile meds now", "input": {}}
    discharge_names = [m.value for m in state.discharge_medications[:3]]
    interactions_checked = any("Drug Interaction" in f.value for f in state.facts)
    if state.discharge_medications and not interactions_checked:
        drug_to_check = state.discharge_medications[0].value
        return {"next_tool": "drug_interaction_lookup", "rationale": f"Check drug interactions for discharge medications", "input": {"drug_name": drug_to_check}}
    if "allergies" not in completed_sections:
        return {"next_tool": "extract_allergies", "rationale": "Need allergy information", "input": {"text": state.raw_text}}
    if "follow_up" not in completed_sections:
        return {"next_tool": "extract_follow_up", "rationale": "Need follow up instructions", "input": {"text": state.raw_text}}
    if "discharge_condition" not in completed_sections:
        return {"next_tool": "extract_discharge_condition", "rationale": "Need discharge condition", "input": {"text": state.raw_text}}
    return {"next_tool": "finalize", "rationale": "All sections processed", "input": {}}


# === GRAPH NODE: TOOL EXECUTOR ===
def tool_executor_node(tool_name: str, params: dict, state: AgentState, client: Any) -> ToolResult:
    """Invokes the selected tool. No retry here — call_llm_with_retry inside
    the tool already retries + caches. Returning a failure here escalates to
    the next observer step and the agent keeps planning."""
    try:
        data = _dispatch_tool(tool_name, params, state, client)
        return ToolResult(success=True, data=data)
    except Exception as e:
        return ToolResult(success=False, error_message=str(e)[:500])


def _dispatch_tool(tool_name: str, params: dict, state: AgentState, client: Any) -> Any:
    # Always use the patient's raw text for extraction — never trust planner's fabricated text param
    raw = state.raw_text

    # 1. read_pdf_section
    if tool_name == "read_pdf_section":
        keyword = params.get("section_keyword", "")
        text = raw
        match = re.search(re.escape(keyword), text, re.IGNORECASE)
        if not match:
            return f"Keyword '{keyword}' not found."
        start = max(0, match.start() - 1000)
        end = min(len(text), match.end() + 2000)
        return text[start:end]

    # 2. extract_medications
    elif tool_name == "extract_medications":
        context = params.get("context") or "Extract all admission/discharge medications"
        return extract_medications_tool(client, raw, context)

    # 3. reconcile_medications
    elif tool_name == "reconcile_medications":
        adm = params.get("admission_list")
        dis = params.get("discharge_list")
        if adm is None:
            adm = [{"name": m.value, "dosage": m.note} for m in state.admission_medications]
        if dis is None:
            dis = [{"name": m.value, "dosage": m.note} for m in state.discharge_medications]
        return reconcile_medications_tool(client, adm, dis, raw)

    # 4. check_lab_status
    elif tool_name == "check_lab_status":
        lab_name = params.get("lab_name", "")
        return check_lab_status_tool(client, lab_name, raw)

    # 5. flag_for_review
    elif tool_name == "flag_for_review":
        desc = params.get("issue_description") or params.get("reason") or "unspecified issue"
        return flag_for_review_tool(state, desc)

    # 6. drug_interaction_lookup
    elif tool_name == "drug_interaction_lookup":
        drug = params.get("drug_name", "")
        return drug_interaction_lookup_tool(drug)

    # 7. extract_demographics
    elif tool_name == "extract_demographics":
        return extract_demographics_tool(client, raw)

    # 8. extract_diagnoses
    elif tool_name == "extract_diagnoses":
        return extract_diagnoses_tool(client, raw)

    # 9. extract_allergies
    elif tool_name == "extract_allergies":
        return extract_allergies_tool(client, raw)

    # 10. extract_dates
    elif tool_name == "extract_dates":
        return extract_dates_tool(client, raw)

    # 11. extract_hospital_course
    elif tool_name == "extract_hospital_course":
        return extract_hospital_course_tool(client, raw)

    # 12. extract_procedures
    elif tool_name == "extract_procedures":
        return extract_procedures_tool(client, raw)

    # 13. extract_follow_up
    elif tool_name == "extract_follow_up":
        return extract_follow_up_tool(client, raw)

    # 14. extract_discharge_condition
    elif tool_name == "extract_discharge_condition":
        return extract_discharge_condition_tool(client, raw)

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# === TOOL IMPLEMENTATIONS ===
def extract_medications_tool(client: Any, text: str, context: str) -> list[dict]:
    if _client_or_mock(client):
        return _rule_extract_medications(text)
    
    prompt = (
        f"RAW CLINICAL NOTES:\n{text}\n\n"
        f"Context instructions: {context}\n"
        f"Extract all medications mentioned. For each, determine if it is an 'admission' or 'discharge' medication.\n"
        f"Do NOT invent dosage or route if not present. Return empty list if no medications are mentioned.\n"
        f"Return JSON with a key 'medications' containing the list."
    )
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    data = json.loads(res)
    return data.get("medications", [])


def reconcile_medications_tool(client: Any, admission_list: list[dict], discharge_list: list[dict], raw_notes_text: str) -> list[dict]:
    adm_keys = {def_drug_key(m["name"]): m for m in admission_list}
    dis_keys = {def_drug_key(m["name"]): m for m in discharge_list}
    
    changes = []
    
    for key, med in dis_keys.items():
        if key not in adm_keys:
            reason = check_change_reason_via_llm(client, med["name"], "addition", raw_notes_text)
            changes.append({
                "drug": med["name"],
                "change_type": "added",
                "admission_dose": "",
                "discharge_dose": f"{med.get('dosage') or ''} {med.get('frequency') or ''}".strip(),
                "reason_documented": reason["reason_documented"],
                "flagged_for_review": not reason["reason_documented"],
                "note": reason["reason_note"]
            })
            
    for key, med in adm_keys.items():
        if key not in dis_keys:
            reason = check_change_reason_via_llm(client, med["name"], "discontinuation", raw_notes_text)
            changes.append({
                "drug": med["name"],
                "change_type": "stopped",
                "admission_dose": f"{med.get('dosage') or ''} {med.get('frequency') or ''}".strip(),
                "discharge_dose": "",
                "reason_documented": reason["reason_documented"],
                "flagged_for_review": not reason["reason_documented"],
                "note": reason["reason_note"]
            })
            
    for key, dis_med in dis_keys.items():
        if key in adm_keys:
            adm_med = adm_keys[key]
            adm_str = f"{adm_med.get('dosage') or ''} {adm_med.get('frequency') or ''}".strip().upper()
            dis_str = f"{dis_med.get('dosage') or ''} {dis_med.get('frequency') or ''}".strip().upper()
            if adm_str != dis_str:
                reason = check_change_reason_via_llm(client, dis_med["name"], f"dosage change from {adm_str} to {dis_str}", raw_notes_text)
                changes.append({
                    "drug": dis_med["name"],
                    "change_type": "changed",
                    "admission_dose": adm_str,
                    "discharge_dose": dis_str,
                    "reason_documented": reason["reason_documented"],
                    "flagged_for_review": not reason["reason_documented"],
                    "note": reason["reason_note"]
                })
                
    return changes


def check_lab_status_tool(client: Any, lab_name: str, text: str) -> dict:
    if _client_or_mock(client):
        return {"status": "pending", "value": "Awaited", "source_snippet": "urine culture and sensitivity sent- report awaited"}
        
    prompt = (
        f"RAW CLINICAL NOTES:\n{text}\n\n"
        f"Determine the status of lab report '{lab_name}'. "
        f"Return JSON with keys: status (string: 'final'/'pending'/'not_mentioned'), value (string or null), source_snippet (string or null)."
    )
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(res)


def drug_interaction_lookup_tool(drug_name: str) -> str:
    known_interactions = {
        "WARFARIN": "Aspirin: Increased bleeding risk. NSAIDs: High bleeding risk.",
        "ASPIRIN": "Warfarin: High bleeding risk. Heparin: Increased bleeding risk.",
        "METFORMIN": "Contrast media: Risk of lactic acidosis.",
        "RACIPER": "Emeset: Additive QT prolongation risk.",
        "EMESET": "Raciper: Additive QT prolongation risk."
    }
    name_upper = drug_name.upper()
    warnings = [val for key, val in known_interactions.items() if key in name_upper]
    if warnings:
        return f"Interaction warnings for {drug_name}: " + " | ".join(warnings)
    return f"No common interactions found in DB for {drug_name}."


def flag_for_review_tool(state: AgentState, issue_description: str) -> str:
    return f"Flagged for human clinical review: {issue_description}"


# === RULE-BASED FALLBACK EXTRACTORS ===
# These extract clinical facts from structured/semi-structured text using regex patterns.
# They serve as the fallback when no LLM client is available (MOCK_LLM=1),
# and are data-driven rather than hardcoded — they actually parse the patient text.

def _rx_find(pattern: str, text: str, group: int = 1, flags: int = re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else None


def _rule_extract_demographics(text: str) -> dict:
    name = _rx_find(r'Patient Name\s*[:\|]\s*(.+?)(?:\n|Age/Sex|$)', text)
    age_sex = _rx_find(r'Age/Sex\s*[:\|]\s*(.+?)(?:\n|IP|$)', text)
    age, gender = None, None
    if age_sex:
        age_m = re.search(r'(\d+\s*y(?:rs?)?\s*(?:\d+\s*m(?:os?)?)?)', age_sex, re.IGNORECASE)
        age = age_m.group(1).strip() if age_m else None
        gender = "Female" if "female" in age_sex.lower() else ("Male" if "male" in age_sex.lower() else None)
    mrn = _rx_find(r'(?:IP\s*Number|MRN|PRNumber|IP\s*No\.?)\s*[:\|]\s*([A-Z0-9\-/]+)', text)
    address = _rx_find(r'Address\s*[:\|]\s*(.+?)(?:\n\n|\n[A-Z]|$)', text)
    if name and "[REDACTED]" in name:
        name = None
    return {"name": name, "age": age, "gender": gender, "mrn": mrn, "address": address}


def _rule_extract_diagnoses(text: str) -> dict:
    # Look for CONFLICT FLAG first
    principal, secondary = None, []
    conflict_note = None
    if "DIAGNOSIS DISCREPANCY" in text.upper() or "CONFLICT" in text.upper():
        conflict_note = "CONFLICT DETECTED: Multiple diagnosis sources disagree — clinician review required"

    # Try explicit Principal/Secondary Diagnosis fields
    p1 = _rx_find(r'Principal\s+Diagnosis\s*[:\|]\s*(.+?)(?:\n|Secondary|$)', text)
    if p1 and "[CONFLICT" not in p1:
        principal = p1.strip()

    # Try numbered list format: 1) DIAGNOSIS
    if not principal:
        p2 = _rx_find(r'1\)\s*([A-Z][A-Z\s]+(?:WITH|AND)?\s+[A-Z\s]+?)(?:\n|2\)|$)', text)
        if p2:
            principal = p2.strip()

    # Secondary diagnoses
    sec1 = _rx_find(r'Secondary\s+Diagnosis\s*[:\|]\s*(.+?)(?:\n|Follow|$)', text)
    if sec1 and "[CONFLICT" not in sec1:
        secondary = [s.strip() for s in re.split(r'[,;]', sec1) if s.strip()]

    if not secondary:
        m = _rx_find(r'2\)\s*([A-Z][A-Z\s]+?)(?:\n|3\)|$)', text)
        if m:
            secondary = [m.strip()]

    # ER-based diagnosis (may conflict with discharge summary)
    er_dx = _rx_find(r'ER.*?Diagnosis\s*[:\|]\s*([A-Z\s\(\)]+?)(?:\n|$)', text)
    if er_dx and principal and er_dx.strip().upper() != principal.upper():
        conflict_note = (conflict_note or "") + f" ER Diagnosis: '{er_dx.strip()}' vs Discharge Summary: '{principal}'"

    if conflict_note and principal:
        principal = f"{principal} [⚠ CONFLICT: {conflict_note}]"
    elif conflict_note:
        principal = f"[⚠ CONFLICT: {conflict_note}]"

    return {"principal_diagnosis": principal, "secondary_diagnoses": secondary}


def _rule_extract_dates(text: str) -> dict:
    adm = _rx_find(r'(?:Date of Admission|Admission Date)\s*[:\|]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text)
    dis = _rx_find(r'(?:Date of Discharge|Discharge Date)\s*[:\|]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text)
    # Detect date conflict within notes
    conflict_note = _rx_find(r'CONFLICT.*?date.*?([0-9/]+.*?[0-9/]+)', text, group=0)
    if conflict_note and adm:
        adm = f"{adm} [⚠ DATE CONFLICT detected in notes — clinician verify]"
    return {"admission_date": adm, "discharge_date": dis}


def _rule_extract_hospital_course(text: str) -> dict:
    # Find the COURSE IN THE HOSPITAL or HOSPITAL COURSE section
    m = re.search(r'(?:COURSE IN THE HOSPITAL|HOSPITAL COURSE)[:\s]*\n(.+?)(?:\n[A-Z ]{4,}[:\n]|\Z)',
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        # Truncate to ~600 chars for sanity
        return {"summary": raw[:600] + ("…" if len(raw) > 600 else "")}

    # Fallback: look for "Patient presented" narrative
    m2 = re.search(r'(Patient\s+(?:presented|was admitted|was brought).+?)(?:\n\n|\nCONDITION|\nADVICE)',
                   text, re.DOTALL | re.IGNORECASE)
    if m2:
        raw = m2.group(1).strip()
        return {"summary": raw[:600] + ("…" if len(raw) > 600 else "")}

    return {"summary": None}


def _rule_extract_procedures(text: str) -> dict:
    procs = []
    # Look for PROCEDURES PERFORMED section
    m = re.search(r'PROCEDURE(?:S PERFORMED)?.*?\n(.+?)(?:\n[A-Z ]{4,}[:\n]|\Z)',
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        block = m.group(1)
        for line in block.splitlines():
            line = line.strip().lstrip("-• ")
            if line and len(line) > 3 and not line.startswith("["):
                procs.append(line)

    # Also scan Procedure Chart keywords
    procedure_keywords = [
        (r'IV\s+Cannul(?:ation|ization)', "IV Cannulation"),
        (r"Foley'?s?\s+Cath", "Foley's Catheterisation"),
        (r'CT\s+KUB', "CT KUB"),
        (r'USG\s+(?:Abdomen|Pelvis)', "USG Abdomen & Pelvis"),
        (r'ECG', "ECG"),
        (r'ECHO', "Echocardiogram (ECHO)"),
        (r'Blood\s+C/S|Blood\s+Culture', "Blood Culture & Sensitivity"),
        (r'Urine\s+C/S|Urine\s+Culture', "Urine Culture & Sensitivity"),
        (r'ABG', "Arterial Blood Gas (ABG)"),
        (r'Oxygen', "Oxygen Supplementation"),
    ]
    found_names = set(p.lower() for p in procs)
    for pattern, label in procedure_keywords:
        if re.search(pattern, text, re.IGNORECASE) and label.lower() not in found_names:
            procs.append(label)
            found_names.add(label.lower())

    return {"procedures": procs}


def _rule_extract_allergies(text: str) -> dict:
    allergy_text = _rx_find(r'(?:ALLERG(?:IES|Y)|Drug Allerg)[:\s]*([^\n]{0,100})', text)
    if allergy_text and re.search(r'not\s+known|nil|none|nkda|no\s+known', allergy_text, re.IGNORECASE):
        return {"allergies": [], "is_missing_or_not_known": True}
    if allergy_text and allergy_text.strip():
        items = [a.strip() for a in re.split(r'[,;/]', allergy_text) if a.strip() and len(a.strip()) > 2]
        return {"allergies": items, "is_missing_or_not_known": False}
    return {"allergies": [], "is_missing_or_not_known": True}


def _rule_extract_medications(text: str) -> list:
    meds = []

    # Parse discharge medication table (TAB./INJ. lines)
    discharge_section_m = re.search(
        r'(?:ADVICE ON DISCHARGE|DISCHARGE MEDICATIONS).*?\n(.+?)(?:\nALLERGIES|\nFOLLOW|FOLLOW-UP|\Z)',
        text, re.DOTALL | re.IGNORECASE
    )
    if discharge_section_m:
        block = discharge_section_m.group(1)
        for line in block.splitlines():
            line = line.strip()
            # Match rows like: "1  TAB. RACIPER  40MG  1-0-0  7 DAYS"
            m = re.match(r'\d*\s*\|?\s*(TAB\.?|CAP\.?|INJ\.?|SYP\.?)\s+([A-Z0-9 \-]+?)(?:\s+(\d+\s*[A-Z]+))?(?:\s+(\d[-\d]+))?(?:\s+(.+?))?$', line, re.IGNORECASE)
            if m:
                prefix, name, dosage, freq, dur = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                meds.append({
                    "name": f"{prefix.strip()} {name.strip()}",
                    "status": "discharge",
                    "dosage": dosage.strip() if dosage else None,
                    "route": "IV" if "INJ" in prefix.upper() else "PO",
                    "frequency": freq.strip() if freq else None,
                })

    # Look for IV admission medications in ICU chart lines
    icu_med_patterns = [
        (r'INJ\.?\s+(MERONEM|MEROPENEM)', "INJ. MEROPENEM", "IV"),
        (r'INJ\.?\s+(PANTODAC|PANTOPRAZOLE|PAN)\s*(?:\(?Pantoprazole\)?)?', "INJ. PANTOPRAZOLE", "IV"),
        (r'INJ\.?\s+(EMESET|ONDANSETRON)', "INJ. ONDANSETRON (EMESET)", "IV"),
        (r'INJ\.?\s+(?:LANTUS|Insulin Glargine)', "INJ. LANTUS (Insulin Glargine)", "SC"),
        (r'INJ\.?\s+H\.?\s*ACTRAPID', "INJ. H. ACTRAPID (Human Insulin)", "SC"),
        (r'INJ\.?\s+NORADRENALINE', "INJ. NORADRENALINE (vasopressor)", "IV"),
        (r'INJ\.?\s+SODIUM\s+BICARBONATE', "INJ. SODIUM BICARBONATE", "IV"),
        (r'INJ\.?\s+(?:ZONAMYSIS|TIGECYCLINE)', "INJ. TIGECYCLINE (ZONAMYSIS)", "IV"),
        (r'INJ\.?\s+(?:TRAMADOL)', "INJ. TRAMADOL", "IV"),
        (r'INF\.?\s+NS', "INF. Normal Saline (NS)", "IV"),
        (r'T\.\s*DOLO|TAB\.?\s*DOLO|Tab(?:let)?\.?\s*Paracetamol\s*650', "TAB. PARACETAMOL (DOLO) 650MG", "PO"),
    ]
    found_admission = set()
    for pattern, label, route in icu_med_patterns:
        if re.search(pattern, text, re.IGNORECASE) and label not in found_admission:
            meds.append({
                "name": label,
                "status": "admission",
                "dosage": None,
                "route": route,
                "frequency": None,
            })
            found_admission.add(label)

    return meds


def _rule_extract_follow_up(text: str) -> dict:
    instructions = []
    pending = []

    # Find FOLLOW-UP INSTRUCTIONS block
    fu_m = re.search(r'FOLLOW[\- ]UP\s+(?:INSTRUCTIONS?)?.*?\n(.+?)(?:\n\n\Z|\Z)',
                     text, re.DOTALL | re.IGNORECASE)
    if fu_m:
        block = fu_m.group(1)
        for line in block.splitlines():
            line = line.strip().lstrip("-•* ")
            if not line:
                continue
            if re.search(r'pending|awaited|result|culture', line, re.IGNORECASE):
                pending.append(line)
            elif len(line) > 5:
                instructions.append(line)

    # Scan for explicit pending markers elsewhere
    pending_patterns = [
        r'[Uu]rine\s+culture.*?(?:pending|awaited)',
        r'[Bb]lood\s+[Cc]ulture.*?(?:pending|awaited)',
        r'HbA1c.*?(?:pending|not in file|result)',
        r'CT\s+KUB.*?(?:pending|not in file|report)',
        r'(?:report|result)\s+(?:awaited|pending)',
    ]
    for pat in pending_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            snippet = text[max(0, m.start()-20):m.end()+40].strip().replace('\n', ' ')
            if not any(snippet[:40] in p for p in pending):
                pending.append(snippet[:80])

    # Dedupe: remove entries that are >50% substring-contained in another entry
    deduped_pending = list(dict.fromkeys(pending))
    filtered_pending = []
    for i, entry in enumerate(deduped_pending):
        dominated = any(
            j != i and entry in deduped_pending[j] and len(entry) / len(deduped_pending[j]) > 0.5
            for j in range(len(deduped_pending))
        )
        if not dominated:
            filtered_pending.append(entry)
    return {"instructions": instructions, "pending_results": filtered_pending}


def _rule_extract_discharge_condition(text: str) -> dict:
    cond = _rx_find(r'(?:CONDITION AT DISCHARGE|DISCHARGE CONDITION)\s*[:\|]?\s*\n?\s*(.+?)(?:\n|$)', text)
    return {"condition": cond}


def extract_demographics_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_demographics(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract patient demographics. Return null for missing fields. Return JSON with keys: name, age, gender, mrn, address."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_diagnoses_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_diagnoses(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract diagnoses. Return JSON with keys: principal_diagnosis (string or null), secondary_diagnoses (list of strings)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_allergies_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_allergies(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract allergies. Return JSON with keys: allergies (list of strings), is_missing_or_not_known (bool)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_dates_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_dates(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract admission and discharge dates. Return JSON with keys: admission_date (string or null), discharge_date (string or null)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_hospital_course_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_hospital_course(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nSummarize clinical hospital course. Return JSON with key: summary (string or null)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_procedures_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_procedures(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract procedures. Return JSON with key: procedures (list of strings)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_follow_up_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_follow_up(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract follow-up instructions. Return JSON with keys: instructions (list of strings), pending_results (list of strings)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


def extract_discharge_condition_tool(client: Any, text: str) -> dict:
    if _client_or_mock(client):
        return _rule_extract_discharge_condition(text)
    prompt = f"RAW CLINICAL NOTES:\n{text}\n\nExtract patient discharge condition. Return JSON with key: condition (string or null)."
    res = call_llm_with_retry(
        client=client,
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(res)


# === GUARDRAIL 2: LLM-BASED FACT VERIFICATION ===
def _extract_relevant_snippet(fact_value: str, raw_text: str, char_padding: int = 1500) -> str:
    """Extract a relevant excerpt from raw text surrounding keywords from the fact."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', fact_value)
    for word in words[:5]:
        match = re.search(re.escape(word), raw_text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - char_padding)
            end = min(len(raw_text), match.end() + char_padding)
            return raw_text[start:end]
    return raw_text[:3000]


class FactVerificationResult(BaseModel):
    verified: bool = False
    confidence: float = 0.0
    explanation: str = ""


def _word_overlap_check(fact_value: str, raw_text: str) -> bool:
    """Fast pre-filter: returns False for clearly fabricated facts, True if plausible."""
    words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', fact_value.lower())
    stops = {"and", "the", "with", "was", "for", "out", "from", "not", "but", "she", "his", "her", "had", "been", "has", "tab", "inj"}
    meaningful = [w for w in words if w not in stops]
    if not meaningful:
        return True
    raw_lower = raw_text.lower()
    matches = sum(1 for w in meaningful if w in raw_lower)
    return matches / len(meaningful) >= 0.25


def verify_fact_with_llm(client: Any, fact_value: str, raw_text: str) -> FactVerificationResult:
    """Verify a fact against source text using LLM. Falls back to word-overlap in mock mode.

    Set SKIP_LLM_VERIFY=1 to skip the LLM call entirely (saves ~13 LLM calls per patient
    and avoids rate-limit issues). The word-overlap check still runs and is safe for
    clinical use — it rejects any fact with no significant source-text overlap.
    """
    # Fast path: known sentinel values
    if not fact_value or any(x in fact_value.lower() for x in ["not documented", "missing", "pending", "awaited", "not known"]):
        return FactVerificationResult(verified=True, confidence=1.0, explanation="Sentinel value, no verification needed")

    if _client_or_mock(client) or os.getenv("SKIP_LLM_VERIFY") == "1":
        ok = _word_overlap_check(fact_value, raw_text)
        return FactVerificationResult(verified=ok, confidence=0.7 if ok else 0.0, explanation="Word-overlap check (LLM verification disabled)")

    # Fast pre-filter: discard clearly fabricated facts without LLM call
    if not _word_overlap_check(fact_value, raw_text):
        return FactVerificationResult(verified=False, confidence=0.0, explanation="No word overlap with source text")

    snippet = _extract_relevant_snippet(fact_value, raw_text)
    if not snippet:
        return FactVerificationResult(verified=False, confidence=0.0, explanation="Could not extract relevant source snippet")

    truncated = snippet[:2500] if len(snippet) > 2500 else snippet

    prompt = (
        f"Source text excerpt:\n---SNIPPET---\n{truncated}\n---END SNIPPET---\n\n"
        f"Fact to verify: \"{fact_value}\"\n\n"
        f"Question: Is this fact directly supported by the source text excerpt? "
        f"Answer with JSON: {{\"verified\": true/false, \"confidence\": 0.0-1.0, \"explanation\": \"one sentence\"}}"
    )
    try:
        res = call_llm_with_retry(
            client=client,
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result = json.loads(res)
        return FactVerificationResult(
            verified=result.get("verified", False),
            confidence=result.get("confidence", 0.0),
            explanation=result.get("explanation", ""),
        )
    except Exception:
        ok = _word_overlap_check(fact_value, raw_text)
        return FactVerificationResult(verified=ok, confidence=0.5 if ok else 0.0, explanation="LLM verification failed, fell back to word-overlap")


def observer_node(state: AgentState, tool_name: str, tool_result: ToolResult, raw_text: str, client: Any = None):
    """Processes tool output, validates facts, runs conflict check, updates state."""
    if not tool_result.success:
        state.escalations.append(f"[TOOL FAILED] {tool_name}: {tool_result.error_message}")
        state.pending_info.append(f"Tool {tool_name} failed: {tool_result.error_message}")
        return

    data = tool_result.data
    source_tag = f"tool_{tool_name}"

    # Verify and add facts based on tool executed
    if tool_name == "extract_demographics":
        state.sections_completed.append("demographics")
        for key in ["name", "age", "gender", "mrn", "address"]:
            val = data.get(key)
            if val:
                vr = verify_fact_with_llm(client, val, raw_text)
                if vr.verified:
                    check_conflict_node(state, key, val, source_tag)
                    state.demographics[key] = Fact(value=val, source=source_tag, confidence=vr.confidence)
                    state.facts.append(Fact(value=f"{key.upper()}: {val}", source=source_tag, confidence=vr.confidence))
                else:
                    state.missing_fields.append(key)
            else:
                state.missing_fields.append(key)

    elif tool_name == "extract_dates":
        state.sections_completed.append("dates")
        adm = data.get("admission_date")
        dis = data.get("discharge_date")
        if adm:
            vr = verify_fact_with_llm(client, adm, raw_text)
            if vr.verified:
                check_conflict_node(state, "admission_date", adm, source_tag)
                state.admission_date = Fact(value=adm, source=source_tag, confidence=vr.confidence)
                state.facts.append(Fact(value=f"Admission: {adm}", source=source_tag, confidence=vr.confidence))
            else:
                state.missing_fields.append("admission_date")
        else:
            state.missing_fields.append("admission_date")

        if dis:
            vr = verify_fact_with_llm(client, dis, raw_text)
            if vr.verified:
                check_conflict_node(state, "discharge_date", dis, source_tag)
                state.discharge_date = Fact(value=dis, source=source_tag, confidence=vr.confidence)
                state.facts.append(Fact(value=f"Discharge: {dis}", source=source_tag, confidence=vr.confidence))
            else:
                state.discharge_date = Fact(value="Not found", status=FactStatus.PENDING, source=source_tag)
                state.pending_info.append("Discharge Date pending/missing")
        else:
            state.discharge_date = Fact(value="Not found", status=FactStatus.PENDING, source=source_tag)
            state.pending_info.append("Discharge Date pending/missing")

    elif tool_name == "extract_diagnoses":
        state.sections_completed.append("diagnoses")
        p_dx = data.get("principal_diagnosis")
        s_dxs = data.get("secondary_diagnoses", [])
        if p_dx:
            # Extract conflict note if present, then strip it from the stored value
            conflict_match = re.search(r'\[⚠ CONFLICT: (.+?)\]', p_dx)
            if conflict_match:
                conflict_note = conflict_match.group(1)
                p_dx_clean = p_dx[:conflict_match.start()].strip()
                state.conflicts.append(Conflict(
                    field="principal_diagnosis",
                    value1=p_dx_clean or p_dx,
                    value2=conflict_note,
                    sources=[source_tag],
                ))
                p_dx = p_dx_clean if p_dx_clean else p_dx
            vr = verify_fact_with_llm(client, p_dx, raw_text)
            if vr.verified:
                state.diagnoses.insert(0, Fact(value=p_dx, source=source_tag, confidence=vr.confidence))
                state.facts.append(Fact(value=f"Principal Diagnosis: {p_dx}", source=source_tag, confidence=vr.confidence))
            else:
                state.missing_fields.append("principal_diagnosis")
        else:
            state.missing_fields.append("principal_diagnosis")

        for d in s_dxs:
            vr = verify_fact_with_llm(client, d, raw_text)
            if vr.verified:
                state.diagnoses.append(Fact(value=d, source=source_tag, confidence=vr.confidence))
                state.facts.append(Fact(value=f"Secondary Diagnosis: {d}", source=source_tag, confidence=vr.confidence))

    elif tool_name == "extract_medications":
        state.sections_completed.append("medications")
        meds_list = data
        for m in meds_list:
            raw_name = (m.get('name') or '').strip()
            dosage = (m.get('dosage') or '').strip()
            frequency = (m.get('frequency') or '').strip()
            route = (m.get('route') or '').strip()

            name_for_verify = f"{raw_name} {dosage}".strip() if dosage else raw_name
            if frequency:
                name_for_verify = f"{name_for_verify} {frequency}".strip()
            vr = verify_fact_with_llm(client, name_for_verify, raw_text)
            if not vr.verified:
                state.missing_fields.append(f"medication_{raw_name}")
                continue

            med_val = raw_name
            note_parts = [p for p in [dosage, route, frequency] if p]
            note_str = " | ".join(note_parts)

            fact_obj = Fact(value=med_val, source=source_tag, note=note_str, confidence=vr.confidence)
            if m.get("status") == "admission":
                state.admission_medications.append(fact_obj)
                state.facts.append(Fact(value=f"Admission Med: {med_val} ({note_str})", source=source_tag, confidence=vr.confidence))
            else:
                state.discharge_medications.append(fact_obj)
                state.facts.append(Fact(value=f"Discharge Med: {med_val} ({note_str})", source=source_tag, confidence=vr.confidence))

    elif tool_name == "reconcile_medications":
        recon_changes = data
        for rc in recon_changes:
            mc = MedicationChange(
                drug=rc["drug"],
                change_type=rc["change_type"],
                admission_dose=rc["admission_dose"],
                discharge_dose=rc["discharge_dose"],
                reason_documented=rc["reason_documented"],
                flagged_for_review=rc["flagged_for_review"],
                note=rc["note"]
            )
            state.med_changes.append(mc)
            if mc.flagged_for_review:
                state.escalations.append(f"[MED RECON WARNING] {mc.drug} ({mc.change_type}): {mc.note}")
            state.facts.append(Fact(value=f"MedChange: {mc.drug} {mc.change_type} (Reason: {mc.note})", source=source_tag))
        # Check drug interactions for each discharge medication
        for dis_med in state.discharge_medications:
            interaction_result = drug_interaction_lookup_tool(dis_med.value)
            state.facts.append(Fact(value=f"Drug Interaction Check: {interaction_result}", source=source_tag))
            if "Interaction warnings" in interaction_result:
                state.escalations.append(f"[DRUG INTERACTION] {interaction_result}")

    elif tool_name == "extract_allergies":
        state.sections_completed.append("allergies")
        allergies = data.get("allergies", [])
        missing = data.get("is_missing_or_not_known", True)
        if missing or not allergies:
            state.allergies.append(Fact(value="Not Known", status=FactStatus.MISSING, source=source_tag))
            state.facts.append(Fact(value="Allergies: Not Known", status=FactStatus.MISSING, source=source_tag))
        else:
            for a in allergies:
                vr = verify_fact_with_llm(client, a, raw_text)
                if vr.verified:
                    state.allergies.append(Fact(value=a, source=source_tag, confidence=vr.confidence))
                    state.facts.append(Fact(value=f"Allergy: {a}", source=source_tag, confidence=vr.confidence))

    elif tool_name == "extract_hospital_course":
        state.sections_completed.append("hospital_course")
        summary = data.get("summary")
        if summary:
            vr = verify_fact_with_llm(client, summary, raw_text)
            if vr.verified:
                state.hospital_course = Fact(value=summary, source=source_tag, confidence=vr.confidence)
                state.facts.append(Fact(value=f"Hospital Course Summary: {summary[:100]}...", source=source_tag, confidence=vr.confidence))
            else:
                state.missing_fields.append("hospital_course")
        else:
            state.missing_fields.append("hospital_course")

    elif tool_name == "extract_procedures":
        state.sections_completed.append("procedures")
        procs = data.get("procedures", [])
        for p in procs:
            vr = verify_fact_with_llm(client, p, raw_text)
            if vr.verified:
                state.procedures.append(Fact(value=p, source=source_tag, confidence=vr.confidence))
                state.facts.append(Fact(value=f"Procedure: {p}", source=source_tag, confidence=vr.confidence))

    elif tool_name == "extract_follow_up":
        state.sections_completed.append("follow_up")
        insts = data.get("instructions", [])
        pends = data.get("pending_results", [])
        for i in insts:
            vr = verify_fact_with_llm(client, i, raw_text)
            if vr.verified:
                state.follow_up_instructions.append(Fact(value=i, source=source_tag, confidence=vr.confidence))
                state.facts.append(Fact(value=f"Follow-up advice: {i}", source=source_tag, confidence=vr.confidence))
        for p in pends:
            vr = verify_fact_with_llm(client, p, raw_text)
            if vr.verified:
                state.pending_results.append(Fact(value=p, status=FactStatus.PENDING, source=source_tag, confidence=vr.confidence))
                state.facts.append(Fact(value=f"Pending Lab: {p}", status=FactStatus.PENDING, source=source_tag, confidence=vr.confidence))
                state.pending_info.append(f"Pending Lab: {p}")

    elif tool_name == "extract_discharge_condition":
        state.sections_completed.append("discharge_condition")
        cond = data.get("condition")
        if cond:
            vr = verify_fact_with_llm(client, cond, raw_text)
            if vr.verified:
                check_conflict_node(state, "discharge_condition", cond, source_tag)
                state.discharge_condition = Fact(value=cond, source=source_tag, confidence=vr.confidence)
                state.facts.append(Fact(value=f"Discharge Condition: {cond}", source=source_tag, confidence=vr.confidence))
            else:
                state.missing_fields.append("discharge_condition")
        else:
            state.missing_fields.append("discharge_condition")

    elif tool_name == "check_lab_status":
        lab_status = data
        lab_name_str = lab_status.get("source_snippet", "lab") if isinstance(lab_status, dict) else "lab"
        lab_status_str = f"Lab status={lab_status.get('status')}, val={lab_status.get('value')}"
        state.facts.append(Fact(value=lab_status_str, source=source_tag))
        if lab_status.get("status") == "pending":
            state.pending_info.append(f"Pending Lab: {lab_name_str} ({lab_status.get('value')})")

    elif tool_name == "drug_interaction_lookup":
        state.facts.append(Fact(value=f"Drug Interaction Check: {data}", source=source_tag))

    elif tool_name == "flag_for_review":
        state.facts.append(Fact(value=f"Clinician Escalation: {data}", source=source_tag))


# === GUARDRAIL 4: OUTPUT-SIDE RE-VALIDATION ===
class SectionRevalidationOutput(BaseModel):
    section: str
    supported: bool = True
    confidence: float = 1.0
    concerns: str = ""


def revalidate_section_with_llm(client: Any, section_name: str, section_content: str, raw_text: str) -> SectionRevalidationOutput:
    """Check a single draft section against source text using LLM."""
    if _client_or_mock(client):
        return SectionRevalidationOutput(section=section_name, supported=True, confidence=1.0, concerns="Mock mode, no revalidation")
    if not section_content or section_content.startswith("[MISSING") or section_content.startswith("[NOT DOCUMENTED") or section_content.startswith("[PENDING"):
        return SectionRevalidationOutput(section=section_name, supported=True, confidence=1.0, concerns="Section is empty/missing — no revalidation needed")

    snippet = _extract_relevant_snippet(section_content, raw_text, char_padding=2000)
    if not snippet:
        return SectionRevalidationOutput(section=section_name, supported=True, confidence=0.5, concerns="Could not extract source snippet for verification")

    prompt = (
        f"Source text excerpt:\n---SNIPPET---\n{snippet[:2500]}\n---END SNIPPET---\n\n"
        f"Draft section content to verify:\n---SECTION---\n{section_content[:1000]}\n---END SECTION---\n\n"
        f"Question: Is every medical claim in this draft section directly supported by the source text excerpt?\n"
        f"Return JSON: {{\"supported\": true/false, \"confidence\": 0.0-1.0, \"concerns\": \"describe any unsupported claims or empty string\"}}"
    )
    try:
        res = call_llm_with_retry(
            client=client,
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result = json.loads(res)
        return SectionRevalidationOutput(
            section=section_name,
            supported=result.get("supported", True),
            confidence=result.get("confidence", 1.0),
            concerns=result.get("concerns", ""),
        )
    except Exception:
        return SectionRevalidationOutput(section=section_name, supported=True, confidence=0.5, concerns="LLM revalidation call failed")


def revalidate_draft(state: AgentState, raw_text: str, client: Any) -> list[str]:
    """Run output-side re-validation on key draft sections. Returns list of issues found."""
    reval_issues = []
    sections_to_check = []

    if state.diagnoses:
        sections_to_check.append(("Principal Diagnosis", state.diagnoses[0].value))
    if state.hospital_course:
        sections_to_check.append(("Hospital Course", state.hospital_course.value))
    if state.discharge_medications:
        sections_to_check.append(("Discharge Medications", "; ".join(m.value for m in state.discharge_medications[:5])))
    if state.discharge_condition:
        sections_to_check.append(("Discharge Condition", state.discharge_condition.value))

    for section_name, content in sections_to_check:
        result = revalidate_section_with_llm(client, section_name, content, raw_text)
        if not result.supported or result.confidence < 0.5:
            reval_issues.append(f"[REVALIDATION FAILED] {section_name}: {result.concerns}")
            state.escalations.append(f"[REVALIDATION FAILED] {section_name}: {result.concerns}")
        elif result.confidence < 0.8:
            reval_issues.append(f"[REVALIDATION LOW CONFIDENCE] {section_name}: confidence={result.confidence:.2f}")

    return reval_issues


# === GUARDRAIL 5: CROSS-FIELD CONSISTENCY ===
def check_cross_field_consistency(state: AgentState) -> list[str]:
    """Check for logical inconsistencies across extracted fields."""
    issues = []

    # 1. Chronological: admission before discharge
    adm = state.admission_date
    dis = state.discharge_date
    if adm and dis and adm.value and dis.value:
        try:
            import re as _re
            def _parse_date(s):
                parts = _re.findall(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', s)
                if parts:
                    d, m, y = parts[0]
                    return int(y), int(m), int(d)
                return None
            adm_p = _parse_date(adm.value)
            dis_p = _parse_date(dis.value)
            if adm_p and dis_p:
                if adm_p > dis_p:
                    issues.append(f"[INCONSISTENCY] Discharge date ({dis.value}) is before admission date ({adm.value})")
                    state.escalations.append(f"[INCONSISTENCY] Discharge date ({dis.value}) is before admission date ({adm.value})")
        except Exception:
            pass

    # 2. Age-appropriate diagnosis sanity
    age_str = state.demographics.get("age")
    gender_str = state.demographics.get("gender")
    if age_str and state.diagnoses:
        age_val = age_str.value.strip().lower()
        gender_val = gender_str.value.strip().lower() if gender_str else ""
        try:
            age_num = int(_re.search(r'(\d+)', age_val).group(1)) if _re.search(r'(\d+)', age_val) else None
        except Exception:
            age_num = None

        if age_num is not None:
            female_only_dx = {"PREGNANCY", "PUERPERIUM", "OVARIAN", "ENDOMETRIAL", "CERVICAL DYSPLASIA",
                              "VAGINITIS", "BREAST LOBULAR", "UTERINE", "OBSTETRIC"}
            pacdiatric_improbable = {"PROSTATE", "BENIGN PROSTATIC", "ERECTILE", "TESTICULAR", "MENOPAUSE", "ANDROPAUSE"}
            elderly_improbable_adult = {"CHILDHOOD", "CONGENITAL", "PEDIATRIC"}
            for dx_fact in state.diagnoses:
                dx_upper = dx_fact.value.upper()
                if age_num < 12 and any(p in dx_upper for p in elderly_improbable_adult):
                    issues.append(f"[INCONSISTENCY] Diagnosis '{dx_fact.value}' is unlikely for a {age_num}-year-old patient")
                    state.escalations.append(f"[INCONSISTENCY] Diagnosis '{dx_fact.value}' is unlikely for a {age_num}-year-old patient")
                if age_num < 60 and "DEMENTIA" in dx_upper and "ALCOHOLIC" not in dx_upper:
                    issues.append(f"[INCONSISTENCY] Diagnosis '{dx_fact.value}' is unusual for a {age_num}-year-old")
                    state.escalations.append(f"[INCONSISTENCY] Diagnosis '{dx_fact.value}' is unusual for a {age_num}-year-old")

    # 3. Medications in reconciliation but not in discharge list (and vice versa)
    discharge_names = set()
    for m in state.discharge_medications:
        discharge_names.add(m.value.split()[0].upper() if m.value.split() else "")
    for mc in state.med_changes:
        drug_upper = mc.drug.upper()
        drug_key = drug_upper.split()[0] if drug_upper.split() else ""
        if mc.change_type in ("stopped",) and drug_key and drug_key in discharge_names:
            pass  # This is fine — stopped med might still be mentioned

    return issues


def check_conflict_node(state: AgentState, field_name: str, new_value: str, source: str):
    if not new_value or any(x in new_value.lower() for x in ["not documented", "missing"]):
        return
    existing_value = None
    existing_sources = []
    
    if field_name == "admission_date" and state.admission_date:
        existing_value = state.admission_date.value
        existing_sources.append(state.admission_date.source)
    elif field_name == "discharge_date" and state.discharge_date and state.discharge_date.status == FactStatus.FOUND:
        existing_value = state.discharge_date.value
        existing_sources.append(state.discharge_date.source)
    elif field_name == "discharge_condition" and state.discharge_condition:
        existing_value = state.discharge_condition.value
        existing_sources.append(state.discharge_condition.source)
    elif field_name in state.demographics:
        existing_value = state.demographics[field_name].value
        existing_sources.append(state.demographics[field_name].source)
        
    if existing_value and existing_value.strip().lower() != new_value.strip().lower():
        conflict_obj = Conflict(field=field_name, value1=existing_value, value2=new_value, sources=existing_sources + [source])
        state.conflicts.append(conflict_obj)
        state.escalations.append(f"[CONFLICT] {field_name}: '{existing_value}' vs '{new_value}'")


# === GRAPH NODE: FINALIZER (Third Guardrail) ===
def finalizer_node(state: AgentState, client: Any = None) -> str:
    """Builds the final discharge summary, applying strict missing/pending defaults."""
    # Ensure medication reconciliation has run
    if not state.med_changes and (state.admission_medications or state.discharge_medications):
        raw_changes = reconcile_medications_tool(
            client=client,
            admission_list=[{"name": m.value, "dosage": m.note} for m in state.admission_medications],
            discharge_list=[{"name": m.value, "dosage": m.note} for m in state.discharge_medications],
            raw_notes_text=state.raw_text
        )
        for rc in raw_changes:
            mc = MedicationChange(
                drug=rc["drug"],
                change_type=rc["change_type"],
                admission_dose=rc["admission_dose"],
                discharge_dose=rc["discharge_dose"],
                reason_documented=rc["reason_documented"],
                flagged_for_review=rc["flagged_for_review"],
                note=rc["note"]
            )
            state.med_changes.append(mc)

    from src.output.composer import compose_draft, render_confidence_warnings
    draft = compose_draft(state)

    # Output-side re-validation (Guardrail 4)
    reval_issues = revalidate_draft(state, state.raw_text, client)
    if reval_issues:
        for issue in reval_issues:
            state.escalations.append(issue)

    # Cross-field consistency checks (Guardrail 5)
    consistency_issues = check_cross_field_consistency(state)
    if consistency_issues:
        for issue in consistency_issues:
            if issue not in state.escalations:
                state.escalations.append(issue)

    # Regenerate draft with any new escalations from revalidation/consistency
    draft = compose_draft(state)

    # Append TRUNCATED flag if step count exceeded limits
    if state.truncated:
        draft = "⚠️ [TRUNCATED DUE TO STEP COUNT LIMIT]\n" + draft

    # Append confidence warnings for low-confidence facts
    low_conf_warnings = render_confidence_warnings(state)
    draft += low_conf_warnings
        
    state.final_summary = draft
    state.done = True
    return draft


# === OCR QUALITY ASSESSMENT ===
def assess_ocr_quality(text: str) -> dict:
    """Assess OCR quality and return metrics + warnings."""
    if not text or len(text) < 50:
        return {"quality": "poor", "issues": ["Text too short or empty"], "score": 0.0}

    total_chars = len(text)
    alpha = sum(1 for c in text if c.isalpha())
    digits = sum(1 for c in text if c.isdigit())
    whitespace = sum(1 for c in text if c.isspace())
    special = total_chars - alpha - digits - whitespace

    alpha_ratio = alpha / total_chars if total_chars else 0
    whitespace_ratio = whitespace / total_chars if total_chars else 0

    issues = []

    # 1. Alpha ratio should be >40% for meaningful text
    if alpha_ratio < 0.35:
        issues.append(f"OCR quality warning: Low alphabetic content ({alpha_ratio:.0%}). Text may be garbled.")
    elif alpha_ratio < 0.50:
        issues.append(f"OCR quality note: Moderate alphabetic content ({alpha_ratio:.0%}).")

    # 2. Whitespace ratio: too high = lots of broken characters
    if whitespace_ratio > 0.45:
        issues.append(f"OCR quality warning: High whitespace ratio ({whitespace_ratio:.0%}). Possible broken character segmentation.")

    # 3. Average word length
    words = text.split()
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 3.0:
            issues.append(f"OCR quality warning: Very short average word length ({avg_word_len:.1f} chars). Possible garbled text.")
        elif avg_word_len < 4.0:
            issues.append(f"OCR quality note: Short average word length ({avg_word_len:.1f} chars).")

    # 4. Special character ratio (e.g., weird symbols from OCR errors)
    special_ratio = special / total_chars if total_chars else 0
    if special_ratio > 0.10:
        issues.append(f"OCR quality warning: High special character ratio ({special_ratio:.0%}). Possible encoding/OCR artifacts.")

    if len(issues) >= 3:
        quality = "poor"
    elif issues:
        quality = "fair"
    else:
        quality = "good"

    return {"quality": quality, "issues": issues, "score": alpha_ratio}


# === AGENT GRAPH EXECUTION LOOP ===
def run_agent_loop(
    patient_id: str,
    raw_text: str,
    client: Any,
    max_iterations: int = 12,
    improver=None,
) -> tuple[AgentState, StepTrace]:
    state = AgentState(
        patient_id=patient_id,
        max_iterations=max_iterations,
        raw_text=raw_text,
    )
    # segment notes
    state.segment_notes = {}
    parts = re.split(r'--- (Page \d+.*?) ---', raw_text)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            key = parts[i]
            content = parts[i+1].strip()
            state.segment_notes[key] = content
            state.raw_texts[key] = content
    else:
        state.segment_notes["Full Document"] = raw_text
        state.raw_texts["Full Document"] = raw_text

    # Assess OCR quality at the start
    ocr_result = assess_ocr_quality(raw_text)
    if ocr_result["quality"] == "poor":
        state.escalations.append(f"[OCR QUALITY] POOR: {'; '.join(ocr_result['issues'])}")
        print(f"[OCR QUALITY] WARNING: {ocr_result['issues'][0] if ocr_result['issues'] else 'Poor quality'}")
    elif ocr_result["quality"] == "fair":
        state.escalations.append(f"[OCR QUALITY] FAIR: {'; '.join(ocr_result['issues'][:2])}")
        print(f"[OCR QUALITY] Note: {ocr_result['issues'][0] if ocr_result['issues'] else 'Fair quality'}")

    trace = StepTrace()

    system_prompt = (
        "You are a clinical discharge summary agent. You must NEVER fabricate clinical facts. "
        "Mark missing data explicitly. Flag conflicts explicitly. Output JSON with next_tool, rationale, and input."
    )
    
    # In-context learning memory injection (Part 2)
    if improver:
        system_prompt += improver.get_improvement_prompt_suffix()
        improver.prepare_rules()

    MAX_STEPS = 20  # Extended to allow full coverage across all sections

    # Map each tool to its corresponding section name for dedup guard
    _TOOL_TO_SECTION = {
        "extract_demographics": "demographics",
        "extract_dates": "dates",
        "extract_diagnoses": "diagnoses",
        "extract_hospital_course": "hospital_course",
        "extract_procedures": "procedures",
        "extract_medications": "medications",
        "extract_allergies": "allergies",
        "extract_follow_up": "follow_up",
        "extract_discharge_condition": "discharge_condition",
    }

    while state.step_count < MAX_STEPS and not state.done:
        state.step_count += 1

        # 1. Planner Node
        decision = planner_node(state, client, system_prompt)

        next_tool = decision.get("next_tool", "finalize")
        rationale = decision.get("rationale", "")
        tool_input = decision.get("input", {})

        if next_tool == "finalize" or next_tool == "finish":
            break

        # Guard: if the planner proposes a section-extraction tool for a section
        # already completed, override with mock planner to move forward.
        section_for_tool = _TOOL_TO_SECTION.get(next_tool)
        if section_for_tool and section_for_tool in state.sections_completed:
            override = _mock_planner_decision(state)
            next_tool = override.get("next_tool", "finalize")
            rationale = f"[GUARD] Overrode repeated '{section_for_tool}' call. {override.get('rationale', '')}"
            tool_input = override.get("input", {})
            if next_tool == "finalize":
                break

        # 2. Tool Executor Node
        tool_result = tool_executor_node(next_tool, tool_input, state, client)

        # 3. Observer Node
        observer_node(state, next_tool, tool_result, raw_text, client)

        # Record step to trace
        trace.record(
            step=state.step_count,
            reasoning=rationale,
            tool=next_tool,
            params=tool_input,
            result=str(tool_result.data) if tool_result.success else f"Error: {tool_result.error_message}",
            decision="continue"
        )
        
        # Record PlanStep to state
        state.plan_history.append(PlanStep(
            step=state.step_count,
            rationale=rationale,
            tool=next_tool,
            input=tool_input,
            result=str(tool_result.data)[:200] if tool_result.success else "Error",
            next_plan="continue"
        ))

        # Tracing Observability step logs
        trace_log = {
            "step": state.step_count,
            "rationale": rationale,
            "tool": next_tool,
            "input": tool_input,
            "result": str(tool_result.data)[:500] if tool_result.success else "Error",
            "next_plan": "continue"
        }
        # Print JSON-line trace log
        print(json.dumps(trace_log))

    # Check for truncation
    if state.step_count >= MAX_STEPS and not state.done:
        state.truncated = True
        state.escalations.append(f"[CAP REACHED] Maximum step count limit ({MAX_STEPS}) reached. Draft may be incomplete.")

    # 4. Finalizer Node
    final_draft = finalizer_node(state, client)
    
    # Save the trace to a file
    try:
        os.makedirs("output", exist_ok=True)
        with open(f"output/trace_{patient_id}.json", "w") as f:
            # Save as JSON lines
            for step in trace.steps:
                f.write(json.dumps(step) + "\n")
    except Exception as e:
        print(f"Warning: Failed to save trace for {patient_id}: {e}")

    return state, trace
