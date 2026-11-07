# CodeLens API. Run with no outbound network for the strongest sandbox:
#   docker run --rm -p 8000:8000 --network=bridge -e OLLAMA_BASE_URL=http://host.docker.internal:11434 codelens-api
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 codelens
USER codelens
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
