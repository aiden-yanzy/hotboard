<template>
  <button
    v-if="show"
    type="button"
    class="back-top"
    title="返回顶部"
    aria-label="返回顶部"
    @click="toTop"
  >
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M12 4l8 8h-5v8h-6v-8H4z" />
    </svg>
  </button>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

// 纯实现，不用 naive-ui 的 NBackTop（CSS-in-JS，要等 hydration 才注入样式）
const show = ref(false);
const THRESHOLD = 300;

function onScroll() {
  show.value = window.scrollY > THRESHOLD;
}

function toTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

onMounted(() => {
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
});

onUnmounted(() => {
  window.removeEventListener("scroll", onScroll);
});
</script>

<style scoped>
.back-top {
  position: fixed;
  right: 36px;
  bottom: 72px;
  z-index: 40;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--n-border-color, #e0e0e6);
  border-radius: 50%;
  background: var(--n-color, #fff);
  color: var(--n-text-color-2, #666);
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
  transition: all 0.18s;
}

.back-top svg {
  width: 20px;
  height: 20px;
}

.back-top:hover {
  color: var(--brand, #ff5722);
  border-color: var(--brand, #ff5722);
  transform: translateY(-2px);
}

@media (max-width: 900px) {
  .back-top {
    right: 16px;
    bottom: 56px;
    width: 40px;
    height: 40px;
  }
}
</style>
