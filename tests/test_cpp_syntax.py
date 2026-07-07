from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from multipop_runner.config import expand_runs, load_config
from multipop_runner.cppgen import render_main


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ is not installed")
def test_all_generated_entry_points_are_valid_cpp(tmp_path: Path):
    headers = {
        "parameter.hpp": """#pragma once
#include <vector>
class Parameter {
public:
    std::vector<double> ss;
    std::vector<std::vector<double>> ms;
    std::vector<int> pop_sizes;
};
""",
        "detsimu.hpp": """#pragma once
#include <vector>
#include "parameter.hpp"
class Detsimu {
public:
    explicit Detsimu(Parameter) {}
    double calculate_det_trajectory(int, std::vector<double>&, std::vector<std::vector<double>>&, double) { return 0.0; }
    double ret_invasion1() const { return 1.0; }
    double ret_invasion2() const { return 1.0; }
    double return_fin_ave_freq() const { return 0.5; }
    std::vector<double> return_fin_freq() const { return {0.5, 0.5}; }
};
""",
        "diffusion.hpp": """#pragma once
#include <vector>
#include "parameter.hpp"
class Diffusion {
public:
    Diffusion(Parameter, int, int, const std::vector<double>&, const std::vector<std::vector<double>>&) {}
    Diffusion(Parameter, double, int, const std::vector<double>&, const std::vector<std::vector<double>>&) {}
    void calculate_diffusion() {}
    bool return_invasion() const { return true; }
    bool return_convergence() const { return true; }
    double return_max_eigen() const { return -0.1; }
    double return_sum_sojourn() const { return 10.0; }
};
""",
        "stocsimu.hpp": """#pragma once
#include <vector>
#include "parameter.hpp"
class Stocsimu {
public:
    Stocsimu(Parameter, int, int) {}
    Stocsimu(Parameter, const std::vector<double>&, int) {}
    void run_simulation() {}
};
""",
    }
    for name, content in headers.items():
        (tmp_path / name).write_text(content, encoding="utf-8")

    runs = [
        expand_runs(load_config(Path("configs/two_deme_migration_sweep.yml")))[0],
        expand_runs(load_config(Path("configs/three_deme_example.yml")))[0],
    ]
    for run in runs:
        for program in ("theory", "simulation"):
            (tmp_path / "main.cpp").write_text(render_main(run, program), encoding="utf-8")
            result = subprocess.run(
                ["g++", "-std=c++17", "-fsyntax-only", "main.cpp"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
