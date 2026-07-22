FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8787

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements-prod.txt

COPY alfahou ./alfahou
COPY weights ./weights
COPY data ./data
COPY outputs/.gitkeep ./outputs/.gitkeep

RUN mkdir -p outputs

EXPOSE 8787
CMD uvicorn alfahou.api.app:app --host 0.0.0.0 --port ${PORT}
