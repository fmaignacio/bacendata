FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e ".[api]"

EXPOSE 8000

CMD ["uvicorn", "bacendata.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
