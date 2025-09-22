#!/usr/bin/env python3
"""
Test suite for the ObsForge Cycle Processor application.

Creates mock obsForge directory structures and tests the scanning,
observation mapping, and configuration generation functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
import yaml
import shutil

# Add both src and apps to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps'))

from obsforge_cycle_processor import (
    ObsForgeScanner,
    ObsForgeCycleProcessor
)


class TestObsForgeScanner(unittest.TestCase):
    """Test cases for the ObsForgeScanner class."""

    def setUp(self):
        """Set up test fixtures with mock obsForge directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.obsforge_root = Path(self.temp_dir) / "obsforge_root"

        # Create the expected directory structure
        self.obsforge_root.mkdir(parents=True)        # Create test cycles
        self.test_cycles = [
            ('gdas', '20210831', '18'),
            ('gfs', '20210831', '18'),
            ('gdas', '20210901', '00'),
            ('gfs', '20210901', '06')
        ]

        # Create cycle directories and populate with mock data
        for cycle_type, date, hour in self.test_cycles:
            cycle_dir = self.obsforge_root / f"{cycle_type}.{date}" / hour / "ocean"
            cycle_dir.mkdir(parents=True)

            # Create observation type directories with mock files
            obs_types = {
                'adt': [
                    f'{cycle_type}.t{hour}z.rads_adt_3a.tm00.nc',
                    f'{cycle_type}.t{hour}z.rads_adt_3b.tm00.nc',
                    f'{cycle_type}.t{hour}z.rads_adt_c2.tm00.nc',
                    f'{cycle_type}.t{hour}z.rads_adt_j3.tm00.nc',
                    f'{cycle_type}.t{hour}z.rads_adt_sa.tm00.nc'
                ],
                'sst': [
                    f'{cycle_type}.t{hour}z.sst_viirs.tm00.nc',
                    f'{cycle_type}.t{hour}z.sst_avhrr.tm00.nc'
                ],
                'sss': [
                    f'{cycle_type}.t{hour}z.sss_smap.tm00.nc'
                ],
                'icec': [
                    f'{cycle_type}.t{hour}z.icec_amsr2.tm00.nc'
                ]
            }

            for obs_type, files in obs_types.items():
                obs_dir = cycle_dir / obs_type
                obs_dir.mkdir()

                # Create mock data files
                for filename in files:
                    mock_file = obs_dir / filename
                    mock_file.write_text("# Mock NetCDF data file\n")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test scanner initialization."""
        scanner = ObsForgeScanner(str(self.obsforge_root))
        self.assertTrue(scanner.obsforge_root.exists())
        self.assertEqual(scanner.obsforge_root, self.obsforge_root)

    def test_initialization_missing_obsforge(self):
        """Test initialization with missing obsforge directory."""
        nonexistent_obsforge_root = (Path(self.temp_dir) /
                                     "nonexistent_obsforge_root")

        with self.assertRaises(FileNotFoundError):
            ObsForgeScanner(str(nonexistent_obsforge_root))

    def test_find_cycles(self):
        """Test finding all available cycles."""
        scanner = ObsForgeScanner(str(self.obsforge_root))
        cycles = scanner.find_cycles()

        self.assertEqual(len(cycles), 4)

        # Check that all test cycles are found
        for expected_cycle in self.test_cycles:
            self.assertIn(expected_cycle, cycles)

        # Verify cycles are sorted
        self.assertEqual(cycles, sorted(cycles))

    def test_scan_cycle_observations(self):
        """Test scanning observations for a specific cycle."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        # Test GDAS cycle
        obs_files = scanner.scan_cycle_observations('gdas', '20210831', '18')

        # Should find all 4 observation types
        self.assertEqual(len(obs_files), 4)
        self.assertIn('adt', obs_files)
        self.assertIn('sst', obs_files)
        self.assertIn('sss', obs_files)
        self.assertIn('icec', obs_files)

        # Check ADT files (should have 5 files)
        self.assertEqual(len(obs_files['adt']), 5)
        self.assertTrue(any('3a' in f for f in obs_files['adt']))
        self.assertTrue(any('3b' in f for f in obs_files['adt']))
        self.assertTrue(any('c2' in f for f in obs_files['adt']))
        self.assertTrue(any('j3' in f for f in obs_files['adt']))
        self.assertTrue(any('sa' in f for f in obs_files['adt']))

        # Check SST files (should have 2 files)
        self.assertEqual(len(obs_files['sst']), 2)
        self.assertTrue(any('viirs' in f for f in obs_files['sst']))
        self.assertTrue(any('avhrr' in f for f in obs_files['sst']))

    def test_scan_nonexistent_cycle(self):
        """Test scanning observations for nonexistent cycle."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        obs_files = scanner.scan_cycle_observations('gdas', '20210101', '00')

        # Should return empty dictionary
        self.assertEqual(obs_files, {})

    def test_map_adt_observations(self):
        """Test mapping ADT files to JCB types."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        adt_files = [
            'gdas.t18z.rads_adt_3a.tm00.nc',
            'gdas.t18z.rads_adt_3b.tm00.nc',
            'gdas.t18z.rads_adt_c2.tm00.nc'
        ]

        jcb_types = scanner.map_obsforge_to_jcb_types('adt', adt_files)

        expected_types = ['rads_adt_3a', 'rads_adt_3b', 'rads_adt_c2']
        self.assertEqual(sorted(jcb_types), sorted(expected_types))

    def test_map_sst_observations(self):
        """Test mapping SST files to JCB types."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        sst_files = [
            'gdas.t18z.sst_viirs.tm00.nc',
            'gdas.t18z.sst_avhrr.tm00.nc'
        ]

        jcb_types = scanner.map_obsforge_to_jcb_types('sst', sst_files)

        expected_types = ['sst_viirs_npp_l3u', 'sst_avhrr_metop_l3u']
        self.assertEqual(sorted(jcb_types), sorted(expected_types))

    def test_map_sss_observations(self):
        """Test mapping SSS files to JCB types."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        sss_files = ['gdas.t18z.sss_smap.tm00.nc']

        jcb_types = scanner.map_obsforge_to_jcb_types('sss', sss_files)

        expected_types = ['sss_smap_l2']
        self.assertEqual(jcb_types, expected_types)

    def test_map_icec_observations(self):
        """Test mapping sea ice concentration files to JCB types."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        icec_files = ['gdas.t18z.icec_amsr2.tm00.nc']

        jcb_types = scanner.map_obsforge_to_jcb_types('icec', icec_files)

        expected_types = ['icec_generic']
        self.assertEqual(jcb_types, expected_types)

    def test_map_unknown_observations(self):
        """Test mapping unknown observation type."""
        scanner = ObsForgeScanner(str(self.obsforge_root))

        jcb_types = scanner.map_obsforge_to_jcb_types('unknown', ['test.nc'])

        self.assertEqual(jcb_types, [])


class TestObsForgeCycleProcessor(unittest.TestCase):
    """Test cases for the ObsForgeCycleProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.obsforge_root = Path(self.temp_dir) / "obsforge_root"
        self.output_dir = Path(self.temp_dir) / "output"

        # Create mock JCB-GDAS directory structure
        self.jcb_path = Path(self.temp_dir) / 'jcb-gdas'
        self.marine_path = self.jcb_path / 'observations' / 'marine'
        self.marine_path.mkdir(parents=True)

        # Create mock templates directory
        self.template_dir = Path(self.temp_dir) / 'templates'
        self.template_dir.mkdir()

        # Create mock obsForge structure (simplified)
        self.obsforge_root.mkdir(parents=True)

        # Create one test cycle
        cycle_dir = self.obsforge_root / "gdas.20210831" / "18" / "ocean"
        cycle_dir.mkdir(parents=True)        # Add some observation files
        adt_dir = cycle_dir / "adt"
        adt_dir.mkdir()
        (adt_dir / "gdas.t18z.rads_adt_3a.tm00.nc").write_text("mock data")

        sst_dir = cycle_dir / "sst"
        sst_dir.mkdir()
        (sst_dir / "gdas.t18z.sst_viirs.tm00.nc").write_text("mock data")

        # Create mock JCB templates
        jcb_template_content = """
# Mock JCB template for {{ observation_from_jcb }}
observations:
  observers:
  - obs space:
      name: "{{ observation_from_jcb }}"
      obsdatain:
        engine:
          type: H5File
          obsfile: "{{ marine_obsdatain_path }}/mock_{{ observation_from_jcb }}.nc"
      simulated variables: [mock_variable]
    obs operator:
      name: Identity
    obs error:
      covariance model: diagonal
"""

        jcb_templates = ['rads_adt_3a.yaml.j2', 'sst_viirs_npp_l3u.yaml.j2']
        for template_name in jcb_templates:
            template_path = self.marine_path / template_name
            template_path.write_text(jcb_template_content)

        # Create mock 3DVAR template
        template_3dvar_content = """
cost_function:
  cost_type: 3D-Var
  window_begin: "{{ window_begin | default('2024-01-01T00:00:00Z') }}"
  window_length: "{{ window_length | default('PT6H') }}"

  observations:
    observers:
{% for obs_config in obs_configs %}
{{ obs_config | indent(6, True) }}
{% endfor %}

output:
  filename: "{{ output_filename | default('analysis.nc') }}"
"""

        template_3dvar_path = self.template_dir / 'jedi_3dvar_template.yaml.j2'
        template_3dvar_path.write_text(template_3dvar_content)

        # Create mock job card template
        job_card_template_content = """#!/bin/bash
#SBATCH --job-name=3dvar_{{ cycle_name }}
#SBATCH --output=3dvar_{{ cycle_name }}.%j.out
#SBATCH --error=3dvar_{{ cycle_name }}.%j.err
#SBATCH --time={{ job_time | default('02:00:00') }}
#SBATCH --ntasks={{ ntasks | default(24) }}
#SBATCH --partition={{ partition | default('analysis') }}

# Marine 3DVAR job for {{ cycle_name }}
# Generated observations: {{ jcb_obs_types | join(', ') }}

# Environment setup
export CYCLE_TYPE={{ cycle_type }}
export CYCLE_DATE={{ cycle_date }}
export CYCLE_HOUR={{ cycle_hour }}
export CONFIG_FILE="config_{{ cycle_name }}.yaml"

# Data paths
export OBSFORGE_ROOT="{{ obsforge_root }}"
export CYCLE_DATA_DIR="${OBSFORGE_ROOT}/{{ cycle_type }}.{{ cycle_date }}/{{ cycle_hour }}/ocean"

# Run directory
RUNDIR="run_{{ cycle_name }}"
mkdir -p $RUNDIR
cd $RUNDIR

# Copy configuration
cp ../$CONFIG_FILE .

# Link observation data
{% for obs_category in obs_categories %}
ln -sf ${CYCLE_DATA_DIR}/{{ obs_category }}/*.nc .
{% endfor %}

echo "Job card for {{ cycle_name }} executed"
"""

        job_card_template_path = self.template_dir / 'job_card.sh.j2'
        job_card_template_path.write_text(job_card_template_content)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test processor initialization."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        self.assertTrue(processor.output_dir.exists())
        self.assertIsInstance(processor.scanner, ObsForgeScanner)

    def test_process_cycle(self):
        """Test processing a single cycle."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        result = processor.process_cycle('gdas', '20210831', '18')

        # Check result structure
        self.assertEqual(result['cycle'], 'gdas.20210831.18')
        self.assertIn('observations', result)
        self.assertIn('jcb_types', result)
        self.assertIn('job_card', result)
        self.assertIn('config_file', result)

        # Check that observations were found
        self.assertIn('adt', result['observations'])
        self.assertIn('sst', result['observations'])

        # Check that JCB types were mapped
        self.assertIn('rads_adt_3a', result['jcb_types'])
        self.assertIn('sst_viirs_npp_l3u', result['jcb_types'])

        # Check that files were created
        self.assertTrue(Path(result['job_card']).exists())
        self.assertTrue(Path(result['config_file']).exists())

    def test_job_card_generation(self):
        """Test job card content generation."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        result = processor.process_cycle('gdas', '20210831', '18')
        job_card_path = Path(result['job_card'])

        # Read job card content
        job_card_content = job_card_path.read_text()

        # Check for expected content
        self.assertIn('#!/bin/bash', job_card_content)
        self.assertIn('#SBATCH', job_card_content)
        self.assertIn('gdas.20210831.18', job_card_content)
        self.assertIn('CYCLE_TYPE=gdas', job_card_content)
        self.assertIn('CYCLE_DATE=20210831', job_card_content)
        self.assertIn('CYCLE_HOUR=18', job_card_content)

        # Check that file is executable
        file_mode = job_card_path.stat().st_mode
        self.assertTrue(file_mode & 0o111)  # Check execute permission

    def test_config_generation(self):
        """Test 3DVAR configuration generation."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        result = processor.process_cycle('gdas', '20210831', '18')
        config_path = Path(result['config_file'])

        # Read and parse config
        config_content = config_path.read_text()
        config_data = yaml.safe_load(config_content)

        # Check for expected structure
        self.assertIn('cost_function', config_data)
        self.assertIn('observations', config_data['cost_function'])
        self.assertIn('observers', config_data['cost_function']['observations'])

        # Check that observations are present
        observers = config_data['cost_function']['observations']['observers']
        self.assertGreater(len(observers), 0)

        # Check output configuration
        self.assertIn('output', config_data)
        self.assertIn('analysis_gdas.20210831.18.nc',
                      config_data['output']['filename'])

    def test_process_all_cycles(self):
        """Test processing all available cycles."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        summary = processor.process_all_cycles()

        # Check summary structure
        self.assertIn('total_cycles', summary)
        self.assertIn('processed_cycles', summary)
        self.assertIn('failed_cycles', summary)
        self.assertIn('cycles', summary)

        # Should have processed 1 cycle
        self.assertEqual(summary['total_cycles'], 1)
        self.assertEqual(summary['processed_cycles'], 1)
        self.assertEqual(summary['failed_cycles'], 0)

    def test_empty_cycle_handling(self):
        """Test handling of cycles with no observations."""
        # Create empty cycle directory
        empty_cycle_dir = (self.obsforge_root / "gfs.20210901" /
                          "00" / "ocean")
        empty_cycle_dir.mkdir(parents=True)

        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        result = processor.process_cycle('gfs', '20210901', '00')

        # Should handle empty cycle gracefully
        self.assertEqual(result['cycle'], 'gfs.20210901.00')
        self.assertEqual(result['observations'], {})
        self.assertEqual(result['jcb_types'], [])
        self.assertIsNone(result['job_card'])
        self.assertIsNone(result['config_file'])


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.obsforge_root = Path(self.temp_dir) / "obsforge_root"
        self.output_dir = Path(self.temp_dir) / "output"

        # Create a complete test environment
        self._create_complete_obsforge_structure()
        self._create_jcb_templates()
        self._create_custom_templates()

    def tearDown(self):
        """Clean up integration test environment."""
        shutil.rmtree(self.temp_dir)

    def _create_complete_obsforge_structure(self):
        """Create a complete obsForge directory structure."""
        obsforge_root = self.obsforge_root

        # Multiple cycles with varying observation availability
        cycles_data = [
            ('gdas', '20210831', '18', ['adt', 'sst', 'sss']),
            ('gfs', '20210831', '18', ['adt', 'sst']),
            ('gdas', '20210901', '00', ['adt', 'sss', 'icec']),
            ('gfs', '20210901', '06', ['sst', 'icec'])
        ]

        for cycle_type, date, hour, obs_types in cycles_data:
            cycle_dir = obsforge_root / f"{cycle_type}.{date}" / hour / "ocean"
            cycle_dir.mkdir(parents=True)

            for obs_type in obs_types:
                obs_dir = cycle_dir / obs_type
                obs_dir.mkdir()

                # Create realistic file names
                if obs_type == 'adt':
                    files = [f'{cycle_type}.t{hour}z.rads_adt_{sat}.tm00.nc'
                            for sat in ['3a', 'c2', 'j3']]
                elif obs_type == 'sst':
                    files = [f'{cycle_type}.t{hour}z.sst_viirs.tm00.nc']
                elif obs_type == 'sss':
                    files = [f'{cycle_type}.t{hour}z.sss_smap.tm00.nc']
                elif obs_type == 'icec':
                    files = [f'{cycle_type}.t{hour}z.icec_amsr2.tm00.nc']

                for filename in files:
                    (obs_dir / filename).write_text("mock data")

    def _create_jcb_templates(self):
        """Create mock JCB-GDAS templates."""
        self.jcb_path = Path(self.temp_dir) / 'jcb-gdas'
        marine_path = self.jcb_path / 'observations' / 'marine'
        marine_path.mkdir(parents=True)

        # Template content
        template_content = """
observations:
  observers:
  - obs space:
      name: "{{ observation_from_jcb }}"
      obsdatain:
        engine:
          type: H5File
          obsfile: "{{ marine_obsdatain_path }}/{{ observation_from_jcb }}.nc"
      simulated variables: [test_var]
    obs operator:
      name: Identity
"""

        # Create templates for all observation types used in tests
        templates = [
            'rads_adt_3a.yaml.j2', 'rads_adt_c2.yaml.j2', 'rads_adt_j3.yaml.j2',
            'sst_viirs_npp_l3u.yaml.j2', 'sss_smap_l2.yaml.j2', 'icec_generic.yaml.j2'
        ]

        for template_name in templates:
            (marine_path / template_name).write_text(template_content)

    def _create_custom_templates(self):
        """Create custom 3DVAR template."""
        self.template_dir = Path(self.temp_dir) / 'templates'
        self.template_dir.mkdir()

        template_content = """
cost_function:
  cost_type: 3D-Var
  window_begin: "{{ window_begin }}"
  window_length: "{{ window_length }}"

  observations:
    observers:
{% for obs_config in obs_configs %}
{{ obs_config | indent(6, True) }}
{% endfor %}

output:
  filename: "{{ output_filename }}"
  datadir: "{{ output_dir }}"
"""

        template_path = self.template_dir / 'jedi_3dvar_template.yaml.j2'
        template_path.write_text(template_content)

        # Create job card template
        job_card_template_content = """#!/bin/bash
#SBATCH --job-name=3dvar_{{ cycle_name }}
#SBATCH --output=3dvar_{{ cycle_name }}.%j.out
#SBATCH --error=3dvar_{{ cycle_name }}.%j.err

# Marine 3DVAR job for {{ cycle_name }}
# Generated observations: {{ jcb_obs_types | join(', ') }}

# Environment setup
export CYCLE_TYPE={{ cycle_type }}
export CYCLE_DATE={{ cycle_date }}
export CYCLE_HOUR={{ cycle_hour }}

# Data paths
export OBSFORGE_ROOT="{{ obsforge_root }}"

# Link observation data
{% for obs_category in obs_categories %}
ln -sf "${OBSFORGE_ROOT}/{{ cycle_type }}.{{ cycle_date }}/{{ cycle_hour }}/ocean/{{ obs_category }}/*.nc" .
{% endfor %}

echo "Job card for {{ cycle_name }} executed"
"""

        job_card_template_path = self.template_dir / 'job_card.sh.j2'
        job_card_template_path.write_text(job_card_template_content)

    def test_complete_workflow(self):
        """Test the complete end-to-end workflow."""
        processor = ObsForgeCycleProcessor(
            obsforge_comroot=str(self.obsforge_root),
            output_dir=str(self.output_dir),
            jcb_gdas_path=str(self.jcb_path),
            template_dir=str(self.template_dir)
        )

        # Process all cycles
        summary = processor.process_all_cycles()

        # Should process 4 cycles
        self.assertEqual(summary['total_cycles'], 4)
        self.assertEqual(summary['processed_cycles'], 4)
        self.assertEqual(summary['failed_cycles'], 0)

        # Check that output files were created in cycle-specific directories
        output_files = list(self.output_dir.rglob('*'))
        job_cards = [f for f in output_files if f.name.startswith('job_')]
        config_files = [f for f in output_files if f.name.startswith('config_')]

        self.assertEqual(len(job_cards), 4)
        self.assertEqual(len(config_files), 4)

        # Verify directory structure exists
        expected_dirs = [
            self.output_dir / 'gdas.20210831' / '18',
            self.output_dir / 'gfs.20210831' / '18',
            self.output_dir / 'gdas.20210901' / '00',
            self.output_dir / 'gfs.20210901' / '06'
        ]
        for expected_dir in expected_dirs:
            self.assertTrue(expected_dir.exists(),
                            f"Directory {expected_dir} should exist")

        # Verify one configuration in detail
        gdas_config_path = (self.output_dir / 'gdas.20210831' / '18' /
                            'config_gdas.20210831.18.yaml')
        self.assertTrue(gdas_config_path.exists())

        with open(gdas_config_path) as f:
            config_data = yaml.safe_load(f)

        # Should have observations section with multiple observers
        observers = config_data['cost_function']['observations']['observers']
        self.assertGreater(len(observers), 2)  # Should have adt, sst, sss


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)

    unittest.main(verbosity=2)
