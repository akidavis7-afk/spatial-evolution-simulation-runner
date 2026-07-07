from __future__ import annotations

import copy
import itertools
import math
import re
from pathlib import Path
from typing import Any

import yaml

from .models import ExperimentRun


class ConfigError(ValueError):
    """Raised when the experiment configuration is invalid."""


def _slug(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip("-") or "run"


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Top-level YAML value must be a mapping.")
    return data


def _as_tuple_of_ints(value: Any, field: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a non-empty list.")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ConfigError(f"Every value in {field} must be an integer.")
    return tuple(value)


def _as_tuple_of_floats(value: Any, field: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a non-empty list.")
    try:
        values = tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Every value in {field} must be numeric.") from exc
    if not all(math.isfinite(item) for item in values):
        raise ConfigError(f"Every value in {field} must be finite.")
    return values


def _as_matrix(value: Any, field: str) -> tuple[tuple[float, ...], ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a non-empty list of rows.")
    rows: list[tuple[float, ...]] = []
    for row in value:
        rows.append(_as_tuple_of_floats(row, field))
    return tuple(rows)


def validate_run(run: ExperimentRun, tolerance: float = 1e-10) -> None:
    if run.model not in {"new_mutation", "from_equilibrium"}:
        raise ConfigError("model must be 'new_mutation' or 'from_equilibrium'.")

    n = run.population_count
    if n < 2:
        raise ConfigError("At least two subpopulations are required.")
    if any(size <= 0 for size in run.population_sizes):
        raise ConfigError("population_sizes must contain only positive integers.")
    if len(run.selection_coefficients) != n:
        raise ConfigError("selection_coefficients length must match population_sizes.")
    if all(abs(value) <= tolerance for value in run.selection_coefficients):
        raise ConfigError("Purely neutral selection is outside the upstream program's documented scope.")
    if len(run.migration_matrix) != n or any(len(row) != n for row in run.migration_matrix):
        raise ConfigError("migration_matrix must be square and match the number of populations.")

    for i, row in enumerate(run.migration_matrix):
        if row[i] > tolerance:
            raise ConfigError(f"migration_matrix diagonal [{i},{i}] must be non-positive.")
        for j, value in enumerate(row):
            if i != j and value < -tolerance:
                raise ConfigError(f"Off-diagonal migration rate [{i},{j}] must be non-negative.")
        if abs(sum(row)) > tolerance:
            raise ConfigError(
                f"Migration row {i} sums to {sum(row):.6g}; each row must sum to zero."
            )

    if run.sep < 20:
        raise ConfigError("sep must be at least 20.")
    if run.replicates < 1:
        raise ConfigError("replicates must be at least 1.")
    if run.model == "new_mutation":
        if run.initial_population is None:
            raise ConfigError("initial_population is required for new_mutation.")
        if not 0 <= run.initial_population < n:
            raise ConfigError("initial_population is outside the population index range.")


def _scale_migration(matrix: list[list[float]], factor: float) -> list[list[float]]:
    n = len(matrix)
    output = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                output[i][j] = float(matrix[i][j]) * factor
        output[i][i] = -sum(output[i][j] for j in range(n) if j != i)
    return output


def _apply_sweep(base: dict[str, Any], target: str, value: float | int) -> dict[str, Any]:
    output = copy.deepcopy(base)
    if target == "migration_scale":
        factor = float(value)
        if factor <= 0:
            raise ConfigError("migration_scale values must be positive.")
        output["migration_matrix"] = _scale_migration(output["migration_matrix"], factor)
    elif target == "selection_scale":
        factor = float(value)
        output["selection_coefficients"] = [
            float(item) * factor for item in output["selection_coefficients"]
        ]
    elif target == "population_scale":
        factor = float(value)
        if factor <= 0:
            raise ConfigError("population_scale values must be positive.")
        output["population_sizes"] = [
            max(1, int(round(int(item) * factor))) for item in output["population_sizes"]
        ]
    elif target == "initial_population":
        output["initial_population"] = int(value)
    elif target == "replicates":
        output["replicates"] = int(value)
    elif target == "sep":
        output["sep"] = int(value)
    else:
        raise ConfigError(
            "Unsupported sweep target. Use migration_scale, selection_scale, "
            "population_scale, initial_population, replicates, or sep."
        )
    return output


def _build_run(
    experiment_name: str,
    model: str,
    settings: dict[str, Any],
    run_number: int,
    sweep_name: str | None,
    sweep_value: float | int | None,
) -> ExperimentRun:
    sizes = _as_tuple_of_ints(settings.get("population_sizes"), "population_sizes")
    selection = _as_tuple_of_floats(
        settings.get("selection_coefficients"), "selection_coefficients"
    )
    migration = _as_matrix(settings.get("migration_matrix"), "migration_matrix")

    suffix = f"{run_number:03d}"
    if sweep_name is not None:
        suffix += f"-{_slug(sweep_name)}-{_slug(sweep_value)}"

    run = ExperimentRun(
        run_id=f"{_slug(experiment_name)}-{suffix}",
        model=model,
        population_sizes=sizes,
        selection_coefficients=selection,
        migration_matrix=migration,
        sep=int(settings.get("sep", 1000)),
        replicates=int(settings.get("replicates", 1000)),
        initial_population=(
            int(settings.get("initial_population", 0))
            if model == "new_mutation"
            else None
        ),
        sweep_name=sweep_name,
        sweep_value=sweep_value,
    )
    validate_run(run)
    return run


def expand_runs(config: dict[str, Any]) -> list[ExperimentRun]:
    experiment = config.get("experiment", {})
    if not isinstance(experiment, dict):
        raise ConfigError("experiment must be a mapping.")
    name = str(experiment.get("name", "multipopulation-experiment"))
    model = str(experiment.get("model", "new_mutation"))

    base = config.get("parameters")
    if not isinstance(base, dict):
        raise ConfigError("parameters must be a mapping.")

    sweeps = config.get("sweeps", [])
    if sweeps is None:
        sweeps = []
    if not isinstance(sweeps, list):
        raise ConfigError("sweeps must be a list.")

    if not sweeps:
        return [_build_run(name, model, base, 1, None, None)]

    targets: list[str] = []
    value_lists: list[list[float | int]] = []
    for entry in sweeps:
        if not isinstance(entry, dict):
            raise ConfigError("Each sweep entry must be a mapping.")
        target = str(entry.get("target", ""))
        values = entry.get("values")
        if not isinstance(values, list) or not values:
            raise ConfigError(f"Sweep {target!r} must define a non-empty values list.")
        targets.append(target)
        value_lists.append(values)

    runs: list[ExperimentRun] = []
    for index, combination in enumerate(itertools.product(*value_lists), start=1):
        settings = copy.deepcopy(base)
        labels: list[str] = []
        for target, value in zip(targets, combination):
            settings = _apply_sweep(settings, target, value)
            labels.append(f"{target}={value}")
        sweep_name = ";".join(targets)
        sweep_value: float | int | str
        if len(combination) == 1:
            sweep_value = combination[0]
        else:
            sweep_value = ";".join(str(value) for value in combination)
        runs.append(_build_run(name, model, settings, index, sweep_name, sweep_value))
    return runs
