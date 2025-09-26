#!/usr/bin/env python3
"""
Render the sbatch driver script from
templates/sbatch_driver.sh.j2.

This generates an sbatch script that runs the obsForge cycle processor over
 a date range.
"""

import os
import argparse
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader


def render_sbatch_driver(context: Dict[str, Any], template_dir: Path) -> str:
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("sbatch_driver.sh.j2")
    return template.render(**context)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an sbatch driver script for obsForge validation"
        )
    )
    parser.add_argument(
        "--cycle-type",
        choices=["gfs", "gdas"],
        required=True,
        help="Cycle type to process",
    )
    parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        required=True,
        help="Date range YYYYMMDD YYYYMMDD",
    )
    parser.add_argument(
        "--obsforge-db",
        required=True,
        help=(
            "Path to obsForge database root (contains "
            "gfs.YYYYMMDD/gdas.YYYYMMDD)"
        ),
    )
    parser.add_argument(
        "--socascratch",
        help=(
            "Path to SOCA scratch directory (optional; overrides template "
            "default)"
        ),
    )
    parser.add_argument(
        "--jedi-root",
        help=(
            "Path to JEDI installation root (optional; overrides template "
            "default)"
        ),
    )
    parser.add_argument(
        "--ntasks",
        type=int,
        default=4,
        help="Number of tasks for sbatch (default: 4)",
    )
    parser.add_argument(
        "--job-time",
        default="00:05:00",
        help="Sbatch time limit (default: 00:05:00)",
    )
    parser.add_argument(
        "--account",
        help="Sbatch account (optional; template may have a default)",
    )
    parser.add_argument(
        "--outputdir-name",
        help=(
            "Value for the 'outputdir' variable inside the job (default: "
            "<cycle>_obs_validation_<start>-<end>)"
        ),
    )
    parser.add_argument(
        "--job-script-path",
        help=(
            "Where to write the rendered sbatch script (default: "
            "./sbatch_<cycle>_obs_validation_<start>_<end>.sh)"
        ),
    )
    parser.add_argument(
        "--hpc-modules",
        dest="hpc_modules",
        help=(
            "Modules suffix to load (template variable hpc_modules), e.g. "
            "'intel/2023.1' or 'gnu/11.2'"
        ),
    )
    parser.add_argument(
        "--templates",
        default=str(Path(__file__).parent.parent / "templates"),
        help="Path to templates directory (default: ../templates)",
    )

    args = parser.parse_args()

    date_start, date_end = args.date_range
    cycle_type = args.cycle_type

    # Determine repository root to pass as home_obsforge_validate
    repo_root = Path(__file__).parent.parent.resolve()

    # Compute defaults
    default_outputdir = f"{cycle_type}_obs_validation_{date_start}-{date_end}"
    outputdir_name = args.outputdir_name or default_outputdir

    default_job_name = (
        f"sbatch_{cycle_type}_obs_validation_{date_start}_{date_end}.sh"
    )
    job_script_path = Path(args.job_script_path or default_job_name).resolve()

    # Build context for the Jinja template
    context = {
        "cycle_type": cycle_type,
        "date_start": date_start,
        "date_end": date_end,
        "home_obsforge_validate": str(repo_root),
        "obsforge_db": args.obsforge_db,
        "outputdir": outputdir_name,
        "ntasks": args.ntasks,
        "job_time": args.job_time,
    }
    if args.socascratch:
        context["socascratch"] = args.socascratch
    if args.jedi_root:
        context["jedi_root"] = args.jedi_root
    if args.account:
        context["account"] = args.account
    if args.hpc_modules:
        context["hpc_modules"] = args.hpc_modules

    # Render
    template_dir = Path(args.templates).resolve()
    rendered = render_sbatch_driver(context, template_dir)

    # Write and chmod +x
    job_script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(job_script_path, "w") as f:
        f.write(rendered)
    os.chmod(job_script_path, 0o755)

    print(f"Wrote sbatch driver to: {job_script_path}")


if __name__ == "__main__":
    main()
