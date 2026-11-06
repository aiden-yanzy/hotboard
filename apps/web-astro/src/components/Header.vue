<template>
  <n-card :bordered="false" class="header" content-style="padding: 0">
    <section>
      <div class="logo" @click="router.push('/')">
        <img src="/ico/favicon.png" alt="logo" />
        <div class="name">
          <n-text>热辣榜</n-text>
          <n-text :depth="3">汇聚全网热点，热门尽览无余</n-text>
        </div>
      </div>
      <!-- 2026-10-12：分类菜单**融合进顶部菜单栏**（与 logo 同一行，靠左跟随 logo）；日期时间先隐藏 -->
      <CategoryBar v-if="showCatNav" class="nav-slot" />
      <!-- 日期时间：先隐藏（用户要求「先隐藏日期和时间看看」）；要恢复把下面注释去掉即可
      <div class="current-time" v-if="store.timeData">
        <n-text class="time">{{ store.timeData.time.text }}</n-text>
        <n-text class="date" :depth="3">
          {{
            store.timeData.lunar.GanZhiYear +
            "年 " +
            store.timeData.lunar.text +
            " " +
            store.timeData.time.weekday
          }}
        </n-text>
      </div>
      <div class="current-time" v-else>
        <n-text class="time">时间获取中</n-text>
      </div>
      -->
      <div class="controls">
        <n-space justify="end">
          <n-popover v-if="showRefresh">
            <template #trigger>
              <n-button secondary strong round @click="router.go(0)">
                <template #icon>
                  <n-icon :component="Refresh" />
                </template>
              </n-button>
            </template>
            刷新页面
          </n-popover>
          <n-popover>
            <template #trigger>
              <n-button
                secondary
                strong
                round
                @click="
                  store.setSiteTheme(
                    store.siteTheme === 'light' ? 'dark' : 'light'
                  )
                "
              >
                <template #icon>
                  <n-icon
                    :component="store.siteTheme === 'light' ? Moon : SunOne"
                  />
                </template>
              </n-button>
            </template>
            {{ store.siteTheme === "light" ? "深色模式" : "浅色模式" }}
          </n-popover>
          <n-popover>
            <template #trigger>
              <n-button secondary strong round @click="toggleView">
                {{ isCards ? "列表" : "卡片" }}
              </n-button>
            </template>
            {{ isCards ? "切换到源列表" : "切换到卡片总览" }}
          </n-popover>
          <n-popover>
            <template #trigger>
              <n-button secondary strong round @click="router.push('/setting')">
                <template #icon>
                  <n-icon :component="SettingTwo" />
                </template>
              </n-button>
            </template>
            全局设置
          </n-popover>
        </n-space>
      </div>
      <div class="mobile">
        <n-dropdown
          :options="menuOptions"
          size="large"
          trigger="click"
          placement="bottom-end"
          @select="menuOptionsSelect"
        >
          <n-button secondary strong round>
            <template #icon>
              <n-icon :component="HamburgerButton" />
            </template>
          </n-button>
        </n-dropdown>
      </div>
    </section>
  </n-card>
</template>

<script setup>
import {
  SunOne,
  Moon,
  Refresh,
  SettingTwo,
  HamburgerButton,
} from "@icon-park/vue-next";
import { getCurrentTime } from "@/utils/getTime.js";
import { mainStore } from "@/store";
import { NText, NIcon } from "naive-ui";
import { useRouter } from "vue-router";
import CategoryBar from "@/components/CategoryBar.vue";

const router = useRouter();
const store = mainStore();
const timeInterval = ref(null);
const showRefresh = ref(false);

// 顶栏分类菜单：有分类且不在设置页时显示
const showCatNav = computed(
  () => (store.categories || []).length > 0 && router.currentRoute.value?.name !== "setting"
);

// 「卡片 ↔ 列表」一键切换（2026-10-12）
const isCards = computed(() => router.currentRoute.value?.name === "cards");
const toggleView = () => {
  if (isCards.value) {
    // 回列表：优先打开上次看的源
    router.push(
      store.lastSource ? { path: "/list", query: { type: store.lastSource } } : { path: "/" }
    );
  } else {
    router.push("/cards");
  }
};

// 移动端时间模块
const timeRender = () => {
  return h(
    "div",
    {
      style: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "6px 18px",
      },
    },
    [
      h(NText, null, {
        default: () =>
          store.timeData ? store.timeData.time.text : "时间获取失败",
      }),
      h(
        NText,
        { depth: 3, style: "font-size: 12px" },
        {
          default: () =>
            store.timeData
              ? store.timeData.lunar.GanZhiYear +
                "年 " +
                store.timeData.lunar.text +
                " " +
                store.timeData.time.weekday
              : "日期获取失败",
        }
      ),
    ]
  );
};

// 移动端菜单
const menuOptions = [
  {
    key: "header",
    type: "render",
    render: timeRender,
  },
  {
    key: "header-divider",
    type: "divider",
  },
  {
    label: "切换卡片/列表",
    key: "view",
  },
  {
    label: "刷新页面",
    key: "refresh",
    icon: () => {
      return h(NIcon, null, {
        default: () => h(Refresh),
      });
    },
  },
  {
    label: () => {
      return h(NText, null, {
        default: () => (store.siteTheme === "light" ? "深色模式" : "浅色模式"),
      });
    },
    key: "changeTheme",
    icon: () => {
      return h(NIcon, null, {
        default: () => (store.siteTheme === "light" ? h(Moon) : h(SunOne)),
      });
    },
  },
  {
    label: "全局设置",
    key: "setting",
    icon: () => {
      return h(NIcon, null, {
        default: () => h(SettingTwo),
      });
    },
  },
];

// 移动端下拉菜单点击事件
const menuOptionsSelect = (val) => {
  if (val === "refresh") {
    router.go(0);
  } else if (val === "changeTheme") {
    store.setSiteTheme(store.siteTheme === "light" ? "dark" : "light");
  } else if (val === "setting") {
    router.push("/setting");
  } else if (val === "view") {
    toggleView();
  }
};

// 监听路由参数变化
watch(
  () => router.currentRoute.value,
  (val) => {
    const isHome = val.path === "/";
    showRefresh.value = isHome ? true : false;
  }
);

onMounted(() => {
  window.$timeInterval = timeInterval.value = setInterval(() => {
    store.timeData = getCurrentTime();
  }, 1000);
  showRefresh.value = router.currentRoute.value?.path === "/" ? true : false;
});

onBeforeUnmount(() => {
  clearInterval(timeInterval.value);
});
</script>

<style lang="scss" scoped>
.header {
  // 2026-10-12：**不再用 flex 居中**（那会把 n-card 内容盒收缩居中 → 标题看着像居中）；
  // 分类菜单融合进这一行，日期时间隐藏，所以顶栏还是单行，高度由内容决定
  padding: 14px 5vw;
  z-index: 2;
  top: 0;
  background-color: transparent;
  transition: all 0.3s;
  // 滚动收缩态：行内间距收紧（高度自动收缩）
  &.show {
    padding: 9px 5vw;
  }
  section {
    width: 100%;
    // 2026-10-12：与内容列（.page 1280px）对齐，宽屏下顶栏不会"跑偏"到内容外面
    max-width: 1280px;
    margin: 0 auto;
    display: grid;
    // logo | 分类菜单（占满剩余）| 操作按钮
    grid-template-columns: auto minmax(0, 1fr) auto;
    grid-template-areas: "logo nav controls";
    align-items: center;
    column-gap: 26px;
    // 分类菜单在中间列，靠左紧贴 logo
    .nav-slot {
      grid-area: nav;
      min-width: 0;
    }
    .logo {
      grid-area: logo;
    }
    .controls {
      grid-area: controls;
    }
    .mobile {
      grid-area: mobile;
    }
    .logo {
      display: flex;
      flex-direction: row;
      align-items: center;
      cursor: pointer;
      img {
        width: 50px;
        height: 50px;
        margin-right: 16px;
        transition: all 0.3s;
      }
      .name {
        display: flex;
        flex-direction: column;
        span {
          &:nth-of-type(1) {
            font-size: 20px;
            font-weight: bold;
            transition: all 0.3s;
          }
          &:nth-of-type(2) {
            font-size: 12px;
          }
        }
      }
    }
    .current-time {
      display: flex;
      flex-direction: column;
      align-items: center;
      .date {
        font-size: 12px;
      }
    }
    .mobile {
      display: none;
    }
    @media (max-width: 768px) {
      // 窄屏：logo + 菜单按钮一行，分类菜单换到第二行（横向可滚）
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-areas:
        "logo mobile"
        "nav nav";
      column-gap: 12px;
      row-gap: 6px;
      .logo {
        img {
          width: 40px;
          height: 40px;
        }
        .name {
          span {
            &:nth-of-type(1) {
              font-size: 18px;
            }
          }
        }
      }
      .current-time,
      .controls {
        display: none;
      }
      .mobile {
        display: block;
      }
    }
  }
}
</style>
