// @ts-check
import { defineConfig } from "astro/config";
import vue from "@astrojs/vue";
import node from "@astrojs/node";

// SSR 模式：榜单在服务端渲染成真 HTML，爬虫（尤其百度）无需执行 JS 即可读到内容。
// 本地用 6610（6700 被 api 占用，6600 是现有 SPA）。
export default defineConfig({
  integrations: [vue()],
  output: "server",
  adapter: node({ mode: "standalone" }),
  server: { port: 6610, host: true },
  site: "https://example.com",
});
