# ---- build frontend ----
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY v1-simple/frontend/package.json v1-simple/frontend/package-lock.json* ./
RUN npm ci
COPY v1-simple/frontend/ .
RUN npm run build

# ---- production ----
FROM python:3.11-slim
WORKDIR /app

COPY v1-simple/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY v1-simple/backend/ ./backend/
COPY v1-simple/config.yaml ./config.yaml
COPY --from=frontend-build /build/dist ./static/

ENV PYTHONUNBUFFERED=1
ENV PORT=18816

EXPOSE 18816

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "18816"]
