from pydantic import BaseModel, Field
from typing import Optional, Any


class FactStatus:
    FOUND = "found"
    MISSING = "missing"
    PENDING = "pending"
    CONFLICT = "conflict"
    UNCLEAR_OCR = "unclear_ocr"


class Fact(BaseModel):
    value: str
    status: str = FactStatus.FOUND
    source: str = ""
    page: Optional[str] = None
    note: str = ""
    confidence: float = 1.0  # 0.0 (unsupported) to 1.0 (directly stated in source)


class Conflict(BaseModel):
    field: str
    value1: str
    value2: str
    sources: list[str] = Field(default_factory=list)


class Medication(BaseModel):
    name: str
    status: str  # "admission" or "discharge"
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None


class MedicationChange(BaseModel):
    drug: str
    change_type: str = ""  # "added", "stopped", "changed"
    admission_dose: str = ""
    discharge_dose: str = ""
    reason_documented: bool = False
    flagged_for_review: bool = False
    note: str = ""


class PlanStep(BaseModel):
    step: int
    rationale: str
    tool: str
    input: Any
    result: str
    next_plan: str


class AgentState(BaseModel):
    patient_id: str
    raw_texts: dict[str, str] = Field(default_factory=dict)  # segment_key -> text
    facts: list[Fact] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    pending_info: list[str] = Field(default_factory=list)
    step_count: int = 0
    plan_history: list[PlanStep] = Field(default_factory=list)
    final_summary: Optional[str] = None
    truncated: bool = False

    # Backwards compatibility fields for composer and UI
    demographics: dict[str, Fact] = Field(default_factory=dict)
    diagnoses: list[Fact] = Field(default_factory=list)
    hospital_course: Optional[Fact] = None
    procedures: list[Fact] = Field(default_factory=list)
    admission_medications: list[Fact] = Field(default_factory=list)
    discharge_medications: list[Fact] = Field(default_factory=list)
    med_changes: list[MedicationChange] = Field(default_factory=list)
    allergies: list[Fact] = Field(default_factory=list)
    follow_up_instructions: list[Fact] = Field(default_factory=list)
    pending_results: list[Fact] = Field(default_factory=list)
    discharge_condition: Optional[Fact] = None
    admission_date: Optional[Fact] = None
    discharge_date: Optional[Fact] = None
    escalations: list[str] = Field(default_factory=list)
    sections_completed: list[str] = Field(default_factory=list)
    max_iterations: int = 12
    done: bool = False
    raw_text: str = ""
    segment_notes: dict[str, str] = Field(default_factory=dict)
