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
COPY extract/ ./extract/
COPY bot.py .
COPY scripts/ ./scripts/
COPY setup.sh run_db.sh .env.example ./

# Bundle Wikidata properties cache to avoid SPARQL fetch on first run
COPY extract_data/wikidata_properties_cache.json ./extract_data/

# models/ and wikidata_big/ are volume-mounted (or downloaded at runtime via entrypoint.sh)
# to keep the image size manageable and allow model updates without rebuilds.

CMD ["bash", "scripts/entrypoint.sh"]
