# ── 构建阶段 ──────────────────────────────────────────
FROM node:22-alpine AS build
WORKDIR /app

# 先只拷依赖清单，利用镜像层缓存（代码改动不用重装依赖）
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# 再拷源码并构建（Astro SSR standalone 产物在 dist/）
COPY . .
RUN npm run build

# ── 运行阶段 ──────────────────────────────────────────
FROM node:22-alpine
WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=80

# 运行只需要 dist + node_modules（Astro standalone 自带 http 服务）
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json

EXPOSE 80

# 容器内健康检查：SSR 首页能出内容就说明服务和 API 都通
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||80)+'/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/server/entry.mjs"]
