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

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import yaml
import logging
import argparse
import re
from jinja2 import Environment, FileSystemLoader

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from marine_obs_config import MarineObsConfigGenerator


class ObsForgeScanner:
    """Scans obsForge directory structure to find available observations."""

    def __init__(self, obsforge_comroot: str,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the cycle processor.

        Args:
            obsforge_comroot: Path to obsForge root directory containing
                            gfs.YYYYMMDD and gdas.YYYYMMDD directories
            output_dir: Directory to write job cards and configs
            jcb_gdas_path: Path to JCB-GDAS repository
            template_dir: Path to custom templates
        """
        self.obsforge_comroot = Path(obsforge_comroot)
        self.obsforge_root = self.obsforge_comroot
        self.logger = logger or logging.getLogger(__name__)

        if not self.obsforge_root.exists():
            raise FileNotFoundError(
                f"ObsForge directory not found: {self.obsforge_root}"
            )

    def find_cycles(self) -> List[Tuple[str, str, str]]:
        """
        Find all available cycles in the obsForge directory.

        Returns:
            List of tuples (cycle_type, date, hour) where:
            - cycle_type: 'gfs' or 'gdas'
            - date: YYYYMMDD format
            - hour: HH format
        """
        cycles = []

        # Pattern to match cycle directories: gfs.YYYYMMDD or gdas.YYYYMMDD
        cycle_pattern = re.compile(r'^(gfs|gdas)\.(\d{8})$')

        for cycle_dir in self.obsforge_root.iterdir():
            if not cycle_dir.is_dir():
                continue

            match = cycle_pattern.match(cycle_dir.name)
            if not match:
                continue

            cycle_type, date = match.groups()

            # Look for hour subdirectories
            for hour_dir in cycle_dir.iterdir():
                if hour_dir.is_dir() and hour_dir.name.isdigit():
                    hour = hour_dir.name.zfill(2)  # Ensure 2-digit format
                    cycles.append((cycle_type, date, hour))

        return sorted(cycles)

    def scan_cycle_observations(self, cycle_type: str, date: str,
                                hour: str) -> Dict[str, List[str]]:
        """
        Scan a specific cycle for available observations.

        Args:
            cycle_type: 'gfs' or 'gdas'
            date: Date in YYYYMMDD format
            hour: Hour in HH format

        Returns:
            Dictionary mapping observation types to lists of available files
        """
        cycle_path = (self.obsforge_root / f"{cycle_type}.{date}" /
                      hour / "ocean")

        if not cycle_path.exists():
            self.logger.warning(f"Ocean directory not found: {cycle_path}")
            return {}

        observations = {}

        # Scan known observation type directories
        obs_types = ['adt', 'icec', 'sss', 'sst']

        for obs_type in obs_types:
            obs_dir = cycle_path / obs_type
            if obs_dir.exists():
                # Find all .nc files in this directory
                nc_files = list(obs_dir.glob("*.nc"))
                if nc_files:
                    file_names = [f.name for f in nc_files]
                    observations[obs_type] = file_names
                    msg = (f"Found {len(nc_files)} {obs_type} files for "
                           f"{cycle_type}.{date}.{hour}")
                    self.logger.info(msg)

        return observations

    def map_obsforge_to_jcb_types(self, obs_type: str,
                                  files: List[str]) -> List[str]:
        """
        Map obsForge observation types to JCB template names.

        Args:
            obs_type: ObsForge observation type ('adt', 'icec', 'sss', 'sst')
            files: List of available files for this observation type

        Returns:
            List of JCB template names that correspond to the available files
        """
        # Mapping from obsForge types to JCB template patterns
        type_mapping = {
            'adt': self._map_adt_files,
            'sst': self._map_sst_files,
            'sss': self._map_sss_files,
            'icec': self._map_icec_files
        }

        if obs_type in type_mapping:
            return type_mapping[obs_type](files)
        else:
            self.logger.warning(f"Unknown observation type: {obs_type}")
            return []

    def _map_adt_files(self, files: List[str]) -> List[str]:
        """Map ADT files to JCB template names."""
        jcb_types = []

        # Pattern matching for RADS altimeter data
        satellite_patterns = {
            '3a': 'rads_adt_3a',
            '3b': 'rads_adt_3b',
            'c2': 'rads_adt_c2',
            'j3': 'rads_adt_j3',
            'sa': 'rads_adt_sa'
        }

        for file in files:
            for sat_code, jcb_type in satellite_patterns.items():
                if f"_{sat_code}." in file or f"_{sat_code}_" in file:
                    if jcb_type not in jcb_types:
                        jcb_types.append(jcb_type)
                    break

        return jcb_types

    def _map_sst_files(self, files: List[str]) -> List[str]:
        """Map SST files to JCB template names."""
        jcb_types = []

        # Common SST sensor patterns
        sensor_patterns = {
            'viirs': 'sst_viirs_npp_l3u',
            'avhrr': 'sst_avhrr_metop_l3u',
            'amsre': 'sst_amsre_l3u',
            'modis': 'sst_modis_l3u'
        }

        for file in files:
            file_lower = file.lower()
            for sensor, jcb_type in sensor_patterns.items():
                if sensor in file_lower:
                    if jcb_type not in jcb_types:
                        jcb_types.append(jcb_type)
                    break
            else:
                # Generic SST if no specific sensor found
                if 'sst_generic' not in jcb_types:
                    jcb_types.append('sst_generic')

        return jcb_types

    def _map_sss_files(self, files: List[str]) -> List[str]:
        """Map SSS files to JCB template names."""
        jcb_types = []

        # Common SSS sensor patterns
        sensor_patterns = {
            'smap': 'sss_smap_l2',
            'smos': 'sss_smos_l3'
        }

        for file in files:
            file_lower = file.lower()
            for sensor, jcb_type in sensor_patterns.items():
                if sensor in file_lower:
                    if jcb_type not in jcb_types:
                        jcb_types.append(jcb_type)
                    break
            else:
                # Generic SSS if no specific sensor found
                if 'sss_generic' not in jcb_types:
                    jcb_types.append('sss_generic')

        return jcb_types

    def _map_icec_files(self, files: List[str]) -> List[str]:
        """Map sea ice concentration files to JCB template names."""
        # For now, use a generic ice concentration type
        return ['icec_generic'] if files else []


class ObsForgeCycleProcessor:
    """Main processor for generating job cards and configs from cycles."""

    def __init__(self, obsforge_comroot: str, output_dir: str,
                 jcb_gdas_path: str = "jcb-gdas",
                 template_dir: str = "templates"):
        """
        Initialize the cycle processor.

        Args:
            obsforge_comroot: Root directory path for obsForge data
            output_dir: Directory to write job cards and configs
            jcb_gdas_path: Path to JCB-GDAS repository
            template_dir: Path to custom templates
        """
        self.obsforge_comroot = obsforge_comroot
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment for job card templates
        self.template_dir = Path(template_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir))
        )

        self.logger = logging.getLogger(__name__)
        self.scanner = ObsForgeScanner(obsforge_comroot, self.logger)
        self.config_generator = MarineObsConfigGenerator(
            jcb_gdas_path, template_dir
        )

    def process_all_cycles(self) -> Dict[str, Any]:
        """
        Process all available cycles and generate job cards and configs.

        Returns:
            Summary dictionary of processed cycles
        """
        cycles = self.scanner.find_cycles()
        processed_cycles = []

        self.logger.info(f"Found {len(cycles)} cycles to process")

        for cycle_type, date, hour in cycles:
            try:
                result = self.process_cycle(cycle_type, date, hour)
                processed_cycles.append(result)
                self.logger.info(f"Successfully processed {cycle_type}.{date}.{hour}")
            except Exception as e:
                self.logger.error(f"Failed to process {cycle_type}.{date}.{hour}: {e}")
                continue

        summary = {
            'total_cycles': len(cycles),
            'processed_cycles': len(processed_cycles),
            'failed_cycles': len(cycles) - len(processed_cycles),
            'cycles': processed_cycles
        }

        return summary

    def process_cycle(self, cycle_type: str, date: str, hour: str) -> Dict[str, Any]:
        """
        Process a single cycle and generate job card and config.

        Args:
            cycle_type: 'gfs' or 'gdas'
            date: Date in YYYYMMDD format
            hour: Hour in HH format

        Returns:
            Dictionary with processing results
        """
        cycle_name = f"{cycle_type}.{date}.{hour}"
        self.logger.info(f"Processing cycle: {cycle_name}")

        # Scan for available observations
        obs_files = self.scanner.scan_cycle_observations(cycle_type, date, hour)

        if not obs_files:
            self.logger.warning(f"No observations found for {cycle_name}")
            return {
                'cycle': cycle_name,
                'observations': {},
                'jcb_types': [],
                'job_card': None,
                'config_file': None
            }

        # Map to JCB observation types
        jcb_obs_types = []
        for obs_type, files in obs_files.items():
            mapped_types = self.scanner.map_obsforge_to_jcb_types(obs_type, files)
            jcb_obs_types.extend(mapped_types)

        # Remove duplicates while preserving order
        jcb_obs_types = list(dict.fromkeys(jcb_obs_types))

        # Generate job card
        job_card_path = self._generate_job_card(cycle_type, date, hour, jcb_obs_types)

        # Generate 3DVAR configuration
        config_path = self._generate_3dvar_config(cycle_type, date, hour, jcb_obs_types)

        return {
            'cycle': cycle_name,
            'observations': obs_files,
            'jcb_types': jcb_obs_types,
            'job_card': str(job_card_path),
            'config_file': str(config_path)
        }

    def _generate_job_card(self, cycle_type: str, date: str, hour: str,
                          jcb_obs_types: List[str]) -> Path:
        """Generate a job card script for the cycle."""
        cycle_name = f"{cycle_type}.{date}.{hour}"

        # Create cycle-specific output directory
        cycle_output_dir = self.output_dir / f"{cycle_type}.{date}" / hour
        cycle_output_dir.mkdir(parents=True, exist_ok=True)

        job_card_path = cycle_output_dir / f"job_{cycle_name}.sh"

        # Determine observation categories for data linking
        obs_categories = set()
        for obs_type in jcb_obs_types:
            if 'adt' in obs_type or 'rads' in obs_type:
                obs_categories.add('adt')
            elif 'sst' in obs_type:
                obs_categories.add('sst')
            elif 'sss' in obs_type:
                obs_categories.add('sss')
            elif 'icec' in obs_type:
                obs_categories.add('icec')

        # Template context
        template_context = {
            'cycle_name': cycle_name,
            'cycle_type': cycle_type,
            'cycle_date': date,
            'cycle_hour': hour,
            'jcb_obs_types': jcb_obs_types,
            'obsforge_root': self.obsforge_comroot,
            'obs_categories': sorted(obs_categories)
        }

        # Load and render template
        template = self.jinja_env.get_template('job_card.sh.j2')
        job_card_content = template.render(**template_context)

        # Write job card
        with open(job_card_path, 'w') as f:
            f.write(job_card_content)

        # Make executable
        os.chmod(job_card_path, 0o755)

        return job_card_path

    def _generate_3dvar_config(self, cycle_type: str, date: str, hour: str,
                              jcb_obs_types: List[str]) -> Path:
        """Generate 3DVAR YAML configuration for the cycle."""
        cycle_name = f"{cycle_type}.{date}.{hour}"

        # Create cycle-specific output directory (should already exist from job card)
        cycle_output_dir = self.output_dir / f"{cycle_type}.{date}" / hour
        cycle_output_dir.mkdir(parents=True, exist_ok=True)

        config_path = cycle_output_dir / f"config_{cycle_name}.yaml"

        # Prepare datetime objects for configuration
        cycle_datetime = datetime.strptime(f"{date}{hour}", "%Y%m%d%H")
        window_begin = cycle_datetime - timedelta(hours=3)

        # Additional context for template rendering
        additional_context = {
            'window_begin': window_begin.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'window_length': 'PT6H',
            'cycle_type': cycle_type,
            'cycle_date': date,
            'cycle_hour': hour,
            'background_date': cycle_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'output_filename': f'analysis_{cycle_name}.nc',
            'output_dir': f'./output_{cycle_name}'
        }

        # Generate configuration using the existing generator
        self.config_generator.generate_config_from_jcb(
            obs_list=jcb_obs_types,
            additional_context=additional_context,
            output_file=str(config_path)
        )

        return config_path

    def execute_job_card(self, job_card_path: Path,
                        execution_mode: str = 'sbatch') -> Dict[str, Any]:
        """
        Execute a job card either via sbatch or directly in terminal.

        Args:
            job_card_path: Path to the job card script
            execution_mode: Either 'sbatch' for SLURM submission or 'bash' for direct execution

        Returns:
            Dictionary with execution results
        """
        if not job_card_path.exists():
            raise FileNotFoundError(f"Job card not found: {job_card_path}")

        cycle_name = job_card_path.stem.replace('job_', '')

        if execution_mode == 'sbatch':
            return self._submit_to_slurm(job_card_path, cycle_name)
        elif execution_mode == 'bash':
            return self._run_directly(job_card_path, cycle_name)
        else:
            raise ValueError(f"Invalid execution mode: {execution_mode}. Use 'sbatch' or 'bash'")

    def _submit_to_slurm(self, job_card_path: Path, cycle_name: str) -> Dict[str, Any]:
        """Submit job card to SLURM scheduler."""
        try:
            # Change to the job card directory for execution
            original_cwd = Path.cwd()
            job_dir = job_card_path.parent
            os.chdir(job_dir)

            # Submit job
            result = subprocess.run(
                ['sbatch', str(job_card_path.name)],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse job ID from sbatch output
            job_id = None
            if result.stdout:
                # Typical sbatch output: "Submitted batch job 12345"
                import re
                match = re.search(r'Submitted batch job (\d+)', result.stdout)
                if match:
                    job_id = int(match.group(1))

            self.logger.info(f"Submitted {cycle_name} to SLURM: {result.stdout.strip()}")

            return {
                'cycle': cycle_name,
                'execution_mode': 'sbatch',
                'status': 'submitted',
                'job_id': job_id,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to submit {cycle_name}: {e.stderr}")
            return {
                'cycle': cycle_name,
                'execution_mode': 'sbatch',
                'status': 'failed',
                'job_id': None,
                'stdout': e.stdout,
                'stderr': e.stderr,
                'error': str(e)
            }
        except FileNotFoundError:
            error_msg = "sbatch command not found. Is SLURM installed?"
            self.logger.error(error_msg)
            return {
                'cycle': cycle_name,
                'execution_mode': 'sbatch',
                'status': 'failed',
                'job_id': None,
                'error': error_msg
            }
        finally:
            os.chdir(original_cwd)

    def _run_directly(self, job_card_path: Path, cycle_name: str) -> Dict[str, Any]:
        """Run job card directly in bash."""
        try:
            # Change to the job card directory for execution
            original_cwd = Path.cwd()
            job_dir = job_card_path.parent
            os.chdir(job_dir)

            # Run job directly
            result = subprocess.run(
                ['bash', str(job_card_path.name)],
                capture_output=True,
                text=True
            )

            status = 'completed' if result.returncode == 0 else 'failed'
            log_level = logging.INFO if result.returncode == 0 else logging.ERROR

            self.logger.log(log_level,
                           f"Direct execution of {cycle_name} {status} with return code {result.returncode}")

            return {
                'cycle': cycle_name,
                'execution_mode': 'bash',
                'status': status,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except Exception as e:
            self.logger.error(f"Failed to execute {cycle_name}: {str(e)}")
            return {
                'cycle': cycle_name,
                'execution_mode': 'bash',
                'status': 'failed',
                'return_code': -1,
                'error': str(e)
            }
        finally:
            os.chdir(original_cwd)

    def process_and_execute_cycle(self, cycle_type: str, date: str, hour: str,
                                 execution_mode: str = 'sbatch') -> Dict[str, Any]:
        """
        Process a cycle and optionally execute the generated job card.

        Args:
            cycle_type: 'gfs' or 'gdas'
            date: Date in YYYYMMDD format
            hour: Hour in HH format
            execution_mode: Either 'sbatch' for SLURM submission or 'bash' for direct execution

        Returns:
            Dictionary with processing and execution results
        """
        # First process the cycle normally
        process_result = self.process_cycle(cycle_type, date, hour)

        # If processing was successful and job card was created, execute it
        if process_result['job_card'] is not None:
            job_card_path = Path(process_result['job_card'])
            execution_result = self.execute_job_card(job_card_path, execution_mode)

            # Combine results
            process_result['execution'] = execution_result
        else:
            process_result['execution'] = {
                'status': 'skipped',
                'reason': 'No job card generated (no observations found)'
            }

        return process_result

    def generate_cycle_status_report(self, summary: Dict[str, Any]) -> str:
        """
        Generate a detailed status report organized per cycle.

        Args:
            summary: Processing summary dictionary from process_all_cycles
                    or execution

        Returns:
            Formatted status report string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("OBSFORGE CYCLE STATUS REPORT")
        report_lines.append("=" * 80)

        # Overall summary
        report_lines.append("\nOVERALL SUMMARY:")
        total_cycles = summary.get('total_cycles', 0)
        processed_cycles = summary.get('processed_cycles', 0)
        failed_cycles = summary.get('failed_cycles', 0)

        report_lines.append(f"  Total cycles found: {total_cycles}")
        report_lines.append(f"  Successfully processed: {processed_cycles}")
        report_lines.append(f"  Failed to process: {failed_cycles}")

        # Execution summary if available
        if 'execution_results' in summary:
            execution_results = summary['execution_results']
            submitted = len([r for r in execution_results
                            if r.get('status') == 'submitted'])
            completed = len([r for r in execution_results
                            if r.get('status') == 'completed'])
            failed_exec = len([r for r in execution_results
                              if r.get('status') == 'failed'])
            skipped = len([r for r in execution_results
                          if r.get('status') == 'skipped'])

            report_lines.append("\nEXECUTION SUMMARY:")
            report_lines.append(f"  Jobs submitted to SLURM: {submitted}")
            report_lines.append(f"  Jobs completed directly: {completed}")
            report_lines.append(f"  Jobs failed to execute: {failed_exec}")
            report_lines.append(f"  Jobs skipped (no observations): {skipped}")

        # Detailed cycle information
        report_lines.append("\nDETAILED CYCLE STATUS:")
        report_lines.append("-" * 80)

        cycles = summary.get('cycles', [])
        if not cycles:
            report_lines.append("No cycles processed.")
            return "\n".join(report_lines)

        # Sort cycles by cycle name for consistent output
        sorted_cycles = sorted(cycles, key=lambda x: x.get('cycle', ''))

        for cycle_data in sorted_cycles:
            cycle_name = cycle_data.get('cycle', 'Unknown')
            observations = cycle_data.get('observations', {})
            jcb_types = cycle_data.get('jcb_types', [])
            job_card = cycle_data.get('job_card')
            execution = cycle_data.get('execution', {})

            # Determine cycle status for visual indicator
            cycle_status_icon = self._get_cycle_status_icon(
                cycle_data, execution)

            report_lines.append(f"\n{cycle_status_icon} Cycle: {cycle_name}")

            # Observation files found
            if observations:
                report_lines.append("  Observations Found:")
                for obs_type, files in observations.items():
                    obs_line = f"    {obs_type.upper()}: {len(files)} files"
                    report_lines.append(obs_line)
                    # Show ALL files, not just first 3
                    for file in files:
                        report_lines.append(f"      - {file}")
            else:
                report_lines.append("  Observations Found: None")

            # JCB observation types mapped
            if jcb_types:
                report_lines.append("  JCB Types for Assimilation:")
                for jcb_type in jcb_types:
                    report_lines.append(f"    - {jcb_type}")
            else:
                report_lines.append("  JCB Types for Assimilation: None")

            # Job card status
            if job_card:
                job_name = Path(job_card).name
                report_lines.append(f"  Job Card: Generated ({job_name})")
            else:
                report_lines.append("  Job Card: Not generated "
                                  "(no observations)")

            # Execution status
            if execution:
                status = execution.get('status', 'unknown')
                execution_mode = execution.get('execution_mode', 'unknown')

                if status == 'submitted':
                    job_id = execution.get('job_id')
                    exec_line = f"  Execution: SUBMITTED to SLURM " \
                              f"(Job ID: {job_id})"
                    report_lines.append(exec_line)
                elif status == 'completed':
                    return_code = execution.get('return_code', 'unknown')
                    exec_line = f"  Execution: COMPLETED (bash, " \
                              f"return code: {return_code})"
                    report_lines.append(exec_line)
                elif status == 'failed':
                    error = execution.get('error', 'Unknown error')
                    exec_line = f"  Execution: FAILED ({execution_mode}) " \
                              f"- {error}"
                    report_lines.append(exec_line)
                elif status == 'skipped':
                    reason = execution.get('reason', 'Unknown reason')
                    report_lines.append(f"  Execution: SKIPPED - {reason}")
                else:
                    report_lines.append(f"  Execution: {status.upper()}")
            else:
                report_lines.append("  Execution: Not executed")

            report_lines.append("")  # Blank line between cycles

        report_lines.append("=" * 80)
        return "\n".join(report_lines)

    def write_separated_status_reports(self, summary: Dict[str, Any], output_dir: Path) -> None:
        """
        Write separate markdown status reports for gfs and gdas cycles with visual separators and color-coded status icons.

        Args:
            summary: Processing summary dictionary
            output_dir: Directory to write markdown reports
        """
        cycles = summary.get('cycles', [])
        if not cycles:
            print(f"No cycles found. No markdown reports will be written to {output_dir}.")
            return

        # Split cycles by type
        gdas_cycles = [c for c in cycles if c.get('cycle', '').startswith('gdas.')]
        gfs_cycles = [c for c in cycles if c.get('cycle', '').startswith('gfs.')]

        def format_cycle_report(cycle_data):
            cycle_name = cycle_data.get('cycle', 'Unknown')
            observations = cycle_data.get('observations', {})
            jcb_types = cycle_data.get('jcb_types', [])
            job_card = cycle_data.get('job_card')
            execution = cycle_data.get('execution', {})
            cycle_status_icon = self._get_cycle_status_icon(cycle_data, execution)

            lines = []
            lines.append(f"---\n")
            lines.append(f"### {cycle_status_icon} {cycle_name}")
            if observations:
                lines.append("**Observations Found:**")
                for obs_type, files in observations.items():
                    lines.append(f"- {obs_type.upper()}: {len(files)} files")
                    for file in files:
                        lines.append(f"    - {file}")
            else:
                lines.append("**Observations Found:** None")
            if jcb_types:
                lines.append("**JCB Types for Assimilation:**")
                for jcb_type in jcb_types:
                    lines.append(f"- {jcb_type}")
            else:
                lines.append("**JCB Types for Assimilation:** None")
            if job_card:
                job_name = Path(job_card).name
                lines.append(f"**Job Card:** Generated ({job_name})")
            else:
                lines.append("**Job Card:** Not generated (no observations)")
            if execution:
                status = execution.get('status', 'unknown')
                execution_mode = execution.get('execution_mode', 'unknown')
                if status == 'submitted':
                    job_id = execution.get('job_id')
                    lines.append(f"**Execution:** SUBMITTED to SLURM (Job ID: {job_id})")
                elif status == 'completed':
                    return_code = execution.get('return_code', 'unknown')
                    lines.append(f"**Execution:** COMPLETED (bash, return code: {return_code})")
                elif status == 'failed':
                    error = execution.get('error', 'Unknown error')
                    lines.append(f"**Execution:** FAILED ({execution_mode}) - {error}")
                elif status == 'skipped':
                    reason = execution.get('reason', 'Unknown reason')
                    lines.append(f"**Execution:** SKIPPED - {reason}")
                else:
                    lines.append(f"**Execution:** {status.upper()}")
            else:
                lines.append("**Execution:** Not executed")
            lines.append("")
            return "\n".join(lines)

        def write_report(cycles, filename, title):
            report_path = output_dir / filename
            with open(report_path, 'w') as f:
                f.write(f"# {title}\n\n")
                if not cycles:
                    f.write("No cycles processed.\n")
                else:
                    for cycle_data in sorted(cycles, key=lambda x: x.get('cycle', '')):
                        f.write(format_cycle_report(cycle_data))
            self.logger.info(f"Status report written to {report_path}")
            print(f"Status report written to: {report_path.resolve()}")

        write_report(gdas_cycles, "gdas_status_report.md", "GDAS Cycle Status Report")
        write_report(gfs_cycles, "gfs_status_report.md", "GFS Cycle Status Report")

    def _get_cycle_status_icon(self, cycle_data: Dict[str, Any],
                               execution: Dict[str, Any]) -> str:
        """
        Get visual status icon for a cycle based on its processing and
        execution status.

        Args:
            cycle_data: Cycle processing data
            execution: Execution results data

        Returns:
            Colored Unicode icon string with ANSI color codes
        """
        # ANSI color codes
        GREEN = "\033[92m"   # Bright green
        RED = "\033[91m"     # Bright red
        YELLOW = "\033[93m"  # Bright yellow
        RESET = "\033[0m"    # Reset to default color

        # Check if cycle was processed successfully
        has_observations = bool(cycle_data.get('observations', {}))
        job_card_generated = cycle_data.get('job_card') is not None

        # If no observations, it's a skipped cycle
        if not has_observations:
            return f"❌"  # Yellow circle for empty/skipped

        # If observations exist but no job card, something went wrong
        if has_observations and not job_card_generated:
            return f"❌"  # Red cross for processing failure

        # Check execution status if available
        if execution:
            exec_status = execution.get('status', 'unknown')
            if exec_status == 'completed':
                return f"✅"  # Green check for success
            elif exec_status == 'submitted':
                return f"⏳"  # Yellow hourglass for pending
            elif exec_status == 'failed':
                return f"❌"  # Red cross for execution failure
            elif exec_status == 'skipped':
                return f"{YELLOW}○{RESET}"  # Yellow circle for skipped

        # If no execution info but job card was generated successfully
        if job_card_generated:
            return f"{GREEN}✓{RESET}"  # Green check for successful processing

        # Default to neutral
        return f"{YELLOW}○{RESET}"


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
        description="Process obsForge cycles and generate 3DVAR job cards and configs"
    )
    parser.add_argument(
        '--obsforge',
        required=True,
        help='Path to obsForge root directory with gfs/gdas cycle directories'
    )
    parser.add_argument(
        '--output-dir',
        default='./cycle_output',
        help='Output directory for job cards and configs (default: ./cycle_output)'
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
        help=('Execute generated job cards: sbatch for SLURM submission or '
              'bash for direct execution. If not specified, only generate '
              'job cards without executing them.')
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
            template_dir=args.template_dir
        )

        # Process cycles
        logger.info("Starting obsForge cycle processing")

        if args.execution_mode:
            # Process and execute cycles
            cycles = processor.scanner.find_cycles()
            processed_cycles = []
            execution_results = []

            logger.info(f"Found {len(cycles)} cycles to process and execute")

            for cycle_type, date, hour in cycles:
                try:
                    result = processor.process_and_execute_cycle(
                        cycle_type, date, hour, args.execution_mode
                    )
                    processed_cycles.append(result)

                    if 'execution' in result:
                        execution_results.append(result['execution'])

                    msg = (f"Successfully processed and executed "
                           f"{cycle_type}.{date}.{hour}")
                    logger.info(msg)
                except Exception as e:
                    msg = f"Failed to process {cycle_type}.{date}.{hour}: {e}"
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
                submitted = len([r for r in execution_results
                                if r.get('status') == 'submitted'])
                completed = len([r for r in execution_results
                                if r.get('status') == 'completed'])
                failed_exec = len([r for r in execution_results
                                  if r.get('status') == 'failed'])

                print("\nExecution Summary:")
                print(f"  Jobs submitted to SLURM: {submitted}")
                print(f"  Jobs completed directly: {completed}")
                print(f"  Jobs failed to execute: {failed_exec}")

                # Show job IDs for submitted jobs
                job_ids = [r.get('job_id') for r in execution_results
                           if r.get('job_id') is not None]
                if job_ids:
                    job_id_str = ', '.join(map(str, job_ids))
                    print(f"  SLURM Job IDs: {job_id_str}")

        # Save summary to file
        summary_path = Path(args.output_dir) / 'processing_summary.yaml'
        with open(summary_path, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False)

        logger.info(f"Processing complete. Summary saved to {summary_path}")

        # Generate and print detailed cycle status report
        detailed_report = processor.generate_cycle_status_report(summary)
        print(detailed_report)

        # Generate and write separate markdown status reports for gfs and gdas cycles
        processor.write_separated_status_reports(summary, Path(args.output_dir))

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
