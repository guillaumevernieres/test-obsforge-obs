# Marine Observation 3DVAR Application

This application processes obsForge-generated marine observations through a low-resolution marine 3DVAR system to evaluate and increase confidence in marine observation datasets.

## Features

- Configuration YAML generation for JEDI 3DVAR from observation lists
- Jinja template-based configuration management using JCB-GDAS templates
- Marine observation processing for retrospective experiments
- Integration with NOAA-EMC/jcb-gdas repository for official JEDI templates
- Automatic template matching for different marine observation types
- YAML-based configuration for improved readability and consistency

## Structure

- `src/` - Main application source code
- `templates/` - Custom Jinja templates for configuration generation
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

This generates a JEDI 3DVAR configuration using the official JCB-GDAS marine observation templates and example observations from `config/example_observations_jcb.yaml`.

### Command Line Interface

```bash
python src/marine_obs_config.py --template template_name.yaml.j2 \
                                --observations obs_list.yaml \
                                --context context.yaml \
                                --output config.yaml
```

### Custom Template Development

For advanced users who need to create custom observation templates:

```bash
python example.py
```

This demonstrates using custom templates from the `templates/` directory.

## Configuration Format

Observations are specified in YAML format using the JCB-GDAS template system. Each observation type corresponds to a specific template in the JCB-GDAS repository:

```yaml
observations:
  - type: sst_generic
    input_path: ./data/marine
    input_prefix: ""
    input_suffix: .nc
    output_path: ./output/marine
    output_prefix: "diag_"
    output_suffix: _out.nc

  - type: insitu_temp_profile_argo
    input_path: ./data/marine
    input_prefix: ""
    input_suffix: .nc
    output_path: ./output/marine
    output_prefix: "diag_"
    output_suffix: _out.nc
```

### Supported Marine Observation Types

The application automatically maps observation types to JCB-GDAS templates. Currently supported types include:

- `sst_generic` - Sea Surface Temperature (generic satellite sensors)
- `insitu_temp_profile_argo` - Argo temperature profiles
- `insitu_salt_profile_argo` - Argo salinity profiles
- `adt_rads_all` - Altimeter data (multi-mission)
- `sss_smap_l2` - SMAP Sea Surface Salinity
- `sss_smos_l2` - SMOS Sea Surface Salinity

See `config/example_observations_jcb.yaml` for a complete example.

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
