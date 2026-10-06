# Monitor backend image for the GCP test host (S1-04). Build context: backend/.
# The dashboard SPA is not included; main.py skips the mount when its dist is absent.
FROM python:3.12-slim

ARG GIT_SHA=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PORT=8000 \
    GIT_SHA=${GIT_SHA}

# LightGBM (via nannyml/flaml) needs libgomp.so.1.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
WORKDIR /srv/backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000
# db.engine() runs the ordered migrations at startup; no separate migrate step.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\""]
