# Marine Observation 3DVAR Configuration Generator
# Makefile for development and testing

.PHONY: help install test example example-jcb clean lint init-submodules

# Default target
help:
	@echo "Available targets:"
	@echo "  install          - Install Python dependencies"
	@echo "  init-submodules  - Initialize JCB-GDAS submodule"
	@echo "  test             - Run unit tests"
	@echo "  example          - Run example with custom templates"
	@echo "  example-jcb      - Run example with JCB-GDAS templates"
	@echo "  lint             - Run code linting"
	@echo "  clean            - Clean generated files"
	@echo "  help             - Show this help message"

# Initialize submodules
init-submodules:
	git submodule update --init --recursive

# Install dependencies
install: init-submodules
	pip install -r requirements.txt

# Run unit tests
test:
	python -m pytest tests/ -v

# Run example with custom templates
example:
	python example.py

# Run example with JCB-GDAS templates
example-jcb:
	python example_jcb.py

# Run linting
lint:
	python -m flake8 src/ tests/ example.py example_jcb.py explore_templates.py --max-line-length=79

# Clean generated files
clean:
	rm -f config/generated_*.yaml
	rm -f config/example_observations.json
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete

# Development setup
dev-install: install
	pip install pytest flake8
