# Makefile for ToWatchList Downloader

# Define variables
IMAGE_NAME := twl-downloader
TEST_IMAGE_NAME := twl-downloader-tester
ENV_FILE := .env

# Phony targets
.PHONY: all build run test test-local test-integration test-all lint format deploy-kodi deploy-kodi-or deploy-kodi-az help

# Default target
all: help

# Build the Docker image
build:
	@echo "Building Docker image..."
	@docker build -t $(IMAGE_NAME) .

# Build the Docker image
build-no-cache:
	@echo "Building Docker image without cache..."
	@docker build --no-cache -t $(IMAGE_NAME) .

# Run the application in a Docker container
# Expects a .env file with TWL_API_KEY
run:
	@echo "Running application in Docker..."
	@docker run --rm \
		--env-file $(ENV_FILE) \
		-v "/exos/video/Other/ToWatchList/":/downloads \
		-v "/exos/docker-data/config/appdata/twl_downloader/":/config \
		-v "/exos/tmp/":/tmp \
		--name $(IMAGE_NAME) \
		$(IMAGE_NAME)

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

# Deploy kodi.rebuild.sh to both Kodi hosts and set up /etc/cron.d
# vero-az requires tailscale SSH (tag:ssh) — add it in tailscaleACL.jsonc if unreachable
CRON_D_CONTENT := 10 * * * * osmc /home/osmc/kodi.rebuild.sh

deploy-kodi: deploy-kodi-or deploy-kodi-az

deploy-kodi-or:
	@echo "Deploying kodi.rebuild.sh to vero-or..."
	@scp kodi.rebuild.sh osmc@vero-or.local:/home/osmc/kodi.rebuild.sh
	@ssh osmc@vero-or.local chmod +x /home/osmc/kodi.rebuild.sh
	@ssh osmc@vero-or.local "echo '$(CRON_D_CONTENT)' | sudo tee /etc/cron.d/kodi-rebuild > /dev/null"
	@echo "vero-or: deployed and cron configured."

deploy-kodi-az:
	@echo "Deploying kodi.rebuild.sh to vero-az..."
	@scp kodi.rebuild.sh osmc@vero-az:/home/osmc/kodi.rebuild.sh
	@ssh osmc@vero-az chmod +x /home/osmc/kodi.rebuild.sh
	@ssh osmc@vero-az "echo '$(CRON_D_CONTENT)' | sudo tee /etc/cron.d/kodi-rebuild > /dev/null"
	@echo "vero-az: deployed and cron configured."

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
	@echo "  build-no-cache   - Build the Docker image without using cache"
	@echo "  run              - Run the application in a Docker container"
	@echo "  test             - Run unit tests inside a Docker container (recommended)"
	@echo "  test-integration - Run slow integration tests inside a Docker container"
	@echo "  test-all         - Run all tests inside a Docker container"
	@echo "  test-local       - Run all tests on the local machine"
	@echo "  lint             - Check code for style issues and errors"
	@echo "  format           - Automatically format the code"
	@echo "  deploy-kodi      - Deploy kodi.rebuild.sh to vero-or and vero-az + set up /etc/cron.d"
	@echo "  deploy-kodi-or   - Deploy to vero-or only"
	@echo "  deploy-kodi-az   - Deploy to vero-az only (requires tailscale SSH tag:ssh)"
