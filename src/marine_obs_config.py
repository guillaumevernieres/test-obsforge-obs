#!/usr/bin/env python3
"""
Marine Observation 3DVAR Configuration Generator

This module generates JEDI 3DVAR configuration YAML files from marine observation
lists using Jinja2 templates from the JCB-GDAS repository.
"""

import yaml
import jinja2
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging


class JCBGDASTemplateManager:
    """Manager for JCB-GDAS marine observation templates."""

    def __init__(self, jcb_gdas_path: str = "jcb-gdas"):
        """
        Initialize the template manager.

        Args:
            jcb_gdas_path: Path to the JCB-GDAS repository
        """
        self.jcb_gdas_path = Path(jcb_gdas_path)
        marine_path = self.jcb_gdas_path / "observations" / "marine"
        self.marine_templates_path = marine_path
        self.logger = logging.getLogger(__name__)

        if not self.marine_templates_path.exists():
            msg = f"JCB-GDAS marine templates not found at " \
                  f"{self.marine_templates_path}"
            raise FileNotFoundError(msg)

    def list_available_templates(self) -> List[str]:
        """
        List all available marine observation templates.

        Returns:
            List of template names (without .yaml.j2 extension)
        """
        templates = []
        for template_file in self.marine_templates_path.glob("*.yaml.j2"):
            template_name = template_file.stem.replace(".yaml", "")
            templates.append(template_name)
        return sorted(templates)

    def get_template_path(self, template_name: str) -> Path:
        """
        Get the full path to a template file.

        Args:
            template_name: Name of the template (without extension)

        Returns:
            Path to the template file
        """
        template_file = self.marine_templates_path / f"{template_name}.yaml.j2"
        if not template_file.exists():
            raise FileNotFoundError(f"Template {template_name} not found")
        return template_file

    def match_observation_to_template(self, obs_type: str) -> Optional[str]:
        """
        Match an observation type to the best available template.

        Args:
            obs_type: The observation type to match

        Returns:
            Template name that best matches the observation type, or None
        """
        available_templates = self.list_available_templates()

        # For GFS v17 format, try exact match first (preferred)
        if obs_type in available_templates:
            return obs_type

        # Direct mapping for common observation types (legacy support)
        type_mapping = {
            'sea_surface_temperature': 'sst_generic',
            'sea_surface_salinity': 'sss_smap_l2',
            'sea_level_anomaly': 'adt_rads_all',
            'temperature_profile': 'insitu_temp_profile_argo',
            'salinity_profile': 'insitu_salt_profile_argo',
            'argo_temperature': 'insitu_temp_profile_argo',
            'argo_salinity': 'insitu_salt_profile_argo',
            'drifter_temperature': 'insitu_temp_surface_drifter',
            'altimeter': 'adt_rads_all',
            'sst': 'sst_generic',
            'sss': 'sss_smap_l2'
        }

        # Try exact match in mapping
        if obs_type in type_mapping:
            template_name = type_mapping[obs_type]
            if template_name in available_templates:
                return template_name

        # Try partial matches (fallback)
        obs_type_lower = obs_type.lower()
        for template in available_templates:
            template_lower = template.lower()
            keywords = obs_type_lower.split('_')
            if any(keyword in template_lower for keyword in keywords):
                return template

        msg = f"No template found for observation type: {obs_type}"
        self.logger.warning(msg)
        return None


class MarineObsConfigGenerator:
    """Generator for JEDI 3DVAR configuration files from marine obs."""

    def __init__(self, jcb_gdas_path: str = "jcb-gdas"):
        """
        Initialize the configuration generator.

        Args:
            jcb_gdas_path: Path to the JCB-GDAS repository
        """
        self.jcb_manager = JCBGDASTemplateManager(jcb_gdas_path)

        # Set up Jinja environment for JCB templates only
        jcb_loader = jinja2.FileSystemLoader(
            self.jcb_manager.marine_templates_path
        )

        self.env = jinja2.Environment(
            loader=jcb_loader,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.logger = logging.getLogger(__name__)

    def load_observations(self, obs_list: List[Dict[str, Any]]) -> \
            Dict[str, Any]:
        """
        Process observation list and prepare data for template rendering.

        Args:
            obs_list: List of observation dictionaries

        Returns:
            Processed observation data for template context
        """
        obs_types = list(set(obs.get('type', 'unknown') for obs in obs_list))
        processed_obs = {
            'observations': obs_list,
            'obs_count': len(obs_list),
            'obs_types': obs_types
        }

        # Group observations by type
        obs_by_type = {}
        for obs in obs_list:
            obs_type = obs.get('type', 'unknown')
            if obs_type not in obs_by_type:
                obs_by_type[obs_type] = []
            obs_by_type[obs_type].append(obs)

        processed_obs['observations_by_type'] = obs_by_type

        return processed_obs

    def generate_config_from_jcb(self,
                                 obs_list: List[Union[str, Dict[str, Any]]],
                                 additional_context: Optional[Dict[str, Any]] = None,  # noqa: E501
                                 output_file: Optional[str] = None) -> str:
        """
        Generate JEDI 3DVAR configuration using JCB-GDAS templates.

        Args:
            obs_list: List of marine observations (strings or dicts)
            additional_context: Additional context variables for templates
            output_file: Optional output file path

        Returns:
            Generated YAML configuration as string
        """
        # Convert observations to consistent format
        normalized_obs = []
        for obs in obs_list:
            if isinstance(obs, str):
                # Simple string format: "sst_viirs_npp_l3u"
                normalized_obs.append({'type': obs})
            elif isinstance(obs, dict):
                # Dictionary format: {"type": "sst_viirs_npp_l3u", ...}
                normalized_obs.append(obs)
            else:
                self.logger.warning(f"Skipping invalid observation: {obs}")
                continue

        if not self.validate_observations(normalized_obs):
            raise ValueError("Invalid observation list format")

        # Generate individual observation configurations
        obs_configs = []

        for obs in normalized_obs:
            obs_type = obs.get('type', 'unknown')
            template_name = self.jcb_manager.match_observation_to_template(
                obs_type)

            if not template_name:
                self.logger.warning(f"Skipping observation type: {obs_type}")
                continue

            # Prepare JCB template context
            jcb_context = self._prepare_jcb_context(obs, additional_context)

            try:
                template_file = f"{template_name}.yaml.j2"
                template = self.env.get_template(template_file)
                rendered_obs = template.render(**jcb_context)

                # Parse the rendered YAML to get the observation config
                obs_config = yaml.safe_load(rendered_obs)
                obs_configs.extend(obs_config)  # JCB templates return a list

            except Exception as e:
                msg = f"Failed to render template {template_name} " \
                      f"for {obs_type}: {e}"
                self.logger.error(msg)
                continue

        # Create the complete 3DVAR configuration
        full_config = self._create_full_3dvar_config(obs_configs,
                                                     additional_context)

        # Convert to YAML string
        rendered_config = yaml.dump(full_config, default_flow_style=False)

        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(rendered_config)
            self.logger.info(f"Configuration saved to {output_path}")

        return rendered_config

    def _prepare_jcb_context(self, obs: Dict[str, Any],
                             additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:  # noqa: E501
        """
        Prepare context variables for JCB-GDAS templates.

        Args:
            obs: Single observation dictionary
            additional_context: Additional context variables

        Returns:
            Context dictionary for template rendering
        """
        # Default JCB context variables
        context = {
            'observation_from_jcb': obs.get('type', 'unknown'),
            'marine_obsdatain_path': obs.get('input_path', './data'),
            'marine_obsdatain_prefix': obs.get('input_prefix', ''),
            'marine_obsdatain_suffix': obs.get('input_suffix', '.nc'),
            'marine_obsdataout_path': obs.get('output_path', './output'),
            'marine_obsdataout_prefix': obs.get('output_prefix', ''),
            'marine_obsdataout_suffix': obs.get('output_suffix', '_out.nc'),
            'letkf_app': (additional_context.get('letkf_app', False)
                          if additional_context else False)
        }

        # Add additional context if provided
        if additional_context:
            context.update(additional_context)

        return context

    def _create_full_3dvar_config(self, obs_configs: List[Dict[str, Any]],
                                  additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:  # noqa: E501
        """
        Create the complete 3DVAR configuration with observations.

        Args:
            obs_configs: List of observation configurations
            additional_context: Additional context variables

        Returns:
            Complete 3DVAR configuration dictionary
        """
        context = additional_context or {}

        config = {
            'cost_function': {
                'cost_type': '3D-Var',
                'window_begin': context.get('window_begin', '2024-01-01T00:00:00Z'),
                'window_length': context.get('window_length', 'PT6H'),
                'background': {
                    'type': 'ensemble',
                    'date': context.get('background_date', context.get('window_begin', '2024-01-01T00:00:00Z')),
                    'members from template': {
                        'template': {
                            'filename': context.get('background_template', 'background_%mem%.nc')
                        },
                        'pattern': '%mem%',
                        'nmembers': context.get('ensemble_members', 20)
                    }
                },
                'model': {
                    'name': context.get('model_name', 'MOM6'),
                    'tstep': context.get('model_tstep', 'PT1H'),
                    'model variables': [
                        'ocean_temperature',
                        'ocean_salinity',
                        'sea_surface_height',
                        'ocean_u_velocity',
                        'ocean_v_velocity'
                    ]
                },
                'observations': {
                    'observers': obs_configs
                }
            },
            'variational': {
                'minimizer': {
                    'algorithm': 'DRIPCG'
                },
                'iterations': [{
                    'ninner': context.get('outer_iterations', 10),
                    'gradient_norm_reduction': context.get('gradient_norm_reduction', 1e-10),
                    'test': 'on',
                    'geometry': {
                        'nml_file_in': context.get('geometry_namelist', 'input.nml'),
                        'fields metadata': context.get('fields_metadata', 'fields_metadata.yaml')
                    }
                }]
            },
            'output': {
                'filetype': 'cube',
                'datadir': context.get('output_dir', './output'),
                'filename': context.get('output_filename', 'analysis.nc'),
                'first': 'PT0H',
                'frequency': 'PT6H'
            }
        }

        return config

    def validate_observations(self, obs_list: List[Union[str, Dict[str, Any]]]) -> bool:
        """
        Validate observation list format.

        Args:
            obs_list: List of observation types (strings or dicts)

        Returns:
            True if observations are valid
        """
        for i, obs in enumerate(obs_list):
            if isinstance(obs, str):
                # Simple string format is always valid
                continue
            elif isinstance(obs, dict):
                # Dictionary format must have 'type' field
                if 'type' not in obs:
                    self.logger.error(f"Observation {i} missing 'type' field")
                    return False
            else:
                self.logger.error(f"Observation {i} must be string or dict")
                return False

        return True


def main():
    """Main entry point for the configuration generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate JEDI 3DVAR configuration from marine obs"
    )
    parser.add_argument("--template", required=True,
                        help="Jinja2 template file name")
    parser.add_argument("--observations", required=True,
                        help="YAML file containing observation list")
    parser.add_argument("--output", required=True,
                        help="Output YAML configuration file")
    parser.add_argument("--context",
                        help="Additional YAML context file")
    parser.add_argument("--template-dir", default="templates",
                        help="Template directory")

    args = parser.parse_args()

    # Load observations
    with open(args.observations, 'r') as f:
        obs_data = yaml.safe_load(f)
        # Handle both formats: list or dict with 'observations' key
        if isinstance(obs_data, list):
            obs_list = obs_data
        else:
            obs_list = obs_data.get('observations', [])

    # Load additional context if provided
    additional_context = {}
    if args.context:
        with open(args.context, 'r') as f:
            additional_context = yaml.safe_load(f)

    # Generate configuration
    generator = MarineObsConfigGenerator(args.template_dir)

    if not generator.validate_observations(obs_list):
        raise ValueError("Invalid observation list format")

    generator.generate_config(
        args.template,
        obs_list,
        additional_context,
        args.output
    )

    print(f"Generated configuration saved to {args.output}")


if __name__ == "__main__":
    main()
