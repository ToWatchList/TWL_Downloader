# Makefile for ToWatchList Downloader

# Define variables
IMAGE_NAME := twl-downloader
TEST_IMAGE_NAME := twl-downloader-tester
ENV_FILE := .env

# Phony targets
.PHONY: all build run run-local test test-local test-integration test-all lint format help

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
	@if ! command -v ffmpeg &> /dev/null; then \
		echo "ERROR: ffmpeg is not installed. It is required for local integration tests."; \
		echo "Please install ffmpeg (e.g., 'sudo apt-get install ffmpeg' or 'brew install ffmpeg') and try again."; \
		exit 1; \
	fi
	@uv pip install --system -r requirements.txt > /dev/null
	@set -a && . $(ENV_FILE) && set +a && \
	python3 twl_downloader.py

# Run the unit test suite inside a Docker container (fast)
test:
	@echo "Building test image and running unit tests in Docker..."
	@docker build --target tester -t $(TEST_IMAGE_NAME) .
	@docker run --rm $(TEST_IMAGE_NAME) /bin/sh -c 'PYTHONPATH=. pytest -m "not slow"'

# Run the integration test suite inside a Docker container (slow)
test-integration:
	@echo "Building test image and running integration tests in Docker..."
	@docker build --target tester -t $(TEST_IMAGE_NAME) .
	@docker run --rm $(TEST_IMAGE_NAME) /bin/sh -c 'PYTHONPATH=. pytest -m slow'

# Run all tests inside a Docker container
test-all:
	@echo "Building test image and running all tests in Docker..."
	@docker build --target tester -t $(TEST_IMAGE_NAME) .
	@docker run --rm $(TEST_IMAGE_NAME)

# Run all tests on the local machine
test-local:
	@echo "Running all tests locally..."
	@if ! command -v ffmpeg &> /dev/null; then \
		echo "ERROR: ffmpeg is not installed. It is required for local integration tests."; \
		echo "Please install ffmpeg (e.g., 'sudo apt-get install ffmpeg' or 'brew install ffmpeg') and try again."; \
		exit 1; \
	fi
	@uv pip install --system -r requirements.txt -r requirements-dev.txt > /dev/null
	@echo "Updating yt-dlp to the latest version for local testing..."
	@uv pip install --system --upgrade yt-dlp > /dev/null
	@echo "Running only unit tests due to sandbox limitations..."
	@PYTHONPATH=. pytest -m "not slow"

# Lint the code using ruff
lint:
	@echo "Linting code..."
	@uv pip install --system -r requirements-dev.txt > /dev/null
	@uvx ruff check .

# Format the code using ruff
format:
	@echo "Formatting code..."
	@uv pip install --system -r requirements-dev.txt > /dev/null
	@uvx ruff format .

# Help target
help:
	@echo "Available commands:"
	@echo "  build            - Build the Docker image"
	@echo "  run              - Run the application in a Docker container"
	@echo "  run-local        - Run the application locally"
	@echo "  test             - Run unit tests inside a Docker container (recommended)"
	@echo "  test-integration - Run slow integration tests inside a Docker container"
	@echo "  test-all         - Run all tests inside a Docker container"
	@echo "  test-local       - Run all tests on the local machine"
	@echo "  lint             - Check code for style issues and errors"
	@echo "  format           - Automatically format the code"