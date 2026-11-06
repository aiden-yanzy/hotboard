import { defineStore } from "pinia";

// ─────────────────────────────────────────────────────────────────────────────
// SSR 安全垫：服务端没有 window / localStorage，naive-ui 的 $message 也不存在。
// 用 no-op 实现顶上，这样同一份 store 在服务端渲染和客户端 hydrate 都能跑。
// ─────────────────────────────────────────────────────────────────────────────
const hasWindow = typeof window !== "undefined";
const LS =
  hasWindow && window.localStorage
    ? window.localStorage
    : { getItem: () => null, setItem: () => {}, removeItem: () => {} };

/** 全局提示（服务端静默，客户端转到 naive-ui 的 message） */
const toast = (text) => {
  if (!hasWindow) return;
  const m = globalThis.$message;
  if (m && typeof m.success === "function") m.success(text);
};

export const mainStore = defineStore("mainData", {
  state: () => {
    return {
      // 系统主题
      siteTheme: "light",
      siteThemeAuto: true,
      // 新闻类别
      defaultNewsArr: [
        {
          label: "哔哩哔哩",
          name: "bilibili",
          order: 0,
          show: true,
        },
        {
          label: "微博",
          name: "weibo",
          order: 1,
          show: true,
        },
        {
          label: "抖音",
          name: "douyin",
          order: 2,
          show: true,
        },
        {
          label: "知乎",
          name: "zhihu",
          order: 3,
          show: true,
        },
        {
          label: "36氪",
          name: "36kr",
          order: 4,
          show: true,
        },
        {
          label: "百度",
          name: "baidu",
          order: 5,
          show: true,
        },
        {
          label: "少数派",
          name: "sspai",
          order: 6,
          show: true,
        },
        {
          label: "IT之家",
          name: "ithome",
          order: 7,
          show: true,
        },
        {
          label: "澎湃新闻",
          name: "thepaper",
          order: 8,
          show: true,
        },
        {
          label: "今日头条",
          name: "toutiao",
          order: 9,
          show: true,
        },
        {
          label: "百度贴吧",
          name: "tieba",
          order: 10,
          show: true,
        },
        {
          label: "稀土掘金",
          name: "juejin",
          order: 11,
          show: true,
        },
        {
          label: "腾讯新闻",
          name: "qq-news",
          order: 12,
          show: true,
        },
        {
          label: "豆瓣电影",
          name: "douban-movie",
          order: 13,
          show: true,
        },
        {
          label: "原神",
          name: "genshin",
          order: 14,
          show: true,
        },
        {
          label: "崩坏：星穹铁道",
          name: "starrail",
          order: 16,
          show: true,
        },
        {
          label: "LOL",
          name: "lol",
          order: 15,
          show: true,
        },
        {
          label: "网易新闻",
          name: "netease-news",
          order: 17,
          show: true,
        },
        {
          label: "微信读书",
          name: "weread",
          order: 18,
          show: true,
        },
        {
          label: "豆瓣讨论小组",
          name: "douban-group",
          order: 19,
          show: true,
        },
        {
          label: "NGA",
          name: "ngabbs",
          order: 20,
          show: true,
        },
        {
          label: "HelloGitHub",
          name: "hellogithub",
          order: 21,
          show: true,
        },
        {
          label: "简书",
          name: "jianshu",
          order: 22,
          show: true,
        },
        {
          label: "知乎日报",
          name: "zhihu-daily",
          order: 23,
          show: true,
        },
      ],
      newsArr: [],
      // 链接跳转方式
      linkOpenType: "open",
      // 页头固定
      headerFixed: true,
      // 时间数据
      timeData: null,
      // 字体大小
      listFontSize: 16,
      // 卡片每行个数（3 或 4；设置页可改）
      gridCols: 4,
      // 启动页：「list」= 源详情页（默认，用户要求进站直达详情页）/「cards」= 卡片总览
      startPage: "list",
      // 上次看的源 → 详情页默认打开它
      lastSource: "",
      // —— 自建扩展：源清单与分类（来自 hotboard-api，见 actions.loadSources）——
      categories: [],
      activeCategory: "", // 2026-10-12：移除「全部」→ 载入分类后默认第一个（综合）
      // 分类聚合项（对标 rebang：综合→全站、科技→热榜科技…，每分类置顶且默认选中）
      aggregates: [],
      // 右侧列表当前展示的源（源 id 或聚合项 agg:分类）
      activeSource: "",
      sourcesLoaded: false,
      // 用户对「源」的个人配置（**独立持久化**，与源清单解耦，拉新源不会冲掉）：
      //   { [源id]: { show?: boolean, followed?: boolean, order?: number } }
      sourcePrefs: {},
    };
  },
  getters: {
    // 关注（收藏）的源
    followedSources(state) {
      return state.newsArr.filter((it) => it.followed);
    },
    followedCount(state) {
      return state.newsArr.filter((it) => it.followed).length;
    },
    // 当前分类下要展示的源（"⭐ 关注"= 只看关注的；其余按分类）
    visibleSources(state) {
      const cat = state.activeCategory;
      return state.newsArr.filter((item) => {
        if (!item.show) return false;
        if (!cat) return true; // 分类还没载入 → 先全显示
        if (cat === "⭐ 关注") return !!item.followed;
        // 失效分类（如历史遗留的「全部」）→ 不过滤，避免空白页
        if (!state.categories.includes(cat)) return true;
        return item.category === cat;
      });
    },
    // 左栏分组：每个分类一组，**组内第一项是该分类的聚合项**（置顶）；另加「⭐ 关注」组
    sidebarGroups(state) {
      const groups = [];
      const fav = state.newsArr.filter((i) => i.followed && i.show !== false);
      if (fav.length) {
        groups.push({
          category: `⭐ 关注 (${fav.length})`,
          sources: fav.map((f) => ({ name: f.name, label: f.label, logo: f.logo })),
        });
      }
      for (const a of state.aggregates || []) {
        const members = state.newsArr.filter(
          (i) => i.category === a.category && i.show !== false
        );
        if (!members.length) continue;
        groups.push({
          category: a.category,
          sources: [
            {
              name: a.name,
              label: a.label,
              category: a.category,
              aggregate: true,
              count: members.length,
            },
            ...members.map((m) => ({
              name: m.name,
              label: m.label,
              logo: m.logo,
              category: m.category,
            })),
          ],
        });
      }
      // 兜底：接口没给聚合项时，按分类直接从源清单分组
      if (!groups.length) {
        const byCat = {};
        for (const s of state.newsArr) {
          if (s.show === false) continue;
          (byCat[s.category || "其他"] = byCat[s.category || "其他"] || []).push({
            name: s.name,
            label: s.label,
            logo: s.logo,
          });
        }
        for (const c of Object.keys(byCat)) groups.push({ category: c, sources: byCat[c] });
      }
      return groups;
    },
  },
  actions: {
    // 从 hotboard-api 拉源清单（含分类）；失败则回退到内置 defaultNewsArr
    async loadSources() {
      try {
        const res = await fetch(`${import.meta.env.VITE_GLOBAL_API}/sources`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const list = (data.sources || []).filter((s) => s.display !== false);
        if (!list.length) throw new Error("空清单");
        this.categories = data.categories || [...new Set(list.map((s) => s.category))];
        // 先按接口顺序给个基准 order，再套用用户配置（个人的排序/显隐/关注都在 sourcePrefs 里）
        const prefs = this.sourcePrefs || {};
        this.newsArr = list
          .map((s, i) => {
            const p = prefs[s.name] || {};
            return {
              label: s.label, // 中文名
              name: s.name, // hotboard-api 的源 id（前端请求路径）
              logo: s.key, // /logo/<key>.png 图标（老源才有图）
              category: s.category || "其他",
              engine: s.engine,
              show: p.show !== undefined ? p.show : true,
              followed: !!p.followed,
              order: p.order !== undefined ? p.order : 1000 + i, // 用户排过的在前，新源自动排后面
            };
          })
          .sort((a, b) => a.order - b.order);
        this.sourcesLoaded = true;
        this.aggregates = data.aggregates || [];
        // 右侧默认选中：上次选过的（若仍存在）→ 否则**第一个分类的聚合项**（对标 rebang）
        const valid = new Set([
          ...this.aggregates.map((a) => a.name),
          ...this.newsArr.map((s) => s.name),
        ]);
        const preferred = this.activeSource || LS.getItem("activeSource") || "";
        this.activeSource =
          preferred && valid.has(preferred)
            ? preferred
            : this.aggregates[0]?.name || this.newsArr[0]?.name || "";
        const saved = LS.getItem("activeCategory");
        // 2026-10-12：不再有「全部」；默认落到第一个分类（综合）
        this.activeCategory =
          saved && (saved === "⭐ 关注" || this.categories.includes(saved))
            ? saved
            : this.categories[0] || "";
        console.log(`源清单已从 hotboard-api 载入：${this.newsArr.length} 个源，分类 ${this.categories.join("/")}`);
        return true;
      } catch (e) {
        console.warn("源清单拉取失败，回退到内置清单", e);
        this.sourcesLoaded = false;
        return false;
      }
    },
    setCategory(cat) {
      this.activeCategory = cat;
      LS.setItem("activeCategory", cat);
    },
    // 选中右侧要看的源/聚合项
    setActiveSource(name) {
      this.activeSource = name;
      LS.setItem("activeSource", name);
    },
    // 记住「上次看的源」→ 启动页为详情页时默认打开它
    setLastSource(name) {
      if (name && name !== this.lastSource) this.lastSource = name;
    },
    // —— 源的个人配置（关注 / 显隐 / 排序）统一写进 sourcePrefs，再回写到 newsArr ——
    setPref(name, patch) {
      const old = this.sourcePrefs[name] || {};
      this.sourcePrefs = { ...this.sourcePrefs, [name]: { ...old, ...patch } };
      const it = this.newsArr.find((i) => i.name === name);
      if (it) Object.assign(it, patch);
      if (patch.order !== undefined) {
        this.newsArr = [...this.newsArr].sort((a, b) => a.order - b.order);
      }
    },
    toggleFollow(name) {
      const it = this.newsArr.find((i) => i.name === name);
      const next = !(it && it.followed);
      this.setPref(name, { followed: next });
      toast(next ? `已关注「${it ? it.label : name}」` : `已取消关注「${it ? it.label : name}」`);
    },
    setShow(name, val) {
      this.setPref(name, { show: val });
    },
    // 设置页拖拽结束后调用：按新顺序整体写回 order
    setOrder(names) {
      const patch = {};
      names.forEach((n, i) => {
        patch[n] = { ...(this.sourcePrefs[n] || {}), order: i };
      });
      this.sourcePrefs = { ...this.sourcePrefs, ...patch };
      this.newsArr = [...this.newsArr].sort(
        (a, b) => (this.sourcePrefs[a.name]?.order ?? 9999) - (this.sourcePrefs[b.name]?.order ?? 9999)
      );
      toast("排序已保存");
    },
    // 恢复默认：清空个人配置（关注/显隐/排序都回到接口默认）
    resetPrefs() {
      this.sourcePrefs = {};
      this.loadSources();
      toast("已恢复默认（关注/显隐/排序）");
    },
    // 更改系统主题（2026-10-12：去掉切换时的 $message 提示 —— 每次切主题都弹一条通知是多余的）
    setSiteTheme(val) {
      this.siteTheme = val;
      this.siteThemeAuto = false;
    },
    // 检查更新
    checkNewsUpdate() {
      const mainData = JSON.parse(LS.getItem("mainData"));
      let updatedNum = 0;
      if (!mainData) return false;
      console.log("列表尝试更新", this.defaultNewsArr, this.newsArr);
      // 执行比较并迁移
      if (this.newsArr.length > 0) {
        for (const newItem of this.defaultNewsArr) {
          const exists = this.newsArr.some(
            (news) => newItem.label === news.label && newItem.name === news.name
          );
          if (!exists) {
            console.log("列表有更新：", newItem);
            updatedNum++;
            this.newsArr.push(newItem);
          }
        }
        if (updatedNum) toast(`成功更新 ${updatedNum} 个榜单数据`);
      } else {
        console.log("列表无内容，写入默认");
        this.newsArr = this.defaultNewsArr;
      }
    },
  },
  persist: [
    {
      storage: LS,
      paths: [
        "siteTheme",
        "siteThemeAuto",
        "newsArr",
        "sourcePrefs",
        "linkOpenType",
        "headerFixed",
        "listFontSize",
        "gridCols",
        "startPage",
        "lastSource",
      ],
    },
  ],
});
