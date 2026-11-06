/**
 * 服务端数据层：Astro SSR 时由 Node 直接请求 hotboard-api，不经过浏览器。
 *
 * 后端契约（实测）：
 *   GET /sources                     → { code, count, categories[], aggregates[], sources[] }
 *   GET /{中文源名}（URL 编码）        → { code, name, title, type, total, updateTime, data[] }
 *   GET /rising?limit&offset         → { code, total, offset, nextOffset, items[] }
 *
 * 注意：后端用**中文源名**做路径（如 /知乎），所以对外 URL 用 slug（/zhihu）时
 * 必须维护 slug ↔ 中文名 映射。这份映射同时决定哪些源可以被搜索引擎收录。
 */

// SSR 下必须直连后端容器；浏览器侧才用 /api
export const API_BASE =
  import.meta.env.API_BASE ||
  process.env.API_BASE ||
  "http://127.0.0.1:6700";

export interface HotItem {
  id: string;
  title: string;
  desc?: string;
  cover?: string;
  timestamp?: number;
  hot?: number;
  url?: string;
  mobileUrl?: string;
}

export interface SourceInfo {
  name: string; // 中文源名，如 "知乎"
  label: string;
  category: string;
  key?: string | null;
}

export interface SourcesResponse {
  code: number;
  count: number;
  categories: string[];
  aggregates: { name: string; label: string; category: string; items: number; sources: number }[];
  sources: SourceInfo[];
}

export interface SourceBoard {
  code: number;
  name: string;
  title: string;
  type: string;
  total: number;
  updateTime: number;
  fromCache?: boolean;
  data: HotItem[];
}

export interface RisingResponse {
  code: number;
  total: number;
  offset: number;
  nextOffset: number;
  items: HotItem[];
}

// ⚠️ 性能实测（2026-11-04）：各源响应差异极大 —— 微信读书 0.7s / 百度 19s / **微博 54s**。
//    超时必须 > 54s 否则微博百度必然超时空白；再加内存缓存，热榜 30 分钟才更新一次，不必每次回源。
const TIMEOUT_MS = 70_000;

// ───────────────────────── 内存缓存 ─────────────────────────
interface CacheEntry {
  data: unknown;
  ts: number;
  pending?: Promise<unknown>;
}
const CACHE = new Map<string, CacheEntry>();

const TTL_BOARD = 180_000; // 榜单 3 分钟
const TTL_SOURCES = 600_000; // 源清单 10 分钟

async function getJSON<T>(path: string): Promise<T | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: ctrl.signal,
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    // SSR 页面不能因为后端抖动整体 500 —— 返回 null 让页面走降级展示
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 带缓存的取数：同一个 key 的并发请求合并成一次回源，
 * 否则多个用户同时打开会把慢源（微博 54s）打出雪崩。
 */
async function cached<T>(key: string, ttl: number, fetcher: () => Promise<T | null>): Promise<T | null> {
  const hit = CACHE.get(key);
  if (hit) {
    if (hit.pending) return (await hit.pending) as T | null; // 等同一次回源
    if (Date.now() - hit.ts < ttl) return hit.data as T;
  }
  const p = fetcher();
  CACHE.set(key, { data: hit?.data ?? null, ts: hit?.ts ?? 0, pending: p });
  const data = await p;
  if (data) {
    CACHE.set(key, { data, ts: Date.now() });
    return data;
  }
  // 回源失败：有旧数据就继续用（别让页面突然空掉）
  if (hit?.data) {
    CACHE.set(key, { data: hit.data, ts: hit.ts });
    return hit.data as T;
  }
  CACHE.delete(key);
  return null;
}

export async function getSources(): Promise<SourcesResponse | null> {
  return cached("sources", TTL_SOURCES, () => getJSON<SourcesResponse>("/sources"));
}

export async function getSourceBoard(name: string): Promise<SourceBoard | null> {
  return cached(`board:${name}`, TTL_BOARD, () =>
    getJSON<SourceBoard>(`/${encodeURIComponent(name)}`)
  );
}

export async function getRising(limit = 20, offset = 0): Promise<RisingResponse | null> {
  return cached(`rising:${limit}:${offset}`, TTL_BOARD, () =>
    getJSON<RisingResponse>(`/rising?limit=${limit}&offset=${offset}`)
  );
}

/**
 * slug → 源展示名（与后端 adapters 里的 NAME 严格一致）
 * 这份映射由 jobs/collector/adapters/*.py 的 SRC_ID / NAME 生成。
 * 新增数据源后：重新生成本文件（或手工补一行）。
 */
export const SLUG_TO_SOURCE: Record<string, string> = {
  "36kr": "36氪热榜",
  "51cto": "51CTO推荐",
  "52pojie": "吾爱破解精选",
  "acfun": "AcFun排行",
  "baidu": "百度热搜",
  "bilibili": "B站排行榜",
  "cankaoxiaoxi": "参考消息",
  "cls": "财联社电报",
  "cnblogs": "博客园",
  "coolapk": "酷安今日热门",
  "csdn": "CSDN热榜",
  "dgtle": "数字尾巴",
  "dongqiudi": "懂球帝",
  "douban-group": "豆瓣小组",
  "douban-movie": "豆瓣电影榜",
  "douban": "豆瓣热门电影",
  "douyin": "抖音热搜",
  "freebuf": "FreeBuf",
  "gcores": "机核",
  "geekpark": "极客公园",
  "genshin": "原神公告",
  "github": "GitHub Trending",
  "guokr": "果壳",
  "hackernews": "Hacker News",
  "hellogithub": "HelloGitHub",
  "history": "历史上的今天",
  "honkai": "崩坏3公告",
  "hupu": "虎扑步行街",
  "huxiu": "虎嗅24小时",
  "ifanr": "爱范儿快讯",
  "ifeng": "凤凰网热点",
  "ithome-xijiayi": "IT之家喜加一",
  "ithome": "IT之家热榜",
  "jianshu": "简书",
  "jin10": "金十数据",
  "juejin": "掘金热榜",
  "kuaishou": "快手热榜",
  "lol": "英雄联盟视频",
  "miyoushe": "米游社",
  "netease-news": "网易新闻",
  "newsmth": "水木热帖",
  "ngabbs": "NGA",
  "nodeseek": "NodeSeek",
  "nowcoder": "牛客热榜",
  "nytimes": "纽约时报",
  "oschina": "开源中国",
  "producthunt": "Product Hunt",
  "qbitai": "量子位",
  "qq-news": "腾讯新闻热点",
  "sina-news": "新浪新闻榜",
  "sina": "新浪热榜",
  "smzdm": "什么值得买",
  "solidot": "Solidot",
  "sspai": "少数派",
  "starrail": "星穹铁道公告",
  "steam": "Steam 在线榜",
  "thepaper": "澎湃新闻",
  "tieba": "贴吧热议榜",
  "tonghuashun": "同花顺热榜",
  "toutiao": "今日头条热榜",
  "v2ex": "V2EX热门",
  "wallstreetcn": "华尔街见闻",
  "weatheralarm": "气象预警",
  "weibo": "微博热搜",
  "weread": "微信读书",
  "xueqiu": "雪球热股",
  "yystv": "游研社",
  "zhihu-daily": "知乎日报",
  "zhihu": "知乎热榜",
};

/** 反向映射：中文名 → slug（生成链接用） */
export const SOURCE_TO_SLUG: Record<string, string> = Object.fromEntries(
  Object.entries(SLUG_TO_SOURCE).map(([slug, name]) => [name, slug])
);

/** 给任意源名生成 SEO 友好的 slug；没有映射的中文源退化为编码后的路径 */
export function slugOf(sourceName: string): string {
  return SOURCE_TO_SLUG[sourceName] || encodeURIComponent(sourceName);
}

/**
 * 实际存在图标文件的 slug 集合（由 public/logo/*.png 生成）。
 * 源清单 68 个源，但只有这些有图 —— 其余必须退回文字头像，
 * 否则 <img src="/logo/xxx.png"> 404 后 @error 只隐藏不显示文字，就成空白了。
 */
export const HAS_LOGO = new Set<string>([
  "10jqka",
  "36kr",
  "51cto",
  "52pojie",
  "acfun",
  "baidu",
  "bilibili",
  "cls",
  "cnblogs",
  "csdn",
  "dgtle",
  "dongqiudi",
  "douban",
  "douban-group",
  "douban-movie",
  "douyin",
  "freebuf",
  "gcores",
  "geekpark",
  "genshin",
  "github",
  "guokr",
  "hackernews",
  "hellogithub",
  "honkai",
  "hupu",
  "huxiu",
  "ifanr",
  "ifeng",
  "ithome",
  "ithome-freebie",
  "jianshu",
  "jin10",
  "juejin",
  "kuaishou",
  "lol",
  "miyoushe",
  "netease-news",
  "netease_music_toplist",
  "newsmth",
  "ngabbs",
  "nodeseek",
  "nowcoder",
  "nytimes",
  "oschina",
  "producthunt",
  "qbitai",
  "qq-news",
  "qq_music_toplist",
  "sina",
  "sina-news",
  "smzdm",
  "solidot",
  "sspai",
  "starrail",
  "steam",
  "thepaper",
  "tieba",
  "toutiao",
  "v2ex",
  "wallstreetcn",
  "weatheralarm",
  "weibo",
  "weread",
  "xueqiu",
  "yystv",
  "zhihu",
  "zhihu-daily",
]);

/** 给源名返回「可用」的图标 slug；没有图标返回空串（调用方据此走文字头像） */
export function logoOf(sourceName: string): string {
  const slug = slugOf(sourceName);
  return HAS_LOGO.has(slug) ? slug : "";
}


/**
 * 分类列表前置一个「关注」分类（只有关注过源时才出现）。
 * 关注的源是跨分类的，所以它不属于任何一个原始分类。
 */
export const FOLLOW_CATEGORY = "关注";

export function categoriesWithFollow(base: string[], hasFollowed: boolean): string[] {
  return hasFollowed ? [FOLLOW_CATEGORY, ...base] : base;
}
