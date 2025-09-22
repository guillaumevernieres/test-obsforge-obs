# Applications Directory

This directory contains complete applications built on top of the marine observation configuration system.

## ObsForge Cycle Processor

**File:** `obsforge_cycle_processor.py`

### Overview

The ObsForge Cycle Processor is an application that automatically scans an obsForge directory structure and generates job cards and YAML configuration files for each available cycle (both GFS and GDAS). The generated JEDI 3DVAR configurations will only contain observations that are actually available for each specific cycle.

### Directory Structure Expected

```
obsforge_root/
├── gdas.YYYYMMDD
│   └── HH
│       └── ocean
│           ├── adt/
│           │   ├── gdas.tHHz.rads_adt_3a.tm00.nc
│           │   ├── gdas.tHHz.rads_adt_3b.tm00.nc
│           │   ├── gdas.tHHz.rads_adt_c2.tm00.nc
│           │   ├── gdas.tHHz.rads_adt_j3.tm00.nc
│           │   └── gdas.tHHz.rads_adt_sa.tm00.nc
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
```

### Features

- **Automatic cycle detection**: Scans for both GFS and GDAS cycles
- **Observation file discovery**: Finds all available observation files per cycle
- **Smart observation mapping**: Maps obsForge file names to JCB-GDAS observation types
- **Job card generation**: Creates SLURM batch scripts for each cycle using Jinja2 templates
- **Job execution**: Execute generated job cards via SLURM submission or direct bash execution
- **Custom 3DVAR configs**: Generates YAML configurations with only available observations
- **Template-based**: Uses Jinja2 templates for flexible configuration generation

### Usage

#### Command Line Interface

```bash
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./cycle_output
```

**Options:**
- `--obsforge` (required): Path to obsForge root directory containing gfs.YYYYMMDD and gdas.YYYYMMDD directories
- `--output-dir`: Output directory for job cards and configs (default: ./cycle_output)
- `--jcb-gdas-path`: Path to JCB-GDAS repository (default: ../jcb-gdas)
- `--template-dir`: Path to custom templates (default: ../templates)
- `--cycle-type`: Process only specific cycle type: gfs, gdas, or both (default: both)
- `--date-range`: Process cycles in date range YYYYMMDD YYYYMMDD
- `--execution-mode`: Execute generated job cards: sbatch for SLURM submission or bash for direct execution. If not specified, only generate job cards without executing them.
- `--status-report`: Generate detailed status report organized per cycle
- `--verbose`: Enable verbose logging

#### Execution Examples

**Generate job cards only:**
```bash
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./output
```

**Generate and execute via SLURM:**
```bash
# Generate job cards and execute via SLURM
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./output --execution-mode sbatch
```

**Generate and execute directly in bash:**
```bash
# Generate job cards and execute directly in bash
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./output --execution-mode bash
```

**Generate detailed status report:**
```bash
# Basic processing with detailed status report
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./output --status-report

# Execute and generate detailed status report
python obsforge_cycle_processor.py --obsforge /path/to/obsforge_root --output-dir ./output --execution-mode bash --status-report
```

#### Programmatic Usage

```python
from obsforge_cycle_processor import ObsForgeCycleProcessor

processor = ObsForgeCycleProcessor(
    obsforge_comroot="/path/to/obsforge_root",
    output_dir="./cycle_output",
    jcb_gdas_path="./jcb-gdas",
    template_dir="./templates"
)

# Process all cycles
summary = processor.process_all_cycles()

# Process specific cycle
result = processor.process_cycle('gdas', '20210831', '18')
```

### Generated Files

For each processed cycle, the application generates files in organized directories:

**Directory Structure:**
```
output_dir/
├── gdas.20210831/
│   └── 18/
│       ├── job_gdas.20210831.18.sh
│       └── config_gdas.20210831.18.yaml
├── gfs.20210831/
│   └── 18/
│       ├── job_gfs.20210831.18.sh
│       └── config_gfs.20210831.18.yaml
└── processing_summary.yaml
```

**Generated Files Per Cycle:**

1. **Job Card** (`job_{cycle_type}.{date}.{hour}.sh`):
   - SLURM batch script generated from Jinja2 template (`job_card.sh.j2`)
   - Environment setup
   - Data linking commands
   - JEDI 3DVAR execution

2. **Configuration File** (`config_{cycle_type}.{date}.{hour}.yaml`):
   - Complete JEDI 3DVAR configuration
   - Only includes available observations
   - Generated from Jinja2 templates

3. **Processing Summary** (`processing_summary.yaml`):
   - Overview of all processed cycles (in output root)
   - Success/failure statistics
   - Detailed cycle information

### Job Execution

The application can optionally execute the generated job cards using two modes:

#### SLURM Mode (`--execution-mode sbatch`)
- Submits job cards to SLURM scheduler using `sbatch`
- Returns SLURM job IDs for monitoring
- Suitable for HPC environments with SLURM workload manager
- Jobs run according to SLURM scheduling policies

#### Direct Execution Mode (`--execution-mode bash`)
- Runs job cards directly using `bash`
- Executes immediately in the current session
- Suitable for testing, development, or non-SLURM environments
- Returns execution output and return codes

#### Execution Results
When using `--execution-mode`, the application provides detailed execution information:
- Execution status (submitted/completed/failed)
- SLURM job IDs (for sbatch mode)
- Return codes and output (for bash mode)
- Execution summary statistics

**Example execution output:**
```
Processing Summary:
  Total cycles found: 2
  Successfully processed: 2
  Failed: 0

Execution Summary:
  Jobs submitted to SLURM: 2
  Jobs completed directly: 0
  Jobs failed to execute: 0
  SLURM Job IDs: 12345, 12346
```

#### Status Report
When using `--status-report`, the application generates a comprehensive status report organized per cycle, showing:

- **Visual status indicators**: Color-coded symbols for quick status identification
  - 🟢 **Green checkmarks (✓)**: Successfully processed and/or executed cycles
  - 🔴 **Red crosses (✗)**: Failed processing or execution
  - 🟡 **Yellow circles (○)**: Skipped or empty cycles
  - 🟡 **Yellow clocks (⧗)**: Submitted jobs pending execution
- **Complete observation file listings**: Shows ALL observation files found (not just a summary)
- **JCB types for assimilation**: Mapped observation types for the JEDI configuration
- **Job card generation status**: Whether job cards were successfully created
- **Execution status**: Success/failure status of job execution with return codes or job IDs

**Example status report output:**
```
================================================================================
OBSFORGE CYCLE STATUS REPORT
================================================================================

OVERALL SUMMARY:
  Total cycles found: 3
  Successfully processed: 3
  Failed to process: 0

EXECUTION SUMMARY:
  Jobs submitted to SLURM: 0
  Jobs completed directly: 2
  Jobs failed to execute: 0
  Jobs skipped (no observations): 1

DETAILED CYCLE STATUS:
--------------------------------------------------------------------------------

✓ Cycle: gdas.20240101.00
  Observations Found:
    ADT: 5 files
      - rads_adt_j3_20240101_000000.nc
      - rads_adt_3a_20240101_000000.nc
      - rads_adt_c2_20240101_000000.nc
      - rads_adt_3a_20240101_030000.nc
      - rads_adt_j3_20240101_030000.nc
    SST: 3 files
      - viirs_sst_npp_20240101_000000.nc
      - modis_sst_aqua_20240101_000000.nc
      - avhrr_sst_metop_20240101_000000.nc
  JCB Types for Assimilation:
    - rads_adt_j3
    - rads_adt_3a
    - rads_adt_c2
    - sst_viirs_npp_l3u
    - sst_modis_l3u
    - sst_avhrr_metop_l3u
  Job Card: Generated (job_gdas.20240101.00.sh)
  Execution: COMPLETED (bash, return code: 0)

○ Cycle: gfs.20240101.00
  Observations Found: None
  JCB Types for Assimilation: None
  Job Card: Not generated (no observations)
  Execution: SKIPPED - No job card generated (no observations found)
```

### Job Card Template

The job cards are generated using a Jinja2 template located at `templates/job_card.sh.j2`. This template provides:

- **Flexible SLURM options**: Customizable job parameters like time, ntasks, partition
- **Environment variables**: Automatic setup of cycle-specific variables
- **Data linking**: Automatic linking of observation data files
- **Template context variables**:
  - `cycle_name`: Full cycle name (e.g., 'gdas.20210831.18')
  - `cycle_type`, `cycle_date`, `cycle_hour`: Individual cycle components
  - `jcb_obs_types`: List of JCB observation types available
  - `obsforge_root`: Path to obsForge data directory
  - `obs_categories`: Observation categories for data linking

### Observation Type Mapping

The application automatically maps obsForge observation files to JCB-GDAS templates:

| ObsForge Type | File Pattern | JCB Template |
|---------------|--------------|--------------|
| adt | `*_3a.*` | `rads_adt_3a` |
| adt | `*_3b.*` | `rads_adt_3b` |
| adt | `*_c2.*` | `rads_adt_c2` |
| adt | `*_j3.*` | `rads_adt_j3` |
| adt | `*_sa.*` | `rads_adt_sa` |
| sst | `*viirs*` | `sst_viirs_npp_l3u` |
| sst | `*avhrr*` | `sst_avhrr_metop_l3u` |
| sst | `*modis*` | `sst_modis_l3u` |
| sss | `*smap*` | `sss_smap_l2` |
| sss | `*smos*` | `sss_smos_l3` |
| icec | `*` | `icec_generic` |

### Example Output

For a cycle `gdas.20210831.18` with ADT, SST, and SSS observations available:

**Job Card** (`job_gdas.20210831.18.sh`):
```bash
#!/bin/bash
#SBATCH --job-name=3dvar_gdas.20210831.18
#SBATCH --output=3dvar_gdas.20210831.18.%j.out
#SBATCH --time=02:00:00
#SBATCH --ntasks=24

# Environment setup
export CYCLE_TYPE=gdas
export CYCLE_DATE=20210831
export CYCLE_HOUR=18
export CONFIG_FILE="config_gdas.20210831.18.yaml"

# Data paths
export OBSFORGE_ROOT="/path/to/obsforge_root"
export CYCLE_DATA_DIR="${OBSFORGE_ROOT}/gdas.20210831/18/ocean"

# Link observation data files
ln -sf ${CYCLE_DATA_DIR}/adt/*.nc .
ln -sf ${CYCLE_DATA_DIR}/sst/*.nc .
ln -sf ${CYCLE_DATA_DIR}/sss/*.nc .

# Run JEDI 3DVAR
mpirun -np $SLURM_NTASKS ${JEDI_BUILD}/bin/fv3jedi_var.x $CONFIG_FILE
```

**Configuration** (`config_gdas.20210831.18.yaml`):
```yaml
cost_function:
  cost_type: 3D-Var
  window_begin: "2021-08-31T15:00:00Z"
  window_length: "PT6H"

  observations:
    observers:
    # Only observations actually available for this cycle
    - obs space:
        name: "rads_adt_3a"
        # ... (configuration from JCB template)
    - obs space:
        name: "sst_viirs_npp_l3u"
        # ... (configuration from JCB template)
    - obs space:
        name: "sss_smap_l2"
        # ... (configuration from JCB template)

output:
  filename: "analysis_gdas.20210831.18.nc"
```

### Dependencies

- Python 3.8+
- PyYAML
- Jinja2
- Pathlib
- The main marine observation configuration system (../src)
- JCB-GDAS templates (../jcb-gdas)
- Custom 3DVAR templates (../templates)

### Testing

Run the comprehensive test suite:

```bash
python -m pytest tests/test_obsforge_cycle_processor.py -v
```

### Demo

Run the demonstration script:

```bash
python example_obsforge_processor.py
```

This creates a mock obsForge directory structure and demonstrates the complete workflow.

## Future Enhancements

Potential improvements for the obsForge cycle processor:

1. **Parallel processing**: Process multiple cycles concurrently
2. **Configuration validation**: Validate generated YAML against JEDI schemas
3. **Dependency management**: Handle observation dependencies and prerequisites
4. **Quality control**: Add observation quality filtering
5. **Monitoring integration**: Add job status monitoring and notifications
6. **Archive integration**: Support for HPSS or other archive systems
