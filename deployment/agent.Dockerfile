FROM m.menschikov/cuda:12.2.0-runtime-ubuntu22.04

LABEL maintainer="m.menschikov@skoltech.ru"

RUN apt-get update
RUN apt-get --assume-yes install pip
RUN apt-get --assume-yes install python3
RUN alias python=/usr/bin/python3

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install accelerate==0.24.0

ARG APP_DIR=/app
ENV PYTHONPATH "${PYTHONPATH}:${APP_DIR}"

RUN mkdir /app/llm_agent
RUN mkdir /app/models
RUN mkdir /app/notebooks

COPY notebooks/download_llama3_8b.py /app/notebooks
COPY src/llm_agent /app/llm_agent
COPY src/agent_api.py .

RUN ls -la
RUN python3 --version

CMD  ["sh", "-c", "uvicorn agent_api:app --reload --host 0.0.0.0 --port 4567"]
#CMD ["sh", "-c", "sleep infinity"]
