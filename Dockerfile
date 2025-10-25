FROM python:3.13-slim AS base
WORKDIR /app

# Stage 1: The Builder
# This stage installs uv and then creates a virtual environment with all dependencies.
FROM base AS builder

# Install uv, which we will use for package management and also copy to the final image.
RUN pip install uv

# Create a virtual environment for the application.
RUN uv venv /opt/venv

# Copy only the requirements file and install dependencies into the venv.
# This leverages Docker's layer caching.
COPY requirements.txt .
RUN uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt

# Stage 2: The Tester
# This stage builds on the builder and adds test dependencies and ffmpeg.
FROM builder AS tester

# Install ffmpeg for video analysis in tests
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dev dependencies into the virtual environment
COPY requirements-dev.txt .
RUN uv pip install --python /opt/venv/bin/python --no-cache -r requirements-dev.txt

# Copy the application and test code
COPY . .

# Set the PATH to use the virtual environment's python and packages
ENV PATH="/opt/venv/bin:$PATH"

# Set the command to run tests. PYTHONPATH is needed so pytest can find the module.
CMD ["/bin/sh", "-c", "PYTHONPATH=. pytest"]

# Stage 3: The Final Image
# This stage copies the pre-built venv, the uv binary, and the app code into a clean image.
FROM base AS final

# Install ffmpeg (required by yt-dlp and Bun installation).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://bun.sh/install | bash

# Copy the virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy the uv executable from the builder stage.
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy the application scripts.
COPY twl_downloader.py entrypoint.sh ./

# Add the virtual environment's bin directory to the PATH.
# This ensures that the script uses the Python and packages from the venv.
ENV PATH="/opt/venv/bin:$PATH"

# Allow SABR/DRM downloads by default for the production image
# Can be overridden by setting SKIP_SABR_DRM_DOWNLOADS=true at runtime
ENV SKIP_SABR_DRM_DOWNLOADS=false

# Define volumes for persistent storage.
VOLUME ["/downloads", "/config", "/tmp"]

# Set the entrypoint.
ENTRYPOINT ["./entrypoint.sh"]
