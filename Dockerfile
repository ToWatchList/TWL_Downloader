# Use a lightweight Python 3.12 base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install uv, a fast Python package installer
RUN pip install uv

# Copy the requirements file and install dependencies using uv
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# Copy the application script and entrypoint
COPY twl_downloader.py .
COPY entrypoint.sh .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

# Define volumes for persistent storage
# /downloads is for the videos
# /config is for yt-dlp cache and config
VOLUME ["/downloads", "/config"]

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]
