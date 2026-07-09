"""HTTP telemetry client — the monitor's LIVE adapters PULL raw telemetry from the
external model apps (the models never push; the monitor reaches OUT to their URLs).

Uses httpx (already a backend dep). Kept tiny on purpose: this is the ONLY code that
crosses the process boundary to the model services — everything downstream operates on
plain dicts / DataFrames.
"""
from __future__ import annotations

import io

import httpx


def pull(base_url: str, path: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """GET a telemetry Window envelope: {window, from_tick, to_tick, count, records}."""
    r = httpx.get(base_url.rstrip("/") + path, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def pull_model(base_url: str, path: str = "/model/artifact", timeout: float = 60.0):
    """Load the joblib model artifact the app serves. Returns (model, version:int).

    SECURITY: joblib.load is pickle-based (arbitrary code execution on hostile input).
    This is acceptable here because BOTH ends are first-party: the artifact is a fitted
    scikit-learn estimator served by OUR OWN model apps (ai-use-cases), and `base_url`
    is an operator-configured value (localhost in dev, our own deployment in prod) — not
    user-supplied and not an untrusted third party. Deserializing the real fitted model
    is required to run SHAP TreeExplainer / LIME on it (no JSON form works). Production
    hardening path if these ever leave a trusted network: switch both ends to `skops`
    (safe sklearn (de)serialization) or sign the artifact.
    """
    import joblib
    r = httpx.get(base_url.rstrip("/") + path, timeout=timeout)
    r.raise_for_status()
    model = joblib.load(io.BytesIO(r.content))
    version = int(r.headers.get("X-Model-Version", "1"))
    return model, version
