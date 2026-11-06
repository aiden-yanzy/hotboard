# 采集器镜像（云上一键部署时用；本机也可以 docker exec 触发）
# 2026-10-12：日报已下线，本镜像只负责采集
FROM python:3.12-slim

WORKDIR /app
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 只用标准库 + psycopg + PyYAML（少依赖=少坏面）
# curl：WAF 兜底需要（部分站点对 urllib 下发阿里云 WAF 挑战页，curl 能过；见 adapters/base.get_text_curl）
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "psycopg[binary]>=3.2" "PyYAML>=6.0"

COPY . /app/
RUN mkdir -p /app/logs

# 默认被 compose 的 command 覆盖：
#   本机：sleep infinity（等 cron 触发）  云端：--loop --interval N
CMD ["python", "collect.py"]
