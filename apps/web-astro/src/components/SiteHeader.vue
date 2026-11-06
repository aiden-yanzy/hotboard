<template>
  <header class="site-header">
    <!-- 内层与 .page 同宽同居中：logo 左边 = 文章列表左边，按钮右边 = 侧栏右边缘 -->
    <div class="header-inner">
      <a class="brand" href="/">
        <img class="brand-logo" src="/ico/favicon-192.png" :alt="SITE.name" />
        <span class="brand-text">
          <span class="brand-name">{{ SITE.name }}</span>
          <span class="brand-slogan">{{ SITE.slogan }}</span>
        </span>
      </a>

      <nav class="cats" aria-label="分类">
        <button
          v-for="c in categories"
          :key="c"
          type="button"
          class="cat"
          :class="{ on: c === curCat }"
          @click="switchCategory(c)"
        >
          {{ c }}
        </button>
      </nav>

      <!-- 右：刷新 / 主题 / 设置（纯 HTML + 内联 SVG，样式全走静态 CSS，不会闪） -->
      <div class="actions">
        <button type="button" class="icon-btn" title="刷新页面" aria-label="刷新页面" @click="refresh">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
            <path d="M8 16H3v5" />
          </svg>
        </button>

        <button
          type="button"
          class="icon-btn"
          :title="isDark ? '浅色模式' : '深色模式'"
          :aria-label="isDark ? '浅色模式' : '深色模式'"
          @click="toggleTheme"
        >
          <!-- 暗色显示太阳，亮色显示月亮 -->
          <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
          </svg>
        </button>

        <button type="button" class="icon-btn" title="设置" aria-label="设置" @click="goSetting">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import SITE from "../config/site";

const props = defineProps<{
  categories: string[];
  activeCategory?: string;
}>();

const isDark = ref(false);
// 当前分类：可局部切换，不整页跳转（跳转会重载侧栏）
const curCat = ref(props.activeCategory ?? "");

onMounted(() => {
  isDark.value = document.documentElement.classList.contains("dark");
});

function toggleTheme() {
  const dark = !isDark.value;
  isDark.value = dark;
  document.documentElement.classList.toggle("dark", dark);
  localStorage.setItem("siteTheme", dark ? "dark" : "light");
}

function refresh() {
  const url = new URL(location.href);
  url.searchParams.set("r", String(Date.now()));
  location.href = url.toString();
}

/**
 * 切换分类：优先让页面里的 HotBoard 就地拉数据（不跳转 → 侧栏不重绘）。
 *
 * ⚠️ 原来只 `pushState` + 派发事件就完事。但设置页 /setting **没有挂 HotBoard**，
 * 事件发出去没人接，URL 变了、页面纹丝不动 —— 用户点了大分类会以为「卡住了」。
 * 现在用 cancelable 事件做握手：HotBoard 收到就 preventDefault（表示已接单，走局部切换），
 * 没人接就带着分类跳到首页，行为始终有反馈。
 */
function switchCategory(c: string) {
  if (c === curCat.value) return;
  curCat.value = c;
  const url = new URL(location.href);
  url.searchParams.set("cat", c);

  const evt = new CustomEvent("hb:category", { detail: c, cancelable: true });
  // dispatchEvent 返回 false ⇔ 有人调用了 preventDefault ⇔ 页内有 HotBoard 处理了
  const handled = window.dispatchEvent(evt) === false;
  if (handled) {
    history.pushState({ cat: c }, "", url.toString());
    return;
  }
  location.href = `/?cat=${encodeURIComponent(c)}`;
}

function goSetting() {
  location.href = "/setting";
}
</script>

<style scoped lang="scss">
.site-header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: var(--n-color);
  border-bottom: 1px solid var(--n-border-color);
}

/* ⚠️ 必须和 .site-main 用同一套约束（max-width 1240 + padding 5vw），
   否则顶栏内容会比正文多缩进一截，logo 和文章列表左边缘对不齐。 */
.header-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 68px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 5vw;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}
.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 9px;
}
.brand-text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  line-height: 1.15;
}
.brand-name {
  font-size: 19px;
  font-weight: 800;
  color: var(--brand);
  letter-spacing: 0.5px;
}
.brand-slogan {
  font-size: 11px;
  color: var(--n-text-color-3);
  margin-top: 2px;
}

.cats {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  overflow-x: auto;
  scrollbar-width: none;
  &::-webkit-scrollbar {
    display: none;
  }
}
/* 顶栏分类：从 <a> 改成 <button> 后必须清掉按钮的 UA 默认样式，
   否则 font-family 不继承、背景变 buttonface、还有 2px outset 边框
   （用户反馈「怎么还把大分类的样式改了」就是这个问题） */
.cat {
  flex: 0 0 auto;
  appearance: none;
  -webkit-appearance: none;
  border: none;
  background: transparent;
  font-family: inherit;
  padding: 7px 16px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 500;
  line-height: inherit;
  text-align: center;
  cursor: pointer;
  color: var(--n-text-color-2);
  transition: all 0.15s;
  &:hover {
    color: var(--brand);
    background: var(--brand-soft);
  }
  &.on {
    color: #fff;
    background: var(--brand);
    font-weight: 600;
  }
}

.actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 圆形图标按钮：复刻原版 n-button secondary strong round 的观感 */
.icon-btn {
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--n-border-color);
  border-radius: 50%;
  background: var(--n-action-color, rgba(128, 128, 128, 0.08));
  color: var(--n-text-color-2);
  cursor: pointer;
  transition: all 0.15s;

  svg {
    width: 19px;
    height: 19px;
  }
  &:hover {
    color: var(--brand);
    border-color: var(--brand);
    background: var(--brand-soft);
  }
  &:active {
    transform: scale(0.94);
  }
}

@media (max-width: 900px) {
  .header-inner {
    height: 58px;
    gap: 10px;
    padding: 0 12px;
  }
  .brand-logo {
    width: 30px;
    height: 30px;
  }
  .brand-name {
    font-size: 16px;
  }
  .brand-slogan {
    display: none;
  }
  .cats {
    justify-content: flex-start;
    gap: 6px;
  }
  .cat {
    padding: 5px 11px;
    font-size: 13px;
  }
  .actions {
    gap: 6px;
  }
}
</style>
