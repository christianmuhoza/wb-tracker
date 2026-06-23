# ---- Stage 1: build the Vite app ----
FROM node:20-alpine AS build

WORKDIR /app

# Install deps first for better layer caching
COPY package*.json ./
RUN npm ci

COPY . .

# Vite reads VITE_* env vars at BUILD time, not runtime — pass via build-arg
# if your app calls a backend API URL, e.g.:
#   ARG VITE_API_URL
#   ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Stage 2: serve the built static files with Nginx ----
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
