/**
 * 动态 sitemap：SSR 端点，每次请求按当前源清单生成。
 * 为什么手写而不用 @astrojs/sitemap：源列表来自后端 API（会变），静态生成会在新增源时漏掉。
 */
import type { APIRoute } from "astro";
import SITE from "../config/site";
import { getSources, slugOf } from "../lib/api";

export const prerender = false;

export const GET: APIRoute = async ({ site }) => {
  const base = (site?.toString() || SITE.url).replace(/\/$/, "");
  const data = await getSources();
  const now = new Date().toISOString();

  const urls: { loc: string; priority: string; changefreq: string }[] = [
    { loc: `${base}/`, priority: "1.0", changefreq: "hourly" },
    { loc: `${base}/all`, priority: "0.9", changefreq: "hourly" },
  ];

  for (const s of data?.sources ?? []) {
    const name = s.label || s.name;
    urls.push({
      loc: `${base}/${slugOf(name)}`,
      priority: "0.8",
      changefreq: "hourly", // 榜单内容每小时都在变
    });
  }

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) => `  <url>
    <loc>${u.loc}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`
  )
  .join("\n")}
</urlset>`;

  return new Response(body, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=1800",
    },
  });
};
