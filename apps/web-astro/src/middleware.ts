import { defineMiddleware } from "astro:middleware";

/**
 * 静态资源缓存策略
 *
 * 背景：@astrojs/node 默认给 public 下的静态文件下发 `Cache-Control: public, max-age=0`，
 * 意味着浏览器每次打开页面都要为 67 个源图标、favicon 等逐个发条件请求（304），
 * 手机上就是「图标一个个慢慢出来」。这些文件内容几乎不变，应该长缓存。
 *
 * 规则：
 *   /logo/* /ico/* /ad/* /fonts/*  —— 站点自有静态资源，一年 immutable
 *   /_astro/*                      —— 构建产物，文件名带 hash，一年 immutable
 *   /sitemap.xml /robots.txt       —— 一小时（内容会随源变化）
 */
const IMMUTABLE_PREFIX = [/^\/logo\//, /^\/ico\//, /^\/ad\//, /^\/fonts\//, /^\/_astro\//];
const SHORT_PREFIX = [/^\/sitemap\.xml$/, /^\/robots\.txt$/];

export const onRequest = defineMiddleware(async (context, next) => {
  const res = await next();
  const path = new URL(context.request.url).pathname;

  // 只在成功响应上加，避免把错误页也缓存住
  if (res.status >= 200 && res.status < 300) {
    if (IMMUTABLE_PREFIX.some((re) => re.test(path))) {
      res.headers.set("Cache-Control", "public, max-age=31536000, immutable");
    } else if (SHORT_PREFIX.some((re) => re.test(path))) {
      res.headers.set("Cache-Control", "public, max-age=3600");
    }
  }
  return res;
});
