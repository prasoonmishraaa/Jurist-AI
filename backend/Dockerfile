# JURIST AI — Backend Production Dockerfile
FROM node:20-slim AS builder

WORKDIR /app

# Copy root and backend package files
COPY package*.json ./
COPY backend/package*.json ./backend/

# Install dependencies
RUN npm ci --workspace=backend

# Copy source and artifacts
COPY backend ./backend

# Build backend and copy artifacts
RUN npm run build --workspace=backend

# Production Runner
FROM node:20-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/backend/package*.json ./backend/
RUN npm ci --workspace=backend --only=production

COPY --from=builder /app/backend/dist ./backend/dist
COPY --from=builder /app/backend/src/integrations/artifacts ./backend/dist/integrations/artifacts

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5001/api/v1/health || exit 1

WORKDIR /app/backend
CMD ["node", "dist/server.js"]
