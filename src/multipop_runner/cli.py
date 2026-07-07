from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, expand_runs, load_config
from .report import create_plots, create_summary, create_synthetic_demo
from .runner import RunnerError, render_sources, run_upstream


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multipop-runner",
        description="Configuration-driven runner for the published multipopulation approximation code.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate YAML and print expanded runs.")
    validate.add_argument("config", type=Path)

    render = sub.add_parser("render", help="Render generated main.cpp files without compiling.")
    render.add_argument("config", type=Path)
    render.add_argument("--output-dir", type=Path, default=Path("generated_sources"))

    demo = sub.add_parser("demo", help="Generate clearly labeled synthetic portfolio outputs.")
    demo.add_argument("config", type=Path)
    demo.add_argument("--output-dir", type=Path, default=Path("results/demo"))

    run = sub.add_parser("run", help="Compile and execute a local copy of the upstream C++ repository.")
    run.add_argument("config", type=Path)
    run.add_argument("--upstream-repo", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, default=Path("results/real"))
    run.add_argument("--timeout", type=int, default=300)
    run.add_argument("--extra-flag", action="append", default=[])

    report = sub.add_parser("report", help="Regenerate plots and Markdown summary from results.csv.")
    report.add_argument("results_csv", type=Path)
    report.add_argument("--output-dir", type=Path, default=Path("results/report"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            create_plots(args.results_csv, args.output_dir)
            create_summary(args.results_csv, args.output_dir / "summary.md")
            print(f"Report written to {args.output_dir}")
            return 0

        config = load_config(args.config)
        runs = expand_runs(config)

        if args.command == "validate":
            print(json.dumps([run.to_dict() for run in runs], indent=2))
            print(f"Validated {len(runs)} run(s).")
        elif args.command == "render":
            paths = render_sources(runs, args.output_dir)
            print(f"Rendered {len(paths)} C++ main files to {args.output_dir}")
        elif args.command == "demo":
            path = create_synthetic_demo(runs, args.output_dir)
            print(f"Synthetic demo written to {path}")
        elif args.command == "run":
            path = run_upstream(
                runs,
                args.upstream_repo,
                args.output_dir,
                timeout=args.timeout,
                extra_flags=args.extra_flag,
            )
            create_plots(path, args.output_dir)
            create_summary(path, args.output_dir / "summary.md")
            print(f"Upstream results written to {path}")
        return 0
    except (ConfigError, RunnerError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
