FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    git \
    ca-certificates \
    libboost-all-dev \
    libeigen3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir ".[dev]"

COPY . .

CMD ["python", "run.py", "demo", "configs/two_deme_migration_sweep.yml", "--output-dir", "results/demo"]
