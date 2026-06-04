import os
from src.agent.state import AgentState, Fact, FactStatus
from src.tracing.trace import StepTrace

DOCTOR_EDIT_PROMPT = """You are a strict clinical reviewer. Edit the following discharge summary draft according to these rules:
- Capitalize all drug names.
- Expand abbreviations (e.g., "SOB" -> "shortness of breath", "C/O" -> "complaints of", "K/C/O" -> "known case of", "TAB." -> "Tablet", "INJ." -> "Injection").
- Remove speculative phrases like "likely", "possibly".
- If a field is missing but could be inferred from the source, add it with a note "[inferred by reviewer]".
- If the discharge condition is "Hemodynamically stable", expand to "Hemodynamically stable at time of discharge".
- Never change a clinical fact unless it is clearly wrong.
- Do NOT output any explanations or conversational text. Return only the edited summary.

Original draft:
{draft}
"""


import re


def _mock_edit(draft: str) -> str:
    """Simulated clinician editor — only applies edits that the draft hasn't already learned.
    
    If the draft already uses the preferred format, the editor skips that change.
    This simulates decreasing edit burden as the agent learns the reviewer's preferences.
    """
    edited = draft

    # 1. Normalize missing data markers (skip if already using "Not documented")
    if "[Not documented]" not in edited:
        edited = edited.replace("[MISSING — not found in source documents]", "[Not documented]")
        edited = edited.replace("[MISSING — not documented]", "[Not documented]")
        edited = edited.replace("[MISSING — no secondary diagnoses documented]", "[Not documented]")
        edited = edited.replace("[MISSING — no discharge medications documented]", "[Not documented]")

    # 2. Add review line to disclaimer (skip if already present)
    if "Reviewed by AI-assisted pipeline" not in edited and "clinician review" in edited.lower():
        edited = edited.replace(
            "Do not use as a final clinical document without verification.",
            "Do not use as a final clinical document without verification. Reviewed by AI-assisted pipeline."
        )

    # 3. Standardize medication formatting (skip if already using "Tablet")
    if "TAB." in edited or "TAB " in edited:
        # Only replace TAB patterns that are NOT already in "Tablet" context
        edited = re.sub(r'(?<!Tablet )\bTAB\.?\s+', 'Tablet ', edited)
    edited = re.sub(r'\bINJ\.?\s+', 'Injection ', edited)
    edited = re.sub(r'\bSYP\.?\s+', 'Syrup ', edited)

    # 4. Standardize common clinical terms (skip if already using preferred form)
    if "Complaints of " not in edited:
        edited = edited.replace("C/O ", "Complaints of ")
    if "complaints of " not in edited:
        edited = edited.replace("c/o ", "complaints of ")
    if "History of " not in edited and "H/o " in edited:
        edited = edited.replace("H/o ", "History of ")
    if "Known case of " not in edited:
        edited = edited.replace("K/C/O ", "Known case of ")
        edited = edited.replace("K/C/o ", "Known case of ")
    if "Hemodynamically stable at time of discharge" not in edited and "Hemodynamically stable" in edited:
        edited = edited.replace("Hemodynamically stable", "Hemodynamically stable at time of discharge")

    # 5. Fix spacing around headers
    edited = re.sub(r'##  +', '## ', edited)

    return edited


def simulate_review(draft: str, client=None, policy_name: str = "default") -> str:
    if client is None or os.getenv("MOCK_LLM", "0") == "1":
        return _mock_edit(draft)
    
    prompt = DOCTOR_EDIT_PROMPT.format(draft=draft)
    try:
        from src.agent.loop import call_llm_with_retry
        res = call_llm_with_retry(
            client=client,
            model="gemini-1.5-flash",
            contents=[prompt],
            config={
                "temperature": 0.3,
                "system_instruction": "You are a clinical document reviewer and editor. Apply edits strictly, never fabricate."
            }
        )
        return res.text.strip()
    except Exception as e:
        print(f"[REVIEWER ERROR] LLM review failed: {e}. Falling back to rule-based reviewer.")
        return _mock_edit(draft)


def edit_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        cur_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = cur_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            cur_row.append(min(insertions, deletions, substitutions))
        prev_row = cur_row
    return prev_row[-1]


def normalized_edit_distance(s1: str, s2: str) -> float:
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0.0
    return edit_distance(s1, s2) / max_len


class CorrectionMemory:
    def __init__(self):
        self.pairs: list[dict] = []

    def add(self, draft: str, edited: str, section: str = ""):
        self.pairs.append({
            "draft": draft,
            "edited": edited,
            "section": section,
            "edit_distance": edit_distance(draft, edited),
            "normalized_edit_distance": normalized_edit_distance(draft, edited),
        })

    def recent(self, n: int = 5) -> list[dict]:
        return self.pairs[-n:]

    def summary(self) -> dict:
        if not self.pairs:
            return {"count": 0, "avg_edit_distance": 0}
        avg_ed = sum(p["edit_distance"] for p in self.pairs) / len(self.pairs)
        avg_ned = sum(p["normalized_edit_distance"] for p in self.pairs) / len(self.pairs)
        return {
            "count": len(self.pairs),
            "avg_edit_distance": round(avg_ed, 2),
            "avg_normalized_edit_distance": round(avg_ned, 4),
        }

    def get_improvement_prompt(self) -> str:
        recent = self.recent(3)
        if not recent:
            return ""
        examples = []
        for r in recent:
            examples.append(f"Draft: {r['draft'][:200]}\nCorrected: {r['edited'][:200]}\n")
        return "Past corrections to learn from:\n" + "\n---\n".join(examples)


def measure_section_accuracy(draft: str, edited: str) -> dict[str, float]:
    sections = [
        "Patient Demographics", "Principal Diagnosis", "Secondary Diagnoses",
        "Hospital Course", "Discharge Medications", "Allergies",
        "Follow-Up Instructions", "Pending Results", "Discharge Condition"
    ]
    results = {}
    for section in sections:
        d_start = draft.find(f"## {section}")
        e_start = edited.find(f"## {section}")
        d_text = ""
        if d_start >= 0:
            d_end = draft.find("\n## ", d_start + 1)
            d_text = draft[d_start:d_end] if d_end > 0 else draft[d_start:]
        e_text = ""
        if e_start >= 0:
            e_end = edited.find("\n## ", e_start + 1)
            e_text = edited[e_start:e_end] if e_end > 0 else edited[e_start:]
        if d_text and e_text:
            ned = normalized_edit_distance(d_text, e_text)
            results[section] = 1.0 - ned
        elif not d_text and not e_text:
            results[section] = 1.0
        else:
            results[section] = 0.0
    return results
