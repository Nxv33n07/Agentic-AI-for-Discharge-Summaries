"""
conftest.py — Playwright pytest configuration for the Discharge Summary Agent.

Responsibilities:
  - Launches the Streamlit app in a background subprocess before the test session.
  - Tears it down cleanly after all tests complete.
  - Provides a `base_url` fixture so every test knows which port to hit.
  - Provides a `mock_ocr` fixture that writes deterministic OCR text into the
    patient_002 data directory so no real PDF extraction is needed.
"""

import os
import sys
import shutil
import time
import subprocess
import signal
import pytest

# ── Path bootstrap ──────────────────────────────────────────────────────────
# Make the project root importable from tests.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

APP_PATH = os.path.join(ROOT, "ui", "streamlit", "app.py")
STREAMLIT_PORT = 8502          # use a non-default port to avoid conflicts
BASE_URL = f"http://localhost:{STREAMLIT_PORT}"
STARTUP_WAIT_SECONDS = 8       # time to let Streamlit boot before tests run


# ── Session-scoped Streamlit server ─────────────────────────────────────────

@pytest.fixture(scope="session")
def streamlit_server():
    """
    Start a Streamlit server once for the whole E2E test session.
    NOT autouse — only starts when an E2E test requests `app_url`.
    Uses shutil.which to locate the venv's streamlit binary directly,
    avoiding the macOS issue where sys.executable resolves to the
    conda base environment when both (base) and (.venv) are active.
    """
    # Prefer the venv's own streamlit script exactly, fallback to sys.executable
    venv_streamlit = os.path.join(ROOT, ".venv", "bin", "streamlit")
    
    env = os.environ.copy()
    env["MOCK_LLM"] = "1"          # always force mock LLM in tests
    env["PYTHONPATH"] = ROOT       # ensure src imports resolve

    if os.path.exists(venv_streamlit):
        cmd = [venv_streamlit, "run", APP_PATH]
    else:
        cmd = [sys.executable, "-m", "streamlit", "run", APP_PATH]

    cmd += [
        "--server.port", str(STREAMLIT_PORT),
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
    ]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for Streamlit to be ready
    time.sleep(STARTUP_WAIT_SECONDS)

    if proc.poll() is not None:
        out, err = proc.communicate()
        pytest.fail(
            f"Streamlit failed to start.\nSTDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}"
        )

    yield proc

    # Teardown: kill the server
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── URL fixture ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app_url(streamlit_server, mock_ocr):
    """
    Return the base URL for the running Streamlit app.
    Requesting this fixture automatically starts the Streamlit server
    (E2E tests use it; unit tests don't, so no server is started for them).
    """
    return BASE_URL


# ── Mock OCR fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_ocr():
    """
    Write deterministic OCR text to data/patients/patient_002/full_ocr.txt
    before any E2E test run, ensuring the agent reads predictable data.
    Only used by E2E tests (not unit tests — those pass raw text directly).
    Restores the original file (if any) after the session.
    """
    from tests.fixtures.mock_patient_data import MOCK_OCR_TEXT

    ocr_dir = os.path.join(ROOT, "data", "patients", "patient_002")
    ocr_path = os.path.join(ocr_dir, "full_ocr.txt")

    os.makedirs(ocr_dir, exist_ok=True)

    # Back up existing file
    backup = None
    if os.path.exists(ocr_path):
        with open(ocr_path) as f:
            backup = f.read()

    with open(ocr_path, "w") as f:
        f.write(MOCK_OCR_TEXT)

    yield ocr_path

    # Restore original
    if backup is not None:
        with open(ocr_path, "w") as f:
            f.write(backup)
    elif os.path.exists(ocr_path):
        os.remove(ocr_path)



# ── Playwright browser options ────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: quick sanity checks")
    config.addinivalue_line("markers", "e2e: full end-to-end UI flows")
    config.addinivalue_line("markers", "unit: pure-Python unit tests (no browser)")
