from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    model: str
    population_sizes: tuple[int, ...]
    selection_coefficients: tuple[float, ...]
    migration_matrix: tuple[tuple[float, ...], ...]
    sep: int
    replicates: int
    initial_population: int | None
    sweep_name: str | None = None
    sweep_value: float | int | str | None = None

    @property
    def population_count(self) -> int:
        return len(self.population_sizes)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["population_sizes"] = list(self.population_sizes)
        value["selection_coefficients"] = list(self.selection_coefficients)
        value["migration_matrix"] = [list(row) for row in self.migration_matrix]
        return value
