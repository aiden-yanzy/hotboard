/**
 * 真 robots.txt（之前 SPA 的 fallback 把 /robots.txt 也返回成 index.html）。
 * 允许全站抓取，声明 sitemap 位置。
 */
import type { APIRoute } from "astro";
import SITE from "../config/site";

export const prerender = false;

export const GET: APIRoute = async ({ site }) => {
  const base = (site?.toString() || SITE.url).replace(/\/$/, "");
  const body = `User-agent: *
Allow: /

# 搜索与 AI 爬虫全部放行（内容本身就是公开热点聚合）
User-agent: Baiduspider
Allow: /

User-agent: Googlebot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: ${base}/sitemap.xml
`;
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
