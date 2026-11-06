/**
 * 点击「刷新」时的局部刷新接口。
 * 原来 refresh() 用 location.href 整页跳转 → 浏览器重新下载 HTML/CSS/JS，
 * naive-ui 的 CSS-in-JS 要等 hydration 后才注入，于是会先闪一下裸样式再变正常。
 * 改成走这个接口只换数据，页面不重载，就没有任何闪变了。
 */
import type { APIRoute } from "astro";
import { getSourceBoard } from "../../lib/api";
import { slimItems } from "../../lib/slim";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const source = url.searchParams.get("source") || "";
  if (!source) {
    return new Response(JSON.stringify({ ok: false, error: "missing source" }), {
      status: 400,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  const board = await getSourceBoard(source);
  if (!board) {
    return new Response(JSON.stringify({ ok: false, error: "source not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  return new Response(
    JSON.stringify({
      ok: true,
      name: board.name,
      total: board.total ?? (board.data?.length ?? 0),
      updateTime: board.updateTime,
      items: slimItems(board.data),
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    }
  );
};
