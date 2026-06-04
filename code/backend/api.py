"""FastAPI server for Modeling Longitudinal Learning Dynamics Using Markov Models.

Mirrors runManualAssignment(): user supplies a categorical state for each course
position; we count mismatches against every trajectory prototype sequence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# The shared API factory is vendored alongside this file (backend/fyp_shared), so the
# project is fully self-contained and needs no external sibling folder to run.
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fyp_shared.api import create_app  # noqa: E402

_DASHBOARD_PATH = _PROJECT_ROOT / "outputs" / "backend" / "dashboard.json"


def _load() -> Dict[str, Any]:
    if not _DASHBOARD_PATH.exists():
        raise RuntimeError(f"{_DASHBOARD_PATH} missing; run run/run_pipeline.ps1 first.")
    return json.loads(_DASHBOARD_PATH.read_text(encoding="utf-8"))


_DASHBOARD = _load()
_MANUAL = _DASHBOARD.get("manual_demo") or {}
_FIELD_SCHEMA: List[Dict[str, Any]] = list(_MANUAL.get("field_schema") or [])
_STATES: List[str] = list(_MANUAL.get("states") or [])
_TRAJECTORIES: List[Dict[str, Any]] = list(_DASHBOARD.get("trajectory_profiles") or [])
_FEATURE_ORDER = [f["name"] for f in _FIELD_SCHEMA]

_SCHEMA = {
    "input_type": "categorical_sequence",
    "feature_order": _FEATURE_ORDER,
    "field_schema": _FIELD_SCHEMA,
    "states": _STATES,
    "trajectory_profiles": _TRAJECTORIES,
}


def predict(payload: Dict[str, Any]) -> Dict[str, Any]:
    values = payload.get("values", payload)
    if not isinstance(values, dict):
        raise ValueError("payload.values must be an object {step_N: state}")
    sequence: List[str] = []
    for f in _FEATURE_ORDER:
        if f not in values:
            raise ValueError(f"missing field: {f}")
        sequence.append(str(values[f]))

    scored: List[Dict[str, Any]] = []
    for profile in _TRAJECTORIES:
        proto = profile.get("prototype_sequence") or []
        mismatches = sum(1 for i, state in enumerate(sequence) if i < len(proto) and state != proto[i])
        scored.append({
            "label": profile.get("trajectory_label"),
            "distance": mismatches,
            "mean_final_grade": profile.get("mean_final_grade"),
            "prototype": proto,
        })
    scored.sort(key=lambda r: r["distance"])
    best = scored[0] if scored else {}
    return {
        "prediction": {
            "trajectory": best.get("label"),
            "mismatches": best.get("distance"),
            "mean_final_grade": best.get("mean_final_grade"),
            "prototype": best.get("prototype") or [],
        },
        "scores": scored,
        "echo": {"sequence": sequence},
    }


app = create_app(
    title="Modeling Longitudinal Learning Dynamics Using Markov Models",
    predict_fn=predict,
    schema_dict=_SCHEMA,
)
