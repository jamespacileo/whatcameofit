FROM node:24-slim

ENV ASTRO_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 4321

# Build at start so the preview always reflects the current export.
CMD ["sh", "-c", "npm run build && exec npm run preview -- --host 0.0.0.0"]
