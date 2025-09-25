from __future__ import annotations

import os
import glob
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

from .obsforge_scanner import ObsForgeScanner


class ObsForgeCycleProcessor:
    """Main processor for generating job cards and configs from cycles."""

    def __init__(
        self,
        obsforge_comroot: str,
        output_dir: str,
        jcb_gdas_path: str = "jcb-gdas",
        template_dir: str = "templates",
    ):
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

        # Store JCB-GDAS path for 3DVAR rendering includes
        self.jcb_gdas_path = Path(jcb_gdas_path)

        self.logger = logging.getLogger(__name__)
        self.scanner = ObsForgeScanner(obsforge_comroot, self.logger)

    def process_all_cycles(self) -> Dict[str, Any]:
        """
        Process all available cycles and generate job cards and configs.

        Returns:
            Summary dictionary of processed cycles
        """
        cycles = self.scanner.find_cycles(
            cycle_types=["gfs"]
        )  # keep same behavior
        processed_cycles: List[Dict[str, Any]] = []

        self.logger.info(f"Found {len(cycles)} cycles to process")

        for cycle_type, date, hour in cycles:
            try:
                result = self.process_cycle(cycle_type, date, hour)
                processed_cycles.append(result)
                self.logger.info(
                    "Successfully processed %s.%s.%s",
                    cycle_type,
                    date,
                    hour,
                )
            except Exception as e:
                self.logger.error(
                    "Failed to process %s.%s.%s: %s",
                    cycle_type,
                    date,
                    hour,
                    e,
                )
                continue

        summary: Dict[str, Any] = {
            "total_cycles": len(cycles),
            "processed_cycles": len(processed_cycles),
            "failed_cycles": len(cycles) - len(processed_cycles),
            "cycles": processed_cycles,
        }

        return summary

    def process_cycle(
        self, cycle_type: str, date: str, hour: str
    ) -> Dict[str, Any]:
        """
        Process a single cycle and generate job card and config.
        """
        cycle_name = f"{cycle_type}.{date}.{hour}"
        self.logger.info(f"Processing cycle: {cycle_name}")

        # Scan for available observations
        obs_files = self.scanner.scan_cycle_observations(
            cycle_type, date, hour
        )

        if not obs_files:
            self.logger.warning(f"No observations found for {cycle_name}")
            return {
                "cycle": cycle_name,
                "observations": {},
                "jcb_types": [],
                "job_card": None,
                "config_file": None,
            }

        # Map to JCB observation types
        obs_dir = os.path.join(
            self.obsforge_comroot,
            f"{cycle_type}.{date}",
            f"{hour}",
            "ocean",
        )
        obs_file_list = glob.glob(
            os.path.join(obs_dir, "*", f"{cycle_type}.t{hour}z.*.nc")
        )

        jcb_obs_types: List[str] = []
        for obs_file in obs_file_list:
            mapped_type = f"{obs_file.split('.')[3]}"
            jcb_obs_types.append(mapped_type)

        # Generate job card
        job_card_path = self._generate_job_card(
            cycle_type, date, hour, jcb_obs_types
        )

        # Generate 3DVAR configuration
        config_path = self._generate_3dvar_config(
            cycle_type, date, hour, jcb_obs_types
        )

        return {
            "cycle": cycle_name,
            "observations": obs_files,
            "jcb_types": jcb_obs_types,
            "job_card": str(job_card_path),
            "config_file": str(config_path),
        }

    def _generate_job_card(
        self,
        cycle_type: str,
        date: str,
        hour: str,
        jcb_obs_types: List[str],
    ) -> Path:
        """Generate a job card script for the cycle."""
        cycle_name = f"{cycle_type}.{date}.{hour}"

        # Create cycle-specific output directory
        cycle_output_dir = self.output_dir / f"{cycle_type}.{date}" / hour
        cycle_output_dir.mkdir(parents=True, exist_ok=True)

        job_card_path = cycle_output_dir / f"job_{cycle_name}.sh"

        # Determine observation categories for data linking
        obs_categories = {"adt", "sst", "sss", "icec", "insitu"}

        # Template context
        template_context = {
            "cycle_name": cycle_name,
            "cycle_type": cycle_type,
            "cycle_date": date,
            "cycle_hour": hour,
            "jcb_obs_types": jcb_obs_types,
            "obsforge_root": self.obsforge_comroot,
            "obs_categories": sorted(obs_categories),
        }

        # Load and render template
        template = self.jinja_env.get_template("job_card.sh.j2")
        job_card_content = template.render(**template_context)

        # Write job card
        with open(job_card_path, "w") as f:
            f.write(job_card_content)

        # Make executable
        os.chmod(job_card_path, 0o755)

        return job_card_path

    def _generate_3dvar_config(
        self,
        cycle_type: str,
        date: str,
        hour: str,
        jcb_obs_types: List[str],
    ) -> Path:
        """Generate 3DVAR YAML configuration for the cycle."""
        cycle_name = f"{cycle_type}.{date}.{hour}"

        # Create cycle-specific output directory
        # (should already exist from job card)
        cycle_output_dir = self.output_dir / f"{cycle_type}.{date}" / hour
        cycle_output_dir.mkdir(parents=True, exist_ok=True)

        config_path = cycle_output_dir / f"config_{cycle_name}.yaml"

        # Prepare datetime objects for configuration
        cycle_datetime = datetime.strptime(f"{date}{hour}", "%Y%m%d%H")
        window_begin = cycle_datetime - timedelta(hours=3)
        window_middle = cycle_datetime
        window_end = cycle_datetime + timedelta(hours=3)

        # Additional context for template rendering
        additional_context = {
            "window_begin": window_begin.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_middle": window_middle.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_end": window_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_length": "PT6H",
            "cycle_type": cycle_type,
            "cycle_date": date,
            "cycle_hour": hour,
            "output_filename": f"analysis_{cycle_name}.nc",
            "output_dir": f"./output_{cycle_name}",
        }

        # Build list of templates from available observation files
        obs_dir = os.path.join(
            self.obsforge_comroot,
            f"{cycle_type}.{window_middle.strftime('%Y%m%d')}",
            f"{hour}",
            "ocean",
        )
        obs_file_list = glob.glob(
            os.path.join(obs_dir, "*", f"{cycle_type}.t{hour}z.*.nc")
        )

        available_templates: List[str] = []
        for obs_file in obs_file_list:
            available_templates.append(
                f"{obs_file.split('.')[3]}.yaml.j2"
            )

        jcb_templates_dir = (
            Path(self.jcb_gdas_path) / "observations" / "marine"
        )

        env = Environment(
            loader=ChoiceLoader(
                [
                    FileSystemLoader(str(self.template_dir)),
                    FileSystemLoader(str(jcb_templates_dir)),
                ]
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Pre-render each observer template to a YAML block string
        rendered_observer_blocks: List[str] = []
        for name in available_templates:
            observer_name = name.replace(".yaml.j2", "")
            marine_obsdatain_path = "."
            marine_obsdatain_prefix = f"{cycle_type}.t{hour}z."
            render_context = {
                **additional_context,
                "observation_from_jcb": observer_name,
                "marine_obsdatain_prefix": marine_obsdatain_prefix,
                "marine_obsdatain_path": marine_obsdatain_path,
                "marine_obsdatain_suffix": ".nc",
                "marine_obsdataout_path": ".",
                "marine_obsdataout_suffix": ".out.nc",
            }

            try:
                obs_tmpl = env.get_template(name)
                block = obs_tmpl.render(**render_context)
                if block and block.strip():
                    rendered_observer_blocks.append(block)
                else:
                    self.logger.warning(
                        "Rendered observer template is empty, skipping: %s",
                        name,
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to render observer template %s: %s",
                    name,
                    e,
                )

        # Render main 3DVAR template with the list of pre-rendered blocks
        template = env.get_template("jedi_3dvar_template.yaml.j2")
        rendered = template.render(
            **render_context,
            rendered_observer_blocks=rendered_observer_blocks,
        )

        # Write configuration file
        with open(config_path, "w") as f:
            f.write(rendered)

        return config_path

    def execute_job_card(
        self, job_card_path: Path, execution_mode: str = "sbatch"
    ) -> Dict[str, Any]:
        """
        Execute a job card either via sbatch or directly in terminal.
        """
        if not job_card_path.exists():
            raise FileNotFoundError(f"Job card not found: {job_card_path}")

        cycle_name = job_card_path.stem.replace("job_", "")

        if execution_mode == "sbatch":
            return self._submit_to_slurm(job_card_path, cycle_name)
        elif execution_mode == "bash":
            return self._run_directly(job_card_path, cycle_name)
        else:
            raise ValueError(
                (
                    f"Invalid execution mode: {execution_mode}. "
                    "Use 'sbatch' or 'bash'"
                )
            )

    def _submit_to_slurm(
        self, job_card_path: Path, cycle_name: str
    ) -> Dict[str, Any]:
        """Submit job card to SLURM scheduler."""
        try:
            # Change to the job card directory for execution
            original_cwd = Path.cwd()
            job_dir = job_card_path.parent
            os.chdir(job_dir)

            # Submit job
            result = subprocess.run(
                ["sbatch", str(job_card_path.name)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse job ID from sbatch output
            job_id: Optional[int] = None
            if result.stdout:
                import re

                match = re.search(
                    r"Submitted batch job (\d+)",
                    result.stdout,
                )
                if match:
                    job_id = int(match.group(1))

            self.logger.info(
                "Submitted %s to SLURM: %s",
                cycle_name,
                result.stdout.strip(),
            )

            return {
                "cycle": cycle_name,
                "execution_mode": "sbatch",
                "status": "submitted",
                "job_id": job_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to submit {cycle_name}: {e.stderr}"
            )
            return {
                "cycle": cycle_name,
                "execution_mode": "sbatch",
                "status": "failed",
                "job_id": None,
                "stdout": e.stdout,
                "stderr": e.stderr,
                "error": str(e),
            }
        except FileNotFoundError:
            error_msg = (
                "sbatch command not found. Is SLURM installed?"
            )
            self.logger.error(error_msg)
            return {
                "cycle": cycle_name,
                "execution_mode": "sbatch",
                "status": "failed",
                "job_id": None,
                "error": error_msg,
            }
        finally:
            os.chdir(original_cwd)

    def _run_directly(
        self, job_card_path: Path, cycle_name: str
    ) -> Dict[str, Any]:
        """Run job card directly in bash."""
        try:
            # Change to the job card directory for execution
            original_cwd = Path.cwd()
            job_dir = job_card_path.parent
            os.chdir(job_dir)

            # Run job directly
            result = subprocess.run(
                ["bash", str(job_card_path.name)],
                capture_output=True,
                text=True,
            )

            status = (
                "completed" if result.returncode == 0 else "failed"
            )
            log_level = (
                logging.INFO if result.returncode == 0 else logging.ERROR
            )

            self.logger.log(
                log_level,
                (
                    f"Direct execution of {cycle_name} {status} with "
                    f"return code {result.returncode}"
                ),
            )

            return {
                "cycle": cycle_name,
                "execution_mode": "bash",
                "status": status,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            self.logger.error(
                f"Failed to execute {cycle_name}: {str(e)}"
            )
            return {
                "cycle": cycle_name,
                "execution_mode": "bash",
                "status": "failed",
                "return_code": -1,
                "error": str(e),
            }
        finally:
            os.chdir(original_cwd)

    def process_and_execute_cycle(
        self,
        cycle_type: str,
        date: str,
        hour: str,
        execution_mode: str = "sbatch",
    ) -> Dict[str, Any]:
        """
        Process a cycle and optionally execute the generated job card.
        """
        # First process the cycle normally
        process_result = self.process_cycle(cycle_type, date, hour)

        # If processing was successful and job card was created, execute it
        if process_result["job_card"] is not None:
            job_card_path = Path(process_result["job_card"])
            execution_result = self.execute_job_card(
                job_card_path, execution_mode
            )

            # Combine results
            process_result["execution"] = execution_result
        else:
            process_result["execution"] = {
                "status": "skipped",
                "reason": "No job card generated (no observations found)",
            }

        return process_result

    def generate_cycle_status_report(
        self, summary: Dict[str, Any]
    ) -> str:
        """
        Generate a detailed status report organized per cycle.
        """
        report_lines: List[str] = []
        report_lines.append("=" * 80)
        report_lines.append("OBSFORGE CYCLE STATUS REPORT")
        report_lines.append("=" * 80)

        # Overall summary
        report_lines.append("\nOVERALL SUMMARY:")
        total_cycles = summary.get("total_cycles", 0)
        processed_cycles = summary.get("processed_cycles", 0)
        failed_cycles = summary.get("failed_cycles", 0)

        report_lines.append(f"  Total cycles found: {total_cycles}")
        report_lines.append(
            f"  Successfully processed: {processed_cycles}"
        )
        report_lines.append(f"  Failed to process: {failed_cycles}")

        # Execution summary if available
        if "execution_results" in summary:
            execution_results = summary["execution_results"]
            submitted = len(
                [
                    r
                    for r in execution_results
                    if r.get("status") == "submitted"
                ]
            )
            completed = len(
                [
                    r
                    for r in execution_results
                    if r.get("status") == "completed"
                ]
            )
            failed_exec = len(
                [
                    r
                    for r in execution_results
                    if r.get("status") == "failed"
                ]
            )
            skipped = len(
                [
                    r
                    for r in execution_results
                    if r.get("status") == "skipped"
                ]
            )

            report_lines.append("\nEXECUTION SUMMARY:")
            report_lines.append(f"  Jobs submitted to SLURM: {submitted}")
            report_lines.append(f"  Jobs completed directly: {completed}")
            report_lines.append(f"  Jobs failed to execute: {failed_exec}")
            report_lines.append(f"  Jobs skipped (no observations): {skipped}")

        # Detailed cycle information
        report_lines.append("\nDETAILED CYCLE STATUS:")
        report_lines.append("-" * 80)

        cycles = summary.get("cycles", [])
        if not cycles:
            report_lines.append("No cycles processed.")
            return "\n".join(report_lines)

        # Sort cycles by cycle name for consistent output
        sorted_cycles = sorted(cycles, key=lambda x: x.get("cycle", ""))

        for cycle_data in sorted_cycles:
            cycle_name = cycle_data.get("cycle", "Unknown")
            observations = cycle_data.get("observations", {})
            jcb_types = cycle_data.get("jcb_types", [])
            job_card = cycle_data.get("job_card")
            execution = cycle_data.get("execution", {})

            # Determine cycle status for visual indicator
            cycle_status_icon = self._get_cycle_status_icon(
                cycle_data, execution
            )

            report_lines.append(f"\n{cycle_status_icon} Cycle: {cycle_name}")

            # Observation files found
            if observations:
                report_lines.append("  Observations Found:")
                for obs_type, files in observations.items():
                    obs_line = (
                        f"    {obs_type.upper()}: {len(files)} files"
                    )
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
                report_lines.append(
                    "  JCB Types for Assimilation: None"
                )

            # Job card status
            if job_card:
                job_name = Path(job_card).name
                report_lines.append(
                    f"  Job Card: Generated ({job_name})"
                )
            else:
                report_lines.append(
                    "  Job Card: Not generated (no observations)"
                )

            # Execution status
            if execution:
                status = execution.get("status", "unknown")
                execution_mode = execution.get(
                    "execution_mode", "unknown"
                )

                if status == "submitted":
                    job_id = execution.get("job_id")
                    exec_line = (
                        f"  Execution: SUBMITTED to SLURM (Job ID: {job_id})"
                    )
                    report_lines.append(exec_line)
                elif status == "completed":
                    return_code = execution.get(
                        "return_code", "unknown"
                    )
                    exec_line = (
                        "  Execution: COMPLETED (bash, return code: "
                        f"{return_code})"
                    )
                    report_lines.append(exec_line)
                elif status == "failed":
                    error = execution.get(
                        "error", "Unknown error"
                    )
                    exec_line = (
                        f"  Execution: FAILED ({execution_mode}) - {error}"
                    )
                    report_lines.append(exec_line)
                elif status == "skipped":
                    reason = execution.get(
                        "reason", "Unknown reason"
                    )
                    report_lines.append(
                        f"  Execution: SKIPPED - {reason}"
                    )
                else:
                    report_lines.append(
                        f"  Execution: {status.upper()}"
                    )
            else:
                report_lines.append("  Execution: Not executed")

            report_lines.append("")  # Blank line between cycles

        report_lines.append("=" * 80)
        return "\n".join(report_lines)

    def write_separated_status_reports(
        self, summary: Dict[str, Any], output_dir: Path
    ) -> None:
        """
        Write separate markdown status reports for gfs and gdas cycles with
        visual separators and color-coded status icons.
        """
        cycles = summary.get("cycles", [])
        if not cycles:
            print(
                "No cycles found. No markdown reports will be written to "
                f"{output_dir}."
            )
            return

        # Split cycles by type
        gdas_cycles = [
            c for c in cycles if c.get("cycle", "").startswith("gdas.")
        ]
        gfs_cycles = [
            c for c in cycles if c.get("cycle", "").startswith("gfs.")
        ]

        def format_cycle_report(cycle_data: Dict[str, Any]) -> str:
            cycle_name = cycle_data.get("cycle", "Unknown")
            observations = cycle_data.get("observations", {})
            jcb_types = cycle_data.get("jcb_types", [])
            job_card = cycle_data.get("job_card")
            execution = cycle_data.get("execution", {})
            cycle_status_icon = self._get_cycle_status_icon(
                cycle_data, execution
            )

            lines: List[str] = []
            lines.append("---\n")
            lines.append(f"### {cycle_status_icon} {cycle_name}")
            if observations:
                lines.append("**Observations Found:**")
                for obs_type, files in observations.items():
                    lines.append(
                        f"- {obs_type.upper()}: {len(files)} files"
                    )
                    for file in files:
                        lines.append(f"    - {file}")
            else:
                lines.append("**Observations Found:** None")
            if jcb_types:
                lines.append("**JCB Types for Assimilation:**")
                for jcb_type in jcb_types:
                    lines.append(f"- {jcb_type}")
            else:
                lines.append(
                    "**JCB Types for Assimilation:** None"
                )
            if job_card:
                job_name = Path(job_card).name
                lines.append(
                    f"**Job Card:** Generated ({job_name})"
                )
            else:
                lines.append(
                    "**Job Card:** Not generated (no observations)"
                )
            if execution:
                status = execution.get("status", "unknown")
                execution_mode = execution.get(
                    "execution_mode", "unknown"
                )
                if status == "submitted":
                    job_id = execution.get("job_id")
                    lines.append(
                        f"**Execution:** SUBMITTED to SLURM (Job ID: {job_id})"
                    )
                elif status == "completed":
                    return_code = execution.get(
                        "return_code", "unknown"
                    )
                    lines.append(
                        "**Execution:** COMPLETED (bash, return code: "
                        f"{return_code})"
                    )
                elif status == "failed":
                    error = execution.get(
                        "error", "Unknown error"
                    )
                    lines.append(
                        f"**Execution:** FAILED ({execution_mode}) - {error}"
                    )
                elif status == "skipped":
                    reason = execution.get(
                        "reason", "Unknown reason"
                    )
                    lines.append(
                        f"**Execution:** SKIPPED - {reason}"
                    )
                else:
                    lines.append(
                        f"**Execution:** {status.upper()}"
                    )
            else:
                lines.append("**Execution:** Not executed")
            lines.append("")
            return "\n".join(lines)

        def write_report(
            cycles_list: List[Dict[str, Any]], filename: str, title: str
        ) -> None:
            report_path = output_dir / filename
            with open(report_path, "w") as f:
                f.write(f"# {title}\n\n")
                if not cycles_list:
                    f.write("No cycles processed.\n")
                else:
                    for cycle_data in sorted(
                        cycles_list, key=lambda x: x.get("cycle", "")
                    ):
                        f.write(format_cycle_report(cycle_data))
            self.logger.info(
                f"Status report written to {report_path}"
            )
            print(
                f"Status report written to: {report_path.resolve()}"
            )

        write_report(
            gdas_cycles,
            "gdas_status_report.md",
            "GDAS Cycle Status Report",
        )
        write_report(
            gfs_cycles,
            "gfs_status_report.md",
            "GFS Cycle Status Report",
        )

    def _get_cycle_status_icon(
        self, cycle_data: Dict[str, Any], execution: Dict[str, Any]
    ) -> str:
        """
        Get visual status icon for a cycle based on its processing and
        execution status.
        """
        # ANSI color codes
        GREEN = "\033[92m"  # Bright green
        YELLOW = "\033[93m"  # Bright yellow
        RESET = "\033[0m"  # Reset to default color

        # Check if cycle was processed successfully
        has_observations = bool(cycle_data.get("observations", {}))
        job_card_generated = cycle_data.get("job_card") is not None

        # If no observations, it's a skipped cycle
        if not has_observations:
            return "❌"

        # If observations exist but no job card, something went wrong
        if has_observations and not job_card_generated:
            return "❌"

        # Check execution status if available
        if execution:
            exec_status = execution.get("status", "unknown")
            if exec_status == "completed":
                return "✅"
            elif exec_status == "submitted":
                return "⏳"
            elif exec_status == "failed":
                return "❌"
            elif exec_status == "skipped":
                return f"{YELLOW}○{RESET}"

        # If no execution info but job card was generated successfully
        if job_card_generated:
            return f"{GREEN}✓{RESET}"

        # Default to neutral
        return f"{YELLOW}○{RESET}"
