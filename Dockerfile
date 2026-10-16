FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg build-essential pkg-config libcairo2-dev libpango1.0-dev libglib2.0-dev \
        fontconfig fonts-inter fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /studio
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# usage: docker run --rm -v "$PWD":/studio -w /studio IMAGE python run_studio.py --script my.json --audio vo.mp3
ENTRYPOINT ["python", "run_studio.py"]
