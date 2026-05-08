FROM python:3.13-slim AS base
WORKDIR /app

# Stage 1a: Python Dependencies Builder
# This stage installs uv and creates a virtual environment with runtime dependencies.
# Can be built in parallel with system-deps stage.
FROM base AS python-builder

# Copy only the requirements file first to leverage Docker's layer caching.
COPY requirements.txt .

# Install uv, create venv, and install dependencies in a single layer.
# Using cache mount for pip to speed up rebuilds.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv && \
    uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python -r requirements.txt

# Stage 1b: Deno Installer
# This stage installs Deno for EJS support.
# Can be built in parallel with python-builder stage.
FROM base AS deno-installer

# Install Deno for EJS (External JavaScript) support.
# Deno is a JavaScript runtime needed for yt-dlp's EJS challenge solver scripts.
# Using cache mounts for apt to speed up rebuilds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl unzip && \
    # Install Deno for EJS support
    curl -fsSL https://deno.land/x/install/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Test Dependencies Builder
# This stage builds on python-builder and adds test dependencies.
FROM python-builder AS test-deps-builder

# Install dev dependencies into the virtual environment.
# Using cache mount for pip to speed up rebuilds.
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    uv pip install --python /opt/venv/bin/python -r requirements-dev.txt

# Stage 3: The Tester
# This stage combines test dependencies with ffmpeg for running tests.
FROM test-deps-builder AS tester

# Install ffmpeg for video analysis in tests.
# Using cache mounts for apt to speed up rebuilds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the application and test code.
COPY . .

# Set the PATH to use the virtual environment's python and packages.
ENV PATH="/opt/venv/bin:$PATH"

# Set the command to run tests. PYTHONPATH is needed so pytest can find the module.
CMD ["/bin/sh", "-c", "PYTHONPATH=. pytest"]

# Stage 4: The Final Image
# This stage combines the pre-built venv and system dependencies into a clean, slim image.
FROM base AS final

# Install ffmpeg for yt-dlp video processing.
# Using cache mounts for apt to speed up rebuilds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy Deno from the deno-installer stage.
COPY --from=deno-installer /root/.deno /root/.deno

# Copy the virtual environment from the python-builder stage.
COPY --from=python-builder /opt/venv /opt/venv

# Copy the uv executable from the python-builder stage.
COPY --from=python-builder /usr/local/bin/uv /usr/local/bin/uv

# Copy the application scripts.
COPY twl_downloader.py entrypoint.sh ./

# Add the virtual environment's bin directory to the PATH, plus Deno.
# This ensures that the script uses the Python and packages from the venv,
# and that yt-dlp can access the JavaScript runtime for EJS.
ENV PATH="/opt/venv/bin:/root/.deno/bin:$PATH"

# Define volumes for persistent storage.
VOLUME ["/downloads", "/config", "/tmp"]

# Set the entrypoint.
ENTRYPOINT ["./entrypoint.sh"]
