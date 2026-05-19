FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5001 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       zlib1g-dev \
       ffmpeg \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN CFLAGS="-I/usr/include -I/usr/include/aarch64-linux-gnu" \
    CPPFLAGS="-I/usr/include -I/usr/include/aarch64-linux-gnu" \
    uv sync --frozen --no-dev

COPY . .
RUN mkdir -p uploads

EXPOSE 5001

CMD ["uv", "run", "python", "app.py"]
