# Makefile for ToWatchList Downloader

# Define variables
IMAGE_NAME := towatchlist-downloader
ENV_FILE := .env

# Phony targets
.PHONY: all build run run-local test lint help

# Default target
all: help

# Build the Docker image
build:
	@echo "Building Docker image..."
	@docker build -t $(IMAGE_NAME) .

# Run the application in a Docker container
# Expects a .env file with TWL_API_KEY
run:
	@echo "Running application in Docker..."
	@docker run --rm \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/videos":/downloads \
		-v "$(shell pwd)/config":/config \
		--name $(IMAGE_NAME) \
		$(IMAGE_NAME)

# Run the application locally
# Expects a .env file with TWL_API_KEY
run-local:
	@echo "Running application locally..."
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "ERROR: .env file not found. Please create one from .env.example."; \
		exit 1; \
	fi
	@set -a && . $(ENV_FILE) && set +a && \
	python3 twl_downloader.py

# Run the test suite
test:
	@echo "Running tests..."
	@uv pip install --system -r requirements.txt -r requirements-dev.txt > /dev/null
	@PYTHONPATH=. pytest

# Lint the code
lint:
	@echo "Linting code..."
	@uv pip install --system -r requirements-dev.txt > /dev/null
	@flake8 twl_downloader.py test_twl_downloader.py

# Help target
help:
	@echo "Available commands:"
	@echo "  build      - Build the Docker image"
	@echo "  run        - Run the application in a Docker container"
	@echo "  run-local  - Run the application locally"
	@echo "  test       - Run the test suite"
	@echo "  lint       - Lint the Python code"
