#!/bin/bash

#------------------------------------------------------------------------------
# This script sets up the environment and runs the obsforge_cycle_processor.py
# Python application to validate observation cycles for a specified date range.
#
# It configures necessary variables such as cycle type, date range, paths to
# validation scripts, HPC modules, and directories for scratch and database
# storage. The script loads required modules, then executes the processor
# in batch mode using SLURM (sbatch), passing all relevant arguments.
#
# Usage:
#   Edit the variables at the top of the script to match your configuration.
#   Run the script to process and validate observation cycles.
#------------------------------------------------------------------------------

cycle_type="your_cycle_type"
date_start="YYYYMMDD"
date_end="YYYYMMDD"
home_obsforge_validate="/path/to/home_obsforge_validate"
hpc_modules="your_hpc_modules"
execution_mode="sbatch"

outputdir="${cycle_type}_obs_validation_${date_start}-${date_end}"
socascratch="${socascratch:-/scratch3/NCEPDEV/da/Guillaume.Vernieres/socascratch}"
jedi_root="${jedi_root:-/scratch3/NCEPDEV/da/Guillaume.Vernieres/sandboxes/global-workflow/sorc/gdas.cd}"
obsforge_db="${obsforge_db:-/scratch3/NCEPDEV/da/common_obsForge}"

module use "${jedi_root}/modulefiles"
module load "GDAS/${hpc_modules}"

python "${home_obsforge_validate}/apps/obsforge_cycle_processor.py" \
    --obsforge "${obsforge_db}" \
    --jcb-gdas-path "${home_obsforge_validate}/jcb-gdas/" \
    --cycle-type "${cycle_type}" \
    --execution-mode "${execution_mode}" \
    --date-range "${date_start}" "${date_end}" \
    --jedi-root "${jedi_root}" \
    --socascratch "${socascratch}" \
    --output-dir "${outputdir}"
