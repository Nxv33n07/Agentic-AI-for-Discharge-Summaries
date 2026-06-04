"""
conftest.py — Pytest configuration for the Discharge Summary Agent.
"""

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: quick sanity checks")
    config.addinivalue_line("markers", "e2e: full end-to-end UI flows")
    config.addinivalue_line("markers", "unit: pure-Python unit tests (no browser)")
