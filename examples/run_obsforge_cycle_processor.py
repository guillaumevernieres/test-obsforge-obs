#!/usr/bin/env python3
"""
Example script for running the obsForge cycle processor.

This script demonstrates how to use the obsForge cycle processor to automatically
scan obsForge directories and generate job cards and 3DVAR configuration files.

Directory Structure Expected:
    obsforge_root/
    ├── gfs.20210831/
    │   └── 18/
    │       └── ocean/
    │           ├── adt/
    │           ├── sst/
    │           └── sss/
    ├── gdas.20210831/
    │   └── 18/
    │       └── ocean/
    │           ├── adt/
    │           ├── sst/
    │           └── sss/
    └── ...

Usage:
    python examples/run_obsforge_cycle_processor.py \\
        --obsforge /path/to/obsforge_root \\
        --output /path/to/output \\
        --jcb-gdas /path/to/jcb-gdas \\
        --template-dir templates/marine_obs
"""

import sys
import os
from pathlib import Path
import argparse
import logging

# Add apps directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps'))

from obsforge_cycle_processor import ObsForgeCycleProcessor


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
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Process obsForge cycles for marine 3DVAR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--obsforge',
        required=True,
        help='Path to obsForge root directory containing gfs.YYYYMMDD and gdas.YYYYMMDD directories'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for job cards and configuration files'
    )

    parser.add_argument(
        '--jcb-gdas',
        required=True,
        help='Path to JCB-GDAS repository'
    )

    parser.add_argument(
        '--template-dir',
        default='templates/marine_obs',
        help='Path to custom templates directory (default: templates/marine_obs)'
    )

    parser.add_argument(
        '--start-date',
        help='Start date for processing (YYYYMMDD format)'
    )

    parser.add_argument(
        '--end-date',
        help='End date for processing (YYYYMMDD format)'
    )

    parser.add_argument(
        '--cycles',
        nargs='*',
        help='Specific cycle types to process (gfs, gdas)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without creating files'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging(args.verbose)

    try:
        # Initialize processor
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=args.obsforge,
            output_dir=args.output,
            jcb_gdas_path=args.jcb_gdas,
            template_dir=args.template_dir,
            logger=logger
        )

        # Process cycles
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be created")
            summary = processor.scan_summary()
            logger.info(f"Found {summary['total_cycles']} cycles with {summary['total_observations']} observations")
            return

        # Process all cycles or specific date range
        if args.start_date or args.end_date:
            logger.info(f"Processing date range: {args.start_date} to {args.end_date}")
            # Note: Date range filtering would need to be implemented in the processor

        logger.info("Processing all available cycles...")
        summary = processor.process_all_cycles()

        logger.info("Processing complete!")
        logger.info(f"Processed {summary['successful_cycles']} cycles successfully")
        logger.info(f"Failed cycles: {summary['failed_cycles']}")
        logger.info(f"Total observations processed: {summary['total_observations']}")

        if summary['failed_cycles'] > 0:
            logger.warning("Some cycles failed to process. Check logs for details.")
            return 1

    except Exception as e:
        logger.error(f"Error processing obsForge cycles: {e}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
