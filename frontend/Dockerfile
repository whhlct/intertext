# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS dependencies

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN chown node:node /app
USER node
RUN --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 \
    npm ci --cache /home/node/.npm

FROM dependencies AS development

ENV NODE_ENV=development
COPY --chown=node:node frontend/ ./
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM dependencies AS production-builder

ARG INTERTEXT_BACKEND_URL=http://backend:8000
ENV NODE_ENV=production \
    INTERTEXT_BACKEND_URL=${INTERTEXT_BACKEND_URL}
COPY --chown=node:node frontend/ ./
RUN npm run build

FROM node:22-alpine AS production

ARG INTERTEXT_BACKEND_URL=http://backend:8000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    INTERTEXT_BACKEND_URL=${INTERTEXT_BACKEND_URL}

WORKDIR /app
COPY --from=production-builder --chown=node:node /app/.next/standalone ./
COPY --from=production-builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
CMD ["node", "server.js"]
