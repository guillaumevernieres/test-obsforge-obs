import unittest
import tempfile
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from marine_obs_config import MarineObsConfigGenerator


class TestMarineObsConfigGenerator(unittest.TestCase):
    """Test cases for the MarineObsConfigGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = os.path.join(self.temp_dir, 'templates')
        os.makedirs(self.template_dir)

        # Create a simple test template
        self.test_template = """
observations:
  count: {{ obs_count }}
  types: {{ obs_types|list }}
  details:
{% for obs in observations %}
  - type: {{ obs.type }}
    file: {{ obs.file }}
    variables: {{ obs.variables|list }}
{% endfor %}
"""
        template_file = os.path.join(self.template_dir, 'test_template.yaml')
        with open(template_file, 'w') as f:
            f.write(self.test_template)

        self.generator = MarineObsConfigGenerator(self.template_dir)

        # Test observations
        self.test_observations = [
            {
                "type": "sea_surface_temperature",
                "file": "sst_data.nc",
                "variables": ["temperature"],
                "observation_operator": "Identity"
            },
            {
                "type": "sea_surface_salinity",
                "file": "sss_data.nc",
                "variables": ["salinity"],
                "observation_operator": "Identity"
            }
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_observations(self):
        """Test observation loading and processing."""
        processed = self.generator.load_observations(self.test_observations)

        self.assertEqual(processed['obs_count'], 2)
        self.assertEqual(len(processed['obs_types']), 2)
        self.assertIn('sea_surface_temperature', processed['obs_types'])
        self.assertIn('sea_surface_salinity', processed['obs_types'])

        # Check grouping by type
        self.assertEqual(len(processed['observations_by_type']), 2)
        obs_sst = processed['observations_by_type']['sea_surface_temperature']
        self.assertEqual(len(obs_sst), 1)

    def test_validate_observations_valid(self):
        """Test validation with valid observations."""
        is_valid = self.generator.validate_observations(self.test_observations)
        self.assertTrue(is_valid)

    def test_validate_observations_invalid(self):
        """Test validation with invalid observations."""
        invalid_obs = [
            {
                "type": "sea_surface_temperature",
                # missing required fields
            }
        ]
        self.assertFalse(self.generator.validate_observations(invalid_obs))

    def test_generate_config(self):
        """Test configuration generation."""
        config = self.generator.generate_config(
            'test_template.yaml',
            self.test_observations
        )

        self.assertIn('observations:', config)
        self.assertIn('count: 2', config)
        self.assertIn('sea_surface_temperature', config)
        self.assertIn('sst_data.nc', config)

    def test_generate_config_with_output_file(self):
        """Test configuration generation with file output."""
        output_file = os.path.join(self.temp_dir, 'output_config.yaml')

        config = self.generator.generate_config(
            'test_template.yaml',
            self.test_observations,
            output_file=output_file
        )

        self.assertTrue(os.path.exists(output_file))
        with open(output_file, 'r') as f:
            file_content = f.read()

        self.assertEqual(config, file_content)

    def test_template_not_found(self):
        """Test handling of missing template."""
        with self.assertRaises(FileNotFoundError):
            self.generator.generate_config(
                'nonexistent_template.yaml',
                self.test_observations
            )


if __name__ == '__main__':
    unittest.main()
