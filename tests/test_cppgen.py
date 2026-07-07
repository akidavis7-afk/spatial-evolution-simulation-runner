from pathlib import Path

from multipop_runner.config import expand_runs, load_config
from multipop_runner.cppgen import render_main


def test_generated_cpp_contains_all_parameters():
    run = expand_runs(load_config(Path("configs/three_deme_example.yml")))[0]
    source = render_main(run, "theory")
    assert "std::vector<int> pop_sizes = {300, 450, 350};" in source
    assert "std::vector<std::vector<double>> ms" in source
    assert "Diffusion diff" in source
    assert "absorption time" in source
