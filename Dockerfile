FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=data

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/ ./backend/
RUN uv sync --project backend --frozen --no-dev

COPY frontend/dist ./frontend/dist
COPY scripts ./scripts
COPY .env.example ./.env.example

RUN mkdir -p "/app/${DATA_DIR}"

EXPOSE 8000

CMD ["uv", "run", "--project", "backend", "backend"]
