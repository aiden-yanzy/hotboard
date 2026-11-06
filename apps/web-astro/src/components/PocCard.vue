<template>
  <n-card class="poc-card" :bordered="true">
    <template #header>
      <div class="poc-head">
        <span class="poc-title">{{ title }}</span>
        <n-tag size="small" round type="primary">{{ count }} 条</n-tag>
      </div>
    </template>
    <n-list hoverable clickable>
      <n-list-item v-for="(item, i) in items" :key="i">
        <template #prefix>
          <n-text class="num">{{ i + 1 }}</n-text>
        </template>
        <n-text>{{ item }}</n-text>
      </n-list-item>
    </n-list>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NTag, NList, NListItem, NText } from "naive-ui";

defineProps<{
  title: string;
  count: number;
  items: string[];
}>();
</script>

<style scoped>
.poc-card {
  margin: 12px 0;
}
.poc-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.poc-title {
  font-weight: 700;
}
.num {
  color: #999;
  min-width: 20px;
}
</style>
