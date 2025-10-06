# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build args for env variables
ARG VITE_API_URL
ARG VITE_GRAFANA_URL

ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_GRAFANA_URL=${VITE_GRAFANA_URL}

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

