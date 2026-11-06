/**
 * 站点配置 —— 所有和「具体部署」相关的个性化内容都集中在这里。
 *
 * 两种改法：
 *   ① 直接改本文件（简单，但改完就进 git 了）
 *   ② **用环境变量覆盖**（推荐给开源项目/多环境）：本文件保持占位符，
 *      线上靠 .env 注入，仓库始终干净。变量名见下方 ENV 段。
 *
 * 空白项会自动隐藏对应模块（备案块 / 广告位 / 友情链接各自独立）。
 */

/* ── 环境变量读取（只在服务端有值；浏览器端读不到就走默认值）────────
   注意：客户端 bundle 里 `process` 不存在，必须用 typeof 判断，
   否则会 ReferenceError。真机验证过。 */
const ENV: Record<string, string | undefined> =
  typeof process !== "undefined" && process.env ? (process.env as Record<string, string | undefined>) : {};

/** 取字符串环境变量，空串视为「未设置」 */
const env = (key: string, fallback = ""): string => {
  const v = ENV[key];
  return v && v.trim() ? v.trim() : fallback;
};

/** 解析友情链接：`名称|https://a.com;名称2|https://b.com` */
function parseLinks(raw: string): { name: string; url: string }[] {
  if (!raw.trim()) return [];
  return raw
    .split(/[;；]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((pair) => {
      const [name, url] = pair.split("|").map((x) => (x || "").trim());
      return name && url ? { name, url } : null;
    })
    .filter((x): x is { name: string; url: string } => x !== null);
}

/* ── 广告位：三项都从环境变量拼出来，任意一项缺失就降级 ── */
const AD_URL = env("SITE_AD_URL");
const AD_IMG = env("SITE_AD_IMG");
const AD_TEXT = env("SITE_AD_TEXT");
const AD_ALT = env("SITE_AD_ALT", "广告");
const ad =
  AD_URL && (AD_IMG || AD_TEXT)
    ? { url: AD_URL, img: AD_IMG || undefined, text: AD_TEXT || undefined, alt: AD_ALT }
    : null;

export const SITE = {
  /* ── 基础信息 ─────────────────────────────────── */
  /** 站点名（顶栏 logo 文字、页面标题后缀、页脚版权） */
  name: env("SITE_NAME", "热辣榜"),
  /** 顶栏 slogan */
  slogan: env("SITE_SLOGAN", "汇聚全网热点，热门尽览无余"),
  /** 默认页面描述（各榜单页会用实时内容覆盖） */
  description: env("SITE_DESCRIPTION", "实时聚合全网热点榜单，一页看尽各大平台热门内容。"),
  /** 站点正式地址（用于 canonical / sitemap / og 标签），结尾不要带斜杠 */
  url: env("SITE_URL", "https://example.com"),
  /** html lang */
  locale: "zh-CN",

  /* ── 主题 ─────────────────────────────────────── */
  /** 品牌主色（选中态、按钮、热度数字等） */
  brand: "#ff5722",
  /** 页面底色（模块卡片固定为白色 / 暗色下一档亮） */
  pageBg: "#f4f5f7",

  /* ── 备案信息（中国大陆部署必须，留空=不显示）─────
     填了 text 才会在侧栏页脚渲染这一块。
     环境变量：SITE_ICP_TEXT / SITE_ICP_URL / SITE_POLICE_TEXT / SITE_POLICE_URL */
  icp: {
    text: env("SITE_ICP_TEXT"),
    url: env("SITE_ICP_URL", "https://beian.miit.gov.cn/"),
  },
  /** 公安联网备案 */
  police: {
    text: env("SITE_POLICE_TEXT"),
    url: env("SITE_POLICE_URL"),
  },

  /* ── 广告位（null = 不显示）──────────────────────
     ⚠️ 国内《广告法》要求广告显著标明，组件已固定渲染「广告」角标。
     环境变量：SITE_AD_URL（必填）/ SITE_AD_IMG / SITE_AD_TEXT / SITE_AD_ALT */
  ad: ad as null | {
    img?: string;
    alt?: string;
    url: string;
    text?: string;
  },

  /* ── 友情链接（空数组 = 不显示该模块）──────────────
     环境变量：SITE_LINKS=优贝副业资源站|https://a.com;U8副业分享|https://b.com */
  links: parseLinks(env("SITE_LINKS")),

  /* ── 侧栏「热点推荐」条目数 ───────────────────── */
  risingCount: 8,

  /* ── 数据源标签折叠时显示几个（剩余用 +N 表示）────── */
  visibleSourceCount: 6,
};

export default SITE;
