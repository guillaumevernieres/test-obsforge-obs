from __future__ import annotations

import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ObsForgeScanner:
    """Scans obsForge directory structure to find available observations."""

    def __init__(
        self,
        obsforge_comroot: str,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the scanner.

        Args:
            obsforge_comroot: Path to obsForge root directory containing
                gfs.YYYYMMDD and gdas.YYYYMMDD directories
            logger: Optional logger instance
        """
        self.obsforge_comroot = Path(obsforge_comroot)
        self.obsforge_root = self.obsforge_comroot
        self.logger = logger or logging.getLogger(__name__)

        if not self.obsforge_root.exists():
            raise FileNotFoundError(
                f"ObsForge directory not found: {self.obsforge_root}"
            )

    def find_cycles(
        self,
        cycle_types: List[str] = ["gfs", "gdas"],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Tuple[str, str, str]]:
        """
        Find available cycles in the obsForge directory, filtered by cycle
        type and date range.

        Args:
            cycle_types: List of cycle types to include ('gfs', 'gdas')
            start_date: Start date in YYYYMMDD format (inclusive)
            end_date: End date in YYYYMMDD format (inclusive)

        Returns:
            List of tuples (cycle_type, date, hour)
        """
        cycles: List[Tuple[str, str, str]] = []
        cycle_types_set = set(cycle_types)
        cycle_pattern = re.compile(r"^(gfs|gdas)\.(\d{8})$")

        # Convert date strings to datetime objects for comparison
        start_dt = (
            datetime.strptime(start_date, "%Y%m%d") if start_date else None
        )
        end_dt = (
            datetime.strptime(end_date, "%Y%m%d") if end_date else None
        )

        for cycle_dir in self.obsforge_root.iterdir():
            if not cycle_dir.is_dir():
                continue

            match = cycle_pattern.match(cycle_dir.name)
            if not match:
                continue

            cycle_type, date = match.groups()
            if cycle_type not in cycle_types_set:
                continue

            # Filter by date range if specified
            date_dt = datetime.strptime(date, "%Y%m%d")
            if start_dt and date_dt < start_dt:
                continue
            if end_dt and date_dt > end_dt:
                continue

            # Look for hour subdirectories
            for hour_dir in cycle_dir.iterdir():
                if hour_dir.is_dir() and hour_dir.name.isdigit():
                    hour = hour_dir.name.zfill(2)
                    cycles.append((cycle_type, date, hour))

        return sorted(cycles)

    def scan_cycle_observations(
        self, cycle_type: str, date: str, hour: str
    ) -> Dict[str, List[str]]:
        """
        Scan a specific cycle for available observations.

        Args:
            cycle_type: 'gfs' or 'gdas'
            date: Date in YYYYMMDD format
            hour: Hour in HH format

        Returns:
            Dictionary mapping observation types to lists of available files
        """
        cycle_path = (
            self.obsforge_root / f"{cycle_type}.{date}" / hour / "ocean"
        )

        if not cycle_path.exists():
            self.logger.warning(
                f"Ocean directory not found: {cycle_path}"
            )
            return {}

        observations: Dict[str, List[str]] = {}

        # Scan known observation type directories
        obs_types = ["adt", "icec", "sss", "sst", "insitu"]

        for obs_type in obs_types:
            obs_dir = cycle_path / obs_type
            if obs_dir.exists():
                # Find all .nc files in this directory
                nc_files = list(obs_dir.glob("*.nc"))
                if nc_files:
                    file_names = [f.name for f in nc_files]
                    observations[obs_type] = file_names
                    msg = (
                        "Found "
                        f"{len(nc_files)} {obs_type} files for "
                        f"{cycle_type}.{date}.{hour}"
                    )
                    self.logger.info(msg)

        return observations
