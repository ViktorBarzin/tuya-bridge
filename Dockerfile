# Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# copy and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .

# default port
EXPOSE 8080

# run with gunicorn
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8080", "api:app"]
