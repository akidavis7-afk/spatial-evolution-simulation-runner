from __future__ import annotations

import math
import re
from typing import Any


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _value(text: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}\s*:\s*({_NUMBER})", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _boolean(text: str, label: str) -> bool | None:
    value = _value(text, label)
    if value is None:
        return None
    return bool(int(value))


def parse_theory_output(text: str) -> dict[str, Any]:
    lower = text.lower()
    if "fail to construct deterministic trajectory" in lower:
        status = "trajectory_error"
    elif "not invasive" in lower:
        status = "not_invasive"
    elif "absorption time" in lower:
        status = "ok"
    else:
        status = "unrecognized"

    return {
        "theory_status": status,
        "theory_invasive": _boolean(text, "invasive or not"),
        "theory_applicable": _boolean(text, "applicable or not"),
        "theory_max_lambda": _value(text, "max lambda"),
        "theory_absorption_time": _value(text, "absorption time"),
    }


def parse_simulation_output(text: str) -> dict[str, Any]:
    lower = text.lower()
    if "fail to construct deterministic trajectory" in lower:
        status = "trajectory_error"
    elif "not invasive" in lower:
        status = "not_invasive"
    elif "mean absorption time" in lower:
        status = "ok"
    else:
        status = "unrecognized"

    rep = _value(text, "# of replicates")
    return {
        "simulation_status": status,
        "simulation_replicates": int(rep) if rep is not None else None,
        "simulation_mean_absorption_time": _value(text, "mean absorption time"),
        "simulation_sd_absorption_time": _value(text, "sd of absorption time"),
        "simulation_long_run": _boolean(text, "existence of long run"),
    }


def relative_error(theory: float | None, simulation: float | None) -> float | None:
    if theory is None or simulation is None or not math.isfinite(simulation) or simulation == 0:
        return None
    return abs(theory - simulation) / abs(simulation)
