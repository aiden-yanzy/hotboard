# 参照站对照：rebang.today 的源清单 vs 我们

> 实测时间：2026-10-19 ｜ 方法：读它线上站点（`robots.txt` → `sitemap.xml` → 6 个分类页），
> 抽取**服务端渲染**的源标签栏（`data-testid="tab-avatar-<slug>-dark"` + `<span>中文名</span>`）。
> 只读"有哪些源"做对照，**不搬它的代码、内容或数据**。

## ⚠️ 先更正一个此前的错误说法

`~/Docker/rebang/app/` **不是** rebang.today 的源码 —— 它是 `github.com/imsyy/DailyHotApi` 的克隆
（`git remote -v` 可证；`package.json` 的 `name = dailyhot-api`；目录里没有任何 `rebang` 字样）。
`~/Docker/rebang/` 只是当年做聚合站时给这个**项目起的代号目录**（对标 rebang.today 之意），
其中的 `source_health.json` 记录的是 **DailyHotApi 的 56 个源**，与 rebang.today 无关。

**结论：rebang.today 的源码我们没有，也不需要有 —— 只需读它线上暴露的源清单即可对照。**

## 一、对照结果

| 项 | 数量 |
|---|---|
| rebang.today 的源（含它的 5 个分类 tab） | **107** |
| 我们（`custom` 引擎自研适配器） | **63** |
| 两边对得上 | **34** |
| ⭐ **它有、我们没有** | **约 65+** |
| 我们有、它没有 | ~29（含 13 个从 newsnow 迁来的，如雪球/财联社/金十/参考消息/自由财经等）|

它比我们强在**广度**：财经、汽车、游戏、AI、软件这几个垂类比我们深得多。

## 二、缺口清单（按类别，⭐=本身带榜单/热度口径，优先级高）

### ⭐ A 档：本身就是榜单/热度类（最值得补）
| 源 | slug | 热度口径（待逐个实测）|
|---|---|---|
| **同花顺** | `tonghuashun` | 有热度/人气榜 |
| **东方财富** | `eastmoney` | 有人气榜 |
| **360热搜** | `360-hot-search` | 热搜榜（有热度值）|
| **抽屉新热榜** | `ichouti` | 本身就是热榜 |
| **博客园** | `cnblogs` | ✅ **已实测**：页面带 `title="评论7, 推荐6, 阅读1782"`，可直接取数 |
| **快科技** | `mydrivers` | 排行页（需另找真实榜位）|
| **机核** | `gcores` | 机组推荐排序 |
| **酷安** | `coolapk` | 热榜有热度值，但**需 cookie** |

### 财经（它有一整块，我们只有雪球/财联社/金十/华尔街见闻/参考消息）
`gelonghui` 格隆汇 · `diyicaijing` 第一财经 · `sina-fin` 新浪财经 · `caixin` 财新 · `jiemian` 界面新闻 · `latepost` 晚点

### 游戏
`gamersky` 游民星空 · `3dmgame-news` 3DM游戏 · `17173` · `xiaoheihe` 小黑盒 · `taptap` TapTap · `zhibo8` 直播吧

### AI（我们完全没有）
`qbitai` 量子位 · `aiera` 新智元 · `jiqizhixin` 机器之心 · `aibase` AIBase · `ahead-of-ai` · `huggingface`

### 开发
`oschina` 开源中国 · `infoq` · `segmentfault` · `kanxue` 看雪 · `daily-dev` · `devto` · `journal-tech` 技术期刊

### 软件/科技资讯
`appinn` 小众软件 · `landian` 蓝点网 · `iplaysoft` 异次元软件 · `youquhome` 有趣网址之家 · `pingwest` 品玩 · `myzaker` ZAKER · `toodaylab` 理想生活实验室 · `rsshub`?（无）

### 汽车 / 社区 / 其他
`autohome` 汽车之家（+论坛）· `xchuxing` 新出行（+社区）· `kds` 宽带山 · `feng` 威锋 · `penti` 喷嚏网 · `shadiao-news` 沙雕新闻 · `woshipm` 人人都是产品经理 · `cyzone` 创业邦 · `donews` DoNews · `mittrchina` 麻省理工科技评论 · `readhub` · `pearvideo` 梨视频

### 音乐 / 播客 / 小说 / 电商（看产品定位再决定）
`netease-cloud-music` 网易云音乐 · `kugou-music` 酷狗 · `ximalaya` 喜马拉雅 · `xiaoyuzhou` 小宇宙 · `qidian` 起点 · `qdmm` 起点女生 · `xmyp` 小米有品 · `pdd` 拼多多 · `jd` 京东

### 我们已有但被归到它别的 tab 的（无需重复加）
`ifanr` 爱范儿 · `ifeng-news` 凤凰新闻 · `baidu-tieba` 百度贴吧 · `douban-community`/`douban-media` 豆瓣社区/书影音（我们已有 3 个豆瓣源）· `nga` NGA · `tencent-news` 腾讯新闻 · `ne-news` 网易新闻 · `newsmth` 水木 · `weread` 微信读书 · `zhihu-daily` 知乎日报

## 三、和 RSSHub 清单的交集（互相印证"这些是公认的好源"）

两边都出现 → 优先做：**博客园 `cnblogs`、东方财富 `eastmoney`、机核 `gcores`、界面新闻 `jiemian`、
量子位 `qbitai`、开源中国 `oschina`、InfoQ、SegmentFault、酷安 `coolapk`、快科技 `mydrivers`**

## 四、建议的推进顺序

1. **第一批（带真热度、免配、成本低）**：博客园 → 360热搜 → 抽屉新热榜 → 同花顺 → 东方财富
2. **第二批（垂类补广度，无热度但量大）**：量子位 / 新智元 / 机器之心（AI）、游民星空 / 3DM / 小黑盒（游戏）、开源中国 / InfoQ / SegmentFault / 看雪（开发）
3. **第三批（需 cookie 或成本高）**：酷安（cookie）、小红书（强反爬）、汽车之家（需实测）

每加一个都按现有规范：`adapters/<src_id>.py` 一源一文件 → 单独实测 → 入库注册 → 出回滚 SQL。
