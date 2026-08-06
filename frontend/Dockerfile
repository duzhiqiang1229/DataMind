# Stage 1: Build Vue frontend
FROM node:22-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

# Stage 2: Nginx serving static files
FROM nginx:alpine

# Copy built files
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
