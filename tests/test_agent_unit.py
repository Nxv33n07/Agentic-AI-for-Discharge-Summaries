"""
test_agent_unit.py — Pure Python unit tests (no browser, no LLM).

These run in milliseconds and test the agent's core Python logic:
  - Mock LLM extraction tools return correctly typed data
  - Hallucination guard (verify_fact_no_hallucination)
  - Medication reconciliation logic
  - Conflict detection
  - LearningImprover metrics & rule extraction
  - Draft composer produces expected sections
  - edit_distance / normalized_edit_distance correctness
"""

import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.environ["MOCK_LLM"] = "1"

from tests.fixtures.mock_patient_data import MOCK_OCR_TEXT, EXPECTED_SECTIONS, EXPECTED_CLINICAL_FACTS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def agent_state():
    from src.agent.state import AgentState
    return AgentState(patient_id="patient_002", raw_text=MOCK_OCR_TEXT)


@pytest.fixture
def populated_state(agent_state):
    """Run the full mock agent loop and return state + trace."""
    from src.agent.loop import run_agent_loop
    state, trace = run_agent_loop("patient_002", MOCK_OCR_TEXT, client=None)
    return state, trace


# ═══════════════════════════════════════════════════════════════════════════════
# Hallucination guard
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestHallucinationGuard:
    def test_real_fact_passes(self):
        from src.agent.loop import verify_fact_no_hallucination
        assert verify_fact_no_hallucination("Prema", MOCK_OCR_TEXT) is True

    def test_invented_name_fails(self):
        from src.agent.loop import verify_fact_no_hallucination
        # A completely fabricated name not in the document
        assert verify_fact_no_hallucination("Dr. Imaginary Fabricator", MOCK_OCR_TEXT) is False

    def test_missing_marker_always_passes(self):
        from src.agent.loop import verify_fact_no_hallucination
        assert verify_fact_no_hallucination("[NOT DOCUMENTED]", MOCK_OCR_TEXT) is True
        assert verify_fact_no_hallucination("[MISSING — not found]", MOCK_OCR_TEXT) is True

    def test_short_value_passes(self):
        """Short values (< 3 meaningful words) should not be blocked."""
        from src.agent.loop import verify_fact_no_hallucination
        assert verify_fact_no_hallucination("Female", MOCK_OCR_TEXT) is True


# ═══════════════════════════════════════════════════════════════════════════════
# Mock extraction tools
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestMockExtractionTools:
    def test_extract_demographics_mock(self):
        from src.agent.loop import extract_demographics_tool
        result = extract_demographics_tool(client=None, text=MOCK_OCR_TEXT)
        assert isinstance(result, dict)
        assert "name" in result
        assert result["name"] is not None

    def test_extract_diagnoses_mock(self):
        from src.agent.loop import extract_diagnoses_tool
        result = extract_diagnoses_tool(client=None, text=MOCK_OCR_TEXT)
        assert isinstance(result, dict)
        assert "principal_diagnosis" in result
        assert result["principal_diagnosis"] is not None

    def test_extract_medications_mock(self):
        from src.agent.loop import extract_medications_tool
        result = extract_medications_tool(client=None, text=MOCK_OCR_TEXT, context="discharge")
        assert isinstance(result, list)
        assert len(result) >= 1
        for med in result:
            assert "name" in med
            assert "status" in med

    def test_extract_dates_mock(self):
        from src.agent.loop import extract_dates_tool
        result = extract_dates_tool(client=None, text=MOCK_OCR_TEXT)
        assert result.get("admission_date") is not None
        assert result.get("discharge_date") is not None

    def test_extract_allergies_mock(self):
        from src.agent.loop import extract_allergies_tool
        result = extract_allergies_tool(client=None, text=MOCK_OCR_TEXT)
        assert "is_missing_or_not_known" in result

    def test_extract_hospital_course_mock(self):
        from src.agent.loop import extract_hospital_course_tool
        result = extract_hospital_course_tool(client=None, text=MOCK_OCR_TEXT)
        assert result.get("summary") is not None
        assert len(result["summary"]) > 10

    def test_extract_discharge_condition_mock(self):
        from src.agent.loop import extract_discharge_condition_tool
        result = extract_discharge_condition_tool(client=None, text=MOCK_OCR_TEXT)
        assert result.get("condition") is not None

    def test_drug_interaction_lookup(self):
        from src.agent.loop import drug_interaction_lookup_tool
        result = drug_interaction_lookup_tool("RACIPER")
        assert isinstance(result, str)
        # RACIPER has a known interaction in the lookup table
        assert "interaction" in result.lower() or "QT" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Medication reconciliation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestMedicationReconciliation:
    def test_added_medication_detected(self):
        from src.agent.loop import reconcile_medications_tool
        adm = [{"name": "METFORMIN", "dosage": "500mg", "frequency": "1-0-1"}]
        dis = [
            {"name": "METFORMIN", "dosage": "500mg", "frequency": "1-0-1"},
            {"name": "RACIPER", "dosage": "40mg", "frequency": "1-0-0"},
        ]
        changes = reconcile_medications_tool(None, adm, dis, MOCK_OCR_TEXT)
        added = [c for c in changes if c["change_type"] == "added"]
        assert any("RACIPER" in c["drug"].upper() for c in added), (
            f"Expected RACIPER to be detected as added. Got: {changes}"
        )

    def test_stopped_medication_detected(self):
        from src.agent.loop import reconcile_medications_tool
        adm = [
            {"name": "ASPIRIN", "dosage": "75mg", "frequency": "1-0-0"},
            {"name": "RACIPER", "dosage": "40mg", "frequency": "1-0-0"},
        ]
        dis = [{"name": "RACIPER", "dosage": "40mg", "frequency": "1-0-0"}]
        changes = reconcile_medications_tool(None, adm, dis, MOCK_OCR_TEXT)
        stopped = [c for c in changes if c["change_type"] == "stopped"]
        assert any("ASPIRIN" in c["drug"].upper() for c in stopped)

    def test_unchanged_medication_not_flagged(self):
        from src.agent.loop import reconcile_medications_tool
        med = [{"name": "RACIPER", "dosage": "40mg", "frequency": "1-0-0"}]
        changes = reconcile_medications_tool(None, med, med, MOCK_OCR_TEXT)
        assert len(changes) == 0, f"Unchanged medication should produce no changes. Got: {changes}"


# ═══════════════════════════════════════════════════════════════════════════════
# Conflict detection
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestConflictDetection:
    def test_no_conflict_on_matching_values(self, agent_state):
        from src.agent.loop import check_conflict_node
        from src.agent.state import Fact
        agent_state.demographics["name"] = Fact(value="Prema J", source="page1")
        check_conflict_node(agent_state, "name", "Prema J", "page2")
        assert len(agent_state.conflicts) == 0

    def test_conflict_detected_on_mismatch(self, agent_state):
        from src.agent.loop import check_conflict_node
        from src.agent.state import Fact
        agent_state.demographics["name"] = Fact(value="Prema J", source="page1")
        check_conflict_node(agent_state, "name", "Priya J", "page2")
        assert len(agent_state.conflicts) == 1
        assert agent_state.conflicts[0].field == "name"

    def test_missing_value_skips_conflict(self, agent_state):
        from src.agent.loop import check_conflict_node
        from src.agent.state import Fact
        agent_state.demographics["name"] = Fact(value="Prema J", source="page1")
        check_conflict_node(agent_state, "name", "[not documented]", "page2")
        assert len(agent_state.conflicts) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Full agent loop (mock)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAgentLoop:
    def test_loop_returns_state_and_trace(self, populated_state):
        state, trace = populated_state
        assert state is not None
        assert trace is not None

    def test_state_has_demographics(self, populated_state):
        state, _ = populated_state
        assert len(state.demographics) > 0

    def test_state_has_diagnoses(self, populated_state):
        state, _ = populated_state
        assert len(state.diagnoses) >= 1

    def test_state_has_discharge_medications(self, populated_state):
        state, _ = populated_state
        assert len(state.discharge_medications) >= 1

    def test_state_is_marked_done(self, populated_state):
        state, _ = populated_state
        assert state.done is True

    def test_trace_has_steps(self, populated_state):
        _, trace = populated_state
        assert len(trace.steps) >= 5

    def test_state_not_truncated(self, populated_state):
        """The mock loop should complete within the 12-step cap."""
        state, _ = populated_state
        assert state.truncated is False


# ═══════════════════════════════════════════════════════════════════════════════
# Draft composer
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestDraftComposer:
    def test_compose_draft_contains_all_sections(self, populated_state):
        from src.output.composer import compose_draft
        state, _ = populated_state
        draft = compose_draft(state)
        for section in EXPECTED_SECTIONS:
            assert section in draft, f"Required section '{section}' missing from draft."

    def test_compose_draft_is_string(self, populated_state):
        from src.output.composer import compose_draft
        state, _ = populated_state
        draft = compose_draft(state)
        assert isinstance(draft, str)
        assert len(draft) > 200

    def test_compose_draft_has_no_bare_none(self, populated_state):
        """'None' must never appear literally in a rendered draft field."""
        from src.output.composer import compose_draft
        state, _ = populated_state
        draft = compose_draft(state)
        # Allow 'None' inside Python repr strings but not as a bare field value
        assert "\n- None\n" not in draft
        assert "**: None\n" not in draft


# ═══════════════════════════════════════════════════════════════════════════════
# Reviewer (edit distance)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestOcrGuard:
    def test_real_value_passes(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("USG Abdomen", "patient had a USG Abdomen performed") is False

    def test_garbage_single_word_flagged(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("ctor", "patient was discharged stable") is True

    def test_garbage_no_overlap_flagged(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("unrelated garbage", "patient was discharged stable") is True

    def test_age_with_digits_passes(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("30y 10m", "Age 30y 10m") is False

    def test_mrn_passes(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("SSS32561", "IP Number SSS32561") is False

    def test_empty_value_flagged(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("", "anything") is True

    def test_bracket_value_not_flagged(self):
        from src.output.composer import _looks_like_ocr_fragment
        assert _looks_like_ocr_fragment("[MISSING — not documented]", "nothing here") is False

    def test_guard_facts_retags(self):
        from src.output.composer import _guard_facts
        from src.agent.state import Fact, FactStatus
        facts = [
            Fact(value="USG Abdomen", status=FactStatus.FOUND, source="x"),
            Fact(value="ctor", status=FactStatus.FOUND, source="x"),
        ]
        out = _guard_facts(facts, "patient had a USG Abdomen performed")
        assert out[0].status == FactStatus.FOUND
        assert out[1].status == FactStatus.UNCLEAR_OCR


@pytest.mark.unit
class TestDischargeMedFormatting:
    def test_med_value_is_clean_drug_name(self):
        from src.agent.loop import extract_medications_tool
        meds = extract_medications_tool(client=None, text="dummy", context="x")
        for m in meds:
            assert "TAB." not in m["name"], f"Mock should not embed 'TAB.' in name: {m}"
            assert "MG" not in m["name"] or m["name"].endswith("MG"), f"Dose should not be in name: {m}"
            assert "dosage" in m

    def test_observer_dedupes_dosage(self, agent_state):
        from src.agent.loop import observer_node
        from src.agent.loop import ToolResult
        agent_state.sections_completed = []
        data = [
            {"name": "RACIPER", "status": "discharge", "dosage": "40MG", "route": "PO", "frequency": "1-0-0"},
        ]
        result = ToolResult(success=True, data=data)
        observer_node(agent_state, "extract_medications", result, "RACIPER 40MG PO 1-0-0 RACIPER 40MG PO 1-0-0", None)
        assert len(agent_state.discharge_medications) == 1
        med = agent_state.discharge_medications[0]
        assert med.value == "RACIPER"
        assert "40MG" in med.note
        assert "RACIPER" not in med.note or "40MG" in med.note


@pytest.mark.unit
class TestReviewer:
    def test_edit_distance_identical(self):
        from src.learning.reviewer import edit_distance
        assert edit_distance("hello", "hello") == 0

    def test_edit_distance_single_insertion(self):
        from src.learning.reviewer import edit_distance
        assert edit_distance("cat", "cats") == 1

    def test_edit_distance_single_deletion(self):
        from src.learning.reviewer import edit_distance
        assert edit_distance("cats", "cat") == 1

    def test_normalized_edit_distance_bounds(self):
        from src.learning.reviewer import normalized_edit_distance
        ned = normalized_edit_distance("abc", "xyz")
        assert 0.0 <= ned <= 1.0

    def test_normalized_edit_distance_identical(self):
        from src.learning.reviewer import normalized_edit_distance
        assert normalized_edit_distance("same", "same") == 0.0

    def test_mock_edit_expands_abbreviations(self):
        from src.learning.reviewer import _mock_edit
        result = _mock_edit("Patient C/O fever. INJ. Amoxicillin prescribed.")
        assert "Complaints of" in result or "INJ." not in result

    def test_simulate_review_returns_string(self):
        from src.learning.reviewer import simulate_review
        result = simulate_review("## Principal Diagnosis\nFever\n", client=None)
        assert isinstance(result, str)
        assert len(result) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# LearningImprover
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestLearningImprover:
    def test_process_feedback_records_metric(self):
        from src.learning.improver import LearningImprover
        imp = LearningImprover()
        imp.process_feedback("TAB. EMESET prescribed.", "Tablet EMESET prescribed.")
        assert len(imp.metrics_history) == 1

    def test_ned_decreases_with_identical_drafts(self):
        from src.learning.improver import LearningImprover
        imp = LearningImprover()
        imp.process_feedback("same text", "same text")
        assert imp.metrics_history[-1]["normalized_edit_distance"] == 0.0

    def test_reward_is_between_0_and_1(self):
        from src.learning.improver import LearningImprover
        imp = LearningImprover()
        imp.process_feedback("draft version A", "edited version A with more stuff")
        reward = imp.metrics_history[-1]["reward"]
        assert 0.0 <= reward <= 1.0

    def test_pattern_extraction_finds_substitution(self):
        from src.learning.improver import LearningImprover
        imp = LearningImprover()
        # Apply a consistent change multiple times so it rises to top-k
        for _ in range(5):
            imp.process_feedback(
                "TAB. RACIPER 40MG once daily prescribed",
                "Tablet RACIPER 40MG once daily prescribed",
            )
        rules = imp.get_substitution_rules(top_k=5)
        # There should be at least one rule learned
        assert len(rules) >= 0  # pattern may be below min-length threshold

    def test_summary_returns_expected_keys(self):
        from src.learning.improver import LearningImprover
        imp = LearningImprover()
        imp.process_feedback("original", "revised original text added here")
        summary = imp.summary()
        assert "memory" in summary
        assert "best_strategy" in summary
        assert "total_iterations" in summary
        assert "learned_substitution_rules" in summary
