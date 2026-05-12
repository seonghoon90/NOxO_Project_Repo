FROM python:3.11-slim

WORKDIR /app

COPY streaming/requirements.txt /tmp/streaming-requirements.txt
RUN pip install --no-cache-dir -r /tmp/streaming-requirements.txt

CMD ["python", "-m", "streaming.producer"]
