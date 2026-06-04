import difflib
import re
from collections import Counter
from src.learning.reviewer import CorrectionMemory, normalized_edit_distance


class ContextualBandit:
    def __init__(self):
        self.strategies = {
            "default": "Use the standard extraction approach.",
            "verbose": "Include more contextual detail from surrounding text.",
            "conservative": "Only extract if confidence is high; mark as MISSING otherwise.",
            "structured": "Present findings in bullet-point format.",
        }
        self.rewards = {s: [] for s in self.strategies}
        self.counts = {s: 0 for s in self.strategies}

    def select_strategy(self, context: dict) -> str:
        if sum(self.counts.values()) < 4:
            return list(self.strategies.keys())[min(sum(self.counts.values()), 3)]
        avg_rewards = {s: (sum(self.rewards[s]) / len(self.rewards[s])) if self.rewards[s] else 0 for s in self.strategies}
        return max(avg_rewards, key=avg_rewards.get)

    def update(self, strategy: str, reward: float):
        self.rewards[strategy].append(reward)
        self.counts[strategy] += 1

    def get_best_strategy(self) -> str:
        if not any(self.rewards.values()):
            return "default"
        avg_rewards = {s: (sum(self.rewards[s]) / len(self.rewards[s])) if self.rewards[s] else 0 for s in self.strategies}
        return max(avg_rewards, key=avg_rewards.get)


class LearningImprover:
    def __init__(self):
        self.memory = CorrectionMemory()
        self.bandit = ContextualBandit()
        self.metrics_history: list[dict] = []
        self.substitution_rules: list[tuple[str, str]] = []
        self.correction_pattern_count: Counter = Counter()

    def compute_information_density(self, draft: str) -> float:
        """Measures content completeness: fraction of sections with actual data (not placeholder)."""
        sections = [
            "## Principal Diagnosis", "## Secondary Diagnoses", "## Patient Demographics",
            "## Hospital Course", "## Procedures", "## Discharge Medications",
            "## Allergies", "## Follow-Up Instructions", "## Pending Results", "## Discharge Condition"
        ]
        filled = 0
        for section in sections:
            idx = draft.find(section)
            if idx >= 0:
                content = draft[idx + len(section):].strip()
                if content and not content.startswith("[MISSING") and not content.startswith("[Not"):
                    filled += 1
        return filled / len(sections) if sections else 0.0

    def process_feedback(self, draft: str, edited: str, section: str = ""):
        self.memory.add(draft, edited, section)
        ned = normalized_edit_distance(draft, edited)
        density = self.compute_information_density(draft)
        # Reward weights: 70% conciseness (low edit distance), 30% completeness
        reward = (1.0 - ned) * 0.7 + density * 0.3
        self.bandit.update(self.bandit.get_best_strategy(), reward)
        self.metrics_history.append({
            "draft_len": len(draft),
            "edited_len": len(edited),
            "edit_distance": self.memory.pairs[-1]["edit_distance"],
            "normalized_edit_distance": ned,
            "information_density": density,
            "reward": round(reward, 4),
        })
        self._extract_patterns(draft, edited)

    def _extract_patterns(self, draft: str, edited: str):
        """Diff draft vs edited at word level to extract substitution patterns the reviewer applied."""
        d_words = draft.split()
        e_words = edited.split()
        matcher = difflib.SequenceMatcher(None, d_words, e_words)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                old = " ".join(d_words[i1:i2])
                new = " ".join(e_words[j1:j2])
                if old and new and old != new:
                    self.correction_pattern_count[(old, new)] += 1

    def get_substitution_rules(self, top_k: int = 5) -> list[tuple[str, str, int]]:
        """Return top-K frequent (old→new) patterns. Filters noisy partial matches."""
        seen = set()
        deduped = []
        for (old, new), count in self.correction_pattern_count.most_common(top_k * 3):
            if (old, new) in seen or old == new:
                continue
            if len(old) < 3:  # Lowered from 12 to 3 to catch 'TAB', 'C/O', 'INJ'
                continue
            seen.add((old, new))
            deduped.append((old, new, count))
        return deduped[:top_k]

    def apply_rules(self, text: str) -> str:
        """Apply learned substitution rules longest-first to avoid partial-match corruption."""
        sorted_rules = sorted(self.substitution_rules, key=lambda r: len(r[0]), reverse=True)
        for old, new, _ in sorted_rules:
            text = text.replace(old, new)
        return text

    def prepare_rules(self, top_k: int = 5):
        """Finalize and store the top-K rules for active use."""
        raw = self.get_substitution_rules(top_k)
        self.substitution_rules = [(old, new, cnt) for old, new, cnt in raw]

    def get_improvement_prompt_suffix(self) -> str:
        recent = self.memory.recent(3)
        mem_prompt = ""
        if recent:
            parts = ["\n[LEARNING] Here are examples of previous doctor corrections (draft -> edited):"]
            for i, r in enumerate(recent):
                parts.append(
                    f"Correction Example {i+1}:\n"
                    f"--- Agent Draft Snippet ---\n{r['draft'][:400]}...\n"
                    f"--- Doctor Preferred Snippet ---\n{r['edited'][:400]}...\n"
                )
            parts.append("Study the differences. Avoid spelling mistakes, expand clinical abbreviations, standardize medication formatting, and strive for completeness.")
            mem_prompt = "\n".join(parts)

        strategy = self.bandit.get_best_strategy()
        strat_desc = self.bandit.strategies[strategy]
        rules = self.get_substitution_rules()
        suffix_parts = []
        if rules:
            suffix_parts.append("[LEARNING] Learned correction patterns (apply these style changes to future extracts):")
            for old, new, cnt in rules:
                suffix_parts.append(f"  - \"{old[:60]}\" → \"{new[:60]}\"")
        suffix_parts.append(f"[LEARNING] Recommended strategy: {strategy} — {strat_desc}")
        suffix = "\n" + "\n".join(suffix_parts)
        if mem_prompt:
            suffix = f"{mem_prompt}\n{suffix}"
        return suffix

    def summary(self) -> dict:
        self.prepare_rules()
        return {
            "memory": self.memory.summary(),
            "strategy_counts": self.bandit.counts,
            "best_strategy": self.bandit.get_best_strategy(),
            "total_iterations": len(self.metrics_history),
            "learned_substitution_rules": [(old, new, cnt) for old, new, cnt in self.substitution_rules],
        }
