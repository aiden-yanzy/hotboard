# 从 RSSHub 挑新源：可行性实测报告

> 实测时间：2026-10-19 ｜ 方法：自建临时 RSSHub 探针容器（`docker.1ms.run/diygod/rsshub`）
> + `/api/namespace/<ns>` 逐个拉路由元数据 + 拉真实 feed 检查字段。**全部是实测，不是印象。**

## 一、先回答：RSSHub 有没有热度？—— **没有**

抽 20 条中文"热榜/排行"类路由，拉真实 feed 检查字段：

| 检查项 | 实测结果 |
|---|---|
| feed 字段 | 只有 `title / description / link / guid / pubDate`（Atom 则是 `title/summary/link/id`）——**没有任何 heat/rank/score 字段** |
| 标题带序号 | 20 条里几乎全为 **0**（只有 `/zhihu/hot` 偶尔 1 条带"第 N"）|
| 描述里的数值 | 用 `\d+\s*(推荐|点赞|浏览|阅读|评论|热度|人气|收藏)` 匹配 → **一条都没匹配到** |
| 描述长度 | 两极：171~588 字符（只有摘要），或 1600~90000 字符（**塞了整篇正文**）|

结论：**RSSHub 的定位是"把网页变成 RSS"，它不解析也不输出热度/排名。**
而本项目的护城河正是 `snapshots.rank + heat` —— 所以它**不能替代**自研适配器，只能当**源目录**。
（补充：`/weibo/search/hot`、`/xueqiu/hots`、`/hupu/hot` 实测 503；`/douyin/hot`、`/toutiao/hot` 404 ——
我们自研版这几个都有真热度，RSSHub 反而不行。）

## 二、⭐ 许可警告（最关键的一条）

```
/app/package.json → "license": "AGPL-3.0"
```
**RSSHub 是 AGPL-3.0，不是 MIT**（dailyhot / newsnow 都是 MIT，所以那两家可以直接移植抓取逻辑；
RSSHub **不行**）。

因此：
- ❌ 不要复制它的 route 源码进本项目（AGPL 的传染性 + 网络服务条款，公开运营会有义务开源风险）
- ✅ 可以把它当**线索**：知道"这个源在 RSSHub 有路由"，说明**这个源可抓**，然后**自己实测端点**（clean-room）
- ⚠️ 长期把 RSSHub 作为后端服务接进公开站点，属于 AGPL 的灰色地带，本项目**不采用**

## 三、候选清单：RSSHub 有、我们没有的中文源

RSSHub 共 **4415** 个路由模块；实测 52 个中文命名空间、403 条路由。
下面按"对热榜站的价值"分档（标注了路由的可用条件）。

### A 档：本身是榜单/排行类（值得自己写适配器）
| 源 | RSSHub 路由 | 条件 | 热度可拿性（待逐个实测）|
|---|---|---|---|
| **酷安** | `/coolapk/hot` 热榜、`/coolapk/toutiao` | 需 cookie | 酷安热榜**有热度值**，值得挖 |
| **博客园** | `/cnblogs/aggsite/topdiggs` 10天推荐排行 | 免配 | digg 数=真热度（需自己从页面取）|
| **快科技** | `/mydrivers/rank` 排行 | 免配 | 排行页有榜位 |
| **东方财富** | `/eastmoney/*`（7 条）| 免配 | 财经人气榜类，需实测 |
| **机核** | `/gcores/topics/recommend` 机组推荐 | 免配 | 有推荐排序 |
| **观察者网** | `/guancha/*`（5 条）| 免配 | 待实测 |
| **界面新闻** | `/jiemian/*`（5 条）| 免配 | 待实测 |
| **量子位** | `/qbitai/*`（2 条）| 免配 | AI 垂类，待实测 |

### B 档：资讯流水（不带热度，属于"补时长"而非"补榜单"）
`cnBeta`(3) · `钛媒体 tmtpost`(3) · `品玩 pingwest`(3) · `Readhub`(2) · `第一财经 yicai`(10) ·
`财新 caixin`(7，付费墙) · `开源中国 oschina`(5) · `InfoQ`(3) · `SegmentFault`(3) · `搜狐 sohu`(2) ·
`人民网 people`(22) · `央视 cctv`(4) · `BBC中文`(5) · `即刻 jike`(3) · `小红书`(4，强反爬) ·
`斗鱼`(3) · `虎牙`(1) · `起点`(5) · `爱奇艺`(2) · `优酷`(1)

### RSSHub 也没有的
`机器之心 jiqizhixin`、`新华网 xinhua`、`网易新闻`（RSSHub 用 `163` 命名空间）——
要加就纯自研。

## 四、建议做法（跟我们刚落地的 63 源同一套）

1. **RSSHub 只当目录**：用它确认"这个源存在且在更新"，然后**自己实测端点**
2. 像移植 newsnow/dailyhot 那样写 `jobs/collector/adapters/<src_id>.py`，能拿热度就拿（拿不到就 `heat=None`）
3. 优先做 A 档里**带真实热度**的（酷安/博客园/快科技最像），B 档只在需要"内容量"时补
4. **不引入 RSSHub 运行时依赖**（AGPL + 已有 63 源自研链路更简单可靠）

## 五、复现方法（下次要再扫一遍时用）

```bash
# 1) 起临时探针（用完即删，--rm）
docker run -d --rm --name rsshub-probe -p 127.0.0.1:1200:1200 docker.1ms.run/diygod/rsshub
# 2) 看某个命名空间有哪些路由（含 example / antiCrawler / requireConfig / requirePuppeteer）
curl -s http://127.0.0.1:1200/api/namespace/zhihu
# 3) 完整路由索引（容器内编译产物，共 4415 个模块）
docker cp rsshub-probe:/app/assets/build/routes.js /tmp/rsshub_routes.js
# 4) 拉真实 feed 看字段（有没有热度就靠这一步）
curl -s http://127.0.0.1:1200/ithome/ranking/24h | head -c 800
```

## 六、候选源端点实测（2026-10-19 二次探测，决定先做谁）

| 源 | 实测端点 | 结果 | 热度可拿性 | 结论 |
|---|---|---|---|---|
| **博客园** | `https://www.cnblogs.com/aggsite/topdiggs` | ✅ 200，77KB，HTML 静态渲染 | ⭐ **可直接取**：`<a title="评论7, 推荐6, 阅读1782" data-postId="...">`，正文里也有 `(7/6/1782)` | **建议先做**（免配 + 有真热度）|
| **快科技** | RSSHub 的 `/mydrivers/rank` 实际抓的是 `m.mydrivers.com/newsclass.aspx?tid=1001` | ⚠️ 是**分类页**不是排行榜 | ❌ 无榜位 | 降级；要做需另找真实排行页 |
| **酷安** | `https://www.coolapk.com/hot` → 200 但**仅 41 字节**（JS 壳）；`api.coolapk.com/v6/feed/hotList` → **403** | ⚠️ 需真实 cookie / 签名 | 热榜页有热度值但拿不到 | **暂缓**（除非提供 cookie，与 BOSS 直聘那套一样让用户手工登录取）|

> 探测方法：`<a title="评论X, 推荐Y, 阅读Z">` 这种**属性里带结构化数字**的页面最适合自研，
> 比正则抠正文稳（参考技能库 8.7：HTML 属性顺序不固定，但**属性值本身**是可靠的）。

## 七、附：本次实测可用/不可用一览（抽样 20 条）

| route | 结果 | 条数 |
| `/zhihu/hot` | ✅ | 30 |
| `/baidu/top` | ✅ | 51 |
| `/36kr/hot-list` | ✅ | 8 |
| `/ithome/ranking/24h` | ✅ | 12 |
| `/juejin/trending/all/weekly` | ✅ | 20 |
| `/nowcoder/hots/1` | ✅ | 20 |
| `/wallstreetcn/hot` | ✅ | 10 |
| `/zaobao/popular/daily` | ✅ | 5 |
| `/douban/movie/weekly` | ✅ | 10 |
| `/bilibili/popular/all` | ✅ | 20 |
| `/cnblogs/aggsite/topdiggs` | ✅ | 20 |
| `/v2ex/topics/latest` | ✅ | 42 |
| `/163/news/rank/money/click/day` | ✅ | 50 |
| `/qq/weread/newbook` | ✅ | 20 |
| `/cls/hot` | ✅ | 13 |
| `/weibo/search/hot` | ❌ 503（需 visitor cookie）| — |
| `/xueqiu/hots` | ❌ 503 | — |
| `/hupu/hot` | ❌ 503 | — |
| `/douyin/hot` | ❌ 404（无该路由）| — |
| `/toutiao/hot` | ❌ 404（无该路由）| — |
