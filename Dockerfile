# HuggingFace Spaces (Docker SDK) — card-free free-tier host.
# The server reads $PORT (Spaces sets 7860); stdlib only, no pip needed.
FROM python:3.12-slim
WORKDIR /app
COPY . /app
EXPOSE 7860
CMD ["python3", "backend/server.py"]
