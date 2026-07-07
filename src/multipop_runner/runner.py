from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .cppgen import render_main
from .models import ExperimentRun
from .parsers import parse_simulation_output, parse_theory_output, relative_error


class RunnerError(RuntimeError):
    """Raised when an upstream source tree cannot be prepared or executed."""


def _expected_source(upstream: Path, run: ExperimentRun, program: str) -> Path:
    return upstream / run.model / program


def render_sources(runs: list[ExperimentRun], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for run in runs:
        for program in ("theory", "simulation"):
            destination = output_dir / run.run_id / program / "main.cpp"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render_main(run, program), encoding="utf-8")
            paths.append(destination)
    return paths


def _compile(work_dir: Path, executable: Path, extra_flags: list[str]) -> tuple[str, float]:
    cpp_files = sorted(str(path.name) for path in work_dir.glob("*.cpp"))
    if not cpp_files:
        raise RunnerError(f"No C++ source files found in {work_dir}")
    command = [
        "g++", *cpp_files, "-Wall", "-Wextra", "-std=c++17", "-O3",
        *extra_flags, "-o", executable.name,
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=work_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RunnerError(
            f"Compilation failed in {work_dir}\nCOMMAND: {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return " ".join(command), elapsed


def _execute(executable: Path, work_dir: Path, timeout: int) -> tuple[str, str, int, float]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [str(executable)],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"Execution timed out after {timeout}s: {executable}") from exc
    elapsed = time.perf_counter() - started
    return completed.stdout, completed.stderr, completed.returncode, elapsed


def run_upstream(
    runs: list[ExperimentRun],
    upstream_repo: Path,
    output_dir: Path,
    timeout: int = 300,
    extra_flags: list[str] | None = None,
) -> Path:
    upstream_repo = upstream_repo.resolve()
    output_dir = output_dir.resolve()
    extra_flags = extra_flags or []
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    for run in runs:
        row: dict[str, Any] = {
            **run.to_dict(),
            "population_count": run.population_count,
            "data_origin": "upstream_cpp_execution",
        }
        record: dict[str, Any] = {"run": run.to_dict(), "programs": {}}

        for program in ("theory", "simulation"):
            source = _expected_source(upstream_repo, run, program)
            if not source.exists():
                raise RunnerError(
                    f"Expected upstream source folder not found: {source}. "
                    "Download TSakamoto-evo/multipopulation_approximation first."
                )
            work_dir = output_dir / "work" / run.run_id / program
            if work_dir.exists():
                shutil.rmtree(work_dir)
            shutil.copytree(source, work_dir)
            (work_dir / "main.cpp").write_text(render_main(run, program), encoding="utf-8")
            executable = work_dir / ("runner.exe" if os.name == "nt" else "runner.out")
            command, compile_seconds = _compile(work_dir, executable, extra_flags)
            stdout, stderr, returncode, run_seconds = _execute(executable, work_dir, timeout)

            log_dir = output_dir / "logs" / run.run_id
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{program}.stdout.txt").write_text(stdout, encoding="utf-8")
            (log_dir / f"{program}.stderr.txt").write_text(stderr, encoding="utf-8")

            parsed = (
                parse_theory_output(stdout)
                if program == "theory"
                else parse_simulation_output(stdout)
            )
            row.update(parsed)
            row[f"{program}_return_code"] = returncode
            row[f"{program}_compile_seconds"] = round(compile_seconds, 6)
            row[f"{program}_run_seconds"] = round(run_seconds, 6)
            record["programs"][program] = {
                "command": command,
                "return_code": returncode,
                "compile_seconds": compile_seconds,
                "run_seconds": run_seconds,
                "stdout_log": str(log_dir / f"{program}.stdout.txt"),
                "stderr_log": str(log_dir / f"{program}.stderr.txt"),
            }

        row["relative_absorption_time_error"] = relative_error(
            row.get("theory_absorption_time"),
            row.get("simulation_mean_absorption_time"),
        )
        rows.append(row)
        manifest.append(record)

    result_path = output_dir / "results.csv"
    _write_rows(rows, result_path)
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return result_path


def _write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized = {
                key: json.dumps(value) if isinstance(value, (list, dict, tuple)) else value
                for key, value in row.items()
            }
            writer.writerow(serialized)
