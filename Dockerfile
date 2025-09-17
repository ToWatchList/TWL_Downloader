# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
