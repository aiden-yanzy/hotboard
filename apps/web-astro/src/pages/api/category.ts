/**
 * 切换大分类（综合/财经/科技…）用的接口。
 *
 * 原来顶栏分类是 <a href="/?cat=xxx">，整页跳转会重载侧栏（广告/热点推荐/友情链接）。
 * 改成走这个接口只返回「该分类的源 + 第一个源的榜单」，由前端局部替换，
 * 侧栏 DOM 完全不动。
 */
import type { APIRoute } from "astro";
import { getSources, getSourceBoard, logoOf, slugOf, FOLLOW_CATEGORY } from "../../lib/api";
import { slimItems } from "../../lib/slim";

export const prerender = false;

export const GET: APIRoute = async ({ url, cookies }) => {
  const cookieVal = cookies.get("hb_followed")?.value ?? "";
  const catParam = url.searchParams.get("cat") || "";

  // 关注列表从 cookie 读（设置页写入时镜像的）
  let followedList: string[] = [];
  try {
    const raw = cookieVal ?? "";
    followedList = raw ? JSON.parse(decodeURIComponent(raw)) : [];
  } catch {
    followedList = [];
  }

  const sourcesData = await getSources();
  const baseCategories: string[] = sourcesData?.categories ?? [];
  const categories =
    followedList.length > 0 ? [FOLLOW_CATEGORY, ...baseCategories] : baseCategories;
  const activeCategory =
    catParam && categories.includes(catParam) ? catParam : categories[0] || "综合";

  const allSrc = sourcesData?.sources ?? [];
  const catSources =
    activeCategory === FOLLOW_CATEGORY
      ? allSrc.filter((s) => followedList.includes(s.label || s.name))
      : allSrc.filter((s) => s.category === activeCategory);

  const chips = catSources.map((s) => {
    const name = s.label || s.name;
    return { name, label: name, logo: logoOf(name), href: `/${slugOf(name)}` };
  });

  const first = catSources[0];
  const firstName = first ? first.label || first.name : "";
  const board = firstName ? await getSourceBoard(firstName) : null;

  return new Response(
    JSON.stringify({
      ok: true,
      categories,
      activeCategory,
      sources: chips,
      board: board
        ? {
            name: board.name ?? firstName,
            subtotal: board.total ?? (board.data?.length ?? 0),
            updateTime: board.updateTime ?? null,
            items: slimItems(board.data),
          }
        : null,
      firstName,
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
