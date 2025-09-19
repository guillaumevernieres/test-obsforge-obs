import unittest
import tempfile
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from marine_obs_config import MarineObsConfigGenerator, JCBGDASTemplateManager


class TestJCBGDASTemplateManager(unittest.TestCase):
    """Test cases for the JCBGDASTemplateManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.jcb_path = os.path.join(self.temp_dir, 'jcb-gdas')
        self.marine_path = os.path.join(
            self.jcb_path, 'observations', 'marine'
        )
        os.makedirs(self.marine_path)

        # Create mock template files
        template_files = [
            'sst_viirs_npp_l3u.yaml.j2',
            'sss_smap_l2.yaml.j2',
            'insitu_temp_profile_argo.yaml.j2',
            'rads_adt_3a.yaml.j2'
        ]

        for template_file in template_files:
            template_path = os.path.join(self.marine_path, template_file)
            with open(template_path, 'w') as f:
                f.write("# Mock JCB template\nobservation: {{ obs_type }}")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test JCB manager initialization."""
        manager = JCBGDASTemplateManager(self.jcb_path)
        self.assertTrue(manager.marine_templates_path.exists())

    def test_list_available_templates(self):
        """Test listing available templates."""
        manager = JCBGDASTemplateManager(self.jcb_path)
        templates = manager.list_available_templates()

        self.assertEqual(len(templates), 4)
        self.assertIn('sst_viirs_npp_l3u', templates)
        self.assertIn('sss_smap_l2', templates)
        self.assertIn('insitu_temp_profile_argo', templates)
        self.assertIn('rads_adt_3a', templates)

    def test_match_observation_exact(self):
        """Test exact observation type matching."""
        manager = JCBGDASTemplateManager(self.jcb_path)

        # Test exact matches
        self.assertEqual(
            manager.match_observation_to_template('sst_viirs_npp_l3u'),
            'sst_viirs_npp_l3u'
        )
        self.assertEqual(
            manager.match_observation_to_template('sss_smap_l2'),
            'sss_smap_l2'
        )

    def test_match_observation_not_found(self):
        """Test observation type not found."""
        manager = JCBGDASTemplateManager(self.jcb_path)

        result = manager.match_observation_to_template('nonexistent_type')
        self.assertIsNone(result)

    def test_initialization_missing_path(self):
        """Test initialization with missing JCB path."""
        nonexistent_path = os.path.join(self.temp_dir, 'nonexistent')

        with self.assertRaises(FileNotFoundError):
            JCBGDASTemplateManager(nonexistent_path)


class TestMarineObsConfigGenerator(unittest.TestCase):
    """Test cases for the MarineObsConfigGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.jcb_path = os.path.join(self.temp_dir, 'jcb-gdas')
        self.marine_path = os.path.join(
            self.jcb_path, 'observations', 'marine'
        )
        os.makedirs(self.marine_path)

        # Create mock template files
        template_content = """
# Mock JCB template for {{ observation_from_jcb }}
observations:
  observers:
  - obs space:
      name: "{{ observation_from_jcb }}"
      obsdatain:
        engine:
          type: H5File
          obsfile: "mock_{{ observation_from_jcb }}.nc"
      simulated variables: [mock_variable]
    obs operator:
      name: Identity
    obs error:
      covariance model: diagonal
"""

        template_files = ['sst_viirs_npp_l3u.yaml.j2', 'sss_smap_l2.yaml.j2']
        for template_file in template_files:
            template_path = os.path.join(self.marine_path, template_file)
            with open(template_path, 'w') as f:
                f.write(template_content)

        self.generator = MarineObsConfigGenerator(self.jcb_path)

        # Test observations in different formats
        self.test_obs_strings = ['sst_viirs_npp_l3u', 'sss_smap_l2']
        self.test_obs_dicts = [
            {'type': 'sst_viirs_npp_l3u'},
            {'type': 'sss_smap_l2'}
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_validate_observations_strings(self):
        """Test validation with string observation types."""
        is_valid = self.generator.validate_observations(self.test_obs_strings)
        self.assertTrue(is_valid)

    def test_validate_observations_dicts(self):
        """Test validation with dictionary observation types."""
        is_valid = self.generator.validate_observations(self.test_obs_dicts)
        self.assertTrue(is_valid)

    def test_validate_observations_mixed(self):
        """Test validation with mixed formats."""
        mixed_obs = ['sst_viirs_npp_l3u', {'type': 'sss_smap_l2'}]
        is_valid = self.generator.validate_observations(mixed_obs)
        self.assertTrue(is_valid)

    def test_validate_observations_invalid(self):
        """Test validation with invalid observations."""
        invalid_obs = [123, {'no_type_field': 'value'}]
        is_valid = self.generator.validate_observations(invalid_obs)
        self.assertFalse(is_valid)

    def test_generate_config_from_jcb_strings(self):
        """Test JCB configuration generation with string observations."""
        output_file = os.path.join(self.temp_dir, 'test_config.yaml')

        config = self.generator.generate_config_from_jcb(
            obs_list=self.test_obs_strings,
            output_file=output_file
        )

        self.assertIn('observations:', config)
        self.assertIn('observers:', config)
        self.assertTrue(os.path.exists(output_file))

    def test_generate_config_from_jcb_dicts(self):
        """Test JCB configuration generation with dict observations."""
        config = self.generator.generate_config_from_jcb(
            obs_list=self.test_obs_dicts
        )

        self.assertIn('observations:', config)
        self.assertIn('observers:', config)

    def test_generate_config_with_context(self):
        """Test JCB configuration generation with additional context."""
        context = {
            'window_begin': '2024-01-01T00:00:00Z',
            'model_name': 'MOM6'
        }

        config = self.generator.generate_config_from_jcb(
            obs_list=self.test_obs_strings,
            additional_context=context
        )

        self.assertIn('observations:', config)


if __name__ == '__main__':
    unittest.main()
