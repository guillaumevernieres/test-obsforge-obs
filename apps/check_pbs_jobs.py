#!/usr/bin/env python
"""
PBS Job Status Checker

This script checks the completion status of PBS jobs by looking at their
output files and generates a simple markdown summary.
"""

import argparse
import sys
import re
from pathlib import Path
from datetime import datetime


def find_pbs_output_files(directory: str) -> list:
    """Find PBS output files (*.o<jobid> pattern) in the given directory."""
    output_files = []
    dir_path = Path(directory)

    if not dir_path.exists():
        return output_files

    # PBS output files typically have pattern: jobname.o<jobid>
    for file_path in dir_path.glob("*.o*"):
        if re.match(r".*\.o\d+$", file_path.name):
            output_files.append(file_path)

    return sorted(output_files)


def parse_pbs_output_file(file_path: Path) -> dict:
    """Parse a PBS output file to determine job status and cycle info."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        return {
            'file': file_path.name,
            'status': 'error',
            'error': f"Could not read file: {e}",
            'cycle': 'unknown'
        }

    # Extract cycle name from filename or content
    cycle_match = re.search(r'(gfs|gdas)\.(\d{8})\.(\d{2})', str(file_path))
    if cycle_match:
        cycle = (f"{cycle_match.group(1)}.{cycle_match.group(2)}."
                 f"{cycle_match.group(3)}")
    else:
        cycle = "unknown"

    # Determine job status based on content
    status = "unknown"
    error_info = None

    # Check for common completion indicators
    if "Job completed" in content or "COMPLETED" in content:
        status = "completed"
    elif "Job failed" in content or "FAILED" in content or "ERROR" in content:
        status = "failed"
        # Try to extract error information
        error_lines = []
        for line in content.split('\n'):
            keywords = ["ERROR", "FAILED", "EXCEPTION"]
            if any(keyword in line.upper() for keyword in keywords):
                error_lines.append(line.strip())
        if error_lines:
            error_info = "; ".join(error_lines[:3])  # First 3 error lines
    elif content.strip() == "":
        status = "running"  # Empty file usually means job is still running
    else:
        # Check for PBS job completion messages
        if "PBS Job" in content:
            if "Exit Status" in content:
                exit_match = re.search(r"Exit Status:\s*(\d+)", content)
                if exit_match:
                    exit_code = int(exit_match.group(1))
                    status = "completed" if exit_code == 0 else "failed"
                    if exit_code != 0:
                        error_info = f"Exit code: {exit_code}"
        else:
            # If file has content but no clear indicators, assume running
            status = "running" if len(content.strip()) < 100 else "completed"

    return {
        'file': file_path.name,
        'status': status,
        'cycle': cycle,
        'error': error_info,
        'size': file_path.stat().st_size if file_path.exists() else 0
    }


def generate_status_summary(job_results: list, output_file: str) -> None:
    """Generate a markdown summary of job statuses."""

    # Count statuses
    completed = len([j for j in job_results if j['status'] == 'completed'])
    failed = len([j for j in job_results if j['status'] == 'failed'])
    running = len([j for j in job_results if j['status'] == 'running'])
    error = len([j for j in job_results if j['status'] == 'error'])
    unknown = len([j for j in job_results if j['status'] == 'unknown'])

    with open(output_file, 'w') as f:
        f.write("# PBS Job Status Summary\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Total jobs: {len(job_results)}\n")
        f.write(f"- Completed: {completed}\n")
        f.write(f"- Failed: {failed}\n")
        f.write(f"- Running: {running}\n")
        f.write(f"- Error (file read issues): {error}\n")
        f.write(f"- Unknown status: {unknown}\n\n")

        if job_results:
            f.write("## Job Details\n\n")

            # Group by status
            statuses = ['completed', 'failed', 'running', 'error', 'unknown']
            for status in statuses:
                jobs_with_status = [j for j in job_results
                                    if j['status'] == status]
                if jobs_with_status:
                    f.write(f"### {status.title()} Jobs\n\n")

                    sorted_jobs = sorted(jobs_with_status,
                                         key=lambda x: x['cycle'])
                    for job in sorted_jobs:
                        status_icon = {
                            'completed': '✅',
                            'failed': '❌',
                            'running': '⏳',
                            'error': '🔥',
                            'unknown': '❓'
                        }.get(status, '❓')

                        cycle_name = job['cycle']
                        file_name = job['file']
                        f.write(f"- {status_icon} **{cycle_name}** "
                                f"({file_name})")

                        if job.get('error'):
                            f.write(f" - Error: {job['error']}")

                        f.write(f" - Size: {job['size']} bytes")
                        f.write("\n")

                    f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Check PBS job completion status from output files"
    )
    parser.add_argument(
        "--directory",
        default=".",
        help="Directory to search for PBS output files "
             "(default: current directory)"
    )
    parser.add_argument(
        "--output",
        default="pbs_job_status.md",
        help="Output markdown file (default: pbs_job_status.md)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Find PBS output files
    output_files = find_pbs_output_files(args.directory)

    if not output_files:
        print(f"No PBS output files found in {args.directory}")
        sys.exit(0)

    if args.verbose:
        print(f"Found {len(output_files)} PBS output files")

    # Parse each file
    job_results = []
    for output_file in output_files:
        if args.verbose:
            print(f"Parsing {output_file.name}...")

        result = parse_pbs_output_file(output_file)
        job_results.append(result)

    # Generate summary
    generate_status_summary(job_results, args.output)

    # Print simple summary to console
    completed = len([j for j in job_results if j['status'] == 'completed'])
    failed = len([j for j in job_results if j['status'] == 'failed'])
    running = len([j for j in job_results if j['status'] == 'running'])

    print(f"PBS Job Status: {completed} completed, {failed} failed, "
          f"{running} running")
    print(f"Detailed report written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
