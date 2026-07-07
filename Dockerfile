FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY features.py predict.py train.py api.py ./
COPY app/ ./app/
COPY data/raw/listings.csv ./data/raw/listings.csv

RUN python train.py

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]