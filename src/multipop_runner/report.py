from __future__ import annotations

import hashlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    number = int.from_bytes(digest[:8], "big")
    return number / float(2**64 - 1)


def create_synthetic_demo(runs, output_dir: Path) -> Path:
    """
    Create portfolio-only synthetic output.

    These numbers are deliberately not claimed to reproduce the paper or the
    upstream C++ implementation. They exercise the reporting layer before an
    upstream build is available.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in runs:
        total_n = sum(run.population_sizes)
        off_diagonal = [
            run.migration_matrix[i][j]
            for i in range(run.population_count)
            for j in range(run.population_count)
            if i != j
        ]
        mean_migration = sum(off_diagonal) / len(off_diagonal)
        selection_spread = max(run.selection_coefficients) - min(run.selection_coefficients)
        stability = 1.0 + 20.0 * mean_migration + 4.0 * selection_spread
        theory = float(total_n * stability)
        jitter = (_stable_unit_interval(run.run_id) - 0.5) * 0.12
        simulation = theory * (1.0 + jitter)
        sd = math.sqrt(abs(simulation)) * 1.8
        applicable = mean_migration >= 0.004
        max_lambda = -max(mean_migration, 1e-6) * 8.0
        rows.append(
            {
                **run.to_dict(),
                "population_count": run.population_count,
                "data_origin": "synthetic_portfolio_demo",
                "theory_status": "ok",
                "theory_invasive": True,
                "theory_applicable": applicable,
                "theory_max_lambda": max_lambda,
                "theory_absorption_time": theory,
                "simulation_status": "ok",
                "simulation_replicates": run.replicates,
                "simulation_mean_absorption_time": simulation,
                "simulation_sd_absorption_time": sd,
                "simulation_long_run": False,
                "relative_absorption_time_error": abs(theory - simulation) / simulation,
            }
        )

    frame = pd.DataFrame(rows)
    result_path = output_dir / "results.csv"
    frame.to_csv(result_path, index=False)
    create_plots(result_path, output_dir)
    create_summary(result_path, output_dir / "summary.md")
    return result_path


def create_plots(result_csv: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(result_csv)
    x_column = "sweep_value" if "sweep_value" in frame and frame["sweep_value"].notna().any() else "run_id"
    x = frame[x_column]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, frame["theory_absorption_time"], marker="o", label="Theory")
    ax.plot(x, frame["simulation_mean_absorption_time"], marker="o", label="Simulation")
    ax.set_xlabel(x_column.replace("_", " ").title())
    ax.set_ylabel("Absorption time")
    ax.set_title("Theory and simulation comparison")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    comparison = output_dir / "theory_vs_simulation.png"
    fig.savefig(comparison, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, frame["relative_absorption_time_error"] * 100.0, marker="o")
    ax.set_xlabel(x_column.replace("_", " ").title())
    ax.set_ylabel("Relative error (%)")
    ax.set_title("Approximation error across runs")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    error_plot = output_dir / "relative_error.png"
    fig.savefig(error_plot, dpi=180)
    plt.close(fig)
    return [comparison, error_plot]


def create_summary(result_csv: Path, output_path: Path) -> None:
    frame = pd.read_csv(result_csv)
    applicable = int(frame.get("theory_applicable", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    mean_error = float(frame["relative_absorption_time_error"].mean())
    origin = ", ".join(sorted(frame["data_origin"].dropna().unique()))
    lines = [
        "# Experiment summary",
        "",
        f"- Runs: **{len(frame)}**",
        f"- Theory-applicable runs: **{applicable}**",
        f"- Mean relative theory/simulation difference: **{mean_error:.2%}**",
        f"- Data origin: **{origin}**",
        "",
        "> Synthetic demo results are interface tests only and are not a scientific reproduction.",
        "",
        "## Result table",
        "",
        frame[[
            "run_id", "sweep_value", "theory_applicable",
            "theory_absorption_time", "simulation_mean_absorption_time",
            "relative_absorption_time_error",
        ]].to_markdown(index=False),
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
