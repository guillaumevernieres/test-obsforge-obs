#!/usr/bin/env python3
"""
Utility script to explore available JCB-GDAS marine observation templates.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from marine_obs_config import JCBGDASTemplateManager


def main():
    """List and explore JCB-GDAS templates."""

    try:
        # Initialize the JCB-GDAS template manager
        jcb_manager = JCBGDASTemplateManager("jcb-gdas")

        print("JCB-GDAS Marine Observation Templates")
        print("=" * 45)

        # Get all available templates
        templates = jcb_manager.list_available_templates()
        print(f"Found {len(templates)} available templates:\n")

        # Group templates by category
        categories = {
            'SST': [],
            'SSS': [],
            'ADT/Altimeter': [],
            'In-situ Profiles': [],
            'Ice Concentration': [],
            'RADS': [],
            'Other': []
        }

        for template in templates:
            if 'sst_' in template:
                categories['SST'].append(template)
            elif 'sss_' in template:
                categories['SSS'].append(template)
            elif 'adt_' in template or 'rads_adt' in template:
                categories['ADT/Altimeter'].append(template)
            elif 'insitu_' in template:
                categories['In-situ Profiles'].append(template)
            elif 'icec_' in template:
                categories['Ice Concentration'].append(template)
            elif 'rads_' in template:
                categories['RADS'].append(template)
            else:
                categories['Other'].append(template)

        # Display by category
        for category, template_list in categories.items():
            if template_list:
                print(f"{category}:")
                for template in sorted(template_list):
                    print(f"  - {template}")
                print()

        # Test template matching
        print("Template Matching Examples:")
        print("-" * 30)

        test_types = [
            'sst_generic',
            'sea_surface_temperature',
            'adt_rads_all',
            'altimeter',
            'insitu_temp_profile_argo',
            'temperature_profile',
            'sss_smap_l2',
            'sea_surface_salinity',
            'unknown_type'
        ]

        for obs_type in test_types:
            matched_template = jcb_manager.match_observation_to_template(obs_type)
            if matched_template:
                print(f"✓ {obs_type:25} -> {matched_template}")
            else:
                print(f"✗ {obs_type:25} -> No match found")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
