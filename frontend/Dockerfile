# --- Build stage: compile the app with Vite ---
FROM node:24-alpine AS builder

RUN npm install --global pnpm@12.8.1

WORKDIR /app

# Dependencies first, so this layer is cached until the lockfile changes
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY . .
RUN pnpm build


# --- Runtime stage: serve the static files with nginx ---
FROM nginx:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
