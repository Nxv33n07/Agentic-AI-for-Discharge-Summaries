"""
Dscribe Agentic API — FastAPI surface for the Web UI.

Endpoints
---------
GET  /api/v1/health              — Liveness probe.
GET  /api/v1/learning/stats      — Aggregated learning-loop stats (Part 2).
POST /api/v1/process_patient     — Trigger an agent run on a patient.
GET  /api/v1/draft/{patient_id}  — Get the markdown draft for a run.
GET  /api/v1/trace/{patient_id}  — Get the JSON trace for a run.
"""

import os
import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.main import get_client, run_patient

app = FastAPI(
    title="Dscribe Agentic API",
    version="1.0.0",
    description=(
        "REST surface for the Dscribe discharge-summary agent. "
        "Wraps the ReAct loop with synchronous and asynchronous run modes."
    ),
)

# Permissive CORS for the Next.js dev server (localhost:3000) and prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    patient_id: str
    output_dir: str = "output"
    sync: bool = False


class ProcessResponse(BaseModel):
    patient_id: str
    status: str
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    """Liveness probe used by the Web UI's Topbar pill."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "up",
            "agent": "ready",
            "learning": "ready",
        },
    }


@app.get("/api/v1/learning/stats")
def learning_stats():
    """
    Aggregated Part-2 learning stats. Reads the improver summary written
    by `python -m src.main --part2 ...` to `output/learning/`.
    Returns a 404 with a helpful message if Part 2 hasn't been run yet.
    """
    summary_path = "output/learning/improver_summary.json"
    metrics_path = "output/learning/metrics.json"
    if not os.path.exists(summary_path):
        raise HTTPException(
            status_code=404,
            detail=(
                "No learning summary found. Run Part 2 first: "
                "MOCK_LLM=1 python -m src.main --part2 "
                "--patients patient_001 patient_002 --iterations 5"
            ),
        )
    with open(summary_path, "r") as f:
        summary = json.load(f)
    metrics = None
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
    return {
        "summary": summary,
        "metrics": metrics,
    }


@app.post("/api/v1/process_patient", response_model=ProcessResponse)
def process_patient_endpoint(
    request: ProcessRequest, background_tasks: BackgroundTasks
):
    """
    Kicks off the agent loop for a given patient. Can run in background
    or synchronously based on the `sync` flag.
    """
    def _run():
        client = get_client()
        try:
            draft, trace, state = run_patient(
                request.patient_id,
                client,
                output_dir=request.output_dir,
            )
            os.makedirs(
                f"{request.output_dir}/{request.patient_id}", exist_ok=True
            )
            with open(
                f"{request.output_dir}/{request.patient_id}/draft_summary.md", "w"
            ) as f:
                f.write(draft)
            with open(
                f"{request.output_dir}/{request.patient_id}/trace.json", "w"
            ) as f:
                f.write(trace.to_json())
        except Exception as e:
            print(f"Error processing {request.patient_id}: {e}")

    if request.sync:
        _run()
        return ProcessResponse(
            patient_id=request.patient_id,
            status="completed",
            message="Patient processing completed synchronously.",
        )

    background_tasks.add_task(_run)
    return ProcessResponse(
        patient_id=request.patient_id,
        status="processing",
        message="Patient processing started in the background.",
    )


@app.get("/api/v1/draft/{patient_id}")
def get_draft(patient_id: str, output_dir: str = "output"):
    """
    Fetches the generated Markdown draft for a completed run.
    """
    draft_path = f"{output_dir}/{patient_id}/draft_summary.md"
    if not os.path.exists(draft_path):
        raise HTTPException(
            status_code=404,
            detail="Draft not found or processing not complete.",
        )
    with open(draft_path, "r") as f:
        return {
            "patient_id": patient_id,
            "content": f.read(),
            "status": "generated",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/api/v1/trace/{patient_id}")
def get_trace(patient_id: str, output_dir: str = "output"):
    """
    Fetches the JSON trace of a completed agent run.
    """
    trace_path = f"{output_dir}/{patient_id}/trace.json"
    if not os.path.exists(trace_path):
        raise HTTPException(
            status_code=404,
            detail="Trace not found or processing not complete.",
        )
    with open(trace_path, "r") as f:
        return json.load(f)
