#!/usr/bin/env python3
"""
Check SLURM job completion status by examining output files.

This script scans for 3DVAR job output files and checks for success/failure
indicators, generating a markdown summary report.
"""

import os
import sys
import argparse
import glob
from typing import Dict, List, Tuple
import re


def find_job_output_files(cycle_output_dir: str, pattern: str) -> List[str]:
    """
    Find all job output files matching the given pattern.

    Args:
        cycle_output_dir: Root directory to search
        pattern: Glob pattern for output files

    Returns:
        List of matching file paths
    """
    search_pattern = os.path.join(cycle_output_dir, pattern)
    return glob.glob(search_pattern)


def extract_cycle_info(filename: str) -> Tuple[str, str, str]:
    """
    Extract cycle type, date, and hour from output filename.

    Args:
        filename: Output file name like "3dvar_gdas.20240219.06.12345.out"

    Returns:
        Tuple of (cycle_type, date, hour)
    """
    basename = os.path.basename(filename)
    # Pattern: 3dvar_<cycle_type>.<date>.<hour>.<job_id>.out
    match = re.match(r"3dvar_(\w+)\.(\d{8})\.(\d{2})\.\d+\.out", basename)
    if match:
        return match.groups()
    # Fallback pattern without job ID
    match = re.match(r"3dvar_(\w+)\.(\d{8})\.(\d{2})\.out", basename)
    if match:
        return match.groups()
    return ("unknown", "unknown", "unknown")


def check_job_success(output_file: str) -> Tuple[bool, str]:
    """
    Check if a job completed successfully by examining its output file.

    Args:
        output_file: Path to the job output file

    Returns:
        Tuple of (success, details)
    """
    try:
        with open(output_file, 'r') as f:
            content = f.read()

        cycle_type, date, hour = extract_cycle_info(output_file)
        cycle_name = f"{cycle_type}.{date}.{hour}"

        # Look for success pattern
        success_pattern = f"3DVAR completed successfully for {cycle_name}"

        if success_pattern in content:
            return True, f"Found success message: {success_pattern}"
        else:
            # Look for common error indicators
            if "3DVAR failed for" in content:
                return False, "Found failure message in output"
            elif "Error:" in content:
                return False, "Found error messages in output"
            elif "SLURM: job" in content and "CANCELLED" in content:
                return False, "Job was cancelled by SLURM"
            else:
                return False, "Success message not found in output"

    except FileNotFoundError:
        return False, f"Output file not found: {output_file}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def generate_markdown_report(
    results: List[Dict],
    output_file: str,
    cycle_output_dir: str
) -> None:
    """
    Generate a markdown summary report of job completion status.

    Args:
        results: List of job check results
        output_file: Path to write the markdown report
        cycle_output_dir: Directory that was scanned
    """
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    with open(output_file, 'w') as f:
        f.write("# SLURM Job Completion Status Report\n\n")
        f.write(f"**Scan Directory:** `{cycle_output_dir}`\n\n")
        f.write(f"**Total Jobs Found:** {len(results)}\n")
        f.write(f"**Successful:** {len(successful)}\n")
        f.write(f"**Failed:** {len(failed)}\n\n")

        if successful:
            f.write("## ✅ Successful Jobs\n\n")
            for result in sorted(successful, key=lambda x: x['cycle']):
                f.write(f"- **{result['cycle']}**\n")
                f.write(f"  - Output: `{result['output_file']}`\n")
                f.write(f"  - Status: {result['details']}\n\n")

        if failed:
            f.write("## ❌ Failed Jobs\n\n")
            for result in sorted(failed, key=lambda x: x['cycle']):
                f.write(f"- **{result['cycle']}**\n")
                f.write(f"  - Output: `{result['output_file']}`\n")
                f.write(f"  - Status: {result['details']}\n\n")

        if not results:
            f.write("## No job output files found\n\n")
            f.write("Check that:\n")
            f.write("- The cycle output directory path is correct\n")
            f.write("- Jobs have completed and generated output files\n")
            f.write("- The file pattern matches your job output naming\n")


def main():
    """Main entry point for the job status checker."""
    parser = argparse.ArgumentParser(
        description="Check SLURM job completion status from output files"
    )
    parser.add_argument(
        "--cycle-output-dir",
        default="./cycle_output",
        help=(
            "Root directory containing job output files "
            "(default: ./cycle_output)"
        )
    )
    parser.add_argument(
        "--pattern",
        default="gdas.202402*/*/3dvar_gdas.20240*.*.*.out",
        help=(
            "Glob pattern for job output files "
            "(default: gdas.202402*/*/3dvar_gdas.20240*.*.*.out)"
        )
    )
    parser.add_argument(
        "--report-file",
        default="slurm_job_status_report.md",
        help=(
            "Output markdown report file "
            "(default: slurm_job_status_report.md)"
        )
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Find all job output files
    output_files = find_job_output_files(args.cycle_output_dir, args.pattern)

    if args.verbose:
        print(f"Found {len(output_files)} output files")
        for f in output_files:
            print(f"  {f}")

    # Check each job's completion status
    results = []
    for output_file in output_files:
        cycle_type, date, hour = extract_cycle_info(output_file)
        cycle_name = f"{cycle_type}.{date}.{hour}"

        success, details = check_job_success(output_file)

        result = {
            'cycle': cycle_name,
            'output_file': output_file,
            'success': success,
            'details': details
        }
        results.append(result)

        if args.verbose:
            status = "SUCCESS" if success else "FAILED"
            print(f"{cycle_name}: {status} - {details}")

    # Generate markdown report
    generate_markdown_report(results, args.report_file, args.cycle_output_dir)

    # Summary output
    successful_count = len([r for r in results if r['success']])
    failed_count = len([r for r in results if not r['success']])

    print("\nJob Status Summary:")
    print(f"  Total jobs checked: {len(results)}")
    print(f"  Successful: {successful_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Report written to: {args.report_file}")

    # Exit with non-zero status if any jobs failed
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
