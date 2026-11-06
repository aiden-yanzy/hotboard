# 源适配器规范（自研源抓取逻辑）

> 目标：**新增一个源 = 新增一个文件**，不改 `collect.py`。
> 适用：`sources.engine = 'custom'` 的所有源（自研抓取逻辑，不依赖外部上游）。

## 一、三步新增一个源

```bash
# 1. 写文件（模板见下）
vim jobs/collector/adapters/<src_id>.py

# 2. 自测（不联网入库，只看解析结果）
python -c "
import sys; sys.path.insert(0,'jobs/collector')
import adapters; m=adapters.get('<src_id>')
c=adapters.new_client()
for it in m.fetch(c)[:3]: print(it.rank, it.heat, it.title[:50])
"

# 3. 注册进库（engine='custom'）
psql -h 127.0.0.1 -p 5433 -U hotboard -d hotboard -c \
  "insert into sources (id, engine, src_id, name, category) values
   ('custom:<src_id>','custom','<src_id>','<中文名>','<分类>') on conflict (id) do nothing;"
```

## 二、文件模板

```python
from .base import Item, clip, num

SRC_ID   = "example"      # 必须与 sources.src_id 一致
NAME     = "示例站"
CATEGORY = "综合"          # 综合/科技/娱乐/开发/社区/购物

API = "https://example.com/api/hot"
HEADERS = {"Referer": "https://example.com/"}   # 需要时带上

def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    if not isinstance(payload, dict) or "data" not in payload:
        raise RuntimeError("响应形状异常（见规范 5）")   # 必须校验
    rows = []
    for i, x in enumerate(payload["data"], 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        rows.append(Item(
            ext_id=str(x["id"]),        # 稳定 id（规范 3）
            title=title,
            url=x.get("url"),
            rank=i,                     # 榜单顺序 = 返回顺序（规范 2）
            heat=num(x.get("hot")),     # 拿不到就是 None（规范 4）
            desc=clip(x.get("desc"), 300),
        ))
    return rows
```

## 三、十条规范（违反任何一条都算 bug）

1. **一个源 = 一个文件**（`adapters/<src_id>.py`），模块级暴露 `SRC_ID / NAME / CATEGORY / fetch`
2. **`fetch()` 只做「取 + 解析」**，返回 `list[Item]`；**禁止碰数据库**（入库由 `collect.py` 统一做 → 换来可 dry-run、可单测）
3. **`rank` = 返回顺序**（第 1 条即 rank 1）；不要按热度重排（热度排序是加工层的事）
4. ⭐ **`heat` 拿不到就是 `None`**：**严禁填 0、严禁拿"权重/score/点赞数"冒充热度** —— `snapshots.heat` 是涨跌护城河，一旦被污染，趋势分析全部失真
5. **必须校验响应形状**：HTTP 200 ≠ 成功（实测：雪球返回 200，内容却是阿里云 WAF 页）。拿到不对劲的内容直接 `raise`，让 `sources.last_err` 留下证据
6. **`ext_id` 跨轮次稳定**：同一条目每轮必须同 id，否则 `items` 的 `first_seen/last_seen` 与 `(source_id,url_hash)` 去重全部失效
7. **HTTP 一律走注入的 `client`**：超时/重试/限速/UA 统一在一处（`HttpClient`），适配器不许自建连接、不许自己 sleep 重试
8. **解析失败抛异常并带上源名与原因**：`collect.py` 会写进 `sources.last_err`，前端健康页可见
9. **`desc` 用 `clip()` 截断**（默认 400 字）：不要把整篇正文塞进 `meta`（36氪的 RSS 正文有一万多字）
10. **旧引擎兼容层不删**：`engine='dailyhot' / 'newsnow'` 走原 HTTP 路径，`base_url` 置空即停用；等自研源对等覆盖后再逐批迁移

## 四、已迁移的源（15 个，全部实测通过）

| src_id | 名称 | 分类 | 形态 | 完成 |
|---|---|---|---|---|
| wallstreetcn | 华尔街见闻 | 综合 | JSON API | ✅ 试点 |
| solidot | Solidot | 科技 | RSS/XML | ✅ 试点 |
| cankaoxiaoxi | 参考消息 | 综合 | JSON（3 频道合并）| ✅ |
| steam | Steam 在线榜 | 娱乐 | HTML | ✅ |
| producthunt | Product Hunt | 开发 | Atom feed | ✅ |
| jin10 | 金十数据 | 综合 | JS 文本 → JSON | ✅ |
| xueqiu | 雪球热股 | 综合 | JSON + Cookie 两步 | ✅ |
| cls | 财联社电报 | 综合 | JSON + 双哈希签名 | ✅ |
| freebuf | FreeBuf | 科技 | RSS（curl 兜底）| ✅ |
| douban | 豆瓣热门电影 | 娱乐 | JSON（需 Referer）| ✅ |
| dongqiudi | 懂球帝 | 娱乐 | JSON | ✅ |
| ifeng | 凤凰网热点 | 综合 | HTML 内联 JSON | ✅ |
| nowcoder | 牛客热榜 | 开发 | JSON | ✅（唯一有真热度值）|

> 全部**移植自 newsnow（ourongxing/newsnow，MIT License）**，纯 Python 重写、仅用标准库；
> 每个适配器文件头注明出处，本仓库保留其版权声明。

## 五、未迁移（如实登记，不做无根据的猜测）

| src_id | 名称 | 原因 |
|---|---|---|
| zaobao | 联合早报 | 上游域名 `zaochenbao.com` 实测 **HTTP 000 不可达**（站点疑似下线/被墙）|
| fastbull | 法布财经 | **地理阻断**：中国大陆 IP 返回"访问提示"页，需非大陆出口（选择器本身简单）|
| xueqiu* | 雪球（子源 `xueqiu-hotstock`）| 同一适配器可同时注册两个 src_id，按需再挂 |
