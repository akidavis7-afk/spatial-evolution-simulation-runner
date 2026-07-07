from pathlib import Path

import pytest

from multipop_runner.config import ConfigError, expand_runs, load_config, validate_run


def test_sweep_expands_and_preserves_zero_row_sums():
    config = load_config(Path("configs/two_deme_migration_sweep.yml"))
    runs = expand_runs(config)
    assert len(runs) == 4
    for run in runs:
        validate_run(run)
        assert all(abs(sum(row)) < 1e-12 for row in run.migration_matrix)


def test_neutral_model_is_rejected():
    config = load_config(Path("configs/two_deme_migration_sweep.yml"))
    config["parameters"]["selection_coefficients"] = [0.0, 0.0]
    with pytest.raises(ConfigError, match="neutral"):
        expand_runs(config)
