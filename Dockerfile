FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY features.py predict.py api.py ./
COPY src/rent_domain/__init__.py src/rent_domain/apartment.py ./src/rent_domain/
COPY src/rent_prediction/__init__.py src/rent_prediction/xgboost_preprocessing.py ./src/rent_prediction/
COPY app/ ./app/
COPY model.joblib ./model.joblib

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
