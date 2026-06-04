"""
Mock clinical OCR text used as a fixture for patient_002 in Playwright tests.
Mirrors the real full_ocr.txt format so the agent's extraction logic runs on
predictable, deterministic data — no PDF needed during CI.
"""

MOCK_OCR_TEXT = """\
--- Page 1 ---
SHREE SHARADA HOSPITAL
DISCHARGE SUMMARY

Patient Name    : Prema J
Age/Sex         : 30y 10m / Female
IP Number       : SSS32561
Address         : Shimoga, Karnataka

Date of Admission  : 24/02/2026
Date of Discharge  : 26/02/2026

--- Page 2 ---
DIAGNOSIS:
Principal Diagnosis  : ACUTE GASTROENTERITIS WITH DEHYDRATION
Secondary Diagnosis  : URINARY TRACT INFECTION

HOSPITAL COURSE:
Patient presented to the OPD with complaints of loose stools x 4 episodes and vomiting x 2 episodes.
On examination patient was found to be dehydrated. Patient was admitted and started on IV fluids.
Lab investigations showed elevated Creatinine which normalized with hydration.
Patient was started on IV antibiotics for UTI coverage.
Urine culture and sensitivity sent — report awaited.
Patient improved symptomatically and was discharged in a hemodynamically stable condition.

--- Page 3 ---
PROCEDURES PERFORMED:
  - USG Abdomen
  - IV fluid administration

DISCHARGE MEDICATIONS:
  TAB. RACIPER 40MG  1-0-0
  TAB. EMESET 4MG    1-1-1
  TAB. OFLOX TZ      1-0-1
  TAB. LOPIRAMIDE 2MG 1-0-1

ALLERGIES: Not Known

FOLLOW-UP INSTRUCTIONS:
  - Review on 09.03.2026 for CBC
  - Review immediately if fever or vomiting recurs
  - Pending: Urine culture and sensitivity report

DISCHARGE CONDITION: Hemodynamically stable
"""

EXPECTED_SECTIONS = [
    "Principal Diagnosis",
    "Secondary Diagnoses",
    "Patient Demographics",
    "Hospital Course",
    "Discharge Medications",
    "Follow-Up Instructions",
    "Discharge Condition",
]

EXPECTED_CLINICAL_FACTS = {
    "patient_name": "Prema",
    "principal_diagnosis": "GASTROENTERITIS",
    "medication": "RACIPER",
    "discharge_condition": "stable",
}
