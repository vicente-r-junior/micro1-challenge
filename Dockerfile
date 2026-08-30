# Judges run this. It must work with no API key and no network access at run
# time: the benchmark replays from the response cache committed in data/.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: prove the harness itself is sound before trusting any number it prints.
CMD ["python", "-m", "pytest", "tests/", "-q"]
