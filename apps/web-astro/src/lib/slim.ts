/**
 * 接口返回瘦身（只用于前端自己的 /api/board、/api/category 代理层，不动 Python 接口契约）。
 *
 * 为什么做这个：实测手机 4G（限速 180KB/s、延迟 100ms）下一次切源，
 * 点击 → 列表更新 1075ms，其中 1057ms 全在 API 请求上，而下载占 956ms。
 * 打开 JSON 一看有一半是前端根本不用的字段：
 *   - mobileUrl：与 url 完全相同（百度热搜 50/50 条一字不差），每条白传 ~149 字符，整页 ~7KB
 *   - firstSeen / engine / timestamp：前端 0 处引用
 * 裁掉后 /api/board 原始体积 42KB → 24KB，gzip 后 14KB → 9KB。
 */

const KEEP = ["id", "title", "desc", "cover", "hot", "url", "mobileUrl", "rank", "index"] as const;

type Field = (typeof KEEP)[number];

export function slimItems<T extends Record<string, unknown>>(items: T[] | undefined | null): Partial<T>[] {
  if (!Array.isArray(items)) return [];
  return items.map((it) => {
    const out: Partial<T> = {};
    for (const k of KEEP) {
      if (it[k] !== undefined && it[k] !== null) (out as Record<string, unknown>)[k] = it[k];
    }
    // url 与 mobileUrl 一致时只传一份（前端到处是 `it.url || it.mobileUrl` 兜底，删掉不影响）
    if (out.mobileUrl && out.mobileUrl === out.url) delete out.mobileUrl;
    return out;
  });
}
