<template>
  <!-- 实心火苗：橙红纯色 + 发光滤镜。
       ⚠️ 不要用 <linearGradient> + 动态 id：
       SSR 时 Math.random() 生成的 id 与客户端 hydration 的不一致，
       会造成 hydration mismatch，整个 SVG 被 Vue 丢弃（列表里火苗就"消失"了）。 -->
  <svg
    class="flame"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <path
      fill="#ff6a00"
      d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"
    />
  </svg>
</template>

<script setup>
defineProps({ size: { type: [Number, String], default: 14 } });
</script>

<style scoped>
.flame {
  display: inline-block;
  vertical-align: -0.125em;
  /* 发光：让火苗亮起来（纯色也够用） */
  filter: drop-shadow(0 0 3px rgba(255, 96, 0, 0.6));
}
</style>
