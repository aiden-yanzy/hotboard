<template>
  <div class="setting-page">
    <h1>设置</h1>
    <p class="sub">这些偏好只保存在本机浏览器，不会上传。</p>

    <!-- 1. 外观 -->
    <section class="blk">
      <div class="blk-title">🎨 外观</div>
      <div class="row">
        <label>主题</label>
        <div class="seg">
          <button
            v-for="t in themeOpts"
            :key="t.v"
            :class="{ on: theme === t.v }"
            @click="setTheme(t.v)"
          >
            {{ t.label }}
          </button>
        </div>
      </div>
      <div class="row">
        <label>自动刷新</label>
        <div class="seg">
          <button
            v-for="r in refreshOpts"
            :key="r"
            :class="{ on: autoRefresh === r }"
            @click="setAutoRefresh(r)"
          >
            {{ r === 0 ? "关闭" : `${r} 分钟` }}
          </button>
        </div>
      </div>
    </section>

    <!-- 2. 数据源显隐 + 排序 -->
    <section class="blk">
      <div class="blk-title">
        <span>📚 数据源</span>
        <span class="hint">共 {{ total }} 个 · 已显示 {{ shownCount }} 个</span>
      </div>

      <div v-for="(list, cat) in grouped" :key="cat" class="cat-group">
        <div class="cat-head">
          <span class="cat-name">{{ cat }}</span>
          <button class="mini" @click="toggleCat(cat)">全选/反选</button>
        </div>
        <div class="src-list">
          <div
            v-for="s in list"
            :key="s.name"
            class="src-item"
            :class="{ off: !s.show, dragging: dragName === s.name, over: overName === s.name }"
            draggable="true"
            @dragstart="onDragStart($event, s.name)"
            @dragenter.prevent="overName = s.name"
            @dragover.prevent
            @drop.prevent="onDrop(s.name)"
            @dragend="onDragEnd"
          >
            <span class="grip" title="拖动排序">⠿</span>
            <button
              type="button"
              class="star"
              :class="{ on: isFollowed(s.name) }"
              :title="isFollowed(s.name) ? '取消关注' : '关注（关注的源会在榜单页置顶）'"
              @click="toggleFollow(s.name)"
            >{{ isFollowed(s.name) ? "★" : "☆" }}</button>
            <label class="chk">
              <input type="checkbox" :checked="s.show" @change="toggleShow(s.name)" />
              <span class="name">{{ s.label }}</span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. 恢复默认 -->
    <section class="blk">
      <div class="blk-title">↺ 重置</div>
      <p class="tip">清空本机的显隐、排序、主题、刷新设置。</p>
      <button class="danger" @click="reset">恢复默认设置</button>
    </section>

    <p class="back"><a href="/">← 返回榜单</a></p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

interface SrcItem {
  name: string;
  label: string;
  category: string;
}
interface Pref {
  show?: boolean;
  order?: number;
}

const props = defineProps<{ sources: SrcItem[] }>();

const KEY_PREFS = "hotboard.sourcePrefs";
/* 关注的源：localStorage 为主存储；
   同时镜像写一个 cookie，让 Astro 服务端渲染 chips 时就能按「关注在前」排好，
   否则客户端 hydration 后重排会让首屏闪一下。 */
const KEY_FOLLOW = "hotboard.followed";
const COOKIE_FOLLOW = "hb_followed";
const KEY_THEME = "siteTheme";
const KEY_REFRESH = "hotboard.autoRefresh";

const prefs = ref<Record<string, Pref>>({});
const followed = ref<string[]>([]);
const theme = ref<"light" | "dark" | "auto">("auto");
const autoRefresh = ref(0);

const themeOpts = [
  { v: "light" as const, label: "亮色" },
  { v: "dark" as const, label: "暗色" },
  { v: "auto" as const, label: "跟随系统" },
];
const refreshOpts = [0, 1, 5, 10, 30];

onMounted(() => {
  try {
    prefs.value = JSON.parse(localStorage.getItem(KEY_PREFS) || "{}");
  } catch {
    prefs.value = {};
  }
  const savedTheme = localStorage.getItem(KEY_THEME);
  theme.value = savedTheme === "dark" ? "dark" : savedTheme === "light" ? "light" : "auto";
  autoRefresh.value = Number(localStorage.getItem(KEY_REFRESH) || 0);
  try {
    followed.value = JSON.parse(localStorage.getItem(KEY_FOLLOW) || "[]");
  } catch {
    followed.value = [];
  }
});

function isFollowed(name: string) {
  return followed.value.includes(name);
}

function toggleFollow(name: string) {
  followed.value = isFollowed(name)
    ? followed.value.filter((n) => n !== name)
    : [...followed.value, name];
  localStorage.setItem(KEY_FOLLOW, JSON.stringify(followed.value));
  // 镜像到 cookie（30 天），供服务端渲染排序用
  const v = encodeURIComponent(JSON.stringify(followed.value));
  document.cookie = `${COOKIE_FOLLOW}=${v}; path=/; max-age=${30 * 86400}; SameSite=Lax`;
}

function persist() {
  localStorage.setItem(KEY_PREFS, JSON.stringify(prefs.value));
}

// 按分类分组 + 应用 show/order
const normalized = computed(() => {
  const list = props.sources.map((s, i) => {
    const p = prefs.value[s.name] || {};
    return {
      ...s,
      show: p.show !== undefined ? p.show : true,
      order: p.order !== undefined ? p.order : i,
    };
  });
  return list.sort((a, b) => a.order - b.order);
});

const grouped = computed(() => {
  const g: Record<string, typeof normalized.value> = {};
  for (const s of normalized.value) {
    (g[s.category] ||= []).push(s);
  }
  return g;
});

const total = computed(() => props.sources.length);
const shownCount = computed(() => normalized.value.filter((s) => s.show).length);

function toggleShow(name: string) {
  const cur = prefs.value[name]?.show;
  setPref(name, { show: cur === false ? true : false });
}

function toggleCat(cat: string) {
  const list = grouped.value[cat] || [];
  const allOn = list.every((s) => s.show);
  for (const s of list) setPref(s.name, { show: !allOn });
}

function setPref(name: string, patch: Pref) {
  prefs.value = { ...prefs.value, [name]: { ...(prefs.value[name] || {}), ...patch } };
  persist();
}

/* ── 拖动排序 ──────────────────────────────────────────
   原来只有 ↑↓ 按钮，用户要求改成拖动式。
   拖拽只在同一分类内生效（不同分类各自排序，跨组拖动没有语义）。 */
const dragName = ref<string | null>(null);
const overName = ref<string | null>(null);

function onDragStart(e: DragEvent, name: string) {
  dragName.value = name;
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", name); // Firefox 必须要 setData 才触发拖拽
  }
}

function onDragEnd() {
  dragName.value = null;
  overName.value = null;
}

/** 把拖动的源插到目标位置，然后按新顺序重排该分类的 order */
function onDrop(targetName: string) {
  const from = dragName.value;
  onDragEnd();
  if (!from || from === targetName) return;

  const cur = normalized.value.find((s) => s.name === from);
  const tgt = normalized.value.find((s) => s.name === targetName);
  if (!cur || !tgt || cur.category !== tgt.category) return; // 跨分类不处理

  const sameCat = normalized.value
    .filter((s) => s.category === cur.category)
    .map((s) => s.name);
  const fromIdx = sameCat.indexOf(from);
  const toIdx = sameCat.indexOf(targetName);
  if (fromIdx < 0 || toIdx < 0) return;

  sameCat.splice(toIdx, 0, sameCat.splice(fromIdx, 1)[0]);

  // 该分类当前的 order 值排好序，按新顺序重新分配（保持与其它分类不冲突）
  const orders = normalized.value
    .filter((s) => s.category === cur.category)
    .map((s) => s.order)
    .sort((a, b) => a - b);
  const patch: Record<string, Pref> = {};
  sameCat.forEach((name, i) => {
    patch[name] = { ...(prefs.value[name] || {}), order: orders[i] };
  });
  prefs.value = { ...prefs.value, ...patch };
  persist();
}

/** 上下移动：只在同分类内交换 order（保留旧接口，拖动之外的键盘用户可用） */
function move(name: string, delta: number) {
  const cur = normalized.value.find((s) => s.name === name);
  if (!cur) return;
  const sameCat = normalized.value.filter((s) => s.category === cur.category);
  const idx = sameCat.findIndex((s) => s.name === name);
  const target = sameCat[idx + delta];
  if (!target) return;
  const a = cur.order;
  const b = target.order;
  setPref(cur.name, { order: b });
  setPref(target.name, { order: a });
}

function setTheme(v: "light" | "dark" | "auto") {
  theme.value = v;
  if (v === "auto") {
    localStorage.removeItem(KEY_THEME);
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
  } else {
    localStorage.setItem(KEY_THEME, v);
    document.documentElement.classList.toggle("dark", v === "dark");
  }
}

function setAutoRefresh(min: number) {
  autoRefresh.value = min;
  localStorage.setItem(KEY_REFRESH, String(min));
}

function reset() {
  if (!confirm("确定清空本机所有设置吗？")) return;
  localStorage.removeItem(KEY_PREFS);
  localStorage.removeItem(KEY_FOLLOW);
  followed.value = [];
  document.cookie = `${COOKIE_FOLLOW}=; path=/; max-age=0`;
  localStorage.removeItem(KEY_REFRESH);
  localStorage.removeItem(KEY_THEME);
  prefs.value = {};
  autoRefresh.value = 0;
  theme.value = "auto";
  document.documentElement.classList.remove("dark");
}
</script>

<style scoped lang="scss">
.setting-page {
  max-width: 860px;
  margin: 0 auto;
}
h1 {
  font-size: 22px;
  margin: 6px 0 4px;
}
.sub {
  color: var(--n-text-color-3);
  font-size: 13px;
  margin-bottom: 18px;
}
.blk {
  border: 1px solid var(--n-border-color);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--n-action-color);
  margin-bottom: 16px;
  font-size: 13px;
}
.blk-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 700;
  font-size: 14px;
  margin: -2px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--n-border-color);
  .hint {
    font-weight: 400;
    font-size: 12px;
    color: var(--n-text-color-3);
  }
}
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 7px 0;
  > label {
    flex: 0 0 76px;
    color: var(--n-text-color-2);
  }
}
.seg {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  button {
    padding: 5px 13px;
    border: 1px solid var(--n-border-color);
    border-radius: 999px;
    background: var(--n-color);
    color: var(--n-text-color-2);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s;
    &:hover {
      border-color: var(--brand);
      color: var(--brand);
    }
    &.on {
      background: var(--brand);
      border-color: var(--brand);
      color: #fff;
      font-weight: 600;
    }
  }
}
.cat-group {
  margin-bottom: 14px;
}
.cat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 8px;
  .cat-name {
    font-weight: 600;
    font-size: 13px;
    color: var(--n-text-color-2);
  }
}
.src-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 6px;
}
.src-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 5px 8px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color);
  &.off {
    opacity: 0.45;
  }
}
.chk {
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
  input {
    accent-color: var(--brand);
    cursor: pointer;
  }
  .name {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
/* 关注星标 */
.star {
  flex: 0 0 auto;
  border: none;
  background: transparent;
  padding: 0 2px;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  color: var(--n-text-color-3);
  transition: all 0.15s;
  &:hover {
    color: #f5a623;
    transform: scale(1.15);
  }
  &.on {
    color: #f5a623;
  }
}
/* 拖动手柄 */
.grip {
  color: var(--n-text-color-3);
  cursor: grab;
  font-size: 12px;
  line-height: 1;
  flex: 0 0 auto;
  user-select: none;
  opacity: 0.5;
  &:hover {
    opacity: 1;
    color: var(--brand);
  }
}
/* 拖动中的源 */
.src-item.dragging {
  opacity: 0.4;
}
/* 拖动经过的目标位置：用顶部高亮条提示会插到这里 */
.src-item.over {
  border-color: var(--brand);
  box-shadow: inset 3px 0 0 var(--brand);
}
.ops {
  display: flex;
  gap: 2px;
}
.mini {
  border: 1px solid var(--n-border-color);
  background: var(--n-color);
  color: var(--n-text-color-3);
  border-radius: 5px;
  font-size: 11px;
  padding: 1px 6px;
  cursor: pointer;
  line-height: 1.6;
  &:hover {
    color: var(--brand);
    border-color: var(--brand);
  }
}
.tip {
  margin: 0 0 10px;
  color: var(--n-text-color-3);
  font-size: 12px;
}
.danger {
  padding: 6px 16px;
  border: 1px solid #e5484d;
  background: transparent;
  color: #e5484d;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  &:hover {
    background: #e5484d;
    color: #fff;
  }
}
.back {
  margin-top: 20px;
  a {
    color: var(--brand);
    font-size: 14px;
  }
}
</style>
