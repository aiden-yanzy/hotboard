import RSSParser from "rss-parser";
import logger from "./logger.js";

/**
 * 提取 RSS 内容
 * @param content HTML 内容
 * @returns RSS 内容
 */
export const extractRss = (content: string): string | null => {
  // 匹配 <rss> 标签及内容
  const rssRegex = /(<rss[\s\S]*?<\/rss>)/i;
  const matches = content.match(rssRegex);
  return matches ? matches[0] : null;
};

/**
 * 从 RSS 条目里挑封面：优先 enclosure / media:*，其次正文 HTML 里的第一张图
 * （2026-10-12 补：RSS 源此前完全没抽封面，导致纽约时报/吾爱破解等源在列表页没有头图）
 */
const pickCover = (item: any): string | undefined => {
  const cands = [
    item?.enclosure?.url,
    item?.["media:thumbnail"]?.$?.url,
    item?.["media:content"]?.$?.url,
    item?.["itunes:image"]?.$?.href,
  ];
  const hit = cands.find((u) => typeof u === "string" && /^https?:\/\//.test(u));
  if (hit) return hit as string;
  const html: string = item?.content || item?.["content:encoded"] || item?.contentSnippet || "";
  const m = /<img[^>]+src=["']([^"']+)["']/i.exec(html);
  return m?.[1];
};

/**
 * 解析 RSS 内容
 * @param rssContent RSS 内容
 * @returns 解析后的 RSS 内容
 */
export const parseRSS = async (rssContent: string) => {
  const parser = new RSSParser();
  // 是否为网址
  const isUrl = (url: string) => {
    try {
      new URL(url);
      return true;
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      return false;
    }
  };
  try {
    const feed = isUrl(rssContent)
      ? await parser.parseURL(rssContent)
      : await parser.parseString(rssContent);
    const items = feed.items.map((item: any) => ({
      title: item.title, // 文章标题
      link: item.link, // 文章链接
      pubDate: item.pubDate, // 发布日期
      author: item.creator ?? item.author, // 作者
      content: item.content, // 内容
      contentSnippet: item.contentSnippet, // 内容摘要
      guid: item.guid, // 全局唯一标识符
      categories: item.categories, // 分类
      cover: pickCover(item), // 封面（新增）
    }));
    // 返回解析数据
    return items;
  } catch (error) {
    logger.error("❌ [RSS] An error occurred while parsing RSS content");
    throw error;
  }
};
