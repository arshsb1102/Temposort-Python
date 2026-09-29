FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN addgroup --system --gid 10001 temposort \
    && adduser --system --uid 10001 --ingroup temposort --home /app --no-create-home temposort \
    && mkdir -p /var/lib/celery /tmp/prometheus \
    && chown -R temposort:temposort /var/lib/celery /tmp/prometheus

COPY --chown=10001:10001 . .

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
