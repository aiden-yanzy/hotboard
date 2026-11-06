<template>
  <nav class="cat-nav" v-if="cats.length">
    <!-- 2026-10-12：内层 max-content + margin:auto = 有空间时**居中**，溢出时自动退化为左对齐可横滑 -->
    <div class="inner">
      <span
        v-for="c in cats"
        :key="c"
        class="item"
        :class="{ on: isActive(c) }"
        @click="pick(c)"
      >
        {{ c }}
      </span>
    </div>
  </nav>
</template>

<script setup>
import { computed } from "vue";
import { mainStore } from "@/store";

const store = mainStore();

// 2026-10-12：**移除「全部」分类**（用户要求）→ 只剩「⭐ 关注」+ 六个分类（综合/科技/娱乐/开发/社区/购物）
const cats = computed(() => [
  store.followedCount ? `⭐ 关注 (${store.followedCount})` : "⭐ 关注",
  ...(store.categories || []),
]);
// 点击时把带数量的显示值还原成内部值
const pick = (c) => store.setCategory(c.startsWith("⭐ 关注") ? "⭐ 关注" : c);
const isActive = (c) =>
  c.startsWith("⭐ 关注") ? store.activeCategory === "⭐ 关注" : store.activeCategory === c;
</script>

<style lang="scss" scoped>
// 2026-10-12：分类从「内容区大号标签」改成**顶部菜单**（对标 rebang 顶部菜单），
// 与下面的「源 chips」拉开层级：菜单 15px + 下划线高亮 / 源 chips 12px 小胶囊
.cat-nav {
  // 2026-10-12：内联在顶栏里用（图标 | 标题 | 分类 | 功能菜单），横向可滚、不换行
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  overflow-x: auto;
  white-space: nowrap;
  scrollbar-width: none;
  &::-webkit-scrollbar {
    display: none;
  }
  // 居中：内层 max-content + margin auto（溢出时 auto 退化为 0，不会把左侧内容藏掉）
  .inner {
    display: flex;
    align-items: center;
    gap: 30px; // 2026-10-12：间距加大
    width: max-content;
    margin: 0 auto;
    // 2026-10-12：整体**视觉左移**。右内边距会被算进 max-content 宽度，
    // 居中后文字块自然偏左 ~48px（60px 内边距 ≈ 左移 30px，按用户要求又加 20px）；用 padding 而不是 transform：
    //   transform 在 overflow-x 容器里会把左边缘裁掉，padding 只是加宽，横滑时依旧安全
    padding: 0 200px 0 4px;
  }
  .item {
    flex: 0 0 auto;
    font-size: 18px; // 2026-10-12：字号加大
    line-height: 38px;
    cursor: pointer;
    opacity: 0.7;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
    user-select: none;
    &:hover {
      opacity: 1;
    }
    &.on {
      opacity: 1;
      font-weight: 700;
      color: var(--primary-color, #2080f0);
      border-bottom-color: var(--primary-color, #2080f0);
    }
  }
}
</style>
