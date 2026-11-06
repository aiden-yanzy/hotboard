# 热榜平台 · 统一运维入口
#   本机：make up && make health；云端：git clone + cp .env.example .env + make up
SHELL := /bin/bash
COMPOSE := docker compose
DC := $(COMPOSE) exec -T

.DEFAULT_GOAL := help

help: ## 显示所有命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## 构建并启动全栈（首次部署用这条）
	$(COMPOSE) up -d --build

up-min: ## 只起必要服务（db/api/web/collector，省内存；engine 与 newsnow 可不起）
	$(COMPOSE) up -d --build db api web collector

bootstrap: ## 初始化数据库（建表 + 灌 68 个源 + 分类种子，幂等）
	$(DC) collector python collect.py --bootstrap

init: up-min bootstrap collect ## 全新部署一条龙：起服务 → 建表灌源 → 跑第一轮采集

down: ## 停止（保留数据）
	$(COMPOSE) down

restart: ## 重启
	$(COMPOSE) restart

ps: ## 查看服务状态
	$(COMPOSE) ps

logs: ## 跟踪全部日志（可 make logs S=web）
	$(COMPOSE) logs -f --tail=120 $(S)

build: ## 只构建镜像
	$(COMPOSE) build

health: ## 健康自检（容器 + 三个 HTTP 端点）
	@echo "── 容器 ──"; $(COMPOSE) ps --format '{{.Name}}\t{{.Status}}'
	@echo "── HTTP ──"
	@. ./.env 2>/dev/null; \
	 for p in "$${HOTBOARD_WEB_PORT:-6600} /" "$${HOTBOARD_API_PORT:-6700} /health"; do \
	   set -- $$p; printf "  :%-6s " "$$1"; \
	   curl -s -o /dev/null -w "HTTP %{http_code}\n" -m 6 "http://127.0.0.1:$$1$$2" || echo FAIL; \
	 done

collect: ## 立刻跑一轮采集（本机 cron 走的就是这条）
	$(DC) collector python collect.py

collect-loop: ## 前台跑常驻采集（调试用）
	$(DC) collector python collect.py --loop --interval 300

psql: ## 进数据库
	$(DC) db psql -U $${POSTGRES_USER:-hotboard} -d $${POSTGRES_DB:-hotboard}

backup: ## 备份数据库到 HOTBOARD_DATA_DIR/backups
	@. ./.env 2>/dev/null; mkdir -p "$$HOTBOARD_DATA_DIR/backups"; \
	 $(DC) db pg_dump -U "$${POSTGRES_USER:-hotboard}" "$${POSTGRES_DB:-hotboard}" \
	   | gzip > "$$HOTBOARD_DATA_DIR/backups/hotboard-$$(date +%Y%m%d-%H%M%S).sql.gz"; \
	 ls -lh "$$HOTBOARD_DATA_DIR/backups" | tail -3

docker-clean: ## 清理本项目未使用的镜像/缓存（不动数据）
	$(COMPOSE) down --remove-orphans
	docker image prune -f --filter label=com.docker.compose.project=hotboard

.PHONY: help up up-min bootstrap init down restart ps logs build health collect collect-loop psql backup docker-clean
