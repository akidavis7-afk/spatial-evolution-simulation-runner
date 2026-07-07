from pathlib import Path

import pandas as pd

from multipop_runner.config import expand_runs, load_config
from multipop_runner.report import create_synthetic_demo


def test_demo_writes_outputs(tmp_path):
    runs = expand_runs(load_config(Path("configs/two_deme_migration_sweep.yml")))
    result_path = create_synthetic_demo(runs, tmp_path)
    frame = pd.read_csv(result_path)
    assert len(frame) == 4
    assert set(frame["data_origin"]) == {"synthetic_portfolio_demo"}
    assert (tmp_path / "theory_vs_simulation.png").exists()
    assert (tmp_path / "relative_error.png").exists()
    assert (tmp_path / "summary.md").exists()
