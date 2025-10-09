# ObsForge Validation Framework

This comprehensive framework validates obsForge-generated marine observations through automated processing, job scheduling, and status monitoring across multiple HPC schedulers. The system evaluates and increases confidence in marine observation datasets using JEDI 3DVAR configurations.

## Features

- **Multi-scheduler support**: SLURM (sbatch) and PBS (qsub) job submission
- **Automated cycle processing**: Scan obsForge directories and process all available cycles
- **JEDI 3DVAR configuration generation** from marine observation lists
- **Integration with official JCB-GDAS templates** from NOAA-EMC
- **Comprehensive validation**: Missing observations, status logs, and template validation
- **Status monitoring**: Job completion tracking and detailed reporting
- **Flexible execution modes**: Direct bash execution or scheduler submission
- **Parameterized templates**: Configurable paths for different environments
- **Failure detection**: Comprehensive error reporting and status tracking
- **Markdown reports**: Automated generation of validation summaries

## Structure

- `src/` - Main application source code
- `apps/` - Complete applications built on the core system
- `config/` - Configuration files and examples
- `templates/` - Jinja2 templates for 3DVAR configuration generation
- `tests/` - Unit tests
- `data/` - Sample data and observations
- `jcb-gdas/` - Git submodule containing JCB-GDAS templates

## JCB-GDAS Integration

The application now integrates with the official JCB-GDAS (JEDI Configuration Builder for GDAS) repository to use production-ready observation templates for marine observations. The following marine observation types are supported:

- Sea Surface Temperature (SST) - Multiple satellite sensors
- Sea Surface Salinity (SSS) - SMAP and SMOS
- Altimeter Data (ADT) - Multiple missions (Jason, Sentinel, etc.)
- In-situ profiles - Argo, XBT, CTD, glider data
- Ice concentration - Various sensors

## Applications

### Core Validation System

The `apps/` directory contains a comprehensive validation framework for obsForge data:

#### ObsForge Cycle Processor
Main validation application with multi-scheduler support:

```bash
# Process cycles with PBS scheduler
python apps/obsforge_cycle_processor.py \
  --obsforge /path/to/obsforge_root \
  --execution-mode qsub \
  --cycle-type gdas \
  --date-range 20250815 20250815 \
  --jedi-root /path/to/jedi \
  --socascratch /path/to/scratch

# Process cycles with SLURM scheduler
python apps/obsforge_cycle_processor.py \
  --obsforge /path/to/obsforge_root \
  --execution-mode sbatch \
  --cycle-type gfs \
  --date-range 20250815 20250820
```

#### Scheduler-Specific Drivers

**SLURM Driver:**
```bash
python apps/sbatch_driver.py \
  --date-start 20250815 \
  --date-end 20250815 \
  --cycle-type gdas \
  --outputdir ./results
```

**PBS Driver:**
```bash
python apps/pbs_driver.py \
  --date-start 20250815 \
  --date-end 20250815 \
  --cycle-type gdas \
  --outputdir ./results \
  --account da-cpu \
  --queue normal
```

#### Job Status Monitoring

**SLURM Job Checker:**
```bash
python apps/check_slurm_jobs.py --directory ./results
```

**PBS Job Checker:**
```bash
python apps/check_pbs_jobs.py --directory ./results
```

### Key Capabilities

- **Automated cycle detection**: Scans for both GFS and GDAS cycles
- **Multi-scheduler execution**: Supports SLURM and PBS workload managers
- **Comprehensive validation**: Checks for missing observations and status logs
- **Template validation**: Verifies JCB-GDAS template availability
- **Status reporting**: Generates detailed markdown reports
- **Job tracking**: Monitors job completion and generates summaries
- **Failure analysis**: Identifies and reports various failure modes

See `apps/README.md` for detailed documentation.

## Usage

### Quick Start

#### 1. Process ObsForge Data
```bash
# Scan and validate cycles with direct execution
python apps/obsforge_cycle_processor.py \
  --obsforge /path/to/obsforge \
  --execution-mode bash \
  --status-report

# Submit validation jobs to SLURM
python apps/obsforge_cycle_processor.py \
  --obsforge /path/to/obsforge \
  --execution-mode sbatch \
  --cycle-type gdas \
  --date-range 20250815 20250820
```

#### 2. Generate Scheduler Scripts
```bash
# Generate and submit SLURM job
python apps/sbatch_driver.py \
  --date-start 20250815 \
  --date-end 20250815 \
  --cycle-type gfs \
  --outputdir ./validation_results

# Generate and submit PBS job
python apps/pbs_driver.py \
  --date-start 20250815 \
  --date-end 20250815 \
  --cycle-type gdas \
  --outputdir ./validation_results \
  --account myproject \
  --queue normal
```

#### 3. Monitor Job Status
```bash
# Check SLURM job completion
python apps/check_slurm_jobs.py --directory ./validation_results

# Check PBS job completion
python apps/check_pbs_jobs.py --directory ./validation_results --output pbs_status.md
```

### Legacy Configuration Generation

For direct 3DVAR configuration generation:

```bash
python example_jcb.py
```

This generates a JEDI 3DVAR configuration using the official JCB-GDAS marine observation templates and example observations from `config/example_obs_list.yaml`.

## Recommended HPC Workflow

### Using main_driver.sh (Preferred Method)

For HPC environments, the **recommended approach** is to use the `main_driver.sh` script, which submits validation jobs as small, parallel tasks. This approach is optimal for HPC systems as it:

- Distributes workload across multiple scheduler jobs
- Enables efficient parallel processing of cycles
- Reduces individual job resource requirements
- Provides better fault tolerance and restart capabilities

#### Configuration

Edit the variables in `apps/main_driver.sh` to match your environment:

```bash
# Edit these variables in main_driver.sh
cycle_type="gdas"                    # or "gfs"
date_start="20250815"               # YYYYMMDD format
date_end="20250820"                 # YYYYMMDD format
home_obsforge_validate="/path/to/obsforge-validate"
hpc_modules="your_hpc_modules"      # e.g., "gnu-openmpi/4.1.4"
execution_mode="sbatch"             # or "qsub" for PBS
```

#### Execution

```bash
# Run the main driver script
cd obsforge-validate/apps
./main_driver.sh
```

This will:
1. Load required HPC modules
2. Submit validation jobs for each cycle in the date range
3. Process cycles in parallel using the specified scheduler
4. Generate job cards and configurations for each cycle

#### Important Notes

**⚠️ Job Status Monitoring Required**

The summary output from the main validation run will **NOT** reflect the success or failure of the actual JEDI 3DVAR execution. The initial summary only indicates whether job submission was successful. To determine if the 3DVAR validation completed successfully, you **must** use the job checking utilities:

**For SLURM jobs:**
```bash
# Check job completion status after jobs finish
python apps/check_slurm_jobs.py --directory ${outputdir} --verbose

# Example output directory name: gdas_obs_validation_20250815-20250820
python apps/check_slurm_jobs.py \
  --directory gdas_obs_validation_20250815-20250820 \
  --output validation_results.md
```

**For PBS jobs:**
```bash
# Check job completion status after jobs finish
python apps/check_pbs_jobs.py --directory ${outputdir} --verbose

# Example for PBS
python apps/check_pbs_jobs.py \
  --directory gdas_obs_validation_20250815-20250820 \
  --output pbs_validation_results.md
```

#### Complete Workflow Example

```bash
# 1. Configure and run validation
cd obsforge-validate/apps
# Edit main_driver.sh variables...
./main_driver.sh

# 2. Wait for jobs to complete (monitor with squeue/qstat)
squeue -u $USER                    # For SLURM
# or
qstat -u $USER                     # For PBS

# 3. Check validation results after jobs complete
python apps/check_slurm_jobs.py \
  --directory gdas_obs_validation_20250815-20250820 \
  --output final_results.md

# 4. Review the markdown report
cat final_results.md
```

#### Advantages of main_driver.sh Approach

1. **Parallel Processing**: Each cycle runs as a separate scheduler job
2. **Resource Efficiency**: Smaller jobs are scheduled more quickly
3. **Fault Tolerance**: Individual cycle failures don't affect other cycles
4. **Scalability**: Can process large date ranges efficiently
5. **HPC Best Practices**: Follows recommended patterns for HPC workloads

## Validation Framework Architecture

### Execution Modes

The framework supports three execution modes:

- **`bash`**: Direct execution for testing and development
- **`sbatch`**: SLURM scheduler submission for HPC environments
- **`qsub`**: PBS scheduler submission for HPC environments

### Validation Criteria

The system validates multiple aspects of obsForge data:

1. **Observation Availability**: Checks for presence of observation files
2. **Status Log Validation**: Verifies required status log files exist
3. **Template Validation**: Ensures JCB-GDAS templates are available
4. **Job Execution**: Monitors job completion and exit codes

### Failure Detection

Comprehensive failure detection includes:
- Cycles with no observations found
- Missing obsForge marine status logs
- Missing JCB-GDAS templates
- Job execution failures
- Processing errors and exceptions

### Output Generation

The framework generates multiple output types:
- **Job Cards**: Scheduler-specific execution scripts
- **YAML Configurations**: JEDI 3DVAR configurations with available observations
- **Status Reports**: Detailed markdown summaries
- **Job Tracking**: Scheduler job IDs and completion status

## Configuration Format

Observations are automatically detected from obsForge directory structures. The system maps obsForge files to JCB-GDAS templates:

```
obsforge_root/
├── gdas.YYYYMMDD/HH/ocean/
│   ├── adt/gdas.tHHz.rads_adt_3a.nc
│   ├── sst/gdas.tHHz.sst_viirs_npp.nc
│   └── sss/gdas.tHHz.sss_smap_l2.nc
└── gfs.YYYYMMDD/HH/ocean/
    └── [similar structure]
```

For manual configuration, observations follow the GFS v17 format:

```yaml
observations:
# ADT (Altimeter Data)
- rads_adt_3a
- rads_adt_j3

# SSS (Sea Surface Salinity)
- sss_smap_l2
- sss_smos_l2

# SST (Sea Surface Temperature)
- sst_viirs_npp_l3u
- sst_avhrrf_ma_l3u

# In situ
- insitu_temp_profile_argo
- insitu_salt_profile_argo
```

### Supported Marine Observation Types

The application automatically maps observation types to JCB-GDAS templates. Currently supported types include:

- **Altimeter Data**: `rads_adt_3a`, `rads_adt_3b`, `rads_adt_6a`, `rads_adt_c2`, `rads_adt_j2`, `rads_adt_j3`, `rads_adt_sa`, `rads_adt_sw`
- **Sea Surface Salinity**: `sss_smap_l2`, `sss_smos_l2`
- **Sea Surface Temperature**: `sst_viirs_n21_l3u`, `sst_viirs_n20_l3u`, `sst_viirs_npp_l3u`, `sst_avhrrf_ma_l3u`, `sst_avhrrf_mb_l3u`, `sst_avhrrf_mc_l3u`
- **Sea Ice**: `icec_amsr2_north`, `icec_amsr2_south`
- **In Situ**: `insitu_temp_profile_argo`, `insitu_salt_profile_argo`, `insitu_temp_surface_drifter`

See `config/example_obs_list.yaml` for a complete example.

## Multi-Scheduler Support

### SLURM (sbatch)
- Job submission via `sbatch` command
- SLURM-specific directives (#SBATCH)
- SLURM environment variables ($SLURM_*)
- Job ID extraction from sbatch output

### PBS (qsub)
- Job submission via `qsub` command
- PBS-specific directives (#PBS)
- PBS environment variables ($PBS_*)
- Job ID tracking and status monitoring

### Template System

The framework uses Jinja2 templates for both schedulers:
- `templates/job_card.sh.j2` - SLURM job template
- `templates/job_card_pbs.sh.j2` - PBS job template
- `templates/sbatch_driver.sh.j2` - SLURM batch driver
- `templates/pbs_driver.sh.j2` - PBS batch driver

## Requirements

### Software Dependencies
- Python 3.8+
- Jinja2 for template processing
- PyYAML for YAML handling
- Git (for submodule support)

### HPC Environment
- SLURM workload manager (for sbatch mode) OR
- PBS/Torque workload manager (for qsub mode)
- MPI implementation (for JEDI execution)
- JEDI build environment

### Required Templates
- JCB-GDAS repository with marine observation templates
- Custom job card templates (provided in templates/)

## Installation

```bash
# Clone the repository
git clone https://github.com/guillaumevernieres/obsforge-validate.git
cd obsforge-validate

# Initialize JCB-GDAS submodule
git submodule update --init --recursive

# Install Python dependencies
pip install pyyaml jinja2

# Make scripts executable
chmod +x apps/*.py
```

### Environment Setup

Configure paths in your environment:

```bash
export OBSFORGE_VALIDATE_ROOT="/path/to/obsforge-validate"
export JEDI_ROOT="/path/to/jedi/build"
export SOCASCRATCH="/path/to/soca/scratch"
export OBSFORGE_DB="/path/to/obsforge/data"
```
