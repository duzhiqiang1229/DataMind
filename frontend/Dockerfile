# Stage 1: Build Vue frontend
FROM node:22-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --silent
COPY . .
RUN npx vite build

# Stage 2: Nginx serving static files
# Nginx 1.31 uses a PID-file pwrite path that is incompatible with the
# CentOS 7 / Linux 3.10 deployment target. Keep the runtime on the last
# stable branch that supports this kernel generation.
FROM nginx:1.24-alpine

# Copy built files
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
