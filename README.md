# Marine Observation 3DVAR Application

This application processes obsForge-generated marine observations through a low-resolution marine 3DVAR system to evaluate and increase confidence in marine observation datasets.

## Features

- JEDI 3DVAR configuration generation from marine observation lists
- Integration with official JCB-GDAS templates from NOAA-EMC
- Support for GFS v17 observation list format
- Automatic template matching for marine observation types
- Marine observation processing for retrospective experiments

## Structure

- `src/` - Main application source code
- `config/` - Configuration files and examples
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

## Usage

### Generate 3DVAR Configuration

```bash
python example_jcb.py
```

This generates a JEDI 3DVAR configuration using the official JCB-GDAS marine observation templates and example observations from `config/example_obs_list.yaml`.

### Command Line Interface

```bash
python src/marine_obs_config.py --obs-list obs_list.yaml \
                                --context context.yaml \
                                --output config.yaml
```

## Configuration Format

Observations are specified as a simple list of observation type names in YAML format. Each observation type corresponds to a specific template in the JCB-GDAS repository:

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

This format matches the GFS v17 observation list format and is much simpler than specifying detailed configuration parameters - the JCB-GDAS templates contain all the necessary details.

### Supported Marine Observation Types

The application automatically maps observation types to JCB-GDAS templates. Currently supported types include:

- **Altimeter Data**: `rads_adt_3a`, `rads_adt_3b`, `rads_adt_6a`, `rads_adt_c2`, `rads_adt_j2`, `rads_adt_j3`, `rads_adt_sa`, `rads_adt_sw`
- **Sea Surface Salinity**: `sss_smap_l2`, `sss_smos_l2`
- **Sea Surface Temperature**: `sst_viirs_n21_l3u`, `sst_viirs_n20_l3u`, `sst_viirs_npp_l3u`, `sst_avhrrf_ma_l3u`, `sst_avhrrf_mb_l3u`, `sst_avhrrf_mc_l3u`
- **Sea Ice**: `icec_amsr2_north`, `icec_amsr2_south`
- **In Situ**: `insitu_temp_profile_argo`, `insitu_salt_profile_argo`, `insitu_temp_surface_drifter`

See `config/example_obs_list.yaml` for a complete example.

## Requirements

- Python 3.8+
- Jinja2 for template processing
- PyYAML for YAML handling
- Git (for submodule support)

## Installation

```bash
# Clone with submodules
git clone --recursive <repository-url>

# Or if already cloned, initialize submodules
git submodule update --init --recursive

# Install dependencies
pip install -r requirements.txt
```
