<!-- ⚠️ 未启用（2026-10-10 用户决定回退到卡片网格，聚合视图暂缓）。
     单列表视图（含来源标记 / 按热度·各源轮转切换）；
     配套后端：hotapi 的 /agg:<分类>?limit=100&order=heat|source 。 -->
<template>
  <div class="source-list">
    <n-card class="card">
      <template #header>
        <Transition name="fade" mode="out-in">
          <template v-if="!listData">
            <div class="loading" style="height: 60px">
              <n-skeleton text round height="40px" />
            </div>
          </template>
          <template v-else>
            <div class="header">
              <div class="logo">
                <img v-if="currentLogo" :src="`/logo/${currentLogo}.png`" alt="logo" @error="hideImg" />
                <span v-else class="letter big" :style="avatarStyle(listData?.title || type)">
                  {{ initialOf(listData?.title || type) }}
                </span>
              </div>
              <div class="name">
                <n-text class="title">{{ listData.title }}</n-text>
                <n-text class="subtitle" :depth="3">{{ subtitle }}</n-text>
              </div>
              <div class="data">
                <n-text v-if="listData.total" :depth="3" class="total" v-html="listData.total" />
                <n-text :depth="3" class="time" v-html="updateTime" />
              </div>
            </div>
          </template>
        </Transition>
      </template>

      <Transition name="fade" mode="out-in">
        <template v-if="!listData">
          <div class="loading" style="flex-direction: column">
            <n-skeleton text round :repeat="16" height="40px" style="margin-bottom: 20px" />
          </div>
        </template>
        <template v-else>
          <div class="all">
            <!-- 聚合视图：排序方式切换（热度 / 各源轮转）-->
            <div class="order-bar" v-if="listData.aggregate">
              <n-radio-group :value="order" size="small" @update:value="setOrder">
                <n-radio-button value="heat">按热度</n-radio-button>
                <n-radio-button value="source">各源轮转</n-radio-button>
              </n-radio-group>
              <n-text :depth="3" class="merge-tip">
                {{ listData.sources?.length || 0 }} 个源合并 · 去重 {{ listData.raw }} → {{ listData.deduped }} 条
              </n-text>
            </div>
            <n-list hoverable clickable style="width: 100%">
              <n-list-item
                v-for="(item, index) in pageData"
                :key="item.id + '-' + index"
                @click="jumpLink(item)"
              >
                <template #prefix>
                  <n-text class="num" :class="rankClass(index)" :depth="2">
                    {{ (pageNumber - 1) * pageSize + index + 1 }}
                  </n-text>
                </template>
                <div class="text">
                  <div class="title-line">
                    <n-text class="title" v-html="item.title" />
                    <!-- 聚合视图：每条标注来源（对标 rebang） -->
                    <n-tag
                      v-if="item.sourceLabel"
                      class="from"
                      size="tiny"
                      round
                      :bordered="false"
                      @click.stop="goSource(item)"
                    >
                      {{ item.sourceLabel }}
                      <template v-if="item.alsoIn?.length"> +{{ item.alsoIn.length }}</template>
                    </n-tag>
                  </div>
                  <n-text v-if="item.desc" class="desc" :depth="3" v-html="item.desc" />
                </div>
                <div class="message">
                  <div class="hot" v-if="item.hot">
                    <n-icon :component="Fire" class="icon" />
                    <n-text class="hot-text" :depth="3">{{ formatHeat(item.hot) }}</n-text>
                  </div>
                </div>
              </n-list-item>
            </n-list>
            <n-pagination
              v-if="listData.data.length > pageSize"
              class="pagination"
              :page-slot="5"
              :item-count="listData.data.length"
              :page-sizes="[pageSize]"
              v-model:page="pageNumber"
            />
          </div>
        </template>
      </Transition>
    </n-card>
  </div>
</template>

<script setup>
import { Fire } from "@icon-park/vue-next";
import { mainStore } from "@/store";
import { formatTime } from "@/utils/getTime";
import { avatarStyle, initialOf } from "@/utils/avatar";
import { formatHeat } from "@/utils/format";
import { getHotLists } from "@/api";

const props = defineProps({
  // 源 id（zhihu）或聚合项（agg:综合）
  type: { type: String, default: "" },
});

const store = mainStore();
const pageSize = 20;
const updateTime = ref(null);
const pageNumber = ref(1);
const listData = ref(null);
const order = ref("heat");

const currentLogo = computed(() => {
  const it = store.newsArr.find((i) => i.name === props.type);
  return (it && it.logo) || null;
});

const subtitle = computed(() => {
  const d = listData.value;
  if (!d) return "";
  if (d.aggregate) return `${d.title} · ${(d.sources || []).map((s) => s.label).join(" / ")}`;
  return d.subtitle || "";
});

const pageData = computed(() => {
  const d = listData.value;
  if (!d) return [];
  return d.data.slice((pageNumber.value - 1) * pageSize, pageNumber.value * pageSize);
});

const rankClass = (index) => {
  const n = (pageNumber.value - 1) * pageSize + index + 1;
  return n === 1 ? "one" : n === 2 ? "two" : n === 3 ? "three" : null;
};

const hideImg = (e) => {
  e.target.style.display = "none";
};

const load = async () => {
  if (!props.type) return;
  listData.value = null;
  pageNumber.value = 1;
  const it = store.newsArr.find((i) => i.name === props.type);
  const params = props.type.startsWith("agg:")
    ? { limit: 100, order: order.value }
    : it?.params || {};
  const res = await getHotLists(props.type, false, params);
  if (res && res.code === 200) {
    listData.value = res;
    updateTime.value = formatTime(res.updateTime);
  } else {
    $message.error(res?.message || "该源暂无数据");
  }
};

const setOrder = (v) => {
  order.value = v;
  load();
};

// 点来源标记 → 切到那个源
const goSource = (item) => {
  const it = store.newsArr.find((i) => i.label === item.sourceLabel);
  if (it) store.setActiveSource(it.name);
};

const jumpLink = (data) => {
  if (!data.url && !data.mobileUrl) return $message.error("链接不存在");
  const url = window.innerWidth > 680 ? data.url || data.mobileUrl : data.mobileUrl || data.url;
  if (store.linkOpenType === "open") {
    window.open(url, "_blank");
  } else if (store.linkOpenType === "href") {
    window.location.href = url;
  }
};

watch(() => props.type, load);
watch(
  () => store.timeData,
  () => {
    if (listData.value) updateTime.value = formatTime(listData.value.updateTime);
  }
);

onMounted(load);
</script>

<style lang="scss" scoped>
.source-list {
  flex: 1;
  min-width: 0;
  .card {
    border-radius: 8px;
    .fade-enter-active,
    .fade-leave-active {
      transition: opacity 0.3s ease-in-out;
    }
    .fade-enter-from,
    .fade-leave-to {
      opacity: 0;
    }
    .loading {
      display: flex;
      align-items: center;
    }
    :deep(.n-card__content) {
      max-height: calc(100vh - 250px);
      overflow-y: auto;
      @media (max-width: 740px) {
        padding: 0 12px 12px 12px;
        max-height: none;
      }
    }
    .header {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      align-items: center;
      justify-content: space-between;
      height: 60px;
      .logo {
        display: flex;
        align-items: center;
        img {
          height: 46px;
          width: 46px;
          border-radius: 6px;
        }
        .letter.big {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          height: 46px;
          width: 46px;
          border-radius: 50%;
          font-size: 22px;
          line-height: 1;
        }
      }
      .name {
        display: flex;
        align-items: center;
        flex-direction: column;
        min-width: 0;
        .title {
          font-size: 20px;
          font-weight: bold;
        }
        .subtitle {
          font-size: 13px;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
      .data {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        font-size: 13px;
        .total {
          &::before {
            content: "共 ";
          }
          &::after {
            content: " 条 ·";
            margin-right: 6px;
          }
        }
      }
      @media (max-width: 740px) {
        display: flex;
        justify-content: flex-start;
        height: auto;
        .logo img {
          width: 32px;
          height: 32px;
        }
        .letter.big {
          width: 32px;
          height: 32px;
          font-size: 16px;
        }
        .name {
          margin-left: 10px;
          align-items: flex-start;
        }
        .data {
          margin-left: auto;
        }
      }
    }
    .all {
      display: flex;
      flex-direction: column;
      align-items: center;
      .order-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
        padding: 8px 0;
        border-bottom: 1px solid var(--n-border-color);
        .merge-tip {
          font-size: 12px;
        }
      }
      .num {
        width: 24px;
        height: 24px;
        min-width: 24px;
        margin-right: 8px;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--n-border-color);
        border-radius: 8px;
        &.one {
          background-color: #ea444d;
          color: #fff;
        }
        &.two {
          background-color: #ed702d;
          color: #fff;
        }
        &.three {
          background-color: #eead3f;
          color: #fff;
        }
      }
      .text {
        display: flex;
        flex-direction: column;
        min-width: 0;
        flex: 1;
        .title-line {
          display: flex;
          align-items: center;
          gap: 8px;
          .title {
            font-size: 16px;
          }
          .from {
            cursor: pointer;
            flex: 0 0 auto;
          }
        }
        .desc {
          overflow: hidden;
          font-size: 14px;
          display: -webkit-inline-box;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 3;
        }
      }
      .message {
        display: flex;
        align-items: center;
        margin-top: 12px;
        .hot {
          display: flex;
          align-items: center;
          font-size: 13px;
          .hot-text {
            margin-left: 4px;
            line-height: 0;
          }
        }
      }
      .pagination {
        margin: 20px 0;
      }
      @media (max-width: 740px) {
        :deep(.n-list-item) {
          padding: 12px 10px;
          .n-list-item__prefix {
            margin-right: 12px;
          }
        }
      }
    }
  }
}
</style>
