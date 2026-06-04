import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.agent.loop import run_agent_loop
from src.output.composer import compose_draft
from src.tracing.trace import StepTrace
from src.learning.reviewer import simulate_review, measure_section_accuracy
from src.learning.improver import LearningImprover
from src.output.validator import validate_state
from openai import OpenAI


DEFAULT_PATIENTS_DIR = "data/patients"


def get_client():
    if os.getenv("MOCK_LLM") == "1":
        print("[INFO] MOCK_LLM=1 — using deterministic mock LLM (no API calls).")
        return None

    # Prefer OpenRouter (allows access to free models)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        print("[LLM] Using OpenRouter")
        os.environ["MOCK_LLM"] = "0"
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

    # Fallback: Groq (free tier, OpenAI-compatible)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("[LLM] Using Groq llama-3.3-70b-versatile")
        os.environ["MOCK_LLM"] = "0"
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)

    os.environ["MOCK_LLM"] = "1"
    print("[INFO] No API keys found (OPENROUTER_API_KEY or GROQ_API_KEY). Using mock LLM.")
    print("[INFO] Set OPENROUTER_API_KEY or GROQ_API_KEY in .env to enable real LLM calls.")
    return None


def run_patient(
    patient_id: str,
    client,
    improver: LearningImprover = None,
    output_dir: str = "output",
):
    from src.tools.pdf_reader import get_patient_text
    raw_text = get_patient_text(patient_id)
    state, trace = run_agent_loop(patient_id, raw_text, client, improver=improver)
    draft = compose_draft(state)
    # Apply learned rules as post-processing so future drafts match reviewer preferences
    if improver:
        improver.prepare_rules()
        draft = improver.apply_rules(draft)
    return draft, trace, state


def run_part2(
    client,
    patient_ids: list[str],
    num_iterations: int = 5,
) -> tuple[LearningImprover, list[dict]]:
    improver = LearningImprover()
    all_metrics = []
    initial_ned = None
    final_ned = None

    for iteration in range(num_iterations):
        print(f"\n=== Learning Iteration {iteration + 1}/{num_iterations} ===")
        interval_metrics = []

        for pid in patient_ids:
            try:
                draft, trace, state = run_patient(pid, client, improver=improver)
                edited = simulate_review(draft, client=client)
                improver.process_feedback(draft, edited, section="full_draft")
                section_acc = measure_section_accuracy(draft, edited)
                ned = improver.metrics_history[-1]["normalized_edit_distance"]
                interval_metrics.append({
                    "patient": pid,
                    "iteration": iteration,
                    "ned": ned,
                    "section_accuracy": section_acc,
                })
                if iteration == 0:
                    initial_ned = ned
                final_ned = ned
                print(f"  Patient {pid}: NED={ned:.4f}")
            except Exception as e:
                import traceback
                print(f"  Patient {pid}: FAILED - {e}")
                traceback.print_exc()

        if interval_metrics:
            avg_ned = sum(m["ned"] for m in interval_metrics) / len(interval_metrics)
            all_metrics.append({
                "iteration": iteration,
                "avg_ned": avg_ned,
                "patients": interval_metrics,
            })
            print(f"  Average NED: {avg_ned:.4f}")

    # Before/after comparison
    if initial_ned is not None and final_ned is not None:
        improvement = ((initial_ned - final_ned) / initial_ned * 100) if initial_ned > 0 else 0
        print(f"\n=== BEFORE / AFTER COMPARISON ===")
        print(f"  Before learning: {initial_ned:.4f} NED (iteration 1)")
        print(f"  After learning:  {final_ned:.4f} NED (iteration {num_iterations})")
        print(f"  Improvement:     {improvement:.1f}% reduction in edit distance")
        if len(patient_ids) > 1:
            print(f"  Held-out patients: {', '.join(patient_ids[1:])}")

    return improver, all_metrics


def plot_results(metrics: list[dict]):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        iterations = [m["iteration"] + 1 for m in metrics]
        ned_values = [m["avg_ned"] for m in metrics]

        plt.figure(figsize=(10, 6))
        plt.plot(iterations, ned_values, marker="o", linewidth=2, markersize=8)
        plt.xlabel("Learning Iteration")
        plt.ylabel("Average Normalized Edit Distance")
        plt.title("Improvement Over Learning Iterations")
        plt.grid(True, alpha=0.3)
        plt.xticks(iterations)

        os.makedirs("output/learning", exist_ok=True)
        plt.savefig("output/learning/improvement_curve.png", dpi=150)
        print("Saved improvement curve to output/learning/improvement_curve.png")

        with open("output/learning/metrics.json", "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        print("Saved metrics to output/learning/metrics.json")

    except ImportError:
        print("Matplotlib not available. Skipping plot.")


def main():
    parser = argparse.ArgumentParser(description="Discharge Summary Agent")
    parser.add_argument("--patient", "-p", default=None,
                        help="Single patient ID to process (Part 1)")
    parser.add_argument("--patients", "-P", nargs="+", default=None,
                        help="One or more patient IDs (Part 1 batch or Part 2). "
                             "First ID trains, rest are held-out in Part 2.")
    parser.add_argument("--patients-dir", default=DEFAULT_PATIENTS_DIR,
                        help="Directory containing patient data folders")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory for drafts and traces")
    parser.add_argument("--part2", action="store_true",
                        help="Run Part 2 learning loop")
    parser.add_argument("--iterations", type=int, default=5,
                        help="Number of Part 2 iterations")
    args = parser.parse_args()

    os.environ["PATIENTS_DIR"] = args.patients_dir
    client = get_client()

    if args.patients:
        patient_ids = args.patients
    elif args.patient:
        patient_ids = [args.patient]
    else:
        patient_ids = ["patient_002"]

    if args.part2:
        print(f"Running Part 2: Learning from Doctor Edits across {len(patient_ids)} patient(s): {patient_ids}")
        try:
            improver, metrics = run_part2(client, patient_ids, args.iterations)
            plot_results(metrics)
            print(f"\nFinal summary: {json.dumps(improver.summary(), indent=2)}")
            with open("output/learning/improver_summary.json", "w") as f:
                json.dump(improver.summary(), f, indent=2, default=str)
        except Exception as e:
            import traceback
            print(f"Part 2 failed: {e}")
            traceback.print_exc()
    else:
        for pid in patient_ids:
            print(f"\n=== Running Part 1: Processing patient {pid} ===")
            try:
                draft, trace, state = run_patient(pid, client, output_dir=args.output_dir)
            except Exception as e:
                import traceback
                print(f"  Patient {pid} FAILED: {e}")
                traceback.print_exc()
                continue

            os.makedirs(f"{args.output_dir}/{pid}", exist_ok=True)
            with open(f"{args.output_dir}/{pid}/draft_summary.md", "w") as f:
                f.write(draft)
            with open(f"{args.output_dir}/{pid}/trace.json", "w") as f:
                f.write(trace.to_json())

            print(f"\nGenerated discharge summary draft at output/{pid}/draft_summary.md")
            print(f"Trace saved at output/{pid}/trace.json")
            print(f"\n=== TRACE SUMMARY ({pid}) ===")
            print(trace.readable_summary())
            print(f"\n=== ISSUES FLAGGED ({pid}) ===")
            issues = validate_state(state)
            for i in issues:
                print(f"  {i}")
            print(f"\n=== DRAFT PREVIEW (first 500 chars, {pid}) ===")
            print(draft[:500])


if __name__ == "__main__":
    main()
