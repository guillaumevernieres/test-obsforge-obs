#!/usr/bin/env python3
"""
Example script demonstrating how to use the Marine Observation 3DVAR
configuration generator.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from marine_obs_config import MarineObsConfigGenerator


def main():
    """Run example configuration generation."""

    # Initialize the generator
    generator = MarineObsConfigGenerator(template_dir="templates")

    # Load example observations
    with open("config/example_observations.json", 'r') as f:
        observations = json.load(f)

    # Additional context for the template
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
        "output_filename": "marine_analysis.nc"
    }

    print("Generating JEDI 3DVAR configuration...")
    print(f"Using {len(observations)} observations")

    # Validate observations first
    if not generator.validate_observations(observations):
        print("ERROR: Invalid observation format!")
        return 1

    # Generate configuration
    try:
        generator.generate_config(
            template_name="jedi_3dvar_template.yaml",
            obs_list=observations,
            additional_context=context,
            output_file="config/generated_3dvar_config.yaml"
        )

        print("Configuration generated successfully!")
        print("Output saved to: config/generated_3dvar_config.yaml")

        # Display summary
        processed = generator.load_observations(observations)
        print("\nSummary:")
        print(f"- Total observations: {processed['obs_count']}")
        print(f"- Observation types: {', '.join(processed['obs_types'])}")
        for obs_type, obs_group in processed['observations_by_type'].items():
            print(f"  - {obs_type}: {len(obs_group)} files")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to generate configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
