FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY bot.py .
COPY scripts/ ./scripts/

# models/ and wikidata_big/ are mounted as volumes — not baked into the image
# to keep the image size manageable and allow model updates without rebuilds.

CMD ["python", "bot.py"]
