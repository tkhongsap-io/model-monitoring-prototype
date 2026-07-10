"""HTTP telemetry client — the monitor's LIVE adapters PULL raw telemetry from the
external model apps (the models never push; the monitor reaches OUT to their URLs).

Uses httpx (already a backend dep). Kept tiny on purpose: this is the ONLY code that
crosses the process boundary to the model services — everything downstream operates on
plain dicts / DataFrames. Contract v1.0: bearer auth is sent when the monitor's
LIVE_TELEMETRY_TOKEN is set (the apps require it when THEIR RAI_TELEMETRY_TOKEN is set);
feature order/categoricals are OWNED by the model service (X-Feature-Order /
X-Categorical-Features headers, echoed in GET /telemetry/meta) — never hardcoded here.
"""
from __future__ import annotations

import io

import httpx


def _auth_headers() -> dict:
    """Bearer header when the monitor is configured with a telemetry token.

    config is imported lazily so this module stays import-cycle-free (config loads .env;
    adapters are imported from many places).
    """
    from .. import config
    token = getattr(config, "LIVE_TELEMETRY_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _split_header(value: str | None) -> list[str] | None:
    """Comma-split a header into a list; missing/empty -> None (caller falls back)."""
    items = [s.strip() for s in (value or "").split(",") if s.strip()]
    return items or None


def pull(base_url: str, path: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    """GET a telemetry Window envelope: {contract_version, window, from_tick, to_tick,
    count, records, ...}."""
    r = httpx.get(base_url.rstrip("/") + path, params=params, timeout=timeout,
                  headers=_auth_headers())
    r.raise_for_status()
    return r.json()


def pull_meta(base_url: str, timeout: float = 10.0) -> dict:
    """GET /telemetry/meta — {contract_version, model_name, use_case_type, latest_tick,
    feature_order, categorical_features, ...}. Best-effort: {} on any failure (callers
    use it for cursor sync / feature ownership, never as a hard dependency)."""
    try:
        r = httpx.get(base_url.rstrip("/") + "/telemetry/meta", timeout=timeout,
                      headers=_auth_headers())
        r.raise_for_status()
        return r.json()
    except Exception:  # noqa: BLE001 — meta is advisory, never crash a tick over it
        return {}


def pull_model(base_url: str, path: str = "/model/artifact", timeout: float = 60.0):
    """Load the joblib model artifact the app serves. Returns (model, version:int, meta)
    where meta = {"feature_order": [...] | None, "categorical": [...] | None} parsed from
    the X-Feature-Order / X-Categorical-Features headers (the model service OWNS its
    feature list — the monitor never hardcodes a per-use-case one).

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
    r = httpx.get(base_url.rstrip("/") + path, timeout=timeout, headers=_auth_headers())
    r.raise_for_status()
    model = joblib.load(io.BytesIO(r.content))
    version = int(r.headers.get("X-Model-Version", "1"))
    meta = {"feature_order": _split_header(r.headers.get("X-Feature-Order")),
            "categorical": _split_header(r.headers.get("X-Categorical-Features"))}
    return model, version, meta
