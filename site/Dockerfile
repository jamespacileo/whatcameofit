FROM node:24-slim

ENV ASTRO_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 4321

# Build at start so the preview always reflects the current export. When EXPORT_FILE
# names a file that the pipeline writes, wait for it; without it the checked-in seed
# export is used.
CMD ["sh", "-c", "if [ -n \"$EXPORT_FILE\" ]; then until [ -f \"$EXPORT_FILE\" ]; do sleep 1; done; fi; npm run build && exec npm run preview -- --host 0.0.0.0"]
