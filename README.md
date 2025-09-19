# Marine Observation 3DVAR Application

This application processes obsForge-generated marine observations through a low-resolution marine 3DVAR system to evaluate and increase confidence in marine observation datasets.

## Features

- Configuration YAML generation for JEDI 3DVAR from observation lists
- Jinja template-based configuration management using JCB-GDAS templates
- Marine observation processing for retrospective experiments
- Integration with NOAA-EMC/jcb-gdas repository for official JEDI templates
- Automatic template matching for different marine observation types

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

### Basic Usage with JCB-GDAS Templates

```bash
python example_jcb.py
```

This will generate a 3DVAR configuration using the official JCB-GDAS marine observation templates.

### Custom Templates

```bash
python example.py
```

This uses the original custom template approach.

### Command Line Interface

```bash
python src/marine_obs_config.py --template template_name.yaml.j2 \
                                --observations obs_list.json \
                                --output config.yaml
```

## Configuration Format

### JCB-GDAS Format (Recommended)

Observations should be specified with the following format:

```json
[
  {
    "type": "sst_generic",
    "input_path": "./data/marine",
    "input_prefix": "",
    "input_suffix": ".nc",
    "output_path": "./output/marine",
    "output_prefix": "diag_",
    "output_suffix": "_out.nc"
  }
]
```

### Legacy Format

```json
[
  {
    "type": "sea_surface_temperature",
    "file": "data/sst_obs.nc",
    "variables": ["seaSurfaceTemperature"],
    "observation_operator": "Identity"
  }
]
```

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
