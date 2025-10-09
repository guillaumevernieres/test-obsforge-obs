#!/usr/bin/env python
"""
PBS Driver Application

This application creates PBS job scripts for running obsForge validation
across multiple cycles using the PBS scheduler.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


def main():
    parser = argparse.ArgumentParser(
        description="Generate PBS job scripts for obsForge validation"
    )
    parser.add_argument(
        "--date-start",
        required=True,
        help="Start date (YYYYMMDD format)"
    )
    parser.add_argument(
        "--date-end",
        required=True,
        help="End date (YYYYMMDD format)"
    )
    parser.add_argument(
        "--cycle-type",
        choices=["gfs", "gdas"],
        required=True,
        help="Type of cycle to process"
    )
    parser.add_argument(
        "--outputdir",
        required=True,
        help="Output directory for results"
    )
    parser.add_argument(
        "--socascratch",
        default="/scratch/da/Guillaume.Vernieres/socascratch",
        help="Path to socascratch directory"
    )
    parser.add_argument(
        "--jedi-root",
        default="/scratch/da/Guillaume.Vernieres/sandboxes/"
                "global-workflow/sorc/gdas.cd",
        help="Path to JEDI root directory"
    )
    parser.add_argument(
        "--obsforge-db",
        default="/scratch/da/common_obsForge",
        help="Path to obsForge database"
    )
    parser.add_argument(
        "--account",
        default="da-cpu",
        help="PBS account/project"
    )
    parser.add_argument(
        "--queue",
        default="normal",
        help="PBS queue"
    )
    parser.add_argument(
        "--job-time",
        default="00:05:00",
        help="Job walltime (HH:MM:SS)"
    )
    parser.add_argument(
        "--ntasks",
        type=int,
        default=4,
        help="Number of tasks/cores"
    )

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date_start, '%Y%m%d')
        datetime.strptime(args.date_end, '%Y%m%d')
    except ValueError:
        print("Error: Dates must be in YYYYMMDD format")
        sys.exit(1)

    # Get the obsforge-validate home directory
    script_dir = Path(__file__).parent
    home_obsforge_validate = script_dir.parent

    # Set up Jinja2 environment
    template_dir = home_obsforge_validate / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))

    try:
        template = env.get_template("pbs_driver.sh.j2")
    except Exception as e:
        print(f"Error loading template: {e}")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_path = Path(args.outputdir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Render the PBS script
    script_content = template.render(
        date_start=args.date_start,
        date_end=args.date_end,
        cycle_type=args.cycle_type,
        outputdir=args.outputdir,
        socascratch=args.socascratch,
        jedi_root=args.jedi_root,
        obsforge_db=args.obsforge_db,
        home_obsforge_validate=str(home_obsforge_validate),
        account=args.account,
        queue=args.queue,
        job_time=args.job_time,
        ntasks=args.ntasks
    )

    # Write the PBS script
    script_filename = (f"pbs_obsforge_{args.cycle_type}_{args.date_start}_"
                       f"to_{args.date_end}.sh")
    script_path = output_path / script_filename

    with open(script_path, 'w') as f:
        f.write(script_content)

    # Make the script executable
    os.chmod(script_path, 0o755)

    print(f"PBS job script generated: {script_path}")

    # Submit the job using qsub
    try:
        result = subprocess.run(
            ["qsub", str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )

        job_id = result.stdout.strip()
        print(f"Job submitted successfully with ID: {job_id}")

        # Save job information
        info_file = (output_path /
                     f"job_info_{args.cycle_type}_{args.date_start}_"
                     f"to_{args.date_end}.txt")
        with open(info_file, 'w') as f:
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Script: {script_path}\n")
            f.write(f"Submitted: {datetime.now().isoformat()}\n")
            f.write(f"Cycle Type: {args.cycle_type}\n")
            f.write(f"Date Range: {args.date_start} to {args.date_end}\n")

        print(f"Job information saved to: {info_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error submitting job: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: qsub command not found. Make sure PBS is "
              "installed and configured.")
        sys.exit(1)


if __name__ == "__main__":
    main()
