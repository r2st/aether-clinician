# Aether Clinician web (Next.js 14)
FROM node:20-slim AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY apps/web ./
RUN npm run build

FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
