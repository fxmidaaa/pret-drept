FROM python:3.13.16-slim-bookworm

ENV PRET_DREPT_MODEL=/models/model.joblib

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 openjdk-17-jre-headless

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
