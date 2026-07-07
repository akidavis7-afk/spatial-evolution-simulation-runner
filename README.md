# Multipopulation Experiment Runner

A small, independent Python workflow layer inspired by:

> Sakamoto T, Yeaman S. **Maintenance of polymorphism in spatially heterogeneous environments.**  
> *GENETICS* 232(1), iyaf229 (2026). DOI: `10.1093/genetics/iyaf229`

The paper introduces a numerical framework that approximates stochastic dynamics in complex multipopulation models with a one-dimensional diffusion process. Its public C++ repository accepts population sizes, selection coefficients, migration matrices, initial conditions, discretization points, and simulation replicates through values written in `main.cpp`, followed by separate compilation of theory and simulation programs.

This repository demonstrates how a remote dry-lab assistant can turn that manual setup into a validated, repeatable parameter-sweep workflow.

## What this companion project does

- Stores experimental parameters in readable YAML files.
- Validates population counts, selection vectors, and migration matrices.
- Enforces the documented backward-migration convention: non-negative off-diagonal rates and zero-sum rows.
- Expands migration, selection, population-size, replicate, or discretization sweeps.
- Generates model-compatible C++ `main.cpp` files for:
  - a new mutation;
  - a polymorphic equilibrium;
  - theory calculations;
  - stochastic simulations.
- Optionally compiles and executes a **local copy** of the authors' repository.
- Parses applicability, eigenvalue, absorption-time, replicate, and long-run outputs.
- Produces tidy CSV results, logs, plots, and a Markdown summary.
- Includes automated tests and GitHub Actions.

## Important boundary

The authors' scientific C++ code is **not copied into this repository**. Download it separately from:

`https://github.com/TSakamoto-evo/multipopulation_approximation`

This avoids implying authorship or redistributing code without an explicit license. The generated entry points are an independent automation layer.

The bundled `results/demo` outputs are clearly labeled **synthetic portfolio data**. They test configuration, reporting, and plotting only; they are not a reproduction of the published numerical results.

## Quick test in Cursor without Docker

Open this folder in Cursor and run from its terminal:

```bash
python -m pip install -r requirements.txt
python run.py validate configs/two_deme_migration_sweep.yml
python run.py demo configs/two_deme_migration_sweep.yml --output-dir results/demo
python -m pytest -q
```

Expected demo outputs:

```text
results/demo/results.csv
results/demo/summary.md
results/demo/theory_vs_simulation.png
results/demo/relative_error.png
```

## Preview generated C++ entry points

This step does not need the upstream repository or a C++ compiler:

```bash
python run.py render \
  configs/two_deme_migration_sweep.yml \
  --output-dir generated_sources
```

Each expanded run gets separate theory and simulation entry points.

## Run against the published C++ implementation

### 1. Download the upstream code

```bash
git clone https://github.com/TSakamoto-evo/multipopulation_approximation.git
```

### 2. Install its native dependencies

The upstream README states that Boost and Eigen are required. You also need a C++17 compiler such as `g++`.

### 3. Run the companion workflow

```bash
python run.py run \
  configs/two_deme_migration_sweep.yml \
  --upstream-repo ../multipopulation_approximation \
  --output-dir results/real \
  --timeout 300
```

On systems where Eigen is installed in a non-default include directory, add a compiler flag, for example:

```bash
python run.py run \
  configs/two_deme_migration_sweep.yml \
  --upstream-repo ../multipopulation_approximation \
  --extra-flag=-I/path/to/eigen3
```

The upstream source folders are copied into `results/real/work`; your original checkout is not changed.

## Example configuration

```yaml
experiment:
  name: two-deme-local-adaptation
  model: new_mutation

parameters:
  population_sizes: [400, 400]
  selection_coefficients: [0.04, -0.04]
  migration_matrix:
    - [-0.01, 0.01]
    - [0.01, -0.01]
  initial_population: 0
  sep: 400
  replicates: 2000

sweeps:
  - target: migration_scale
    values: [0.5, 1.0, 2.0, 4.0]
```

## Scientific and engineering cautions

- A run that the upstream program marks as non-applicable should not be interpreted as a reliable theoretical prediction merely because it returns a number.
- Large replicate counts or highly stable polymorphisms may take a long time to simulate.
- The runner automates execution; it does not validate whether a biological model is appropriate for a particular organism or dataset.
- Any extension toward adaptive-gene scans would require the researcher's exact method, genotype format, sampling design, covariates, and validation plan.

## Why this is relevant to dry-lab support

This project demonstrates a practical service rather than claiming a new population-genetics method: turning research code into a reproducible workflow with validated inputs, batch execution, clear provenance, machine-readable outputs, tests, and CI.
