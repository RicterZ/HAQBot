FROM python:3.13-slim-bookworm AS builder

ARG BUILD_DATE
ARG VERSION
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /build

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt && \
    pip wheel --no-deps --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim-bookworm

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN groupadd -r app && useradd -r -g app app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

WORKDIR /app

COPY supervisord.conf /etc/supervisor/conf.d/homeassistant-qq.conf
COPY --chown=app:app . .

USER root

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
