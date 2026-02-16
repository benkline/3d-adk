.PHONY: help install develop test build docker-build docker-run docker-compose-up clean release

# Default target
help:
	@echo "3D-ADK Makefile - Common development and deployment tasks"
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install package in editable mode (development)"
	@echo "  make develop        - Alias for install"
	@echo "  make test           - Run test suite (pytest)"
	@echo "  make test-fast      - Run tests in parallel"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo ""
	@echo "Building & Packaging:"
	@echo "  make build          - Build Python distribution (wheel + source)"
	@echo "  make clean          - Remove build artifacts (dist/, build/, *.egg-info)"
	@echo "  make release        - Build and show release artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image (3d-adk:latest)"
	@echo "  make docker-run     - Run Docker container interactively"
	@echo "  make docker-shell   - Run Docker container with shell access"
	@echo "  make docker-test    - Run tests in Docker"
	@echo ""
	@echo "Utilities:"
	@echo "  make version        - Show application version"
	@echo "  make lint           - Run code quality checks (requires pylint/flake8)"

# Development installation
install:
	pip install -e ".[dev]"

develop: install

# Test targets
test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -n auto

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Build distribution packages
build: clean
	pip install build
	python -m build

release: build
	@echo ""
	@echo "Release artifacts created in dist/:"
	@ls -lh dist/

clean:
	rm -rf build/ dist/ src/*.egg-info 3d_adk.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Docker targets
docker-build:
	docker build -t 3d-adk:latest .
	@echo ""
	@echo "Docker image built: 3d-adk:latest"

docker-run: docker-build
	docker run -it --rm \
		--env-file .env \
		-v ./projects:/app/projects \
		-v ./sessions:/app/sessions \
		3d-adk:latest

docker-shell: docker-build
	docker run -it --rm \
		--env-file .env \
		-v ./projects:/app/projects \
		-v ./sessions:/app/sessions \
		3d-adk:latest \
		/bin/bash

docker-test: docker-build
	docker run --rm \
		3d-adk:latest \
		pytest /app/tests/ -v

# Docker Compose targets
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f 3d-adk

# Utility targets
version:
	@python -c "from src import __version__; print(f'3D-ADK v{__version__}')"

verify: test
	@echo ""
	@echo "✓ Tests passed"
	@pip install -e ".[dev]" > /dev/null 2>&1
	@3d-adk --version
	@echo "✓ CLI installation verified"

# CI/CD simulation
ci: clean test build
	@echo ""
	@echo "✓ CI pipeline passed (clean, test, build)"
