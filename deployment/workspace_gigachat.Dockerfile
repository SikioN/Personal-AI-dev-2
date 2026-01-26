FROM m.menschikov/cuda:12.2.0-runtime-ubuntu22.04

LABEL maintainer="m.menschikov@skoltech.ru"

RUN apt-get update
RUN apt-get --assume-yes install pip
RUN apt-get --assume-yes install python3
RUN alias python=/usr/bin/python3

WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install accelerate==0.24.0

ARG APP_DIR=/workspace
ENV PYTHONPATH "${PYTHONPATH}:${APP_DIR}"

CMD ["sh", "-c", "ls -la /workspace && cd '/workspace/experiments/qa_astar_pipeline (new_graph_gigachat) (exp #2.2)/' && python3 answer_generation.py"]
