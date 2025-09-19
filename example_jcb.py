#!/usr/bin/env python3
"""
Example script demonstrating how to use the Marine Observation 3DVAR
configuration generator with JCB-GDAS templates.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from marine_obs_config import MarineObsConfigGenerator


def main():
    """Run example configuration generation with JCB-GDAS templates."""

    # Initialize the generator with JCB-GDAS support
    generator = MarineObsConfigGenerator(
        template_dir="templates",
        jcb_gdas_path="jcb-gdas"
    )

    print("Available JCB-GDAS Marine Templates:")
    print("=" * 40)
    available_templates = generator.jcb_manager.list_available_templates()
    for i, template in enumerate(available_templates[:10], 1):  # Show first 10
        print(f"{i:2d}. {template}")
    if len(available_templates) > 10:
        print(f"    ... and {len(available_templates) - 10} more")
    print()

    # Create observation list with JCB-compatible format
    observations = [
        {
            "type": "sst_generic",
            "input_path": "./data/marine",
            "input_prefix": "",
            "input_suffix": ".nc",
            "output_path": "./output/marine",
            "output_prefix": "diag_",
            "output_suffix": "_out.nc"
        },
        {
            "type": "insitu_temp_profile_argo",
            "input_path": "./data/marine",
            "input_prefix": "",
            "input_suffix": ".nc",
            "output_path": "./output/marine",
            "output_prefix": "diag_",
            "output_suffix": "_out.nc"
        },
        {
            "type": "adt_rads_all",
            "input_path": "./data/marine",
            "input_prefix": "",
            "input_suffix": ".nc",
            "output_path": "./output/marine",
            "output_prefix": "diag_",
            "output_suffix": "_out.nc"
        }
    ]

    # Additional context for the 3DVAR configuration
    context = {
        "window_begin": "2024-01-01T00:00:00Z",
        "window_length": "PT6H",
        "background_date": "2024-01-01T00:00:00Z",
        "ensemble_members": 20,
        "model_name": "MOM6",
        "model_tstep": "PT1H",
        "outer_iterations": 10,
        "gradient_norm_reduction": 1e-10,
        "geometry_namelist": "input.nml",
        "fields_metadata": "fields_metadata.yaml",
        "output_dir": "./output",
        "output_filename": "marine_analysis_jcb.nc",
        "letkf_app": False
    }

    print("Generating JEDI 3DVAR configuration with JCB-GDAS templates...")
    print(f"Using {len(observations)} marine observations")

    try:
        # Generate configuration using JCB-GDAS templates
        generator.generate_config_from_jcb(
            obs_list=observations,
            additional_context=context,
            output_file="config/generated_jcb_3dvar_config.yaml"
        )

        print("✓ Configuration generated successfully!")
        print("Output saved to: config/generated_jcb_3dvar_config.yaml")

        # Display template matching information
        print("\nTemplate Matching:")
        print("-" * 20)
        for obs in observations:
            obs_type = obs['type']
            template = generator.jcb_manager.match_observation_to_template(
                obs_type)
            if template:
                print(f"✓ {obs_type} -> {template}")
            else:
                print(f"✗ {obs_type} -> No template found")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to generate configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
