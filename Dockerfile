FROM node:22-slim AS web
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY crescent_vigil ./crescent_vigil
RUN pip install --no-cache-dir .
COPY knowledge ./knowledge
COPY data ./data
COPY reports ./reports
COPY --from=web /app/web/dist ./web/dist
ENV CRESCENT_ROOT=/app
EXPOSE 8000
CMD ["uvicorn", "crescent_vigil.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
