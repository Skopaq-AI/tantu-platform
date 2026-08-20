FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY src ./src
COPY alembic ./alembic 2>/dev/null || true
EXPOSE 8000
CMD ["uvicorn", "tantu.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
