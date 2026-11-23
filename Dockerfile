FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 iputils-ping dnsutils procps curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY app/ /app/
RUN mkdir -p /data && chown -R app:app /app /data
USER app

EXPOSE 8000 8080
CMD ["python", "target_server.py"]
