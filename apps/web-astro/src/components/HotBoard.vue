<template>
      <div class="list" :class="isDark ? 'dark' : ''">
    <div class="page">
      <!-- ============ 主区 ============ -->
      <main class="main">
        <!-- 源 chips：可切换 + 超过一行自动折叠（原版逻辑：测量 offsetTop 判断行数） -->
        <div class="src-bar" v-if="chipsList.length">
          <div ref="chipsRef" class="type">
            <button
              v-for="item in visibleSources"
              :key="item.name"
              type="button"
              class="tag"
              :class="{ on: item.name === curSource }"
              @mouseenter="prefetchSource(item)"
              @touchstart.passive="prefetchSource(item)"
              @focus="prefetchSource(item)"
              @click="go(item)"
            >
              <img
                v-if="item.logo"
                :src="`/logo/${item.logo}.png`"
                alt=""
                class="logo"
                @error="hideImg"
              />
              <span v-else class="letter" :style="avatarStyle(item.label)">
                {{ initialOf(item.label) }}
              </span>
              <span v-if="item.followed" class="tag-star" aria-label="已关注">★</span>
              <span class="tag-label">{{ item.label }}</span>
            </button>

            <!-- 溢出提示：本身也是一个 chip，跟其他标签同一套视觉，
                 不占额外行、不遮挡内容（PatternFly 的 Overflow chip 模式） -->
            <button
              v-if="overflow"
              type="button"
              class="tag more"
              :title="expanded ? '收起数据源' : `展开全部 ${chipsList.length} 个数据源`"
              @click="toggleExpanded"
            >
              {{ expanded ? "收起 ‹" : `+${chipsList.length - visibleCount} ›` }}
            </button>
          </div>
        </div>

        <!-- 榜单卡片 -->
        <div class="card">
          <!--
            这里原来是一整块「源图标 + 名称 + 副标题 + 条数 / 更新时间 / 刷新按钮」的表头，
            手机上占了 60~90px，信息量却很低（源名在 chips 里已经高亮、条数/时间基本没人看）。
            2026-11-05 按用户要求整块移除：条数/更新时间/刷新收进上方 chips 行右侧的窄条，
            内容区直接开始列表。SEO/无障碍需要的标题用下面这行 sr-only 的 h1 保留。
          -->
          <h1 class="sr-only">{{ curTitle }}</h1>

          <!-- 知乎式单栏列表：左文字（标题/摘要/热度）+ 右侧头图 -->
          <div class="all" :class="{ 'is-loading': switching }">
            <div class="hot-list" v-if="list.length">
              <a
                v-for="(it, i) in list"
                :key="`${curSource}:${it.id || it.url || i}`"
                class="hot-item"
                :href="it.url || it.mobileUrl || '#'"
                target="_blank"
                rel="nofollow noopener"
              >
                <span
                  class="num"
                  :class="i === 0 ? 'one' : i === 1 ? 'two' : i === 2 ? 'three' : ''"
                >{{ i + 1 }}</span>
                <div class="row">
                  <div class="text">
                    <span class="title" v-html="cleanHtml(it.title)"></span>
                    <!-- 无摘要时占一行高度，避免卡片高矮不齐（注释必须在 v-if 之前，插在 v-if/v-else 中间会让 v-else 失效） -->
                    <span v-if="it.desc" class="desc" v-html="cleanHtml(stripHash(it.desc))"></span>
                    <div v-else class="desc-empty" aria-hidden="true"></div>
                    <div class="hot" v-if="it.hot">
                      <FlameIcon :size="14" />
                      <span class="hot-text">{{ fmtHot(it.hot) }}</span>
                    </div>
                  </div>
                  <!-- 头图：加载成功才淡入，失败整块移除 -->
                  <div class="thumb" v-if="it.cover && !failedCovers[it.id || '']">
                    <img
                      :src="it.cover"
                      alt=""
                      width="88"
                      height="66"
                      loading="lazy"
                      decoding="async"
                      fetchpriority="low"
                      referrerpolicy="no-referrer"
                      :class="{ in: loadedCovers[it.id || ''] }"
                      @load="loadedCovers[it.id || ''] = true"
                      @error="failedCovers[it.id || ''] = true"
                    />
                  </div>
                </div>
              </a>
            </div>
            <div v-else class="loading">
              {{ curTitle }}榜单暂时没有拉到数据，稍后会自动更新。
            </div>
            <div class="end-tip" v-if="list.length">
              已经到底啦 · 共 {{ list.length }} 条
            </div>
          </div>
        </div>
      </main>

      <!-- ============ 右侧栏 ============ -->
      <aside class="side">
        <!-- 图片广告 -->
        <div class="blk ad" v-if="ad">
          <span class="ad-flag">广告</span>
          <a :href="ad.url" target="_blank" rel="nofollow noopener" :class="{ 'has-img': ad.img }">
            <span class="ad-media" v-if="ad.img">
              <img class="ad-img" :src="ad.img" :alt="ad.alt || '广告'" />
            </span>
            <template v-else>{{ ad.text }}</template>
          </a>
        </div>
        <!-- 热点推荐（飙升榜）：右上角「换一批」 -->
        <div class="blk">
          <div class="blk-title">
            <span>📈 热点推荐</span>
            <button
              type="button"
              class="swap"
              :class="{ loading: risingLoading }"
              @click="swapRising"
            >
              <svg
                class="swap-ico"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                <path d="M21 3v5h-5" />
                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                <path d="M8 16H3v5" />
              </svg>
              {{ risingLoading ? "加载中" : "换一批" }}
            </button>
          </div>
          <div class="rising" v-if="risingList.length">
            <a
              v-for="(it, i) in risingList"
              :key="it.id || i"
              class="rising-item"
              :href="it.url || it.mobileUrl || '#'"
              target="_blank"
              rel="nofollow noopener"
            >
              <span class="rk">{{ i + 1 }}.</span>
              <span class="tt">{{ it.title }}</span>
            </a>
          </div>
          <div v-else class="rising-empty">{{ risingLoading ? "加载中…" : "暂无数据" }}</div>
        </div>

        <!-- 友情链接 -->
        <div class="blk" v-if="links.length">
          <div class="blk-title"><span>🔗 友情链接</span></div>
          <div class="links">
            <a v-for="l in links" :key="l.url" :href="l.url" target="_blank" rel="nofollow noopener">
              {{ l.name }}
            </a>
          </div>
        </div>

        <!-- 版权 / 备案：信息在 src/config/site.ts 里配置，留空则整块不渲染 -->
        <div class="blk beian" v-if="icp?.text || police?.text">
          <div class="blk-title"><span>© {{ year }} {{ SITE.name }}</span></div>
          <a
            v-if="icp?.text"
            :href="icp.url"
            target="_blank"
            rel="noreferrer noopener"
          >{{ icp.text }}</a>
          <a
            v-if="police?.text"
            :href="police.url"
            target="_blank"
            rel="noreferrer noopener"
          >{{ police.text }}</a>
          <p class="tip">本站聚合公开热点信息，内容版权归原平台所有。</p>
        </div>
        </aside>
      </div>
      </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import FlameIcon from "./FlameIcon.vue";
import SITE from "../config/site";

interface SrcItem {
  name: string;
  label: string;
  logo?: string;
  href: string;
}
interface HotItem {
  id?: string;
  title: string;
  desc?: string;
  cover?: string;
  hot?: number;
  url?: string;
  mobileUrl?: string;
}

const props = defineProps<{
  sources: SrcItem[];
  activeSource: string;
  title: string;
  subtitle?: string;
  currentLogo?: string;
  items: HotItem[];
  risingItems?: HotItem[];
  ad?: { text?: string; url: string; img?: string; alt?: string } | null;
  links?: { name: string; url: string }[];
  /** 备案信息由页面传入（客户端不直接读 SITE，否则 hydration 后会消失） */
  icp?: { text: string; url: string };
  police?: { text: string; url: string };
  updateTime?: string;
  /** 服务端按 User-Agent 判定的移动端标记：手机上首屏就只渲染 3 个源标签，
      避免依赖 hydration 时机（实测会抖：有时 6 个、有时 3 个）。 */
  mobile?: boolean;
}>();

// ── 当前源（可切换，不整页跳转）──
// 这些原来直接用 props，切源必须靠页面跳转；改成 ref 后可以 AJAX 局部替换，
// 侧栏（广告/热点推荐/友情链接）完全不受影响，主区也不会闪。
// 源 chips 列表也要可变：切大分类时整批换掉
const chipsList = ref<SrcItem[]>(props.sources ?? []);

const curSource = ref(props.activeSource);
const curTitle = ref(props.title);
const curSubtitle = ref(props.subtitle ?? "");
const curLogo = ref(props.currentLogo ?? "");
const switching = ref(false);
// 请求序号：连点多个源时，只认最后一次的结果（旧响应回来直接丢弃）
let reqSeq = 0;
// 图标加载失败 → 退回文字头像（只隐藏 <img> 会留空白）
const logoFailed = ref(false);

/**
 * 切源预取：鼠标悬停在 chip 上就先偷偷把数据取回来。
 * 实测点击到 DOM 更新本来只要 25~60ms，但「点了没反应」的体感仍在，
 * 悬停预取后点击基本是 0 延迟。
 */
const prefetchCache = new Map<string, any>();
// key → 正在飞的请求。
// 原来只记「有没有在预取」，点击时如果预取还没回来就**再发一次**同样的请求，
// 手机上等于双倍流量（实测能把冷切 380ms 拖到 1.4s）。现在点击直接 await 同一个 Promise。
const inflight = new Map<string, Promise<any>>();

function prefetchSource(item: SrcItem) {
  const key = item.name;
  if (!key || prefetchCache.has(key) || inflight.has(key)) return;
  const p = fetch(`/api/board?source=${encodeURIComponent(key)}&r=${Date.now()}`)
    .then((r) => r.json())
    .then((d) => {
      if (d?.ok) prefetchCache.set(key, { ...d, __at: Date.now() });
      return d;
    })
    .catch(() => null)
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, p);
}

/** 取榜单：预取结果 > 在飞的预取 > 自己发请求，三档兜底，绝不重复下载 */
async function fetchBoard(name: string): Promise<any> {
  const cached = prefetchCache.get(name);
  prefetchCache.delete(name); // 用过就丢掉，避免拿到过期数据
  // 预取结果超过 60 秒就不用了（榜单 30 分钟才更新，60s 是保守值）
  if (cached && Date.now() - (cached.__at || 0) <= 60_000) return cached;

  const pending = inflight.get(name);
  if (pending) {
    const d = await pending;
    if (d?.ok) return d;
  }
  const res = await fetch(`/api/board?source=${encodeURIComponent(name)}&r=${Date.now()}`);
  return res.json();
}

const refreshing = ref(false);
let refreshTimer: number | null = null;
let themeObserver: MutationObserver | null = null;
let sideObserver: ResizeObserver | null = null;

// 列表数据：直接用 props 初始化，保证 SSR 输出的 HTML 里就有完整列表（SEO 关键）。
// 点「刷新」时再用 /api/board 局部替换，不整页跳转。
const list = ref<HotItem[]>(props.items ?? []);
const updateLabel = ref<string>(props.updateTime ?? "");

// 侧栏「热点推荐」：同样用 props 初始化，保证 SSR 有内容；点「换一批」时走 /api/rising 代理
const risingList = ref<HotItem[]>(props.risingItems ?? []);
const risingLoading = ref(false);
let risingOffset = 0;
const year = new Date().getFullYear();

// 头图加载状态（原版行为：加载成功才淡入，失败整块移除）
const loadedCovers = reactive<Record<string, boolean>>({});
const failedCovers = reactive<Record<string, boolean>>({});
// 顶层直接读（hydration 时 <head> 里的 inline script 已经给 <html> 加好 dark 类）
const isDark = ref(
  typeof document !== "undefined" && document.documentElement.classList.contains("dark")
);

// ── 源 chips 折叠：原版逻辑，测量实际行数而不是猜数量 ──
const chipsRef = ref<any>(null);
// 展开状态持久化：切换源走 location.href 会重建组件，ref 会被重置成 false，
// 用户明明展开过、切个源又折叠回去了。存 localStorage 恢复。
// 折叠时最多显示多少个源标签。SSR 阶段就用这个固定值渲染前 8 个，
// 保证首屏 HTML 已经是折叠态（不依赖 JS 量行数 → 不会「先全展开再收起来」）。
const VISIBLE_COUNT = 6;

// 手机上少显示几个：7 个标签在 375px 宽度下会折 3 行、占掉 126px（超过 1/6 屏高）。
// SSR 阶段仍按 6 渲染（保证首屏就是折叠态），hydration 后再按视口收窄。
const narrow = ref(props.mobile === true);
const visibleLimit = computed(() => (narrow.value ? 3 : VISIBLE_COUNT));

const EXPAND_KEY = "hotboard.srcExpanded";
const expanded = ref(
  typeof localStorage !== "undefined" && localStorage.getItem(EXPAND_KEY) === "1"
);

// 折叠态只渲染前 N 个；展开态全部
const visibleSources = computed(() =>
  expanded.value ? chipsList.value : chipsList.value.slice(0, visibleLimit.value)
);

// 是否需要「+N」提示：源数量超过可见数
const overflow = computed(() => chipsList.value.length > visibleLimit.value);

// 折叠态下「+N」里的 N
const visibleCount = visibleLimit;

// ⚠️ 改成「+N chip」方案后，不再需要测量行数：
// 折叠 = 只渲染前 VISIBLE_COUNT 个，展开 = 全部。布局由数据量决定，天然不会有第二行。

/**
 * 展开/折叠：直接操作 DOM class，不用模板 :class 绑定。
 * 实测这个组件的 :class 响应式在 Astro hydration 后不更新 class
 * （CSS 完全正常：手动 classList.add('expanded') 立刻生效），
 * 所以跟暗色主题一样走「直接改 DOM」这条路，稳。
 */
function applyExpanded(v: boolean) {
  expanded.value = v;
  const el = document.querySelector(".src-bar .type");
  if (el) el.classList.toggle("expanded", v);
  try {
    localStorage.setItem("hotboard.srcExpanded", v ? "1" : "0");
  } catch {}
}

function toggleExpanded() {
  applyExpanded(!expanded.value);
}


onMounted(async () => {
  // 视口宽度 → 手机上少显示几个数据源标签（与 CSS 的 740px 断点保持一致）
  const syncNarrow = () => {
    narrow.value = window.innerWidth <= 740;
  };
  syncNarrow();
  window.addEventListener("resize", syncNarrow, { passive: true });

  // 恢复展开状态：SSR 时读不到 localStorage（expanded 初始化为 false），
  // hydration 又复用服务端状态，所以必须在这里主动读一次。
  try {
    applyExpanded(localStorage.getItem("hotboard.srcExpanded") === "1");
  } catch {}

  // 初始状态 + 跟随 <html class="dark">（顶栏切换时通过 MutationObserver 同步）
  themeObserver = new MutationObserver(() => {
    // 只同步主题；不要在这里重置 risingList（否则每次换主题「换一批」结果都会被打回）
    isDark.value = document.documentElement.classList.contains("dark");
  });
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  await nextTick();
  updateSideTop();
  tuneClamp();
  
  window.addEventListener("resize", updateSideTop);
  window.addEventListener("popstate", onPopState);
  window.addEventListener("hb:category", onCatEvent as EventListener);

  // 侧栏高度会变（广告图加载完、「换一批」换内容、字体回流）→ 用 ResizeObserver 自动重算，
  // 否则 --side-top 停在旧值，吸附位置就偏了
  const sideEl = document.querySelector(".list .side");
  if (sideEl) {
    sideObserver = new ResizeObserver(() => updateSideTop());
    sideObserver.observe(sideEl);
  }

  // 自动刷新（设置页可配，默认关闭）
  const min = Number(localStorage.getItem("hotboard.autoRefresh") || 0);
  if (min > 0) {
    refreshTimer = window.setInterval(() => refresh(), min * 60_000);
  }
});

onUnmounted(() => {
  themeObserver?.disconnect();
  sideObserver?.disconnect();
  
  window.removeEventListener("resize", updateSideTop);
  window.removeEventListener("popstate", onPopState);
  window.removeEventListener("hb:category", onCatEvent as EventListener);
  if (refreshTimer) window.clearInterval(refreshTimer);
});

// 服务端重新渲染（切换源）时同步列表
watch(
  () => props.items,
  (v) => {
    list.value = v ?? [];
    updateLabel.value = props.updateTime ?? "";
  }
);

// 源数量变化 → 回到折叠态并重新测量
// 源数量变化 → 重新测量是否超出一行（但不要重置 expanded！
// 之前这里写了 expanded.value = false，导致用户展开过、切个源又折叠回去）
watch(
  () => `${curSource.value}|${chipsList.value.length}`,
  async () => {
  }
);

/** 换一批热点推荐 */
async function swapRising() {
  if (risingLoading.value) return;
  risingLoading.value = true;
  try {
    const res = await fetch(`/api/rising?limit=${risingList.value.length || 8}&offset=${risingOffset}`);
    const data = await res.json();
    if (Array.isArray(data?.items) && data.items.length) {
      risingList.value = data.items;
      risingOffset = data.nextOffset ?? 0;
      await nextTick();
      updateSideTop(); // 内容高度变了，重新算吸附位置
    }
  } catch {
    /* 失败就保持原列表 */
  } finally {
    risingLoading.value = false;
  }
}

/**
 * 参考知乎的做法：标题最多 2 行，摘要按标题实际行数决定给几行。
 *   标题 2 行 → 摘要 1 行（CSS 默认就是 1 行，不动）
 *   标题 1 行 → 摘要 2 行（加 .desc-2 放开）
 * 只用 class 切换，不写 inline style：inline 的 display/flex 会破坏 line-clamp 的裁剪。
 */
function tuneClamp() {
  document.querySelectorAll<HTMLElement>(".hot-item").forEach((it) => {
    const title = it.querySelector<HTMLElement>(".title");
    const desc = it.querySelector<HTMLElement>(".desc");
    if (!title || !desc) return;
    const lh = parseFloat(getComputedStyle(title).lineHeight) || 24;
    const titleLines = Math.round(title.offsetHeight / lh);
    desc.classList.toggle("desc-2", titleLines < 2);
  });
}

/**
 * 计算右侧栏的 sticky 吸附位置（原版逻辑）：
 *   ① 侧栏装得下视口 → top 固定 80px：跟着页面滚，滚到顶栏下方就钉住；
 *   ② 侧栏比视口高   → top = 视口高 - 侧栏高 - 24（可为负）：跟到**底边**贴住视口底部才钉住。
 * 不做这一步，侧栏就一直钉死在 80px，页面往下滚时它一动不动。
 */
function updateSideTop() {
  const el = document.querySelector(".list .side") as HTMLElement | null;
  if (!el) return;
  const h = el.offsetHeight;
  const vh = window.innerHeight;
  const top = h > vh - 120 ? vh - h - 24 : 80;
  el.style.setProperty("--side-top", `${top}px`);
}

/** 切换源（原版 changeType 的等价实现：Astro 里用真实跳转） */
/**
 * 切换数据源：拉新数据 + 改 URL，**不整页跳转**。
 * 整页跳转会重载侧栏（用户会看到广告/热点推荐跟着「刷新」一下），主区也会闪。
 */
async function go(item: SrcItem) {
  if (item.name === curSource.value) return;
  // ⚠️ 原来这里还有 `|| switching.value` → 加载期间点别的源会被静默吃掉，
  //    用户看到的就是「点了没反应 / 列表没及时换」。改成序号制：允许连点，只认最后一次。
  const seq = ++reqSeq;

  curSource.value = item.name;
  curTitle.value = item.name;
  curSubtitle.value = "实时热榜 · 每 30 分钟更新";
  curLogo.value = item.logo ?? "";
  logoFailed.value = false;
  history.pushState({ source: item.name }, "", item.href);

  switching.value = true;
  try {
    const data = await fetchBoard(item.name);
    if (seq !== reqSeq) return; // 期间用户又点了别的源 → 本次结果作废
    if (data?.ok) {
      list.value = data.items ?? [];
      if (data.name) curTitle.value = data.name;
      updateLabel.value = data.updateTime
        ? new Date(data.updateTime).toTimeString().slice(0, 8)
        : "";
      // 缩略图状态要重置，否则上一批的失败记录会误伤新条目
      for (const k of Object.keys(failedCovers)) delete failedCovers[k];
      for (const k of Object.keys(loadedCovers)) delete loadedCovers[k];
      await nextTick();
      tuneClamp();
      updateSideTop();
    }
  } catch {
    /* 失败保持当前内容 */
  } finally {
    if (seq === reqSeq) switching.value = false;
  }
}

/** 事件包装：CustomEvent 的 detail 取出分类名 */
function onCatEvent(e: Event) {
  const cat = (e as CustomEvent<string>).detail;
  if (typeof cat !== "string" || !cat) return;
  // 标记「本页已处理」，SiteHeader 据此决定是否还需要跳首页。
  // （设置页没有 HotBoard，事件没人接 → SiteHeader 会带着 ?cat= 跳首页）
  e.preventDefault();
  onCategorySwitch(cat);
}

/**
 * 切大分类：拉新分类的源 + 第一个源的榜单，就地替换。
 * 不动侧栏（广告/热点推荐/友链），避免用户看到「右侧也刷新了」。
 */
async function onCategorySwitch(cat: string) {
  const seq = ++reqSeq; // 同 go()：允许连点，只认最后一次
  switching.value = true;
  try {
    const res = await fetch(`/api/category?cat=${encodeURIComponent(cat)}&r=${Date.now()}`);
    const data = await res.json();
    if (seq !== reqSeq) return;
    if (!data?.ok) return;

    chipsList.value = data.sources ?? [];
    expanded.value = false;
    applyExpanded(false);

    const b = data.board;
    if (b) {
      curSource.value = b.name ?? data.firstName ?? "";
      curTitle.value = b.name ?? data.firstName ?? "";
      curSubtitle.value = b.name ? "实时热榜 · 每 30 分钟更新" : "";
      const hit = (data.sources ?? []).find((x: SrcItem) => x.name === curSource.value);
      curLogo.value = hit?.logo ?? "";
      logoFailed.value = false;
      list.value = b.items ?? [];
      updateLabel.value = b.updateTime
        ? new Date(b.updateTime).toTimeString().slice(0, 8)
        : "";
      for (const k of Object.keys(failedCovers)) delete failedCovers[k];
      for (const k of Object.keys(loadedCovers)) delete loadedCovers[k];
    }
    await nextTick();
    tuneClamp();
    updateSideTop();
  } catch {
    /* 失败保持当前内容 */
  } finally {
    if (seq === reqSeq) switching.value = false;
  }
}

/** 浏览器前进/后退：把 URL 对应的源切回来 */
async function onPopState() {
  const path = decodeURIComponent(location.pathname.replace(/^\//, ""));
  const hit = chipsList.value.find((x) => x.name === path);
  if (hit && hit.name !== curSource.value) {
    curSource.value = "";
    await go(hit);
  }
}

/** 打开条目（原版 jumpLink 的等价实现） */
function openLink(it: HotItem) {
  const url = it.url || it.mobileUrl;
  if (!url) return;
  window.open(url, "_blank", "noopener");
}

// 刷新：带 buster 重新请求（绕过 SSR / 后端缓存）
/**
 * 刷新：走 /api/board 局部替换数据，**不整页跳转**。
 * 整页跳转会让浏览器重新解析 HTML/CSS，naive-ui 的 CSS-in-JS 要等 hydration 才注入样式，
 * 观感就是「先闪一下裸样式再变回来」。局部刷新完全避免这个问题。
 */
async function refresh() {
  if (refreshing.value) return;
  refreshing.value = true;
  try {
    const src = curSource.value || curTitle.value;
    const res = await fetch(`/api/board?source=${encodeURIComponent(src)}&r=${Date.now()}`);
    const data = await res.json();
    if (data?.ok && Array.isArray(data.items)) {
      list.value = data.items;
      if (data.updateTime) {
        updateLabel.value = new Date(data.updateTime).toTimeString().slice(0, 8);
      }
      // 列表换了内容，缩略图的已加载/已失败状态要清掉，否则会误伤新条目
      for (const k of Object.keys(failedCovers)) delete failedCovers[k];
      for (const k of Object.keys(loadedCovers)) delete loadedCovers[k];
      await nextTick();
      updateSideTop();
      tuneClamp();
    }
  } catch {
    /* 网络失败就保持原列表 */
  } finally {
    refreshing.value = false;
  }
}

function hideImg(e: Event) {
  (e.target as HTMLElement).style.display = "none";
}

function initialOf(s: string) {
  return (s || "?").trim().slice(0, 1);
}

/** 按名称生成稳定的头像底色 */
function avatarStyle(s: string) {
  let h = 0;
  for (const ch of s || "") h = (h * 31 + ch.charCodeAt(0)) % 360;
  return { background: `hsl(${h}, 62%, 52%)` };
}

/** 微博/知乎的摘要常带 #话题# 包裹，去掉井号更干净 */
/**
 * 清理文本：
 * ① 去掉首尾的 # 号（部分源会把话题标签带进来）
 * ② 去掉末尾的省略号 —— 数字尾巴这类源在 API 层就把文本截断了
 *    （标题固定 27 字、摘要 31 字，末尾自带 "..."），
 *    我们再套一层 -webkit-line-clamp 就会变成 "......"，视觉上很脏。
 *    清掉后交给 CSS 统一控制省略号。
 */
function stripHash(s: string) {
  return (s || "")
    .replace(/^[#＃]+|[#＃]+$/g, "")
    .replace(/(\.{2,}|。{3,}|…+)\s*$/, "")
    .trim();
}

/** title/desc 走 v-html，末尾省略号要连同可能的闭合标签一起处理 */
function cleanHtml(s: string) {
  if (!s) return "";
  return s
    .replace(/(\.{2,}|…+)(\s*)(<\/[a-z][^>]*>)?\s*$/, (_m, _dots, _sp, close) => close || "")
    .trim();
}

function fmtHot(n?: number) {
  if (!n) return "";
  if (n >= 100000000) return `${(n / 100000000).toFixed(1)}亿`;
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
  return String(n);
}
</script>
