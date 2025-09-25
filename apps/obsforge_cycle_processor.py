#!/usr/bin/env python3
"""
ObsForge Cycle Processor

This application scans an obsForge directory structure and generates job cards
and YAML configuration files for each cycle (GFS and GDAS). The JEDI 3DVAR
configuration will only contain observations that are actually available for
each specific cycle.

Directory structure expected:
obsforge_comroot/
├── gdas.YYYYMMDD
│   └── HH
│       └── ocean
│           ├── adt/
│           ├── icec/
│           ├── sss/
│           └── sst/
├── gfs.YYYYMMDD
│   └── HH
│       └── ocean
│           ├── adt/
│           ├── icec/
│           ├── sss/
│           └── sst/
"""

import sys
from pathlib import Path
import yaml
import logging
import argparse

# Add project root to path so we can import the 'src' package
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.obsforge_cycle_processor import ObsForgeCycleProcessor  # noqa: E402


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def main():
    """Main entry point for the obsForge cycle processor."""
    parser = argparse.ArgumentParser(
        description=(
            "Process obsForge cycles and generate 3DVAR job cards and configs"
        )
    )
    parser.add_argument(
        '--obsforge',
        required=True,
        help=(
            'Path to obsForge root directory with gfs/gdas cycle directories'
        )
    )
    parser.add_argument(
        '--output-dir',
        default='./cycle_output',
        help=(
            'Output directory for job cards and configs '
            '(default: ./cycle_output)'
        )
    )
    parser.add_argument(
        '--jcb-gdas-path',
        default='../jcb-gdas',
        help='Path to JCB-GDAS repository (default: ../jcb-gdas)'
    )
    parser.add_argument(
        '--template-dir',
        default='../templates',
        help='Path to custom templates (default: ../templates)'
    )
    parser.add_argument(
        '--jedi-root',
        dest='jedi_root',
        help='Path to JEDI installation root (overrides template default)'
    )
    parser.add_argument(
        '--socascratch',
        help='Path to SOCA scratch directory to seed the run directory'
    )
    parser.add_argument(
        '--cycle-type',
        choices=['gfs', 'gdas', 'both'],
        default='both',
        help='Process only specific cycle type (default: both)'
    )
    parser.add_argument(
        '--date-range',
        nargs=2,
        metavar=('START', 'END'),
        help='Process cycles in date range YYYYMMDD YYYYMMDD'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--execution-mode',
        choices=['sbatch', 'bash'],
        help=(
            'Execute generated job cards: sbatch for SLURM submission or '
            'bash for direct execution. If not specified, only generate '
            'job cards without executing them.'
        )
    )
    parser.add_argument(
        '--status-report',
        action='store_true',
        help='Generate detailed status report organized per cycle'
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging(args.verbose)

    try:
        # Initialize processor
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=args.obsforge,
            output_dir=args.output_dir,
            jcb_gdas_path=args.jcb_gdas_path,
            template_dir=args.template_dir,
            jedi_root=args.jedi_root,
            socascratch=args.socascratch,
        )

        # Process cycles
        logger.info("Starting obsForge cycle processing")

        if args.execution_mode:
            # Process and execute cycles
            if args.cycle_type == 'both':
                cycle_types = ['gfs', 'gdas']
            else:
                cycle_types = [args.cycle_type]
            date_range = args.date_range if args.date_range else None
            cycles = processor.scanner.find_cycles(
                cycle_types=cycle_types,
                start_date=date_range[0],
                end_date=date_range[1]
            )
            processed_cycles = []
            execution_results = []

            logger.info(
                f"Found {len(cycles)} cycles to process and execute"
            )

            for cycle_type, date, hour in cycles:
                try:
                    result = processor.process_and_execute_cycle(
                        cycle_type, date, hour, args.execution_mode
                    )
                    processed_cycles.append(result)

                    if 'execution' in result:
                        execution_results.append(result['execution'])

                    msg = (
                        f"Successfully processed and executed "
                        f"{cycle_type}.{date}.{hour}"
                    )
                    logger.info(msg)
                except Exception as e:
                    msg = (
                        f"Failed to process {cycle_type}.{date}.{hour}: {e}"
                    )
                    logger.error(msg)
                    continue

            summary = {
                'total_cycles': len(cycles),
                'processed_cycles': len(processed_cycles),
                'failed_cycles': len(cycles) - len(processed_cycles),
                'cycles': processed_cycles,
                'execution_results': execution_results
            }
        else:
            # Process only (no execution)
            summary = processor.process_all_cycles()

        # Print summary
        if args.status_report:
            # Generate and display detailed status report
            status_report = processor.generate_cycle_status_report(summary)
            print(status_report)
        else:
            # Display basic summary
            print("\nProcessing Summary:")
            print(f"  Total cycles found: {summary['total_cycles']}")
            print(f"  Successfully processed: {summary['processed_cycles']}")
            print(f"  Failed: {summary['failed_cycles']}")

            if args.execution_mode and 'execution_results' in summary:
                execution_results = summary['execution_results']
                submitted = len([
                    r for r in execution_results
                    if r.get('status') == 'submitted'
                ])
                completed = len([
                    r for r in execution_results
                    if r.get('status') == 'completed'
                ])
                failed_exec = len([
                    r for r in execution_results
                    if r.get('status') == 'failed'
                ])

                print("\nExecution Summary:")
                print(f"  Jobs submitted to SLURM: {submitted}")
                print(f"  Jobs completed directly: {completed}")
                print(f"  Jobs failed to execute: {failed_exec}")

                # Show job IDs for submitted jobs
                job_ids = [
                    r.get('job_id') for r in execution_results
                    if r.get('job_id') is not None
                ]
                if job_ids:
                    job_id_str = ', '.join(map(str, job_ids))
                    print(f"  SLURM Job IDs: {job_id_str}")

        # Save summary to file
        summary_path = Path(args.output_dir) / 'processing_summary.yaml'
        with open(summary_path, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False)

        logger.info(
            f"Processing complete. Summary saved to {summary_path}"
        )

        # Generate and print detailed cycle status report
        detailed_report = processor.generate_cycle_status_report(summary)
        print(detailed_report)

        # Generate and write separate markdown status reports
        # for gfs and gdas cycles
        processor.write_separated_status_reports(
            summary, Path(args.output_dir)
        )

        # Write failed cycles summary markdown
        processor.write_failed_cycles_summary(
            summary, Path(args.output_dir)
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
