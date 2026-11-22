# syntax=docker/dockerfile:1
# ---------- base: runtime dependencies ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- test: used by the pipeline to run pytest inside the container ----------
FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["python", "-m", "pytest", "-q", "--junitxml=/app/reports/junit-container.xml"]

# ---------- runtime: the image that is pushed and deployed ----------
FROM base AS runtime
ARG APP_VERSION=""
LABEL org.opencontainers.image.title="aceest-fitness" \
      org.opencontainers.image.version="${APP_VERSION}"
ENV APP_VERSION=${APP_VERSION} \
    DATABASE_PATH=/data/aceest.db \
    PORT=5000
RUN useradd --uid 10001 --create-home aceest && mkdir -p /data && chown aceest /data
COPY VERSION ACEest_Fitness.py ./
COPY aceest ./aceest
USER 10001
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "ACEest_Fitness:app"]
