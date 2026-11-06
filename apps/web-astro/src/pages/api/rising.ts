/**
 * 侧栏「热点推荐 · 换一批」用的客户端接口。
 * 浏览器不能直连 6700（内网），这里由 Astro 服务端转发。
 */
import type { APIRoute } from "astro";
import { getRising } from "../../lib/api";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const offset = Number(url.searchParams.get("offset") || 0);
  const limit = Number(url.searchParams.get("limit") || 8);
  const data = await getRising(limit, offset);
  return new Response(
    JSON.stringify(
      data ?? { code: 500, items: [], total: 0, offset, nextOffset: offset }
    ),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    }
  );
};
