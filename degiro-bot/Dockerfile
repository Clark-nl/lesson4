FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY src/ src/

# .env and config.yaml are intentionally NOT copied into the image —
# they hold credentials/strategy params and are mounted at runtime instead.

CMD ["python", "main.py"]
