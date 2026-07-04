FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# GROQ_API_KEY and SLACK_WEBHOOK_URL are expected as env vars at runtime,
# e.g. docker run -e GROQ_API_KEY=... -e SLACK_WEBHOOK_URL=... eval-pipeline
CMD ["python", "main.py"]
