# ---------------------------------------------------------------------------
# Text-to-CAD Web App — Production Dockerfile
# Build context must be the repo root (text-to-cad/)
#   docker build -f web-app/Dockerfile .
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/web-app/frontend
COPY web-app/frontend/package.json web-app/frontend/package-lock.json* ./
RUN npm install
COPY web-app/frontend/ ./
RUN npm run build

FROM node:20-slim AS admin-builder

WORKDIR /app/web-app/admin
COPY web-app/admin/package.json web-app/admin/package-lock.json* ./
RUN npm install
COPY web-app/admin/ ./
RUN npm run build

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system deps for build123d / OCP
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cadpy + fastapi + openai)
COPY web-app/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy repo skills/packages needed by the backend
COPY skills/ ./skills/
COPY packages/ ./packages/
COPY models/ ./models/
COPY web-app/backend/ ./web-app/backend/

# Copy built frontend & admin dist into the location main.py expects
COPY --from=frontend-builder /app/web-app/frontend/dist ./web-app/frontend/dist
COPY --from=admin-builder /app/web-app/admin/dist ./web-app/admin/dist

# Install cadpy (editable install from the bundled package)
RUN pip install --no-cache-dir -e ./skills/cad/scripts/packages/cadpy

WORKDIR /app/web-app/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
