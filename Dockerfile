FROM python:3.13.16-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PRET_DREPT_MODEL=/models/model.joblib \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-serve.txt ./
RUN python -m pip install --no-cache-dir --only-binary=:all: --no-deps -r requirements-serve.txt \
    && python -m pip check

COPY features.py predict.py api.py ./
COPY app/index.html ./app/index.html
RUN mkdir /models
USER 10001:10001
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
