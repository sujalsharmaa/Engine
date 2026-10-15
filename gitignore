# Use stable Python Linux image
FROM python:3.11-slim

# Prevent interactive prompts during apt installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by Manim, OpenCV, and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    pkg-config \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project code into the container
COPY . /app

# Default command to run the studio pipeline
ENTRYPOINT ["python", "run_studio.py"]