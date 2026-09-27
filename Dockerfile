FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 diffsignal && mkdir -p /data && chown diffsignal:diffsignal /data
USER diffsignal
ENV DIFFSIGNAL_DATABASE_URL=sqlite+aiosqlite:////data/diffsignal.db
EXPOSE 8000
CMD ["uvicorn", "diffsignal.api:app", "--host", "0.0.0.0", "--port", "8000"]
