# 项目规范配方（2026-10-12 工程化）：★ 与上游唯一差异 = 把 pnpm 钉到 9.x
#   原因：上游写 `npm install -g pnpm`，现在会装到 pnpm 10+，而 pnpm 10+ 默认
#         **禁止依赖执行构建脚本**（esbuild 需要 postinstall）→ 报
#         ERR_PNPM_IGNORED_BUILDS，构建失败；pin 9.x 与项目自带 pnpm-lock.yaml(v9) 匹配。
#   上游原版存档在 Dockerfile.upstream，升级上游时先 diff 再合并。
#   用法：compose 的 engine.build.context=./apps/engine（默认即用本文件）
FROM node:20-alpine AS base

ENV NODE_ENV=docker

# 清理缓存
RUN rm -rf /var/cache/apk/*

# 构建阶段
FROM base AS builder

RUN npm install -g pnpm@9
WORKDIR /app

COPY package*json tsconfig.json pnpm-lock.yaml .env.example ./
COPY src ./src
COPY public ./public

# 复制环境变量
RUN [ ! -e ".env" ] && cp .env.example .env || true

# 安装依赖
RUN pnpm install
RUN pnpm build
RUN pnpm prune --production

# 运行阶段
FROM base AS runner

# 创建用户和组
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 hono

# 创建日志目录
RUN mkdir -p /app/logs && chown -R hono:nodejs /app/logs
RUN ln -s /app/logs /logs

# 复制文件
COPY --from=builder --chown=hono:nodejs /app/node_modules /app/node_modules
COPY --from=builder --chown=hono:nodejs /app/dist /app/dist
COPY --from=builder /app/public /app/public
COPY --from=builder /app/.env /app/.env
COPY --from=builder /app/package.json /app/package.json

# 切换用户
USER hono

# 暴露端口
EXPOSE 6688

# 运行
CMD ["node", "/app/dist/index.js"]