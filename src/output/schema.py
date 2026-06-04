from typing import Optional


REQUIRED_SECTIONS = [
    "patient_demographics",
    "admission_discharge_dates",
    "principal_diagnosis",
    "secondary_diagnoses",
    "hospital_course",
    "procedures",
    "discharge_medications",
    "allergies",
    "follow_up_instructions",
    "pending_results",
    "discharge_condition",
]

SECTION_LABELS = {
    "patient_demographics": "Patient Demographics",
    "admission_discharge_dates": "Admission & Discharge Dates",
    "principal_diagnosis": "Principal Diagnosis",
    "secondary_diagnoses": "Secondary Diagnoses",
    "hospital_course": "Hospital Course",
    "procedures": "Procedures",
    "discharge_medications": "Discharge Medications",
    "allergies": "Allergies",
    "follow_up_instructions": "Follow-Up Instructions",
    "pending_results": "Pending Results",
    "discharge_condition": "Discharge Condition",
}

DRAFT_TEMPLATE = """# DISCHARGE SUMMARY DRAFT — FOR CLINICIAN REVIEW

**Patient:** {patient_name}
**MRN/IP No:** {mrn}
**Date of Admission:** {admission_date}
**Date of Discharge:** {discharge_date}

---

## Principal Diagnosis
{principal_diagnosis}

## Secondary Diagnoses
{secondary_diagnoses}

## Patient Demographics
{demographics}

## Hospital Course
{hospital_course}

## Procedures
{procedures}

## Discharge Medications
{discharge_medications}

### Medication Reconciliation Notes
{med_reconciliation}

## Allergies
{allergies}

## Follow-Up Instructions
{follow_up}

## Pending Results
{pending_results}

## Discharge Condition
{discharge_condition}

---

*This is an AI-generated DRAFT for clinician review. All fields not directly sourced from documents are marked [MISSING] or [PENDING]. Do not use as a final clinical document without verification.*

**Conflicts Detected:**
{conflicts}

**Flagged Items for Clinician Review:**
{escalations}
"""
