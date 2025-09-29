# Stage 1: The Builder
# This stage installs uv and then creates a virtual environment with all dependencies.
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv, which we will use for package management and also copy to the final image.
RUN pip install uv

# Create a virtual environment for the application.
RUN uv venv /opt/venv

# Copy only the requirements file and install dependencies into the venv.
# This leverages Docker's layer caching.
COPY requirements.txt .
RUN uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt


# Stage 2: The Tester
# This stage builds on the builder and adds test dependencies.
FROM builder AS tester

WORKDIR /app

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
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy the uv executable from the builder stage.
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy the application scripts.
COPY twl_downloader.py .
COPY entrypoint.sh .

# Make the entrypoint script executable.
RUN chmod +x entrypoint.sh

# Create a non-root user for security.
RUN useradd --create-home appuser
USER appuser

# Add the virtual environment's bin directory to the PATH.
# This ensures that the script uses the Python and packages from the venv.
ENV PATH="/opt/venv/bin:$PATH"

# Define volumes for persistent storage.
VOLUME ["/downloads", "/config"]

# Set the entrypoint.
ENTRYPOINT ["./entrypoint.sh"]